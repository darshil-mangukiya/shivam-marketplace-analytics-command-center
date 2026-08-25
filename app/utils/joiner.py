from __future__ import annotations

import pandas as pd

from app.utils.data_cleaner import AppDataError, clean_text_series
from pipeline_utils import NON_PRODUCT_ID, PRIVATE_AMOUNT_COLUMNS, parse_numeric_series  # type: ignore


def join_transactions_to_product_master(
    transactions: pd.DataFrame,
    products: pd.DataFrame,
    product_metrics: dict[str, object] | None = None,
    marketplace_channels: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    if "sku" not in transactions.columns:
        raise AppDataError("The transaction data is missing a normalized SKU column.")
    if "seller_sku" not in products.columns:
        raise AppDataError("The product master is missing a normalized seller SKU column.")

    transactions = transactions.copy()
    products = products.copy()
    for col in PRIVATE_AMOUNT_COLUMNS + ["quantity", "price"]:
        if col in transactions.columns:
            transactions[col] = parse_numeric_series(transactions[col])
        if col in products.columns:
            products[col] = parse_numeric_series(products[col])

    product_cols = [
        "seller_sku",
        "asin1",
        "item_name",
        "item_description",
        "listing_id",
        "product_id",
        "price",
        "quantity",
        "fulfillment_channel",
        "status",
        "brand",
        "category",
        "subcategory",
        "product_group",
        "mapping_status",
        "public_product_id",
        "listing_price_band",
        "inventory_band",
        "margin_band_public",
        "profitability_band_public",
        "restock_priority",
        "origin_country",
        "imported_flag",
        "pack_size",
        "variant",
        "unit_cost_private_rs",
        "landed_uplift_private_rs",
        "platform_commission_private_rs",
        "shipping_cost_private_rs",
        "packing_cost_private_rs",
        "landed_cost_private_rs",
        "total_estimated_cost_private_rs",
        "estimated_profit_private_rs",
        "estimated_profit_margin_pct_private",
    ]
    product_context = products[[col for col in product_cols if col in products.columns]].drop_duplicates("seller_sku")

    merged = transactions.merge(
        product_context,
        how="left",
        left_on="sku",
        right_on="seller_sku",
        indicator=True,
        suffixes=("", "_listing"),
    )
    merged["product_master_match"] = merged["_merge"].eq("both")
    merged = merged.drop(columns=["_merge"])

    sku_series = clean_text_series(merged["sku"])
    has_sku = sku_series.notna()
    matched = merged["product_master_match"]
    unmatched_skus = sorted(sku_series[has_sku & ~matched].dropna().unique().tolist())
    unmatched_public_ids = {sku: f"UNMAPPED_{idx + 1:04d}" for idx, sku in enumerate(unmatched_skus)}

    merged["public_product_id"] = clean_text_series(merged["public_product_id"])
    merged.loc[has_sku & ~matched, "public_product_id"] = sku_series[has_sku & ~matched].map(unmatched_public_ids)
    merged.loc[~has_sku, "public_product_id"] = NON_PRODUCT_ID

    fill_context = {
        "brand": "Unmapped",
        "category": "Unmapped",
        "subcategory": "Unmapped",
        "product_group": "Unmapped Product",
        "listing_price_band": "Unknown",
        "inventory_band": "Unknown",
        "mapping_status": "Unmatched",
    }
    for col, fill_value in fill_context.items():
        if col not in merged.columns:
            merged[col] = fill_value
        merged[col] = clean_text_series(merged[col]).fillna(fill_value)

    merged.loc[~has_sku, ["brand", "category", "subcategory", "product_group"]] = "Non-product Activity"
    merged.loc[~has_sku, "mapping_status"] = "Non-product"

    marketplace_join_coverage_pct = 0.0
    unmatched_marketplace_channel_rows_count = 0
    if marketplace_channels is not None and not marketplace_channels.empty:
        channels = marketplace_channels.copy()
        if "seller_sku" in channels.columns and "marketplace" in channels.columns:
            channel_cols = [
                "seller_sku",
                "marketplace",
                "channel",
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
                "margin_band_public",
                "profitability_band_public",
                "channel_price_band_public",
                "inventory_band",
                "channel_readiness",
            ]
            channel_context = channels[[col for col in channel_cols if col in channels.columns]].drop_duplicates(
                ["seller_sku", "marketplace"]
            )
            merged = merged.merge(
                channel_context,
                how="left",
                left_on=["sku", "marketplace"],
                right_on=["seller_sku", "marketplace"],
                indicator="marketplace_channel_merge",
                suffixes=("", "_channel"),
            )
            marketplace_matched = merged["marketplace_channel_merge"].eq("both")
            marketplace_join_coverage_pct = (
                float((has_sku & marketplace_matched).sum()) / float(has_sku.sum()) * 100.0
                if int(has_sku.sum())
                else 0.0
            )
            unmatched_marketplace_channel_rows_count = int((has_sku & ~marketplace_matched).sum())
            merged["marketplace_channel_match"] = marketplace_matched
            merged = merged.drop(columns=["marketplace_channel_merge"], errors="ignore")
            if "channel" not in merged.columns:
                merged["channel"] = merged["marketplace"]
            merged["channel"] = clean_text_series(merged["channel"]).fillna(merged["marketplace"])
            if "margin_band_public_channel" in merged.columns:
                merged["channel_margin_band_public"] = clean_text_series(merged["margin_band_public_channel"]).fillna(
                    clean_text_series(merged.get("margin_band_public", pd.Series(index=merged.index))).fillna("Unknown")
                )
            if "profitability_band_public_channel" in merged.columns:
                merged["profitability_band_public"] = clean_text_series(
                    merged["profitability_band_public_channel"]
                ).fillna(clean_text_series(merged.get("profitability_band_public", pd.Series(index=merged.index))).fillna("Unknown"))
    if "channel" not in merged.columns:
        merged["channel"] = merged["marketplace"] if "marketplace" in merged.columns else "Marketplace"
    if "channel_margin_band_public" not in merged.columns:
        merged["channel_margin_band_public"] = clean_text_series(
            merged.get("margin_band_public", pd.Series(index=merged.index))
        ).fillna("Unknown")

    transaction_skus = set(clean_text_series(transactions["sku"]).dropna().unique().tolist())
    listing_skus = set(clean_text_series(products["seller_sku"]).dropna().unique().tolist())
    matched_skus = transaction_skus & listing_skus
    unmatched_listing_skus = listing_skus - transaction_skus
    rows_with_sku = int(has_sku.sum())
    matched_transaction_rows = int((has_sku & matched).sum())
    join_coverage_pct = (matched_transaction_rows / rows_with_sku * 100.0) if rows_with_sku else 0.0

    metrics = {
        "transaction_row_count": int(len(transactions)),
        "order_row_count": int(transactions.get("transaction_type_group", pd.Series(dtype=str)).eq("Order").sum()),
        "product_master_row_count": int(len(products)),
        "marketplace_channel_row_count": int(len(marketplace_channels)) if marketplace_channels is not None else 0,
        "transaction_rows_with_sku": rows_with_sku,
        "matched_transaction_rows": matched_transaction_rows,
        "unmatched_transaction_rows": int((has_sku & ~matched).sum()),
        "unique_transaction_skus": int(len(transaction_skus)),
        "unique_product_master_skus": int(len(listing_skus)),
        "matched_skus": int(len(matched_skus)),
        "unmatched_transaction_skus": int(len(unmatched_skus)),
        "unmatched_listing_skus": int(len(unmatched_listing_skus)),
        "join_coverage_pct": round(join_coverage_pct, 2),
        "marketplace_join_coverage_pct": round(marketplace_join_coverage_pct, 2),
        "unmatched_marketplace_channel_rows_count": unmatched_marketplace_channel_rows_count,
        "products_with_all_5_channels_count": int((product_metrics or {}).get("products_with_all_5_channels_count", 0)),
        "products_missing_channel_count": int((product_metrics or {}).get("products_missing_channel_count", 0)),
        "duplicate_sku_count": int((product_metrics or {}).get("duplicate_sku_count", 0)),
    }
    return merged, metrics
