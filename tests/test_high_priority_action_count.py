from pathlib import Path

import pandas as pd

from shared.public_output_builder import build_public_outputs

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "data" / "public"


def test_committed_channel_high_priority_not_above_product_count():
    channel = pd.read_csv(PUBLIC / "marketplace_channel_performance.csv")
    assert (channel["high_priority_action_count"] <= channel["product_count"]).all()
    # Must be whole-number product counts, never inflated transaction-row counts.
    assert (channel["high_priority_action_count"] >= 0).all()
    assert channel["high_priority_action_count"].dtype.kind in {"i", "u"}


def test_high_priority_counts_distinct_products_not_rows():
    # One product (P0001) generates several Order rows on Amazon, all High via fee.
    rows = []
    for _ in range(20):
        rows.append(
            {
                "transaction_month": "2026-05",
                "dataset_period": "test",
                "marketplace": "Amazon",
                "channel": "Marketplace",
                "public_product_id": "P0001",
                "brand": "Brand A",
                "category": "Cat A",
                "subcategory": "Sub A",
                "product_group": "Group A",
                "fulfillment_type": "FBA",
                "state_group": "Maharashtra",
                "transaction_type_group": "Order",
                "order_id": f"O{_}",
                "gross_sales_private_rs": 1000,
                "units_private": 2,
                "refund_amount_private_rs": 0,
                "promotion_amount_private_rs": 0,
                "total_fee_private_rs": 400,  # 40% fee -> Fee Review High
                "net_amount_private_rs": 600,
                "listing_price_band": "500-999",
                "inventory_band": "Low / 6-20",
            }
        )
    outputs = build_public_outputs(pd.DataFrame(rows), dataset_period="test")
    channel = outputs["marketplace_channel_performance"]
    amazon = channel[channel["marketplace"] == "Amazon"].iloc[0]
    # 20 transaction rows, but only 1 distinct product -> count must be 1, not 20.
    assert amazon["high_priority_action_count"] == 1
    assert amazon["high_priority_action_count"] <= amazon["product_count"]
