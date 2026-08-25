from pathlib import Path

import pandas as pd

from app.utils.product_master_loader import load_product_and_channel_context


def test_advanced_product_master_loads_five_channels(tmp_path: Path):
    workbook = tmp_path / "advanced_master.xlsx"
    product = pd.DataFrame(
        [
            {
                "public_product_id": "P0001",
                "seller_sku_private": "SKU-1",
                "asin_private": "B0PRIVATE1",
                "item_name_private": "Private Product",
                "brand": "Brand",
                "category": "Category",
                "subcategory": "Sub",
                "product_group": "Group",
                "current_quantity": 10,
                "listing_price_private_rs": 1000,
                "margin_band_public": "Healthy Margin",
                "profitability_band_public": "Healthy Margin",
            }
        ]
    )
    channels = pd.DataFrame(
        [
            {
                "public_product_id": "P0001",
                "seller_sku_private": "SKU-1",
                "marketplace": marketplace,
                "channel_enabled": "Yes",
                "total_channel_cost_private_rs": 600,
                "estimated_channel_profit_private_rs": 250,
                "estimated_channel_margin_pct_private": 25,
                "margin_band_public": "Healthy Margin",
                "profitability_band_public": "Healthy Margin",
            }
            for marketplace in ["Amazon", "Flipkart", "Meesho", "JioMart", "Website"]
        ]
    )
    with pd.ExcelWriter(workbook) as writer:
        product.to_excel(writer, sheet_name="Product_Master", index=False)
        channels.to_excel(writer, sheet_name="Marketplace_Channel_Master", index=False)
        pd.DataFrame({"assumption": ["test"]}).to_excel(writer, sheet_name="Assumptions", index=False)

    products, channel, metrics = load_product_and_channel_context(workbook)
    assert len(products) == 1
    assert len(channel) == 5
    assert metrics["marketplace_count"] == 5
    assert metrics["products_missing_channel_count"] == 0

