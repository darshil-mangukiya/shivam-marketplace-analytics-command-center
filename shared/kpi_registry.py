"""KPI governance registry (Priority 2 of the final local completion pass).

A single machine-readable source of truth for the project's governed KPIs
— name, the public output column(s) that carry it, a short business
definition, a pointer to the implementing code (never a duplicated
formula), expected numeric range, display format, and public-safety
classification.

This does NOT re-implement or duplicate any formula — `calculation_reference`
always points back at the one place a KPI is actually computed
(`shared/metrics.py`, `shared/profitability.py`,
`shared/public_output_builder.py`, or `shared/recommendations.py`). The
governance value this module adds is automated, testable *alignment*
checking: does every governed KPI actually appear in the public output(s)
it claims to, does its column name avoid the private-identifier
vocabulary, and does `docs/kpi_catalog.md` still mention it. This is
alignment/metadata governance, not a formula-diff guarantee — see
`docs/business_rules.md` and `docs/kpi_catalog.md` for the authoritative
formulas themselves.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KPI_CATALOG_PATH = PROJECT_ROOT / "docs" / "kpi_catalog.md"

# Column-name vocabulary that must never appear as a governed KPI's output
# column — mirrors the forbidden-field vocabulary already enforced by
# shared/privacy.py and contracts/public_outputs/*.yml. Kept here too so a
# governance-level check exists independent of those layers (defense in
# depth, not a replacement for them).
FORBIDDEN_COLUMN_NAMES = {
    "asin", "asin1", "seller_sku", "sku", "order_id", "listing_id", "product_id",
    "item_name", "item_description", "description", "order_postal",
    "gross_sales_private", "refund_amount_private", "promotion_amount_private",
    "net_amount_private", "total", "price", "maximum_retail_price",
}


@dataclasses.dataclass(frozen=True)
class KpiDefinition:
    kpi_name: str
    output_column: str
    business_definition: str
    calculation_reference: str  # "module.py:function_or_formula"
    expected_range: tuple[float, float] | None  # None for categorical/text KPIs
    format: str  # e.g. "0-100 index", "percent (0-300, can be negative for net)", "categorical"
    public_safe: bool
    source_module: str
    source_outputs: tuple[str, ...]  # public output names (without .csv) that carry this column


REGISTRY: tuple[KpiDefinition, ...] = (
    KpiDefinition(
        kpi_name="Sales Index",
        output_column="sales_index",
        business_definition="Relative sales scale of a marketplace/product/segment within the current dataset, 0-100.",
        calculation_reference="shared/metrics.py:index_from_values",
        expected_range=(0.0, 100.0),
        format="0-100 index",
        public_safe=True,
        source_module="shared.metrics",
        source_outputs=("anonymized_master", "marketplace_summary", "product_performance", "category_performance", "brand_performance"),
    ),
    KpiDefinition(
        kpi_name="Units Index",
        output_column="units_index",
        business_definition="Relative unit-quantity scale of a marketplace/product/segment within the current dataset, 0-100.",
        calculation_reference="shared/metrics.py:index_from_values",
        expected_range=(0.0, 100.0),
        format="0-100 index",
        public_safe=True,
        source_module="shared.metrics",
        source_outputs=("anonymized_master", "marketplace_summary", "product_performance", "category_performance", "brand_performance"),
    ),
    KpiDefinition(
        kpi_name="Fee % of Gross",
        output_column="fee_pct_of_gross",
        business_definition="Marketplace/platform fee burden as a percentage of gross sales.",
        calculation_reference="shared/metrics.py:pct_of_gross",
        expected_range=(0.0, 300.0),
        format="percent (0-300)",
        public_safe=True,
        source_module="shared.metrics",
        source_outputs=("anonymized_master", "product_performance", "fee_refund_summary"),
    ),
    KpiDefinition(
        kpi_name="Refund % of Gross",
        output_column="refund_pct_of_gross",
        business_definition="Refund burden as a percentage of gross sales.",
        calculation_reference="shared/metrics.py:pct_of_gross",
        expected_range=(0.0, 300.0),
        format="percent (0-300)",
        public_safe=True,
        source_module="shared.metrics",
        source_outputs=("anonymized_master", "product_performance", "fee_refund_summary"),
    ),
    KpiDefinition(
        kpi_name="Promotion % of Gross",
        output_column="promotion_pct_of_gross",
        business_definition="Promotional-rebate burden as a percentage of gross sales.",
        calculation_reference="shared/metrics.py:pct_of_gross",
        expected_range=(0.0, 300.0),
        format="percent (0-300)",
        public_safe=True,
        source_module="shared.metrics",
        source_outputs=("anonymized_master", "product_performance", "fee_refund_summary"),
    ),
    KpiDefinition(
        kpi_name="Net-to-Gross %",
        output_column="net_to_gross_pct",
        business_definition="Share of gross sales retained after fees, refunds, and promotions (signed).",
        calculation_reference="shared/metrics.py:pct_of_gross (signed=True)",
        expected_range=(-300.0, 300.0),
        format="percent (-300 to 300)",
        public_safe=True,
        source_module="shared.metrics",
        source_outputs=("anonymized_master", "product_performance", "fee_refund_summary"),
    ),
    KpiDefinition(
        kpi_name="Margin Index",
        output_column="margin_index",
        business_definition="Relative estimated-profit scale of a product within the current dataset, 0-100 (non-negative profit only).",
        calculation_reference="shared/public_output_builder.py:add_public_metrics",
        expected_range=(0.0, 100.0),
        format="0-100 index",
        public_safe=True,
        source_module="shared.public_output_builder",
        source_outputs=("anonymized_master", "product_performance", "profitability_summary"),
    ),
    KpiDefinition(
        kpi_name="Estimated Profitability Index",
        output_column="estimated_profitability_index",
        business_definition="Blended 0-100 analytical profitability SIGNAL (margin scale, revenue quality, inverse margin risk, net retention) — never audited accounting profit.",
        calculation_reference="shared/public_output_builder.py:add_public_metrics",
        expected_range=(0.0, 100.0),
        format="0-100 index",
        public_safe=True,
        source_module="shared.public_output_builder",
        source_outputs=("anonymized_master", "product_performance", "profitability_summary"),
    ),
    KpiDefinition(
        kpi_name="Margin Risk Score",
        output_column="margin_risk_score",
        business_definition="Composite 0-100 risk score from fee/refund/promotion burden, net retention, and margin.",
        calculation_reference="shared/profitability.py:margin_risk_score",
        expected_range=(0.0, 100.0),
        format="0-100 score",
        public_safe=True,
        source_module="shared.profitability",
        # Note: mart_marketplace_variance_drivers is deliberately excluded —
        # it is long-format (one row per metric x dimension), so
        # "margin_risk_score" appears as a VALUE in its `metric` column,
        # never as a column name of its own.
        source_outputs=("anonymized_master", "marketplace_summary", "product_performance", "margin_risk_review"),
    ),
    KpiDefinition(
        kpi_name="Revenue Quality Score",
        output_column="revenue_quality_score",
        business_definition="Composite 0-100 quality score reflecting net retention net of fee/refund/promotion drag.",
        calculation_reference="shared/profitability.py:revenue_quality_score",
        expected_range=(0.0, 100.0),
        format="0-100 score",
        public_safe=True,
        source_module="shared.profitability",
        source_outputs=("anonymized_master", "marketplace_summary", "product_performance"),
    ),
    KpiDefinition(
        kpi_name="Recommended Action",
        output_column="recommended_action",
        business_definition="Deterministic, rule-based recommended review action for a product (one of 8 ordered rules, or Monitor).",
        calculation_reference="shared/recommendations.py:add_actions / ACTION_RULES",
        expected_range=None,
        format="categorical",
        public_safe=True,
        source_module="shared.recommendations",
        source_outputs=("anonymized_master", "product_performance", "product_action_review", "inventory_action_review"),
    ),
    KpiDefinition(
        kpi_name="Action Priority",
        output_column="action_priority",
        business_definition="High/Medium/Low urgency tag attached to recommended_action.",
        calculation_reference="shared/recommendations.py:add_actions / ACTION_RULES",
        expected_range=None,
        format="categorical (High/Medium/Low)",
        public_safe=True,
        source_module="shared.recommendations",
        source_outputs=("anonymized_master", "product_performance", "product_action_review", "inventory_action_review"),
    ),
)


def find_kpi(kpi_name: str) -> KpiDefinition | None:
    for kpi in REGISTRY:
        if kpi.kpi_name == kpi_name:
            return kpi
    return None


def all_kpi_names() -> list[str]:
    return [kpi.kpi_name for kpi in REGISTRY]


# ---------------------------------------------------------------------------
# Governance checks
# ---------------------------------------------------------------------------


def validate_kpi_presence(outputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Confirm each KPI column is present in its listed public outputs.

    Returns one row per KPI.
    """
    rows = []
    for kpi in REGISTRY:
        present_in = [
            name for name in kpi.source_outputs
            if name in outputs and kpi.output_column in outputs[name].columns
        ]
        missing_from = [
            name for name in kpi.source_outputs
            if name in outputs and kpi.output_column not in outputs[name].columns
        ]
        rows.append(
            {
                "kpi_name": kpi.kpi_name,
                "output_column": kpi.output_column,
                "present": bool(present_in),
                "present_in": present_in,
                "missing_from": missing_from,
            }
        )
    return pd.DataFrame(rows)


def validate_kpi_ranges(outputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """For each numeric governed KPI, confirm observed values fall inside
    `expected_range` in every output that carries the column. Returns one
    row per (kpi, output) pair actually checked."""
    rows = []
    for kpi in REGISTRY:
        if kpi.expected_range is None:
            continue
        lower, upper = kpi.expected_range
        for name in kpi.source_outputs:
            if name not in outputs or kpi.output_column not in outputs[name].columns:
                continue
            values = pd.to_numeric(outputs[name][kpi.output_column], errors="coerce").dropna()
            if values.empty:
                continue
            in_range = bool(values.between(lower, upper).all())
            rows.append(
                {
                    "kpi_name": kpi.kpi_name,
                    "output": name,
                    "expected_range": kpi.expected_range,
                    "observed_min": float(values.min()),
                    "observed_max": float(values.max()),
                    "in_range": in_range,
                }
            )
    return pd.DataFrame(rows)


def validate_public_safety() -> pd.DataFrame:
    """Confirm every governed KPI's own metadata is marked public_safe and
    its output_column name doesn't collide with the forbidden-field
    vocabulary. This is a governance-metadata check, not a replacement for
    the real content-level privacy scan in shared/privacy.py."""
    rows = []
    for kpi in REGISTRY:
        forbidden_collision = kpi.output_column in FORBIDDEN_COLUMN_NAMES
        rows.append(
            {
                "kpi_name": kpi.kpi_name,
                "output_column": kpi.output_column,
                "public_safe_flag": kpi.public_safe,
                "forbidden_name_collision": forbidden_collision,
                "governance_ok": kpi.public_safe and not forbidden_collision,
            }
        )
    return pd.DataFrame(rows)


def validate_documentation_references() -> pd.DataFrame:
    """Confirm every governed KPI's name is mentioned somewhere in
    docs/kpi_catalog.md — a lightweight drift check, not a structural
    Markdown parse (deliberately whitespace/heading-format independent)."""
    text = KPI_CATALOG_PATH.read_text(encoding="utf-8") if KPI_CATALOG_PATH.exists() else ""
    rows = [{"kpi_name": kpi.kpi_name, "documented": kpi.kpi_name in text} for kpi in REGISTRY]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Documentation generation (Requirement 29: "generate parts of
# docs/kpi_catalog.md from the registry" where feasible)
# ---------------------------------------------------------------------------

REGISTRY_TABLE_BEGIN = "<!-- BEGIN KPI REGISTRY TABLE (generated by shared/kpi_registry.py — do not hand-edit between these markers) -->"
REGISTRY_TABLE_END = "<!-- END KPI REGISTRY TABLE -->"


def render_registry_table_markdown() -> str:
    header = "| KPI Name | Output Column | Expected Range | Format | Public-Safe | Calculation Reference |"
    separator = "|---|---|---|---|---|---|"
    lines = [header, separator]
    for kpi in REGISTRY:
        range_text = f"{kpi.expected_range[0]:g} to {kpi.expected_range[1]:g}" if kpi.expected_range else "n/a (categorical)"
        lines.append(
            f"| {kpi.kpi_name} | `{kpi.output_column}` | {range_text} | {kpi.format} | "
            f"{'Yes' if kpi.public_safe else 'No'} | `{kpi.calculation_reference}` |"
        )
    return "\n".join(lines)


def regenerate_kpi_catalog_table(*, write: bool = True) -> str:
    """Replace the content between REGISTRY_TABLE_BEGIN/END markers in
    docs/kpi_catalog.md with a freshly-rendered table from REGISTRY. If the
    markers aren't present yet, does nothing (the markers must be added to
    the file once, manually, at the desired location). Returns the new
    file content; writes it to disk unless write=False."""
    if not KPI_CATALOG_PATH.exists():
        raise FileNotFoundError(KPI_CATALOG_PATH)
    text = KPI_CATALOG_PATH.read_text(encoding="utf-8")
    if REGISTRY_TABLE_BEGIN not in text or REGISTRY_TABLE_END not in text:
        raise ValueError(
            f"docs/kpi_catalog.md is missing the {REGISTRY_TABLE_BEGIN!r} / {REGISTRY_TABLE_END!r} markers; "
            "add them once at the desired location before calling regenerate_kpi_catalog_table()."
        )
    before, rest = text.split(REGISTRY_TABLE_BEGIN, 1)
    _, after = rest.split(REGISTRY_TABLE_END, 1)
    new_text = f"{before}{REGISTRY_TABLE_BEGIN}\n\n{render_registry_table_markdown()}\n\n{REGISTRY_TABLE_END}{after}"
    if write:
        KPI_CATALOG_PATH.write_text(new_text, encoding="utf-8")
    return new_text
