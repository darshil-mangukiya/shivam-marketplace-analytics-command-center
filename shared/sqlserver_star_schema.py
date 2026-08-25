"""Flat-mart -> SQL Server-compatible star-schema transformation.

Reshapes the privacy-safe public marts produced by
`shared/public_output_builder.py` into the dimensional tables defined in
`sql/sqlserver/02_create_dimensions.sql` / `03_create_facts.sql`. This
module uses pandas and has no database connection dependency.
`shared/sqlserver_loader.py` is the separate
layer that opens a connection and loads these DataFrames.

`product_performance.csv` (the source of `dim_product` and
`fact_product_performance`) carries **no** `transaction_month` column — it
is aggregated across the whole dataset period, not per month — so
`fact_product_performance` is intentionally grain (product, marketplace)
only, with `dataset_period` carried as a plain attribute rather than a
fabricated `dim_month` foreign key.

Surrogate key strategy
-----------------------
Keys are deterministic, not random: for each dimension, the distinct
natural-key values are sorted ascending and assigned consecutive integers
starting at 1. The same source data therefore always produces the same
keys across repeated runs (a requirement for reproducible reconciliation
and for tests that assert exact key values). Key `0` is reserved on every
dimension for a single synthetic "Unknown" row, used whenever a fact row's
natural key cannot be resolved against the dimension — this guarantees no
fact row is ever silently dropped for a missing/unmapped dimension value
(see `_resolve_key` below).
"""

from __future__ import annotations

import dataclasses

import pandas as pd

UNKNOWN_KEY = 0
UNKNOWN_LABEL = "Unknown"

RECONCILIATION_COLUMNS = [
    "source_name",
    "source_rows",
    "target_table",
    "target_rows",
    "difference",
    "status",
    "notes",
]


# ---------------------------------------------------------------------------
# Surrogate key helpers
# ---------------------------------------------------------------------------


def _deterministic_keys(natural_key_values: list[str]) -> dict[str, int]:
    """Sorted-natural-key -> consecutive integer (starting at 1). Never a
    random UUID, so the same input always produces the same mapping."""
    ordered = sorted({str(v) for v in natural_key_values if pd.notna(v) and str(v).strip()})
    return {value: index + 1 for index, value in enumerate(ordered)}


def _resolve_key(value: object, key_map: dict[str, int]) -> int:
    """Look up a natural-key value's surrogate key, falling back to
    UNKNOWN_KEY (never dropping the row or raising) when the value is
    missing or wasn't part of the dimension build (Requirement 14/16)."""
    if pd.isna(value):
        return UNKNOWN_KEY
    return key_map.get(str(value), UNKNOWN_KEY)


# ---------------------------------------------------------------------------
# Dimension builders
# ---------------------------------------------------------------------------

_DIM_PRODUCT_ATTR_COLUMNS = [
    "brand_group",
    "category_group",
    "subcategory_group",
    "product_group",
    "listing_price_band",
    "inventory_band",
    "margin_band_public",
    "profitability_band_public",
]


def build_dim_product(product_performance: pd.DataFrame) -> pd.DataFrame:
    """One row per public_product_id (Requirement: dim_product grain).

    Only ever reads `public_product_id` and grouped/banded public
    attribute columns — never a real SKU, ASIN, seller SKU, listing ID,
    private title/description, or raw financial value (none of those
    columns exist on `product_performance.csv` in the first place; this is
    stated explicitly so a future column addition to the source can't
    silently leak through this function unnoticed).
    """
    if product_performance.empty or "public_product_id" not in product_performance.columns:
        columns = ["product_key", "public_product_id", *_DIM_PRODUCT_ATTR_COLUMNS]
        return pd.DataFrame(columns=columns)

    forbidden = {"seller_sku", "asin1", "asin", "sku", "order_id", "listing_id", "item_name", "item_description"}
    present_forbidden = forbidden & set(product_performance.columns)
    if present_forbidden:
        raise ValueError(
            f"product_performance frame unexpectedly contains private column(s) {sorted(present_forbidden)}; "
            "refusing to build dim_product from it."
        )

    ids = product_performance["public_product_id"].dropna().astype(str)
    key_map = _deterministic_keys(ids.tolist())

    # One representative row per product: sort for determinism, then keep
    # the first occurrence's attribute values (attributes are expected to
    # be stable per product across marketplace rows; if they ever
    # differ, the first-sorted row is a deterministic,
    # reproducible choice rather than an arbitrary one).
    attr_cols = [c for c in _DIM_PRODUCT_ATTR_COLUMNS if c in product_performance.columns]
    dedup = (
        product_performance[["public_product_id", *attr_cols]]
        .dropna(subset=["public_product_id"])
        .assign(public_product_id=lambda d: d["public_product_id"].astype(str))
        .sort_values(["public_product_id", *attr_cols])
        .drop_duplicates(subset=["public_product_id"], keep="first")
        .reset_index(drop=True)
    )
    dedup["product_key"] = dedup["public_product_id"].map(key_map)
    for col in _DIM_PRODUCT_ATTR_COLUMNS:
        if col not in dedup.columns:
            dedup[col] = UNKNOWN_LABEL

    unknown_row = {"product_key": UNKNOWN_KEY, "public_product_id": UNKNOWN_LABEL}
    unknown_row.update({col: UNKNOWN_LABEL for col in _DIM_PRODUCT_ATTR_COLUMNS})

    result = pd.concat([pd.DataFrame([unknown_row]), dedup], ignore_index=True)
    return result[["product_key", "public_product_id", *_DIM_PRODUCT_ATTR_COLUMNS]]


def build_dim_marketplace(*frames: pd.DataFrame) -> pd.DataFrame:
    """One row per distinct marketplace value seen across any of the given
    frames. `channel` is carried as a constant 'Marketplace' attribute —
    this warehouse does not model a validated sub-channel grain (the
    Marketplace_Channel_Master mapping keys remain incomplete; see
    docs/business_rules.md, rule BR-05 / channel_mapping_status =
    "Unavailable"). No channel-level coverage is claimed here."""
    values: list[str] = []
    for frame in frames:
        if isinstance(frame, pd.DataFrame) and "marketplace" in frame.columns:
            values.extend(frame["marketplace"].dropna().astype(str).tolist())

    key_map = _deterministic_keys(values)
    rows = [{"marketplace_key": UNKNOWN_KEY, "marketplace": UNKNOWN_LABEL, "channel": "Marketplace"}]
    rows.extend({"marketplace_key": key, "marketplace": name, "channel": "Marketplace"} for name, key in key_map.items())
    return pd.DataFrame(rows).sort_values("marketplace_key").reset_index(drop=True)


_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _parse_month_attributes(transaction_month: str) -> dict[str, object]:
    """Parse a "YYYY-MM" label into deterministic calendar attributes.
    Never invents a date beyond what the label itself encodes."""
    try:
        year_str, month_str = transaction_month.split("-", 1)
        year = int(year_str)
        month_number = int(month_str)
        if not (1 <= month_number <= 12):
            raise ValueError
    except (ValueError, AttributeError):
        return {"year": None, "month_number": None, "month_name": UNKNOWN_LABEL, "quarter": None, "year_month": transaction_month}
    return {
        "year": year,
        "month_number": month_number,
        "month_name": _MONTH_NAMES[month_number - 1],
        "quarter": (month_number - 1) // 3 + 1,
        "year_month": transaction_month,
    }


def build_dim_month(*frames: pd.DataFrame, dataset_period: str | None = None) -> pd.DataFrame:
    """One row per distinct `transaction_month` value seen across any of
    the given frames (typically `marketplace_summary`). Only months
    actually present in the source data are included — no calendar range
    is invented beyond the observed periods."""
    values: list[str] = []
    for frame in frames:
        if isinstance(frame, pd.DataFrame) and "transaction_month" in frame.columns:
            values.extend(frame["transaction_month"].dropna().astype(str).tolist())

    key_map = _deterministic_keys([v for v in values if v.strip().lower() not in {"", "unknown", "nan"}])

    unknown_row = {
        "month_key": UNKNOWN_KEY,
        "transaction_month": UNKNOWN_LABEL,
        "year": None,
        "month_number": None,
        "month_name": UNKNOWN_LABEL,
        "quarter": None,
        "year_month": UNKNOWN_LABEL,
        "dataset_period": dataset_period,
    }
    rows = [unknown_row]
    for month_label, key in key_map.items():
        row = {"month_key": key, "transaction_month": month_label, "dataset_period": dataset_period}
        row.update(_parse_month_attributes(month_label))
        rows.append(row)
    return pd.DataFrame(rows).sort_values("month_key").reset_index(drop=True)


def build_dim_fulfillment(*frames: pd.DataFrame) -> pd.DataFrame:
    """One row per distinct `fulfillment_type` value seen across any of
    the given frames."""
    values: list[str] = []
    for frame in frames:
        if isinstance(frame, pd.DataFrame) and "fulfillment_type" in frame.columns:
            values.extend(frame["fulfillment_type"].dropna().astype(str).tolist())

    key_map = _deterministic_keys(values)
    rows = [{"fulfillment_key": UNKNOWN_KEY, "fulfillment_type": UNKNOWN_LABEL}]
    rows.extend({"fulfillment_key": key, "fulfillment_type": name} for name, key in key_map.items())
    return pd.DataFrame(rows).sort_values("fulfillment_key").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Fact builders
# ---------------------------------------------------------------------------


def build_fact_marketplace_activity(
    marketplace_summary: pd.DataFrame, dim_month: pd.DataFrame, dim_marketplace: pd.DataFrame
) -> pd.DataFrame:
    """Grain: (month_key, marketplace_key) — sourced 1:1 from
    marketplace_summary.csv, which carries transaction_month."""
    columns = [
        "fact_key", "month_key", "marketplace_key", "total_orders", "product_count",
        "sales_index", "units_index", "avg_fee_pct_of_gross", "avg_refund_pct_of_gross",
        "avg_promotion_pct_of_gross", "avg_net_to_gross_pct", "margin_risk_score", "revenue_quality_score",
    ]
    if marketplace_summary.empty:
        return pd.DataFrame(columns=columns)

    month_key_map = dict(zip(dim_month["transaction_month"], dim_month["month_key"]))
    marketplace_key_map = dict(zip(dim_marketplace["marketplace"], dim_marketplace["marketplace_key"]))

    out = marketplace_summary.copy()
    out["month_key"] = out["transaction_month"].map(lambda v: _resolve_key(v, month_key_map))
    out["marketplace_key"] = out["marketplace"].map(lambda v: _resolve_key(v, marketplace_key_map))
    out = out.rename(columns={"total_orders": "total_orders", "product_count": "product_count"})
    for col in [
        "total_orders", "product_count", "sales_index", "units_index", "avg_fee_pct_of_gross",
        "avg_refund_pct_of_gross", "avg_promotion_pct_of_gross", "avg_net_to_gross_pct",
        "margin_risk_score", "revenue_quality_score",
    ]:
        if col not in out.columns:
            out[col] = None
    out = out.sort_values(["month_key", "marketplace_key"]).reset_index(drop=True)
    out["fact_key"] = out.index + 1
    return out[columns]


def build_fact_product_performance(
    product_performance: pd.DataFrame, dim_product: pd.DataFrame, dim_marketplace: pd.DataFrame,
    *, dataset_period: str | None = None,
) -> pd.DataFrame:
    """Grain: (product_key, marketplace_key) — sourced 1:1 from
    product_performance.csv. No month FK: the source is not month-grained
    (see module docstring)."""
    columns = [
        "fact_key", "product_key", "marketplace_key", "dataset_period", "sales_index", "units_index",
        "fee_pct_of_gross", "refund_pct_of_gross", "promotion_pct_of_gross", "net_to_gross_pct",
        "margin_index", "estimated_profitability_index", "margin_risk_score", "revenue_quality_score",
        "recommended_action", "action_priority",
    ]
    if product_performance.empty:
        return pd.DataFrame(columns=columns)

    product_key_map = dict(zip(dim_product["public_product_id"], dim_product["product_key"]))
    marketplace_key_map = dict(zip(dim_marketplace["marketplace"], dim_marketplace["marketplace_key"]))

    out = product_performance.copy()
    out["product_key"] = out["public_product_id"].map(lambda v: _resolve_key(v, product_key_map))
    out["marketplace_key"] = out["marketplace"].map(lambda v: _resolve_key(v, marketplace_key_map))
    out["dataset_period"] = dataset_period
    for col in [
        "sales_index", "units_index", "fee_pct_of_gross", "refund_pct_of_gross", "promotion_pct_of_gross",
        "net_to_gross_pct", "margin_index", "estimated_profitability_index", "margin_risk_score",
        "revenue_quality_score", "recommended_action", "action_priority",
    ]:
        if col not in out.columns:
            out[col] = None
    out = out.sort_values(["product_key", "marketplace_key"]).reset_index(drop=True)
    out["fact_key"] = out.index + 1
    return out[columns]


def build_fact_inventory_action(
    inventory_action_review: pd.DataFrame, dim_product: pd.DataFrame, dim_marketplace: pd.DataFrame
) -> pd.DataFrame:
    """Grain: (product_key, marketplace_key) — sourced 1:1 from
    inventory_action_review.csv."""
    columns = [
        "fact_key", "product_key", "marketplace_key", "units_index", "sales_index",
        "restock_priority", "recommended_action", "action_priority",
    ]
    if inventory_action_review.empty:
        return pd.DataFrame(columns=columns)

    product_key_map = dict(zip(dim_product["public_product_id"], dim_product["product_key"]))
    marketplace_key_map = dict(zip(dim_marketplace["marketplace"], dim_marketplace["marketplace_key"]))

    out = inventory_action_review.copy()
    out["product_key"] = out["public_product_id"].map(lambda v: _resolve_key(v, product_key_map))
    out["marketplace_key"] = out["marketplace"].map(lambda v: _resolve_key(v, marketplace_key_map))
    for col in ["units_index", "sales_index", "restock_priority", "recommended_action", "action_priority"]:
        if col not in out.columns:
            out[col] = None
    out = out.sort_values(["product_key", "marketplace_key"]).reset_index(drop=True)
    out["fact_key"] = out.index + 1
    return out[columns]


def build_fact_performance_variance(
    mart_marketplace_variance_drivers: pd.DataFrame,
    mart_performance_driver_summary: pd.DataFrame,
    dim_month: pd.DataFrame,
    dim_marketplace: pd.DataFrame,
) -> pd.DataFrame:
    """Grain: (previous_month_key, current_month_key, marketplace_key,
    metric). The previous/current period labels are not columns on
    mart_marketplace_variance_drivers.csv itself — they are the single
    comparison pair recorded on mart_performance_driver_summary.csv, which
    this function reads and joins in. Returns an empty (correctly-schema'd)
    frame when the dataset had fewer than two valid activity periods — no
    comparison is fabricated (BR-16), matching the Python variance engine's
    own behavior in shared/variance_engine.py.
    """
    columns = [
        "fact_key", "previous_month_key", "current_month_key", "marketplace_key", "metric",
        "previous_value", "current_value", "abs_variance", "pct_variance", "contribution_share_pct", "movement",
    ]
    if mart_marketplace_variance_drivers.empty or mart_performance_driver_summary.empty:
        return pd.DataFrame(columns=columns)

    summary_row = mart_performance_driver_summary.iloc[0]
    previous_period = summary_row.get("previous_period")
    current_period = summary_row.get("current_period")
    if not previous_period or not current_period or previous_period == "n/a" or current_period == "n/a":
        return pd.DataFrame(columns=columns)

    month_key_map = dict(zip(dim_month["transaction_month"], dim_month["month_key"]))
    marketplace_key_map = dict(zip(dim_marketplace["marketplace"], dim_marketplace["marketplace_key"]))

    out = mart_marketplace_variance_drivers.copy()
    out["previous_month_key"] = _resolve_key(previous_period, month_key_map)
    out["current_month_key"] = _resolve_key(current_period, month_key_map)
    out["marketplace_key"] = out["marketplace"].map(lambda v: _resolve_key(v, marketplace_key_map))
    for col in ["previous_value", "current_value", "abs_variance", "pct_variance", "contribution_share_pct", "movement"]:
        if col not in out.columns:
            out[col] = None
    out = out.sort_values(["marketplace_key", "metric"]).reset_index(drop=True)
    out["fact_key"] = out.index + 1
    return out[columns]


def build_audit_validation(validation_summary: pd.DataFrame) -> pd.DataFrame:
    """1:1 copy of validation_summary.csv with a deterministic audit_key."""
    columns = ["audit_key", "check_name", "check_status", "check_value", "expected_value", "notes"]
    if validation_summary.empty:
        return pd.DataFrame(columns=columns)
    out = validation_summary.copy().reset_index(drop=True)
    for col in ["check_name", "check_status", "check_value", "expected_value", "notes"]:
        if col not in out.columns:
            out[col] = None
    out["audit_key"] = out.index + 1
    return out[columns]


def build_audit_dataset_profile(dataset_profile: pd.DataFrame) -> pd.DataFrame:
    """1:1 copy of dataset_profile.csv with a deterministic audit_key."""
    columns = ["audit_key", "public_output_name", "row_count", "dataset_period", "dataset_label"]
    if dataset_profile.empty:
        return pd.DataFrame(columns=columns)
    out = dataset_profile.copy().reset_index(drop=True)
    for col in ["public_output_name", "row_count", "dataset_period", "dataset_label"]:
        if col not in out.columns:
            out[col] = None
    out["audit_key"] = out.index + 1
    return out[columns]


# ---------------------------------------------------------------------------
# Validation helpers (Requirement 15/16)
# ---------------------------------------------------------------------------


def assert_dimension_uniqueness(dim: pd.DataFrame, natural_key_cols: list[str], *, dim_name: str) -> None:
    """Raise ValueError if a dimension's natural key is not unique."""
    if dim.empty:
        return
    duplicated = dim.duplicated(subset=natural_key_cols, keep=False)
    if duplicated.any():
        bad = dim.loc[duplicated, natural_key_cols].drop_duplicates()
        raise ValueError(f"{dim_name} violates natural-key uniqueness on {natural_key_cols}: {bad.to_dict('records')}")


def assert_fact_foreign_keys(fact: pd.DataFrame, key_col: str, dim: pd.DataFrame, dim_key_col: str, *, fact_name: str) -> None:
    """Raise ValueError if a fact table references a surrogate key that
    does not exist in the referenced dimension (an orphan foreign key)."""
    if fact.empty:
        return
    valid_keys = set(dim[dim_key_col].tolist())
    orphans = set(fact[key_col].tolist()) - valid_keys
    if orphans:
        raise ValueError(f"{fact_name}.{key_col} references unknown key(s) not present in the dimension: {sorted(orphans)}")


def build_reconciliation_report(
    source_frames: dict[str, pd.DataFrame], star_schema: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """Source-mart-row-count vs star-schema-fact-row-count, one row per
    fact table (Requirement 17)."""
    checks = [
        ("marketplace_summary", "fact_marketplace_activity", "1:1 load — no aggregation or dedup expected"),
        ("product_performance", "fact_product_performance", "1:1 load — no aggregation or dedup expected"),
        ("inventory_action_review", "fact_inventory_action", "1:1 load — no aggregation or dedup expected"),
        (
            "mart_marketplace_variance_drivers",
            "fact_performance_variance",
            "1:1 load when >=2 valid activity periods exist; both 0 when insufficient periods (BR-16 — no fabricated comparison)",
        ),
        ("validation_summary", "audit_validation", "1:1 load — one row per validation check"),
        ("dataset_profile", "audit_dataset_profile", "1:1 load — one row per public output profiled"),
    ]
    rows = []
    for source_name, target_table, notes in checks:
        source_rows = len(source_frames.get(source_name, pd.DataFrame()))
        target_rows = len(star_schema.get(target_table, pd.DataFrame()))
        difference = source_rows - target_rows
        status = "OK" if difference == 0 else "MISMATCH"
        rows.append(
            {
                "source_name": source_name,
                "source_rows": source_rows,
                "target_table": target_table,
                "target_rows": target_rows,
                "difference": difference,
                "status": status,
                "notes": notes,
            }
        )
    return pd.DataFrame(rows, columns=RECONCILIATION_COLUMNS)


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class StarSchemaResult:
    tables: dict[str, pd.DataFrame]
    reconciliation: pd.DataFrame


def build_sqlserver_star_schema(outputs: dict[str, pd.DataFrame], *, dataset_period: str | None = None) -> StarSchemaResult:
    """Reshape the public marts in `outputs` (the same dict shape used
    throughout the app — e.g. `result["outputs"]` from
    app/utils/data_loader.py) into the SQL Server-compatible dimensional
    tables, validate uniqueness/foreign keys, and build the row-count
    reconciliation report.

    Raises ValueError if any dimension uniqueness or fact foreign-key
    check fails — a star schema that fails these checks is never returned
    silently.
    """
    product_performance = outputs.get("product_performance", pd.DataFrame())
    marketplace_summary = outputs.get("marketplace_summary", pd.DataFrame())
    inventory_action_review = outputs.get("inventory_action_review", pd.DataFrame())
    mart_marketplace_variance_drivers = outputs.get("mart_marketplace_variance_drivers", pd.DataFrame())
    mart_performance_driver_summary = outputs.get("mart_performance_driver_summary", pd.DataFrame())
    validation_summary = outputs.get("validation_summary", pd.DataFrame())
    dataset_profile = outputs.get("dataset_profile", pd.DataFrame())

    if dataset_period is None and "dataset_period" in marketplace_summary.columns and not marketplace_summary.empty:
        dataset_period = str(marketplace_summary["dataset_period"].dropna().iloc[0]) if marketplace_summary["dataset_period"].notna().any() else None

    dim_product = build_dim_product(product_performance)
    dim_marketplace = build_dim_marketplace(marketplace_summary, product_performance, inventory_action_review, mart_marketplace_variance_drivers)
    dim_month = build_dim_month(marketplace_summary, dataset_period=dataset_period)
    dim_fulfillment = build_dim_fulfillment(product_performance)

    assert_dimension_uniqueness(dim_product, ["public_product_id"], dim_name="dim_product")
    assert_dimension_uniqueness(dim_marketplace, ["marketplace", "channel"], dim_name="dim_marketplace")
    assert_dimension_uniqueness(dim_month, ["transaction_month"], dim_name="dim_month")
    assert_dimension_uniqueness(dim_fulfillment, ["fulfillment_type"], dim_name="dim_fulfillment")

    fact_marketplace_activity = build_fact_marketplace_activity(marketplace_summary, dim_month, dim_marketplace)
    fact_product_performance = build_fact_product_performance(product_performance, dim_product, dim_marketplace, dataset_period=dataset_period)
    fact_inventory_action = build_fact_inventory_action(inventory_action_review, dim_product, dim_marketplace)
    fact_performance_variance = build_fact_performance_variance(
        mart_marketplace_variance_drivers, mart_performance_driver_summary, dim_month, dim_marketplace
    )
    audit_validation = build_audit_validation(validation_summary)
    audit_dataset_profile = build_audit_dataset_profile(dataset_profile)

    assert_fact_foreign_keys(fact_marketplace_activity, "month_key", dim_month, "month_key", fact_name="fact_marketplace_activity")
    assert_fact_foreign_keys(fact_marketplace_activity, "marketplace_key", dim_marketplace, "marketplace_key", fact_name="fact_marketplace_activity")
    assert_fact_foreign_keys(fact_product_performance, "product_key", dim_product, "product_key", fact_name="fact_product_performance")
    assert_fact_foreign_keys(fact_product_performance, "marketplace_key", dim_marketplace, "marketplace_key", fact_name="fact_product_performance")
    assert_fact_foreign_keys(fact_inventory_action, "product_key", dim_product, "product_key", fact_name="fact_inventory_action")
    assert_fact_foreign_keys(fact_inventory_action, "marketplace_key", dim_marketplace, "marketplace_key", fact_name="fact_inventory_action")
    assert_fact_foreign_keys(fact_performance_variance, "previous_month_key", dim_month, "month_key", fact_name="fact_performance_variance")
    assert_fact_foreign_keys(fact_performance_variance, "current_month_key", dim_month, "month_key", fact_name="fact_performance_variance")
    assert_fact_foreign_keys(fact_performance_variance, "marketplace_key", dim_marketplace, "marketplace_key", fact_name="fact_performance_variance")

    tables = {
        "dim_product": dim_product,
        "dim_marketplace": dim_marketplace,
        "dim_month": dim_month,
        "dim_fulfillment": dim_fulfillment,
        "fact_marketplace_activity": fact_marketplace_activity,
        "fact_product_performance": fact_product_performance,
        "fact_inventory_action": fact_inventory_action,
        "fact_performance_variance": fact_performance_variance,
        "audit_validation": audit_validation,
        "audit_dataset_profile": audit_dataset_profile,
    }

    source_frames = {
        "marketplace_summary": marketplace_summary,
        "product_performance": product_performance,
        "inventory_action_review": inventory_action_review,
        "mart_marketplace_variance_drivers": mart_marketplace_variance_drivers,
        "validation_summary": validation_summary,
        "dataset_profile": dataset_profile,
    }
    reconciliation = build_reconciliation_report(source_frames, tables)

    return StarSchemaResult(tables=tables, reconciliation=reconciliation)
