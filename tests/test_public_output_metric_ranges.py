import pandas as pd

from shared.public_output_builder import build_public_outputs


def test_public_output_metric_ranges_and_dataset_profile_label():
    private = pd.DataFrame(
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
                "refund_amount_private_rs": 20,
                "promotion_amount_private_rs": 40,
                "total_fee_private_rs": 100,
                "net_amount_private_rs": 840,
                "landed_cost_private_rs": 250,
            }
        ]
    )
    outputs = build_public_outputs(private, dataset_period="12m")

    for output_name, df in outputs.items():
        for column in [col for col in df.columns if col.endswith("_index") or col.endswith("_score")]:
            values = pd.to_numeric(df[column], errors="coerce").dropna()
            assert values.between(0, 100).all(), f"{output_name}.{column} is outside 0-100"
        for column in [col for col in df.columns if "pct" in col or col.endswith("_to_gross_pct")]:
            values = pd.to_numeric(df[column], errors="coerce").dropna()
            assert values.between(0, 300).all(), f"{output_name}.{column} is outside public ratio bounds"

    profile = outputs["dataset_profile"]
    assert "dataset_label" in profile.columns
    assert set(profile["dataset_label"]) == {"12M / 120K Orders"}
