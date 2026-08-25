import pandas as pd

from shared.public_output_builder import build_public_outputs


def test_profitability_outputs_include_scores_and_bands():
    private = pd.DataFrame(
        [
            {
                "transaction_month": "2026-05",
                "dataset_period": "test",
                "marketplace": "Amazon",
                "channel": "Amazon",
                "public_product_id": "P0001",
                "brand": "Brand A",
                "category": "Category A",
                "subcategory": "Sub A",
                "product_group": "Product A",
                "fulfillment_type": "FBA",
                "state_group": "Maharashtra",
                "transaction_type_group": "Order",
                "gross_sales_private_rs": 1000,
                "units_private": 2,
                "refund_amount_private_rs": 0,
                "promotion_amount_private_rs": 50,
                "total_fee_private_rs": 120,
                "net_amount_private_rs": 830,
                "landed_cost_private_rs": 300,
                "listing_price_band": "500-999",
                "inventory_band": "Low / 6-20",
                "margin_band_public": "Healthy Margin",
                "profitability_band_public": "Healthy Margin",
            }
        ]
    )
    outputs = build_public_outputs(private, dataset_period="test")
    product = outputs["product_performance"]
    assert {"margin_index", "estimated_profitability_index", "margin_risk_score", "revenue_quality_score"} <= set(product.columns)
    assert product["margin_risk_score"].between(0, 100).all()
    assert product["revenue_quality_score"].between(0, 100).all()
    assert not outputs["profitability_summary"].empty


def test_estimated_profitability_index_is_distinct_from_margin_index():
    import numpy as np

    rng = np.random.default_rng(7)
    rows = []
    for i in range(12):
        rows.append(
            {
                "transaction_month": "2026-05",
                "dataset_period": "test",
                "marketplace": "Amazon",
                "channel": "Marketplace",
                "public_product_id": f"P{i:04d}",
                "brand": "Brand A",
                "category": "Cat A",
                "subcategory": "Sub A",
                "product_group": f"Group {i}",
                "fulfillment_type": "FBA",
                "state_group": "Maharashtra",
                "transaction_type_group": "Order",
                "order_id": f"O{i}",
                "gross_sales_private_rs": float(rng.integers(400, 3000)),
                "units_private": int(rng.integers(1, 8)),
                "refund_amount_private_rs": float(rng.integers(0, 200)),
                "promotion_amount_private_rs": float(rng.integers(0, 200)),
                "total_fee_private_rs": float(rng.integers(50, 600)),
                "net_amount_private_rs": float(rng.integers(200, 2500)),
                "landed_cost_private_rs": float(rng.integers(100, 1500)),
                "listing_price_band": "500-999",
                "inventory_band": "Low / 6-20",
            }
        )
    product = build_public_outputs(pd.DataFrame(rows), dataset_period="test")["product_performance"]
    # The two indexes must NOT be identical across all rows; the profitability index
    # is a blended signal, not a copy of the relative profit scale.
    assert not product["margin_index"].equals(product["estimated_profitability_index"])
    assert product["estimated_profitability_index"].between(0, 100).all()

