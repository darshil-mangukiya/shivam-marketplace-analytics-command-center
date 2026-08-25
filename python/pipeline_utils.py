from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

PROJECT_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORT))

from shared.dataset_labels import dataset_label
from shared.public_output_builder import build_public_outputs as shared_build_public_outputs
from shared.privacy import scan_public_outputs as shared_scan_public_outputs


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "private_raw"
MAPPING_DIR = PROJECT_ROOT / "data" / "private_mapping"
PUBLIC_DIR = PROJECT_ROOT / "data" / "public"

PRODUCT_MASTER_RAW = RAW_DIR / "Shivam_Product_Master_Project_Ready_06-23-2026.xlsx"
COST_CHANNEL_MASTER_RAW = RAW_DIR / "Shivam_5_Marketplace_Product_Cost_Channel_Master_READY.xlsx"
TRANSACTION_RAW = RAW_DIR / "2026MayMonthlyUnifiedTransaction.csv"
DATASET_FILES = {
    "1m": RAW_DIR / "Shivam_Transactions_1_Month_10K_Orders.csv",
    "3m": RAW_DIR / "Shivam_Transactions_3_Months_30K_Orders.csv",
    "6m": RAW_DIR / "Shivam_Transactions_6_Months_60K_Orders.csv",
    "12m": RAW_DIR / "Shivam_Transactions_12_Months_120K_Orders.csv",
}

CLEAN_PRODUCT_MASTER = MAPPING_DIR / "clean_product_master_private.csv"
CLEAN_MARKETPLACE_CHANNEL_MASTER = MAPPING_DIR / "marketplace_channel_master_private.csv"
CLEAN_TRANSACTIONS = MAPPING_DIR / "clean_transactions_private.csv"
PRIVATE_MASTER = MAPPING_DIR / "private_master.csv"
PRODUCT_METRICS = MAPPING_DIR / "product_master_metrics.json"
JOIN_METRICS = MAPPING_DIR / "join_metrics.json"

PUBLIC_OUTPUTS = {
    "anonymized_master": PUBLIC_DIR / "anonymized_master.csv",
    "marketplace_summary": PUBLIC_DIR / "marketplace_summary.csv",
    "marketplace_channel_performance": PUBLIC_DIR / "marketplace_channel_performance.csv",
    "product_performance": PUBLIC_DIR / "product_performance.csv",
    "category_performance": PUBLIC_DIR / "category_performance.csv",
    "brand_performance": PUBLIC_DIR / "brand_performance.csv",
    "profitability_summary": PUBLIC_DIR / "profitability_summary.csv",
    "margin_risk_review": PUBLIC_DIR / "margin_risk_review.csv",
    "inventory_action_review": PUBLIC_DIR / "inventory_action_review.csv",
    "fee_refund_summary": PUBLIC_DIR / "fee_refund_summary.csv",
    "fulfillment_comparison": PUBLIC_DIR / "fulfillment_comparison.csv",
    "product_action_review": PUBLIC_DIR / "product_action_review.csv",
    "mart_marketplace_variance_drivers": PUBLIC_DIR / "mart_marketplace_variance_drivers.csv",
    "mart_product_variance_contributors": PUBLIC_DIR / "mart_product_variance_contributors.csv",
    "mart_performance_driver_summary": PUBLIC_DIR / "mart_performance_driver_summary.csv",
    "dataset_profile": PUBLIC_DIR / "dataset_profile.csv",
    "validation_summary": PUBLIC_DIR / "validation_summary.csv",
}

PRODUCT_EXPECTED_FIELDS = [
    "seller_sku",
    "asin1",
    "item_name",
    "item_description",
    "listing_id",
    "price",
    "quantity",
    "open_date",
    "product_id",
    "pending_quantity",
    "fulfillment_channel",
    "status",
    "maximum_retail_price",
    "brand",
    "category",
    "subcategory",
    "product_group",
    "brand_confidence",
    "category_confidence",
    "product_group_confidence",
    "mapping_status",
    "mapping_notes",
    "public_product_id",
    "listing_price_band",
    "inventory_band",
]

ADVANCED_PRODUCT_ALIASES = {
    "seller_sku_private": "seller_sku",
    "asin_private": "asin1",
    "item_name_private": "item_name",
    "item_description_private": "item_description",
    "current_quantity": "quantity",
    "listing_price_private_rs": "price",
    "mrp_private_rs": "maximum_retail_price",
    "estimated_margin_pct_private": "estimated_profit_margin_pct_private",
}

ADVANCED_NUMERIC_COLUMNS = [
    "unit_cost_pct_of_selling_price",
    "unit_cost_private_rs",
    "landed_uplift_pct_of_selling_price",
    "landed_uplift_private_rs",
    "shipping_cost_private_rs",
    "packing_cost_private_rs",
    "platform_commission_pct",
    "platform_commission_private_rs",
    "landed_cost_private_rs",
    "total_estimated_cost_private_rs",
    "estimated_profit_private_rs",
    "estimated_profit_margin_pct_private",
    "reorder_point_private",
    "target_stock_level_private",
    "lead_time_days_private",
]

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

TRANSACTION_EXPECTED_FIELDS = [
    "date_time",
    "settlement_id",
    "type",
    "order_id",
    "sku",
    "description",
    "quantity",
    "marketplace",
    "fulfillment",
    "order_city",
    "order_state",
    "order_postal",
    "product_sales",
    "shipping_credits",
    "gift_wrap_credits",
    "promotional_rebates",
    "selling_fees",
    "fba_fees",
    "other_transaction_fees",
    "other",
    "total",
]

PRIVATE_AMOUNT_COLUMNS = [
    "gross_sales_private",
    "units_private",
    "refund_amount_private",
    "promotion_amount_private",
    "amazon_fee_private",
    "net_amount_private",
]

RATIO_COLUMNS = [
    "fee_pct_of_gross",
    "refund_pct_of_gross",
    "promotion_pct_of_gross",
    "net_to_gross_pct",
]

INDEX_COLUMNS = ["sales_index", "units_index"]

NON_PRODUCT_ID = "NON_PRODUCT_ACTIVITY"


def ensure_directories() -> None:
    for path in [RAW_DIR, MAPPING_DIR, PUBLIC_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def normalize_column_name(name: object) -> str:
    text = "" if pd.isna(name) else str(name)
    text = text.strip().lstrip("\ufeff").lower()
    text = text.replace("%", " pct ")
    text = text.replace("&", " and ")
    text = re.sub(r"[/\\-]+", "_", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    aliases = {
        "date": "date_time",
        "date_time": "date_time",
        "sku": "sku",
        "seller_sku": "seller_sku",
        "asin": "asin1",
        "asin1": "asin1",
        "item_name": "item_name",
        "item_description": "item_description",
        "product_id": "product_id",
        "listing_id": "listing_id",
        "selling_fee": "selling_fees",
        "fba_fee": "fba_fees",
    }
    return aliases.get(text, text)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized: list[str] = []
    seen: dict[str, int] = {}
    for raw_name in df.columns:
        name = normalize_column_name(raw_name) or "unnamed"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        normalized.append(name)
    df = df.copy()
    df.columns = normalized
    return df


def apply_product_aliases(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for source, target in ADVANCED_PRODUCT_ALIASES.items():
        if source in df.columns and target not in df.columns:
            df[target] = df[source]
    return df


def clean_text_series(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    cleaned = cleaned.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "None": pd.NA,
            "NULL": pd.NA,
            "<NA>": pd.NA,
        }
    )
    return cleaned


def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == "object" or str(df[col].dtype).startswith("string"):
            df[col] = clean_text_series(df[col])
    return df


def remove_blank_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df.dropna(how="all").copy()


def parse_numeric_series(series: pd.Series) -> pd.Series:
    text = series.astype("string").fillna("").str.strip()
    negative_parentheses = text.str.match(r"^\(.*\)$", na=False)
    text = text.str.replace(r"[\(\)]", "", regex=True)
    text = text.str.replace(",", "", regex=False)
    text = text.str.replace("₹", "", regex=False)
    text = text.str.replace("$", "", regex=False)
    text = text.str.replace("INR", "", case=False, regex=False)
    values = pd.to_numeric(text, errors="coerce")
    values = values.mask(negative_parentheses, -values.abs())
    return values.fillna(0.0)


def parse_datetime_series(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, format="%d %b %Y %I:%M:%S %p UTC", errors="coerce", utc=True)
    missing = parsed.isna()
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(series.loc[missing], errors="coerce", utc=True)
    return parsed


def first_existing_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def detect_product_sheet_and_header(path: Path) -> tuple[str, int]:
    workbook = pd.ExcelFile(path)
    preferred = [s for s in ["Enriched_Listings", "Listings", "Product_Master"] if s in workbook.sheet_names]
    sheet_order = preferred + [s for s in workbook.sheet_names if s not in preferred]
    best: tuple[int, str, int] | None = None
    for sheet_name in sheet_order:
        preview = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=50, dtype=str)
        for idx, row in preview.iterrows():
            names = {normalize_column_name(value) for value in row.dropna().tolist()}
            score = int("seller_sku" in names) + int("public_product_id" in names) + int("item_name" in names)
            if score >= 2:
                return sheet_name, int(idx)
            if best is None or score > best[0]:
                best = (score, sheet_name, int(idx))
    if best and best[0] > 0:
        return best[1], best[2]
    raise ValueError(f"Could not detect product master header row in {path}")


def detect_transaction_header_row(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for idx, row in enumerate(reader):
            names = {normalize_column_name(value) for value in row}
            has_date = "date_time" in names
            has_sku = "sku" in names
            has_finance = bool({"product_sales", "selling_fees", "fba_fees", "total"} & names)
            has_order = "order_id" in names or "type" in names
            if has_date and has_sku and has_finance and has_order:
                return idx
    raise ValueError(f"Could not detect transaction CSV header row in {path}")


def assign_missing_public_ids(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["public_product_id"] = clean_text_series(df.get("public_product_id", pd.Series(index=df.index)))
    existing = df["public_product_id"].dropna().astype(str)
    existing_numbers = (
        existing.str.extract(r"^P(\d+)$", expand=False).dropna().astype(int)
        if not existing.empty
        else pd.Series(dtype=int)
    )
    next_number = int(existing_numbers.max()) + 1 if not existing_numbers.empty else 1
    missing_mask = df["public_product_id"].isna()
    generated = []
    for _ in range(int(missing_mask.sum())):
        generated.append(f"P{next_number:04d}")
        next_number += 1
    df.loc[missing_mask, "public_product_id"] = generated
    return df


def derive_price_band(value: float) -> str:
    if pd.isna(value) or value <= 0:
        return "Unknown"
    bins = [
        (0, 499, "0-499"),
        (500, 999, "500-999"),
        (1000, 1499, "1000-1499"),
        (1500, 1999, "1500-1999"),
        (2000, 2499, "2000-2499"),
        (2500, 2999, "2500-2999"),
        (3000, 3999, "3000-3999"),
    ]
    for lower, upper, label in bins:
        if lower <= value <= upper:
            return label
    return "4000+"


def derive_inventory_band(value: float) -> str:
    if pd.isna(value):
        return "Unknown"
    if value <= 0:
        return "Out of Stock / 0"
    if value <= 5:
        return "Very Low / 1-5"
    if value <= 20:
        return "Low / 6-20"
    if value <= 50:
        return "Moderate / 21-50"
    if value <= 100:
        return "High / 51-100"
    return "Very High / 100+"


def load_and_clean_product_master(
    input_path: Path | None = None,
    output_path: Path = CLEAN_PRODUCT_MASTER,
) -> pd.DataFrame:
    ensure_directories()
    if input_path is None:
        input_path = COST_CHANNEL_MASTER_RAW if COST_CHANNEL_MASTER_RAW.exists() else PRODUCT_MASTER_RAW
    if not input_path.exists():
        raise FileNotFoundError(f"Missing product master: {input_path}")

    sheet_name, header_row = detect_product_sheet_and_header(input_path)
    df = pd.read_excel(input_path, sheet_name=sheet_name, header=header_row, dtype=str)
    df = normalize_columns(df)
    df = apply_product_aliases(df)
    df = remove_blank_rows(clean_text_columns(df))

    for field in PRODUCT_EXPECTED_FIELDS:
        if field not in df.columns:
            df[field] = pd.NA

    df = df.dropna(subset=["seller_sku"]).copy()
    df["seller_sku"] = clean_text_series(df["seller_sku"])
    duplicate_sku_count = int(df["seller_sku"].duplicated().sum())
    df = df.drop_duplicates(subset=["seller_sku"], keep="first").copy()

    for col in ["price", "quantity", "pending_quantity", "maximum_retail_price"] + ADVANCED_NUMERIC_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = parse_numeric_series(df[col])

    open_date_text = clean_text_series(df["open_date"]).str.replace(r"\s+IST$", "", regex=True)
    df["open_date"] = pd.to_datetime(open_date_text, errors="coerce").dt.date.astype("string")
    df = assign_missing_public_ids(df)

    for col in [
        "brand",
        "category",
        "subcategory",
        "product_group",
        "mapping_status",
        "margin_band_public",
        "profitability_band_public",
        "restock_priority",
        "origin_country",
        "imported_flag",
        "pack_size",
        "variant",
    ]:
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = clean_text_series(df[col]).fillna("Unmapped")
    df["restock_priority"] = df["restock_priority"].replace("Unmapped", "Monitor")
    df["origin_country"] = df["origin_country"].replace("Unmapped", "Unknown")
    df["imported_flag"] = df["imported_flag"].replace("Unmapped", "Unknown")

    df["listing_price_band"] = clean_text_series(df["listing_price_band"])
    missing_price_band = df["listing_price_band"].isna()
    df.loc[missing_price_band, "listing_price_band"] = df.loc[missing_price_band, "price"].map(derive_price_band)

    df["inventory_band"] = clean_text_series(df["inventory_band"])
    missing_inventory_band = df["inventory_band"].isna()
    df.loc[missing_inventory_band, "inventory_band"] = df.loc[missing_inventory_band, "quantity"].map(
        derive_inventory_band
    )

    ordered_cols = PRODUCT_EXPECTED_FIELDS + [col for col in df.columns if col not in PRODUCT_EXPECTED_FIELDS]
    df = df[ordered_cols]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    metrics = {
        "source_file": input_path.name,
        "sheet_name": sheet_name,
        "header_row_zero_based": header_row,
        "product_master_row_count": int(len(df)),
        "duplicate_sku_count": duplicate_sku_count,
        "cost_columns_detected": int(sum(col in df.columns for col in ADVANCED_NUMERIC_COLUMNS)),
    }
    PRODUCT_METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    if input_path == COST_CHANNEL_MASTER_RAW:
        channel, channel_metrics = load_and_clean_marketplace_channel_master(input_path)
        metrics.update(channel_metrics)
        PRODUCT_METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return df


def load_and_clean_marketplace_channel_master(
    input_path: Path = COST_CHANNEL_MASTER_RAW,
    output_path: Path = CLEAN_MARKETPLACE_CHANNEL_MASTER,
) -> tuple[pd.DataFrame, dict[str, object]]:
    if not input_path.exists():
        return pd.DataFrame(), {
            "marketplace_channel_row_count": 0,
            "marketplace_count": 0,
            "products_with_all_5_channels_count": 0,
            "products_missing_channel_count": 0,
        }
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
    channel = apply_product_aliases(channel)
    channel = remove_blank_rows(clean_text_columns(channel))
    if "seller_sku" not in channel.columns:
        channel["seller_sku"] = pd.NA
    if "marketplace" not in channel.columns:
        channel["marketplace"] = pd.NA
    channel["seller_sku"] = clean_text_series(channel["seller_sku"])
    channel["marketplace"] = channel["marketplace"].map(standardize_marketplace)
    channel["channel"] = channel["marketplace"]
    for col in CHANNEL_NUMERIC_COLUMNS:
        if col not in channel.columns:
            channel[col] = pd.NA
        channel[col] = parse_numeric_series(channel[col])
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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    channel.to_csv(output_path, index=False)
    sku_marketplace_counts = channel.dropna(subset=["seller_sku"]).groupby("seller_sku")["marketplace"].nunique()
    metrics = {
        "marketplace_channel_row_count": int(len(channel)),
        "marketplace_count": int(channel["marketplace"].nunique()),
        "marketplaces_present": sorted(channel["marketplace"].dropna().unique().tolist()),
        "products_with_all_5_channels_count": int((sku_marketplace_counts >= 5).sum()),
        "products_missing_channel_count": int((sku_marketplace_counts < 5).sum()),
    }
    return channel, metrics


def standardize_transaction_type(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip().lower()
    if "fulfillment" in text and "refund" in text:
        return "Fulfillment Fee Refund"
    if "refund" in text:
        return "Refund"
    if "shipping" in text and "service" in text:
        return "Shipping Service"
    if "reimburse" in text:
        return "Reimbursement"
    if "order" in text:
        return "Order"
    if "service" in text and "fee" in text:
        return "Service Fee"
    if "adjust" in text:
        return "Adjustment"
    if text:
        return text.title()
    return "Other"


def standardize_fulfillment(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip().lower()
    if not text:
        return "Non-order / Unknown"
    if "amazon" in text or "fba" in text:
        return "FBA"
    if "merchant" in text or "seller" in text:
        return "Merchant Fulfilled"
    return str(value).strip().title()


def standardize_marketplace(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip().lower()
    if not text:
        return "Unknown"
    if "amazon" in text:
        return "Amazon"
    if "flipkart" in text:
        return "Flipkart"
    if "meesho" in text:
        return "Meesho"
    if "jiomart" in text or "jio mart" in text:
        return "JioMart"
    if "website" in text or "shopify" in text or text in {"web", "direct"}:
        return "Website"
    return str(value).strip().title()


def standardize_state(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip()
    if not text:
        return "Unknown"
    return re.sub(r"\s+", " ", text).title()


def load_and_clean_transactions(
    input_path: Path = TRANSACTION_RAW,
    output_path: Path = CLEAN_TRANSACTIONS,
) -> pd.DataFrame:
    ensure_directories()
    if not input_path.exists():
        raise FileNotFoundError(f"Missing transaction report: {input_path}")

    header_row = detect_transaction_header_row(input_path)
    df = pd.read_csv(input_path, skiprows=header_row, dtype=str, encoding="utf-8-sig")
    df = normalize_columns(df)
    df = remove_blank_rows(clean_text_columns(df))

    for field in TRANSACTION_EXPECTED_FIELDS:
        if field not in df.columns:
            df[field] = pd.NA

    if "date_time" not in df.columns and "date" in df.columns:
        df["date_time"] = df["date"]

    numeric_cols = [
        "quantity",
        "product_sales",
        "shipping_credits",
        "gift_wrap_credits",
        "promotional_rebates",
        "selling_fees",
        "fba_fees",
        "other_transaction_fees",
        "other",
        "total",
    ]
    for col in numeric_cols:
        df[col] = parse_numeric_series(df[col])

    transaction_dt = parse_datetime_series(df["date_time"])
    df["transaction_month"] = transaction_dt.dt.strftime("%Y-%m").fillna("Unknown")
    df["transaction_type_group"] = df["type"].map(standardize_transaction_type)
    df["fulfillment_type"] = df["fulfillment"].map(standardize_fulfillment)
    df["marketplace"] = df["marketplace"].map(standardize_marketplace)
    df["state_group"] = df["order_state"].map(standardize_state)
    df["sku"] = clean_text_series(df["sku"])

    product_sales = df["product_sales"]
    df["gross_sales_private"] = product_sales.where(product_sales > 0, 0.0)
    df["refund_amount_private"] = np.where(
        (product_sales < 0) | (df["transaction_type_group"].eq("Refund")),
        product_sales.abs(),
        0.0,
    )
    df["promotion_amount_private"] = df["promotional_rebates"].abs()
    df["amazon_fee_private"] = (
        df["selling_fees"].abs() + df["fba_fees"].abs() + df["other_transaction_fees"].abs()
    )
    df["net_amount_private"] = df["total"]
    df["units_private"] = np.where(
        df["transaction_type_group"].eq("Order") & (product_sales > 0),
        df["quantity"].clip(lower=0),
        0.0,
    )
    df["gross_sales_private_rs"] = df["gross_sales_private"]
    df["units_private_rs"] = df["units_private"]
    df["refund_amount_private_rs"] = df["refund_amount_private"]
    df["promotion_amount_private_rs"] = df["promotion_amount_private"]
    df["tax_amount_private_rs"] = parse_numeric_series(df.get("gst_tcs_tds", pd.Series(index=df.index)))
    df["shipping_credit_private_rs"] = df["shipping_credits"]
    df["selling_fee_private_rs"] = df["selling_fees"]
    df["fba_fee_private_rs"] = df["fba_fees"]
    df["other_fee_private_rs"] = df["other_transaction_fees"]
    df["total_fee_private_rs"] = df["amazon_fee_private"]
    df["net_amount_private_rs"] = df["net_amount_private"]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def build_private_master(
    transactions_path: Path = CLEAN_TRANSACTIONS,
    product_master_path: Path = CLEAN_PRODUCT_MASTER,
    marketplace_channel_path: Path = CLEAN_MARKETPLACE_CHANNEL_MASTER,
    output_path: Path = PRIVATE_MASTER,
) -> pd.DataFrame:
    ensure_directories()
    transactions = pd.read_csv(transactions_path, dtype=str)
    products = pd.read_csv(product_master_path, dtype=str)

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
    rows_with_sku = int(has_sku.sum())

    marketplace_join_coverage_pct = 0.0
    unmatched_marketplace_channel_rows_count = 0
    if marketplace_channel_path.exists():
        channels = pd.read_csv(marketplace_channel_path, dtype=str)
        if not channels.empty and {"seller_sku", "marketplace"} <= set(channels.columns):
            for col in CHANNEL_NUMERIC_COLUMNS:
                if col in channels.columns:
                    channels[col] = parse_numeric_series(channels[col])
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
            marketplace_join_coverage_pct = (int((has_sku & marketplace_matched).sum()) / rows_with_sku * 100.0) if rows_with_sku else 0.0
            unmatched_marketplace_channel_rows_count = int((has_sku & ~marketplace_matched).sum())
            merged["marketplace_channel_match"] = marketplace_matched
            merged = merged.drop(columns=["marketplace_channel_merge"], errors="ignore")
            if "channel" not in merged.columns:
                merged["channel"] = merged["marketplace"]
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

    transaction_skus = set(sku_series[has_sku].dropna().unique().tolist())
    listing_skus = set(clean_text_series(products["seller_sku"]).dropna().unique().tolist())
    unmatched_listing_skus = sorted(listing_skus - transaction_skus)
    matched_transaction_rows = int((has_sku & matched).sum())
    join_coverage_pct = (matched_transaction_rows / rows_with_sku * 100.0) if rows_with_sku else 0.0

    product_metrics = json.loads(PRODUCT_METRICS.read_text(encoding="utf-8")) if PRODUCT_METRICS.exists() else {}
    metrics = {
        "transaction_row_count": int(len(transactions)),
        "order_row_count": int(transactions.get("transaction_type_group", pd.Series(dtype=str)).eq("Order").sum()),
        "transaction_rows_with_sku": rows_with_sku,
        "product_master_row_count": int(len(products)),
        "marketplace_channel_row_count": int(len(pd.read_csv(marketplace_channel_path))) if marketplace_channel_path.exists() else 0,
        "matched_transaction_rows": matched_transaction_rows,
        "unmatched_transaction_rows": int((has_sku & ~matched).sum()),
        "unmatched_transaction_skus": int(len(unmatched_skus)),
        "unmatched_listing_skus": int(len(unmatched_listing_skus)),
        "join_coverage_pct": round(join_coverage_pct, 2),
        "marketplace_join_coverage_pct": round(marketplace_join_coverage_pct, 2),
        "unmatched_marketplace_channel_rows_count": unmatched_marketplace_channel_rows_count,
        "duplicate_sku_count": int(product_metrics.get("duplicate_sku_count", 0)),
        "products_with_all_5_channels_count": int(product_metrics.get("products_with_all_5_channels_count", 0)),
        "products_missing_channel_count": int(product_metrics.get("products_missing_channel_count", 0)),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    JOIN_METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return merged


def safe_group_value(value: object, default: str = "Unmapped") -> str:
    if pd.isna(value):
        return default
    text = re.sub(r"\s+", " ", str(value).strip())
    return text if text else default


def build_public_context(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["public_product_id"] = clean_text_series(df["public_product_id"]).fillna(NON_PRODUCT_ID)
    df["brand_group"] = df["brand"].map(lambda value: safe_group_value(value, "Unmapped"))
    df["category_group"] = df["category"].map(lambda value: safe_group_value(value, "Unmapped"))
    df["subcategory_group"] = df["subcategory"].map(lambda value: safe_group_value(value, "Unmapped"))
    df["product_group"] = df["product_group"].map(lambda value: safe_group_value(value, "Unmapped Product"))
    df["fulfillment_type"] = df["fulfillment_type"].map(lambda value: safe_group_value(value, "Unknown"))
    df["state_group"] = df["state_group"].map(lambda value: safe_group_value(value, "Unknown"))
    df["marketplace"] = df["marketplace"].map(lambda value: safe_group_value(value, "unknown"))
    df["listing_price_band"] = df["listing_price_band"].map(lambda value: safe_group_value(value, "Unknown"))
    df["inventory_band"] = df["inventory_band"].map(lambda value: safe_group_value(value, "Unknown"))
    df["mapping_status"] = df["mapping_status"].map(lambda value: safe_group_value(value, "Unmatched"))
    return df


def index_from_values(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").fillna(0.0).clip(lower=0.0)
    denominator = numeric.max()
    if denominator <= 0:
        return pd.Series(0.0, index=values.index)
    return (numeric / denominator * 100.0).clip(lower=0.0, upper=100.0)


def pct_of_gross(numerator: pd.Series, gross: pd.Series, *, signed: bool = False) -> pd.Series:
    num = pd.to_numeric(numerator, errors="coerce").fillna(0.0)
    den = pd.to_numeric(gross, errors="coerce").fillna(0.0)
    if not signed:
        num = num.abs()
    result = np.where(den > 0, num / den * 100.0, 0.0)
    lower = -300.0 if signed else 0.0
    return pd.Series(result, index=gross.index).clip(lower=lower, upper=300.0)


def add_public_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in PRIVATE_AMOUNT_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = parse_numeric_series(df[col])

    df["sales_index"] = index_from_values(df["gross_sales_private"]).round(1)
    df["units_index"] = index_from_values(df["units_private"]).round(1)
    df["fee_pct_of_gross"] = pct_of_gross(df["amazon_fee_private"], df["gross_sales_private"]).round(1)
    df["refund_pct_of_gross"] = pct_of_gross(df["refund_amount_private"], df["gross_sales_private"]).round(1)
    df["promotion_pct_of_gross"] = pct_of_gross(df["promotion_amount_private"], df["gross_sales_private"]).round(1)
    df["net_to_gross_pct"] = pct_of_gross(
        df["net_amount_private"], df["gross_sales_private"], signed=True
    ).round(1)
    return df


def recommended_action(row: pd.Series) -> tuple[str, str, str]:
    fee = float(row.get("fee_pct_of_gross", 0) or 0)
    refund = float(row.get("refund_pct_of_gross", 0) or 0)
    promo = float(row.get("promotion_pct_of_gross", 0) or 0)
    net = float(row.get("net_to_gross_pct", 0) or 0)
    sales = float(row.get("sales_index", 0) or 0)
    units = float(row.get("units_index", 0) or 0)
    price_band = str(row.get("listing_price_band", ""))
    inventory_band = str(row.get("inventory_band", ""))
    price_band_lower = price_band.lower()
    inventory_band_lower = inventory_band.lower()
    higher_price_band = (
        "high" in price_band_lower
        or "premium" in price_band_lower
        or price_band.startswith("3000")
        or price_band.startswith("4000")
        or price_band.endswith("+")
    )
    low_inventory_band = "out of stock" in inventory_band_lower or "low" in inventory_band_lower
    high_inventory_band = "high" in inventory_band_lower

    if fee >= 25 and sales >= 20:
        return "Fee Review", "High", "High sales-index product with elevated fee percentage."
    if refund >= 10 and sales >= 10:
        return "Refund Review", "High", "Meaningful sales-index product with elevated refund percentage."
    if promo >= 10 and net < 70:
        return "Promotion Review", "Medium", "Promotion percentage is elevated while net-to-gross is below target."
    if sales < 10 and units < 10 and higher_price_band:
        return "Pricing Review", "Medium", "Low indexed demand for a higher-price-band listing."
    if units >= 50 and low_inventory_band:
        return "Restock Review", "High", "High indexed unit movement with low inventory band."
    if units < 10 and high_inventory_band:
        return "Slow Mover Review", "Low", "Low indexed unit movement with high inventory band."
    return "Monitor", "Low", "No action threshold triggered; continue monitoring."


def add_actions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    actions = df.apply(recommended_action, axis=1, result_type="expand")
    actions.columns = ["recommended_action", "action_priority", "action_reason"]
    return pd.concat([df, actions], axis=1)


def anonymize_and_index_master(
    private_master_path: Path = PRIVATE_MASTER,
    output_path: Path = PUBLIC_OUTPUTS["anonymized_master"],
) -> pd.DataFrame:
    private = pd.read_csv(private_master_path, dtype=str)
    public = shared_build_public_outputs(private, dataset_period=str(private.get("dataset_period", pd.Series(["custom"])).iloc[0]))[
        "anonymized_master"
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    public.to_csv(output_path, index=False)
    return public


def product_count(series: pd.Series) -> int:
    values = clean_text_series(series).dropna()
    values = values[values != NON_PRODUCT_ID]
    return int(values.nunique())


def aggregate_public(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    group_cols = list(group_cols)
    grouped = df.groupby(group_cols, dropna=False)
    result = grouped.agg(
        gross_sales_private=("gross_sales_private", "sum"),
        units_private=("units_private", "sum"),
        amazon_fee_private=("amazon_fee_private", "sum"),
        refund_amount_private=("refund_amount_private", "sum"),
        promotion_amount_private=("promotion_amount_private", "sum"),
        net_amount_private=("net_amount_private", "sum"),
        product_count=("public_product_id", product_count),
    ).reset_index()

    order_rows = df[df["transaction_type_group"].eq("Order") & clean_text_series(df["order_id"]).notna()]
    if not order_rows.empty:
        orders = order_rows.groupby(group_cols, dropna=False)["order_id"].nunique().reset_index(name="order_count")
        result = result.merge(orders, on=group_cols, how="left")
    else:
        result["order_count"] = 0
    result["order_count"] = result["order_count"].fillna(0).astype(int)

    result = add_public_metrics(result)
    return result


def public_private_master() -> pd.DataFrame:
    private = pd.read_csv(PRIVATE_MASTER, dtype=str)
    for col in PRIVATE_AMOUNT_COLUMNS:
        private[col] = parse_numeric_series(private[col])
    return build_public_context(private)


def build_public_outputs(private_master_path: Path = PRIVATE_MASTER) -> dict[str, pd.DataFrame]:
    ensure_directories()
    private = pd.read_csv(private_master_path, dtype=str)
    dataset_period = str(private["dataset_period"].dropna().iloc[0]) if "dataset_period" in private.columns and private["dataset_period"].notna().any() else "custom"
    outputs = shared_build_public_outputs(private, dataset_period=dataset_period)
    for name, data in outputs.items():
        if name in PUBLIC_OUTPUTS:
            PUBLIC_OUTPUTS[name].parent.mkdir(parents=True, exist_ok=True)
            data.to_csv(PUBLIC_OUTPUTS[name], index=False)
    return outputs


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def collect_public_files() -> list[Path]:
    return [path for name, path in PUBLIC_OUTPUTS.items() if name != "validation_summary" and path.exists()]


def validation_row(check_name: str, passed: bool, value: object, expected: object, notes: str = "") -> dict[str, str]:
    return {
        "check_name": check_name,
        "check_status": "PASS" if passed else "FAIL",
        "check_value": str(value),
        "expected_value": str(expected),
        "notes": notes,
    }


def public_columns_are_safe(path: Path) -> tuple[bool, list[str]]:
    banned_exact = {
        "asin",
        "asin1",
        "seller_sku",
        "sku",
        "order_id",
        "listing_id",
        "product_id",
        "item_name",
        "item_description",
        "description",
        "order_postal",
        "gross_sales_private",
        "refund_amount_private",
        "promotion_amount_private",
        "amazon_fee_private",
        "net_amount_private",
        "product_sales",
        "selling_fees",
        "fba_fees",
        "other_transaction_fees",
        "total",
        "price",
        "maximum_retail_price",
    }
    df = pd.read_csv(path, nrows=5)
    unsafe = [col for col in df.columns if col in banned_exact]
    return not unsafe, unsafe


def public_has_metric_fields(path: Path) -> bool:
    if path.name in {"validation_summary.csv", "dataset_profile.csv"}:
        return True
    df = pd.read_csv(path, nrows=5)
    if any(
        col.endswith("_index") or col.endswith("_score") or col.endswith("_pct_of_gross") or col.endswith("_to_gross_pct")
        for col in df.columns
    ):
        return True
    # Variance marts are long-format (one row per metric x dimension): the
    # metric identity lives in the "metric"/"metric_label" column rather than
    # in the column name itself, and that metric column's domain is
    # restricted to the same already-public index/score/pct_of_gross metric
    # set (see shared/variance_engine.py:METRIC_LABELS) — never a raw amount.
    if path.name in {
        "mart_marketplace_variance_drivers.csv",
        "mart_product_variance_contributors.csv",
        "mart_performance_driver_summary.csv",
    }:
        metric_col = "metric" if "metric" in df.columns else None
        return metric_col is not None
    return False


# Period-over-period *variance* percentages (e.g. "sales_index rose 400%")
# are not bounded the way a percent-of-gross ratio is, so they are a
# distinct metric type and are excluded from the range check below. They
# still pass through the same privacy content scan as every other column.
VARIANCE_PCT_COLUMNS = {"pct_variance", "total_pct_variance"}


def ratio_columns_reasonable(path: Path) -> tuple[bool, str]:
    df = pd.read_csv(path)
    ratio_cols = [col for col in df.columns if "pct" in col and col not in VARIANCE_PCT_COLUMNS]
    if not ratio_cols:
        return True, "No ratio columns"
    for col in ratio_cols:
        values = pd.to_numeric(df[col], errors="coerce").dropna()
        if values.empty:
            continue
        lower = -300 if "net_to_gross" in col or "avg_net_to_gross" in col else 0
        if ((values < lower) | (values > 300)).any():
            return False, f"{path.name}:{col}"
    return True, ",".join(ratio_cols)


def public_metric_has_activity(path: Path, metric_columns: Iterable[str]) -> bool:
    if not path.exists():
        return False
    df = pd.read_csv(path)
    for col in metric_columns:
        if col not in df.columns:
            continue
        values = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        if values.gt(0).any():
            return True
    return False


def validate_outputs() -> pd.DataFrame:
    ensure_directories()
    product_metrics = read_json(PRODUCT_METRICS)
    join_metrics = read_json(JOIN_METRICS)
    rows: list[dict[str, str]] = []

    rows.append(validation_row("private raw files exist", PRODUCT_MASTER_RAW.exists() and TRANSACTION_RAW.exists(), "found", "both files"))

    product_loads = CLEAN_PRODUCT_MASTER.exists()
    txn_loads = CLEAN_TRANSACTIONS.exists()
    rows.append(validation_row("product master loads successfully", product_loads, CLEAN_PRODUCT_MASTER.exists(), True))
    rows.append(validation_row("transaction report loads successfully", txn_loads, CLEAN_TRANSACTIONS.exists(), True))

    product_count_value = int(product_metrics.get("product_master_row_count", 0))
    transaction_count_value = int(join_metrics.get("transaction_row_count", 0))
    order_count_value = int(join_metrics.get("order_row_count", 0) or 0)
    dataset_period_value = "custom"
    if PRIVATE_MASTER.exists():
        private_preview = pd.read_csv(PRIVATE_MASTER, usecols=lambda col: col == "dataset_period")
        if "dataset_period" in private_preview.columns and private_preview["dataset_period"].notna().any():
            dataset_period_value = str(private_preview["dataset_period"].dropna().iloc[0])
    rows.append(validation_row("product master row count > 0", product_count_value > 0, product_count_value, "> 0"))
    rows.append(validation_row("transaction row count > 0", transaction_count_value > 0, transaction_count_value, "> 0"))
    rows.append(
        validation_row(
            "dataset label matches selected transaction volume",
            bool(dataset_period_value),
            dataset_label(dataset_period_value, transaction_rows=transaction_count_value, order_rows=order_count_value),
            "1M / 10K, 3M / 30K, 6M / 60K, 12M / 120K, or Custom Upload",
        )
    )

    sku_columns_exist = False
    if CLEAN_PRODUCT_MASTER.exists() and CLEAN_TRANSACTIONS.exists():
        product_cols = set(pd.read_csv(CLEAN_PRODUCT_MASTER, nrows=1).columns)
        txn_cols = set(pd.read_csv(CLEAN_TRANSACTIONS, nrows=1).columns)
        sku_columns_exist = "seller_sku" in product_cols and "sku" in txn_cols
    rows.append(validation_row("SKU column exists in both files", sku_columns_exist, sku_columns_exist, True))

    rows.append(
        validation_row(
            "duplicate SKU count is reported",
            "duplicate_sku_count" in join_metrics,
            join_metrics.get("duplicate_sku_count", "missing"),
            "reported",
        )
    )
    rows.append(
        validation_row(
            "unmatched transaction SKU count is reported",
            "unmatched_transaction_skus" in join_metrics,
            join_metrics.get("unmatched_transaction_skus", "missing"),
            "reported",
        )
    )
    rows.append(
        validation_row(
            "join coverage percentage is calculated",
            "join_coverage_pct" in join_metrics,
            join_metrics.get("join_coverage_pct", "missing"),
            "reported",
        )
    )

    required_public = [path for name, path in PUBLIC_OUTPUTS.items() if name != "validation_summary"]
    public_created = all(path.exists() for path in required_public)
    rows.append(
        validation_row(
            "public output files are created",
            public_created,
            sum(path.exists() for path in required_public),
            len(required_public),
            "Counts outputs excluding validation_summary; total public CSVs including it is 14.",
        )
    )

    unsafe_by_file: list[str] = []
    for path in collect_public_files():
        safe, unsafe = public_columns_are_safe(path)
        if not safe:
            unsafe_by_file.append(f"{path.name}: {','.join(unsafe)}")
    rows.append(validation_row("public files do not contain ASIN", not unsafe_by_file, "; ".join(unsafe_by_file) or "safe", "safe columns"))
    rows.append(validation_row("public files do not contain seller SKU", not unsafe_by_file, "; ".join(unsafe_by_file) or "safe", "safe columns"))
    rows.append(validation_row("public files do not contain order ID", not unsafe_by_file, "; ".join(unsafe_by_file) or "safe", "safe columns"))
    rows.append(validation_row("public files do not contain item description", not unsafe_by_file, "; ".join(unsafe_by_file) or "safe", "safe columns"))
    rows.append(validation_row("public files do not contain raw currency columns", not unsafe_by_file, "; ".join(unsafe_by_file) or "safe", "safe columns"))

    public_frames = {path.stem: pd.read_csv(path) for path in collect_public_files()}
    privacy_scan = shared_scan_public_outputs(public_frames)
    content_hit_count = int(privacy_scan.get("content_hit_count", 0) or 0)
    rows.append(validation_row("public files do not contain sensitive-looking cell values", content_hit_count == 0, content_hit_count, "0 content hits"))
    rows.append(validation_row("content-level privacy scan passes", bool(privacy_scan.get("is_safe")), "safe" if privacy_scan.get("is_safe") else "review", "safe"))

    content_totals = {
        "No ASIN-like values in public outputs": "asin_like_values",
        "No known SKU/private ID values in public outputs": "known_private_identifier_values",
        "No order-ID-like values in public outputs": "order_id_like_values",
        "No postal-code-like values in public outputs": "postal_code_like_values",
        "No currency-marker values in public outputs": "currency_marker_values",
    }
    content_by_output = privacy_scan.get("content_scan_by_output", {})
    for check_name, key in content_totals.items():
        hit_count = sum(int(output_scan.get(key, 0) or 0) for output_scan in content_by_output.values())
        rows.append(validation_row(check_name, hit_count == 0, hit_count, "0 content hits"))

    metric_field_check = all(public_has_metric_fields(path) for path in collect_public_files())
    rows.append(validation_row("public files contain indexes/ratios instead of raw amounts", metric_field_check, metric_field_check, True))
    rows.append(
        validation_row(
            "public sales indexes contain activity",
            public_metric_has_activity(PUBLIC_OUTPUTS["anonymized_master"], ["sales_index", "units_index"]),
            "sales_index, units_index",
            "nonzero when transactions contain sales activity",
        )
    )
    rows.append(
        validation_row(
            "aggregated sales indexes contain activity",
            public_metric_has_activity(PUBLIC_OUTPUTS["product_performance"], ["sales_index", "units_index"])
            and public_metric_has_activity(PUBLIC_OUTPUTS["marketplace_summary"], ["sales_index", "units_index"]),
            "product_performance and marketplace_summary",
            "nonzero when transactions contain sales activity",
        )
    )

    ratio_results = [ratio_columns_reasonable(path) for path in collect_public_files()]
    ratio_ok = all(status for status, _ in ratio_results)
    rows.append(
        validation_row(
            "financial ratio columns are within reasonable range",
            ratio_ok,
            "; ".join(detail for _, detail in ratio_results),
            "0 to 300 pct, net-to-gross can be -300 to 300",
        )
    )

    public_ids_ok = False
    if PUBLIC_OUTPUTS["product_performance"].exists():
        product_performance = pd.read_csv(PUBLIC_OUTPUTS["product_performance"])
        public_ids_ok = product_performance["public_product_id"].notna().all() and (product_performance["public_product_id"].astype(str).str.len() > 0).all()
    rows.append(validation_row("public product IDs are populated", public_ids_ok, public_ids_ok, True))

    actions_ok = False
    if PUBLIC_OUTPUTS["product_action_review"].exists():
        actions = pd.read_csv(PUBLIC_OUTPUTS["product_action_review"])
        actions_ok = actions["recommended_action"].notna().all() and actions["recommended_action"].astype(str).str.len().gt(0).all()
    rows.append(validation_row("recommended actions are populated", actions_ok, actions_ok, True))

    profitability_ok = PUBLIC_OUTPUTS["profitability_summary"].exists() and not pd.read_csv(PUBLIC_OUTPUTS["profitability_summary"]).empty
    margin_risk_ok = PUBLIC_OUTPUTS["margin_risk_review"].exists() and "margin_risk_score" in pd.read_csv(PUBLIC_OUTPUTS["margin_risk_review"], nrows=1).columns
    revenue_quality_ok = PUBLIC_OUTPUTS["product_performance"].exists() and "revenue_quality_score" in pd.read_csv(PUBLIC_OUTPUTS["product_performance"], nrows=1).columns
    rows.append(validation_row("profitability bands are generated", profitability_ok, profitability_ok, True))
    rows.append(validation_row("margin risk scores are generated", margin_risk_ok, margin_risk_ok, True))
    rows.append(validation_row("revenue quality scores are generated", revenue_quality_ok, revenue_quality_ok, True))
    dataset_profile_has_label = PUBLIC_OUTPUTS["dataset_profile"].exists() and "dataset_label" in pd.read_csv(PUBLIC_OUTPUTS["dataset_profile"], nrows=1).columns
    rows.append(validation_row("dataset_profile includes display label", dataset_profile_has_label, "dataset_label" if dataset_profile_has_label else "missing", "present"))

    rows.append(validation_row("validation_summary.csv is generated", True, PUBLIC_OUTPUTS["validation_summary"].name, "generated"))

    summary = pd.DataFrame(rows)
    PUBLIC_OUTPUTS["validation_summary"].parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(PUBLIC_OUTPUTS["validation_summary"], index=False)
    return summary
