from __future__ import annotations

import pandas as pd

from shared.public_output_builder import build_public_outputs


PUBLIC_OUTPUT_ORDER = [
    "anonymized_master",
    "marketplace_summary",
    "marketplace_channel_performance",
    "product_performance",
    "category_performance",
    "brand_performance",
    "profitability_summary",
    "margin_risk_review",
    "inventory_action_review",
    "fee_refund_summary",
    "fulfillment_comparison",
    "product_action_review",
    "dataset_profile",
    "validation_summary",
]


def build_public_outputs_from_private(
    private_master: pd.DataFrame,
    dataset_period: str = "custom",
) -> dict[str, pd.DataFrame]:
    return build_public_outputs(private_master, dataset_period=dataset_period)


def compute_kpis(outputs: dict[str, pd.DataFrame], join_metrics: dict[str, object]) -> dict[str, object]:
    product = outputs.get("product_performance", pd.DataFrame())
    action = outputs.get("product_action_review", pd.DataFrame())
    marketplace = outputs.get("marketplace_channel_performance", pd.DataFrame())
    margin = outputs.get("margin_risk_review", pd.DataFrame())
    products_with_transactions = int(product.get("public_product_id", pd.Series(dtype=str)).nunique())
    marketplace_channels = int(marketplace.get("marketplace", product.get("marketplace", pd.Series(dtype=str))).nunique())
    return {
        "Product Master Rows": int(join_metrics.get("product_master_row_count", 0) or 0),
        "Transaction Rows": int(join_metrics.get("transaction_row_count", 0) or 0),
        "Order Rows": int(join_metrics.get("order_row_count", 0) or 0),
        "Join Coverage %": float(join_metrics.get("join_coverage_pct", 0) or 0),
        # The mapping status is categorical because the source mapping keys are incomplete.
        "Channel Mapping Status": str(join_metrics.get("channel_mapping_status", "Unavailable")),
        "Products in Analysis": products_with_transactions,
        "Products With Transactions": products_with_transactions,
        "Marketplaces": marketplace_channels,
        "Category Count": int(product.get("category_group", pd.Series(dtype=str)).nunique()),
        "Brand Count": int(product.get("brand_group", pd.Series(dtype=str)).nunique()),
        "Average Fee % of Gross": round(float(product.get("fee_pct_of_gross", pd.Series(dtype=float)).mean() or 0), 1),
        "Average Refund % of Gross": round(float(product.get("refund_pct_of_gross", pd.Series(dtype=float)).mean() or 0), 1),
        "Average Promotion % of Gross": round(float(product.get("promotion_pct_of_gross", pd.Series(dtype=float)).mean() or 0), 1),
        "Average Net-to-Gross %": round(float(product.get("net_to_gross_pct", pd.Series(dtype=float)).mean() or 0), 1),
        "Average Margin Risk Score": round(float(margin.get("margin_risk_score", pd.Series(dtype=float)).mean() or 0), 1),
        "Average Revenue Quality Score": round(float(product.get("revenue_quality_score", pd.Series(dtype=float)).mean() or 0), 1),
        "High Priority Actions": int((action.get("action_priority", pd.Series(dtype=str)) == "High").sum()),
        "Refund Review Count": int((action.get("recommended_action", pd.Series(dtype=str)) == "Refund Review").sum()),
        "Promotion Review Count": int((action.get("recommended_action", pd.Series(dtype=str)) == "Promotion Review").sum()),
        "Fee Review Count": int((action.get("recommended_action", pd.Series(dtype=str)) == "Fee Review").sum()),
        "Slow Mover Review Count": int((action.get("recommended_action", pd.Series(dtype=str)) == "Slow Mover Review").sum()),
        "Margin Risk Review Count": int((action.get("recommended_action", pd.Series(dtype=str)) == "Margin Risk Review").sum()),
        "Restock Review Count": int((action.get("recommended_action", pd.Series(dtype=str)) == "Restock Review").sum()),
    }
