from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_executive_top_action_table_has_requested_public_columns():
    source = _source("app/pages/1_Executive_Overview.py")

    assert "Top Action Candidates" in source
    for column in [
        "public_product_id",
        "marketplace",
        "category_group",
        "product_group",
        "recommended_action",
        "action_priority",
        "sales_index",
        "margin_risk_score",
        "revenue_quality_score",
    ]:
        assert column in source


def test_marketplace_performance_table_uses_business_friendly_product_count_label():
    source = _source("app/pages/2_Marketplace_Performance.py")

    assert "Marketplace Performance Table" in source
    assert "products_in_analysis" in source
    assert "avg_margin_risk_score" in source
    assert "avg_revenue_quality_score" in source


def test_profitability_and_inventory_review_tables_are_visible():
    profitability = _source("app/pages/5_Profitability_&_Margin_Intelligence.py")
    inventory = _source("app/pages/6_Inventory,_Restock_&_Action_Review.py")

    assert "Top Margin Risk Candidates" in profitability
    assert "Restock Review Candidates" in inventory
    assert "Slow Mover Review Candidates" in inventory
    assert "Inventory Action Review Table" in inventory


def test_business_table_column_lists_do_not_include_private_field_names():
    page_sources = "\n".join(
        [
            _source("app/pages/1_Executive_Overview.py"),
            _source("app/pages/2_Marketplace_Performance.py"),
            _source("app/pages/4_Fees,_Refunds_&_Revenue_Quality.py"),
            _source("app/pages/5_Profitability_&_Margin_Intelligence.py"),
            _source("app/pages/6_Inventory,_Restock_&_Action_Review.py"),
        ]
    )
    private_columns = {
        '"asin"',
        '"asin1"',
        '"seller_sku"',
        '"sku"',
        '"order_id"',
        '"postal_code"',
        '"item_description"',
        '"item_name"',
        '"raw_revenue"',
        '"raw_fee"',
    }

    assert not any(column in page_sources for column in private_columns)
