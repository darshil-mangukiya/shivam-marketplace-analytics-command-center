"""Tests for the flat-mart -> SQL Server-compatible star-schema
transformation (shared/sqlserver_star_schema.py).

These are pure-pandas tests — no SQL Server, no pyodbc, no network. They
validate the reshape logic, deterministic surrogate keys, dimension
uniqueness, fact foreign-key resolution, unknown-value handling, row-count
reconciliation, and privacy safety of the generated tables. They do not
and cannot prove real SQL Server runtime behavior — see
docs/sql_server_reporting_model.md for the model.
"""

from __future__ import annotations

import pandas as pd
import pytest

from shared.sqlserver_star_schema import (
    UNKNOWN_KEY,
    UNKNOWN_LABEL,
    assert_dimension_uniqueness,
    assert_fact_foreign_keys,
    build_dim_fulfillment,
    build_dim_marketplace,
    build_dim_month,
    build_dim_product,
    build_fact_inventory_action,
    build_fact_marketplace_activity,
    build_fact_performance_variance,
    build_fact_product_performance,
    build_reconciliation_report,
    build_sqlserver_star_schema,
)


def _product_performance() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "public_product_id": ["P0001", "P0002", "P0003"],
            "marketplace": ["Amazon", "Amazon", "Flipkart"],
            "brand_group": ["Brand A", "Brand B", "Brand B"],
            "category_group": ["Skin Care", "Hair Care", "Hair Care"],
            "subcategory_group": ["Face", "Shampoo", "Shampoo"],
            "product_group": ["Cream", "Bottle", "Bottle"],
            "fulfillment_type": ["FBA", "Merchant", "FBA"],
            "listing_price_band": ["500-1000", "0-500", "0-500"],
            "inventory_band": ["Moderate", "Low", "High"],
            "margin_band_public": ["Healthy Margin", "Low Margin", "Moderate Margin"],
            "profitability_band_public": ["Healthy Margin", "Low Margin", "Moderate Margin"],
            "sales_index": [80.0, 40.0, 20.0],
            "units_index": [70.0, 30.0, 15.0],
            "fee_pct_of_gross": [20.0, 15.0, 10.0],
            "refund_pct_of_gross": [5.0, 2.0, 1.0],
            "promotion_pct_of_gross": [3.0, 1.0, 0.0],
            "net_to_gross_pct": [72.0, 82.0, 89.0],
            "margin_index": [50.0, 40.0, 60.0],
            "estimated_profitability_index": [55.0, 45.0, 65.0],
            "margin_risk_score": [30.0, 20.0, 10.0],
            "revenue_quality_score": [60.0, 70.0, 80.0],
            "recommended_action": ["Monitor", "Fee Review", "Monitor"],
            "action_priority": ["Low", "High", "Low"],
        }
    )


def _marketplace_summary() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "dataset_period": ["12m"] * 4,
            "transaction_month": ["2026-05", "2026-05", "2026-06", "2026-06"],
            "marketplace": ["Amazon", "Flipkart", "Amazon", "Flipkart"],
            "total_orders": [6000, 4000, 6100, 3900],
            "product_count": [80, 60, 82, 58],
            "sales_index": [210.0, 150.0, 210.7, 149.0],
            "units_index": [215.6, 140.0, 215.5, 139.5],
            "avg_fee_pct_of_gross": [20.0, 15.0, 19.5, 14.8],
            "avg_refund_pct_of_gross": [5.0, 3.0, 4.8, 2.9],
            "avg_promotion_pct_of_gross": [3.0, 2.0, 2.8, 1.9],
            "avg_net_to_gross_pct": [72.0, 80.0, 72.5, 80.5],
            "margin_risk_score": [30.0, 25.0, 29.0, 24.5],
            "revenue_quality_score": [60.0, 65.0, 61.0, 66.0],
        }
    )


def _inventory_action_review() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "public_product_id": ["P0001", "P0002"],
            "marketplace": ["Amazon", "Amazon"],
            "brand_group": ["Brand A", "Brand B"],
            "category_group": ["Skin Care", "Hair Care"],
            "product_group": ["Cream", "Bottle"],
            "inventory_band": ["Moderate", "Low"],
            "units_index": [70.0, 30.0],
            "sales_index": [80.0, 40.0],
            "margin_risk_band": ["Medium Risk", "Low Risk"],
            "revenue_quality_band": ["Healthy", "Strong"],
            "restock_priority": ["Monitor", "High"],
            "recommended_action": ["Monitor", "Restock Review"],
            "action_priority": ["Low", "High"],
            "action_reason": ["No action threshold triggered.", "High indexed unit movement with low inventory."],
        }
    )


def _mart_marketplace_variance_drivers() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "marketplace": ["Amazon", "Flipkart"],
            "metric": ["sales_index", "sales_index"],
            "metric_label": ["Sales Index", "Sales Index"],
            "previous_value": [210.0, 150.0],
            "current_value": [210.7, 149.0],
            "abs_variance": [0.7, -1.0],
            "pct_variance": [0.33, -0.67],
            "contribution_share_pct": [41.2, 58.8],
            "movement": ["Improvement", "Deterioration"],
        }
    )


def _mart_performance_driver_summary(previous="2026-05", current="2026-06") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "metric": "sales_index",
                "metric_label": "Sales Index",
                "previous_period": previous,
                "current_period": current,
                "total_abs_variance": -0.3,
                "total_pct_variance": -0.08,
                "movement": "Deterioration",
                "narrative": "Sales Index decreased slightly.",
                "excluded_trailing_periods": "",
            }
        ]
    )


def _validation_summary() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "check_name": ["Public outputs generated", "Privacy scan passes"],
            "check_status": ["PASS", "PASS"],
            "check_value": ["3", "safe"],
            "expected_value": ["> 0 rows", "safe"],
            "notes": ["", ""],
        }
    )


def _dataset_profile() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "public_output_name": ["product_performance", "marketplace_summary"],
            "row_count": [3, 4],
            "dataset_period": ["12m", "12m"],
            "dataset_label": ["12-Month Demo", "12-Month Demo"],
        }
    )


def _full_outputs() -> dict[str, pd.DataFrame]:
    return {
        "product_performance": _product_performance(),
        "marketplace_summary": _marketplace_summary(),
        "inventory_action_review": _inventory_action_review(),
        "mart_marketplace_variance_drivers": _mart_marketplace_variance_drivers(),
        "mart_performance_driver_summary": _mart_performance_driver_summary(),
        "validation_summary": _validation_summary(),
        "dataset_profile": _dataset_profile(),
    }


# ---------------------------------------------------------------------------
# Dimension builders
# ---------------------------------------------------------------------------


def test_build_dim_product_has_one_row_per_public_product_id_plus_unknown():
    dim = build_dim_product(_product_performance())
    assert len(dim) == 4  # 3 real products + Unknown
    assert set(dim["public_product_id"]) == {"P0001", "P0002", "P0003", UNKNOWN_LABEL}
    assert dim["public_product_id"].is_unique


def test_build_dim_product_never_includes_private_columns():
    df = _product_performance()
    dim = build_dim_product(df)
    forbidden = {"seller_sku", "asin1", "asin", "sku", "order_id", "listing_id", "item_name", "item_description"}
    assert not (forbidden & set(dim.columns))


def test_build_dim_product_raises_if_source_has_private_columns():
    df = _product_performance()
    df["seller_sku"] = ["REAL-SKU-1", "REAL-SKU-2", "REAL-SKU-3"]
    with pytest.raises(ValueError):
        build_dim_product(df)


def test_build_dim_marketplace_deduplicates_across_frames():
    dim = build_dim_marketplace(_marketplace_summary(), _product_performance())
    assert set(dim["marketplace"]) == {"Amazon", "Flipkart", UNKNOWN_LABEL}
    assert dim["marketplace"].is_unique
    # channel is a constant attribute, never a validated sub-channel claim.
    assert set(dim["channel"].dropna()) <= {"Marketplace"}


def test_build_dim_month_parses_calendar_attributes():
    dim = build_dim_month(_marketplace_summary())
    real_rows = dim[dim["transaction_month"] != UNKNOWN_LABEL]
    row = real_rows[real_rows["transaction_month"] == "2026-05"].iloc[0]
    assert row["year"] == 2026
    assert row["month_number"] == 5
    assert row["month_name"] == "May"
    assert row["quarter"] == 2


def test_build_dim_month_never_invents_months_outside_source():
    dim = build_dim_month(_marketplace_summary())
    real_months = set(dim[dim["transaction_month"] != UNKNOWN_LABEL]["transaction_month"])
    assert real_months == {"2026-05", "2026-06"}


def test_build_dim_fulfillment_from_product_performance():
    dim = build_dim_fulfillment(_product_performance())
    assert set(dim["fulfillment_type"]) == {"FBA", "Merchant", UNKNOWN_LABEL}


# ---------------------------------------------------------------------------
# Deterministic surrogate keys
# ---------------------------------------------------------------------------


def test_surrogate_keys_are_deterministic_across_repeated_runs():
    dim_a = build_dim_product(_product_performance())
    dim_b = build_dim_product(_product_performance())
    pd.testing.assert_frame_equal(dim_a, dim_b)


def test_surrogate_keys_are_not_random_uuids():
    dim = build_dim_product(_product_performance())
    real_rows = dim[dim["product_key"] != UNKNOWN_KEY]
    # Deterministic integers starting at 1, not UUID strings.
    assert set(real_rows["product_key"]) == {1, 2, 3}


def test_unknown_key_is_reserved_as_zero_on_every_dimension():
    assert UNKNOWN_KEY == 0
    for builder, frame in [
        (build_dim_product, _product_performance()),
        (build_dim_marketplace, _marketplace_summary()),
        (build_dim_month, _marketplace_summary()),
        (build_dim_fulfillment, _product_performance()),
    ]:
        dim = builder(frame)
        key_col = dim.columns[0]
        assert (dim[key_col] == UNKNOWN_KEY).sum() == 1


# ---------------------------------------------------------------------------
# Fact builders + FK resolution + unknown handling
# ---------------------------------------------------------------------------


def test_build_fact_marketplace_activity_grain_and_row_count():
    dim_month = build_dim_month(_marketplace_summary())
    dim_marketplace = build_dim_marketplace(_marketplace_summary())
    fact = build_fact_marketplace_activity(_marketplace_summary(), dim_month, dim_marketplace)
    assert len(fact) == 4  # 2 months x 2 marketplaces
    assert not fact.duplicated(subset=["month_key", "marketplace_key"]).any()


def test_build_fact_product_performance_has_no_month_key_column():
    # The real product_performance.csv has no transaction_month column, so
    # this fact must never fabricate a month grain.
    dim_product = build_dim_product(_product_performance())
    dim_marketplace = build_dim_marketplace(_product_performance())
    fact = build_fact_product_performance(_product_performance(), dim_product, dim_marketplace)
    assert "month_key" not in fact.columns
    assert "dataset_period" in fact.columns
    assert len(fact) == 3


def test_unresolvable_marketplace_maps_to_unknown_key_not_dropped():
    dim_month = build_dim_month(_marketplace_summary())
    dim_marketplace = build_dim_marketplace(_marketplace_summary())  # built WITHOUT the "Meesho" row below
    source = _marketplace_summary()
    source = pd.concat(
        [source, pd.DataFrame([{**source.iloc[0].to_dict(), "marketplace": "Meesho", "transaction_month": "2026-05"}])],
        ignore_index=True,
    )
    fact = build_fact_marketplace_activity(source, dim_month, dim_marketplace)
    # The row is retained (not dropped) and mapped to the Unknown marketplace key.
    assert len(fact) == len(source)
    meesho_row = fact[fact["marketplace_key"] == UNKNOWN_KEY]
    assert len(meesho_row) == 1


def test_build_fact_inventory_action_resolves_product_and_marketplace_keys():
    dim_product = build_dim_product(_product_performance())
    dim_marketplace = build_dim_marketplace(_product_performance())
    fact = build_fact_inventory_action(_inventory_action_review(), dim_product, dim_marketplace)
    assert len(fact) == 2
    assert set(fact["product_key"]) <= set(dim_product["product_key"])
    assert set(fact["marketplace_key"]) <= set(dim_marketplace["marketplace_key"])


def test_build_fact_performance_variance_uses_periods_from_driver_summary():
    dim_month = build_dim_month(_marketplace_summary())
    dim_marketplace = build_dim_marketplace(_marketplace_summary())
    fact = build_fact_performance_variance(
        _mart_marketplace_variance_drivers(), _mart_performance_driver_summary(), dim_month, dim_marketplace
    )
    previous_month_label = dim_month.set_index("month_key").loc[fact["previous_month_key"].iloc[0], "transaction_month"]
    current_month_label = dim_month.set_index("month_key").loc[fact["current_month_key"].iloc[0], "transaction_month"]
    assert previous_month_label == "2026-05"
    assert current_month_label == "2026-06"


def test_build_fact_performance_variance_empty_when_insufficient_periods():
    dim_month = build_dim_month(_marketplace_summary())
    dim_marketplace = build_dim_marketplace(_marketplace_summary())
    insufficient_summary = pd.DataFrame(
        [{"metric": "n/a", "previous_period": "n/a", "current_period": "n/a", "movement": "Insufficient Periods"}]
    )
    fact = build_fact_performance_variance(
        _mart_marketplace_variance_drivers(), insufficient_summary, dim_month, dim_marketplace
    )
    assert fact.empty
    assert list(fact.columns) == [
        "fact_key", "previous_month_key", "current_month_key", "marketplace_key", "metric",
        "previous_value", "current_value", "abs_variance", "pct_variance", "contribution_share_pct", "movement",
    ]


# ---------------------------------------------------------------------------
# Dimension uniqueness / FK validation helpers
# ---------------------------------------------------------------------------


def test_assert_dimension_uniqueness_passes_on_clean_dimension():
    dim = build_dim_product(_product_performance())
    assert_dimension_uniqueness(dim, ["public_product_id"], dim_name="dim_product")  # does not raise


def test_assert_dimension_uniqueness_raises_on_duplicate_natural_key():
    dim = pd.DataFrame({"product_key": [1, 2], "public_product_id": ["P0001", "P0001"]})
    with pytest.raises(ValueError):
        assert_dimension_uniqueness(dim, ["public_product_id"], dim_name="dim_product")


def test_assert_fact_foreign_keys_passes_when_all_keys_resolve():
    dim = pd.DataFrame({"product_key": [0, 1, 2]})
    fact = pd.DataFrame({"product_key": [1, 2, 0]})
    assert_fact_foreign_keys(fact, "product_key", dim, "product_key", fact_name="fact_x")  # does not raise


def test_assert_fact_foreign_keys_raises_on_orphan_key():
    dim = pd.DataFrame({"product_key": [0, 1]})
    fact = pd.DataFrame({"product_key": [1, 99]})  # 99 does not exist in dim
    with pytest.raises(ValueError):
        assert_fact_foreign_keys(fact, "product_key", dim, "product_key", fact_name="fact_x")


# ---------------------------------------------------------------------------
# Row-count reconciliation
# ---------------------------------------------------------------------------


def test_reconciliation_report_all_ok_for_consistent_star_schema():
    result = build_sqlserver_star_schema(_full_outputs(), dataset_period="12m")
    assert (result.reconciliation["status"] == "OK").all()
    assert (result.reconciliation["difference"] == 0).all()


def test_reconciliation_report_has_documented_schema():
    report = build_reconciliation_report({}, {})
    assert list(report.columns) == [
        "source_name", "source_rows", "target_table", "target_rows", "difference", "status", "notes",
    ]


# ---------------------------------------------------------------------------
# End-to-end orchestrator
# ---------------------------------------------------------------------------


def test_build_sqlserver_star_schema_returns_all_expected_tables():
    result = build_sqlserver_star_schema(_full_outputs(), dataset_period="12m")
    expected_tables = {
        "dim_product", "dim_marketplace", "dim_month", "dim_fulfillment",
        "fact_marketplace_activity", "fact_product_performance", "fact_inventory_action",
        "fact_performance_variance", "audit_validation", "audit_dataset_profile",
    }
    assert set(result.tables.keys()) == expected_tables


def test_build_sqlserver_star_schema_no_private_columns_anywhere():
    result = build_sqlserver_star_schema(_full_outputs(), dataset_period="12m")
    forbidden = {"seller_sku", "asin1", "asin", "sku", "order_id", "listing_id", "item_name", "item_description", "order_postal"}
    for name, df in result.tables.items():
        assert not (forbidden & set(df.columns)), f"{name} unexpectedly contains a forbidden column"


def test_build_sqlserver_star_schema_is_deterministic_across_repeated_calls():
    result_a = build_sqlserver_star_schema(_full_outputs(), dataset_period="12m")
    result_b = build_sqlserver_star_schema(_full_outputs(), dataset_period="12m")
    for name in result_a.tables:
        pd.testing.assert_frame_equal(result_a.tables[name], result_b.tables[name])


def test_build_sqlserver_star_schema_empty_outputs_does_not_raise():
    result = build_sqlserver_star_schema({})
    for name, df in result.tables.items():
        assert df.empty or len(df) == 1  # dims may carry only the Unknown row
