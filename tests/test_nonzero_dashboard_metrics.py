import pandas as pd

from shared.public_output_builder import build_public_outputs


def _private_transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "transaction_month": "2026-05",
                "dataset_period": "12m",
                "marketplace": "Amazon",
                "channel": "Amazon",
                "public_product_id": "PUBLIC_PRODUCT_001",
                "brand": "Brand A",
                "category": "Category A",
                "subcategory": "Sub A",
                "product_group": "Product Group A",
                "fulfillment_type": "FBA",
                "state_group": "Maharashtra",
                "transaction_type_group": "Order",
                "gross_sales_private_rs": 1000,
                "units_private": 2,
                "refund_amount_private_rs": 0,
                "promotion_amount_private_rs": 50,
                "total_fee_private_rs": 120,
                "net_amount_private_rs": 830,
                "landed_cost_private_rs": 250,
            },
            {
                "transaction_month": "2026-05",
                "dataset_period": "12m",
                "marketplace": "Flipkart",
                "channel": "Flipkart",
                "public_product_id": "PUBLIC_PRODUCT_002",
                "brand": "Brand B",
                "category": "Category B",
                "subcategory": "Sub B",
                "product_group": "Product Group B",
                "fulfillment_type": "Seller Fulfilled",
                "state_group": "Gujarat",
                "transaction_type_group": "Order",
                "gross_sales_private_rs": 500,
                "units_private": 1,
                "refund_amount_private_rs": 0,
                "promotion_amount_private_rs": 25,
                "total_fee_private_rs": 80,
                "net_amount_private_rs": 395,
                "landed_cost_private_rs": 150,
            },
        ]
    )


def test_aggregated_dashboard_outputs_keep_nonzero_indexes():
    outputs = build_public_outputs(_private_transactions(), dataset_period="12m")

    for name in [
        "marketplace_summary",
        "marketplace_channel_performance",
        "product_performance",
        "category_performance",
        "brand_performance",
        "profitability_summary",
        "fee_refund_summary",
        "fulfillment_comparison",
        "product_action_review",
    ]:
        df = outputs[name]
        metric_cols = [col for col in ["sales_index", "units_index", "margin_index", "fee_pct_of_gross", "avg_fee_pct_of_gross", "net_to_gross_pct", "avg_net_to_gross_pct"] if col in df.columns]
        assert metric_cols, f"{name} has no dashboard metric columns"
        assert any(pd.to_numeric(df[col], errors="coerce").fillna(0).gt(0).any() for col in metric_cols), name
