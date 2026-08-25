from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.utils.data_cleaner import clean_text_columns, clean_text_series, normalize_columns, remove_blank_rows
from app.utils.product_master_cleaner import clean_product_master_file
from pipeline_utils import parse_numeric_series, standardize_marketplace  # type: ignore


CHANNEL_NUMERIC_COLUMNS = [
    "channel_price_multiplier",
    "channel_selling_price_private_rs",
    "platform_commission_pct",
    "platform_commission_private_rs",
    "shipping_cost_private_rs",
    "packing_cost_private_rs",
    "unit_cost_private_rs",
    "landed_cost_private_rs",
    "total_channel_cost_private_rs",
    "estimated_channel_profit_private_rs",
    "estimated_channel_margin_pct_private",
]

CHANNEL_ALIASES = {
    "seller_sku_private": "seller_sku",
    "channel_selling_price_private_rs": "channel_selling_price_private_rs",
}

EXPECTED_MARKETPLACES = {"Amazon", "Flipkart", "Meesho", "JioMart", "Website"}


def _apply_channel_aliases(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for source, target in CHANNEL_ALIASES.items():
        if source in df.columns and target not in df.columns:
            df[target] = df[source]
    return df


def _clean_marketplace_channel_master(input_path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    workbook = pd.ExcelFile(input_path)
    if "Marketplace_Channel_Master" not in workbook.sheet_names:
        return pd.DataFrame(), {
            "marketplace_channel_row_count": 0,
            "marketplace_count": 0,
            "products_with_all_5_channels_count": 0,
            "products_missing_channel_count": 0,
        }

    channel = pd.read_excel(input_path, sheet_name="Marketplace_Channel_Master", dtype=str)
    channel = normalize_columns(channel)
    channel = _apply_channel_aliases(channel)
    channel = remove_blank_rows(clean_text_columns(channel))
    if "seller_sku" not in channel.columns or "marketplace" not in channel.columns:
        return pd.DataFrame(), {
            "marketplace_channel_row_count": int(len(channel)),
            "marketplace_count": 0,
            "products_with_all_5_channels_count": 0,
            "products_missing_channel_count": 0,
        }

    channel["seller_sku"] = clean_text_series(channel["seller_sku"])
    channel["marketplace"] = channel["marketplace"].map(standardize_marketplace)
    channel["channel"] = channel["marketplace"]
    for col in [
        "margin_band_public",
        "profitability_band_public",
        "channel_price_band_public",
        "inventory_band",
        "channel_readiness",
    ]:
        if col not in channel.columns:
            channel[col] = pd.NA
        channel[col] = clean_text_series(channel[col]).fillna("Unknown")

    for col in CHANNEL_NUMERIC_COLUMNS:
        if col not in channel.columns:
            channel[col] = pd.NA
        channel[col] = parse_numeric_series(channel[col])

    sku_marketplace_counts = channel.dropna(subset=["seller_sku"]).groupby("seller_sku")["marketplace"].nunique()
    products_with_all_5 = int((sku_marketplace_counts >= 5).sum())
    products_missing = int((sku_marketplace_counts < 5).sum())
    metrics = {
        "marketplace_channel_row_count": int(len(channel)),
        "marketplace_count": int(channel["marketplace"].nunique()),
        "marketplaces_present": sorted(channel["marketplace"].dropna().unique().tolist()),
        "expected_marketplaces_present": EXPECTED_MARKETPLACES <= set(channel["marketplace"].dropna().unique().tolist()),
        "products_with_all_5_channels_count": products_with_all_5,
        "products_missing_channel_count": products_missing,
    }
    return channel, metrics


def load_product_and_channel_context(input_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    products, product_metrics = clean_product_master_file(input_path)
    channel, channel_metrics = _clean_marketplace_channel_master(input_path)
    product_metrics.update(channel_metrics)
    if not channel.empty:
        product_metrics["products_missing_channel_count"] = max(
            0,
            int(product_metrics.get("product_master_row_count", 0)) - int(channel_metrics.get("products_with_all_5_channels_count", 0)),
        )
    return products, channel, product_metrics

