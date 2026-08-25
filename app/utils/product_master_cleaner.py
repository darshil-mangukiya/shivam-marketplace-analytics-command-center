from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.utils.data_cleaner import AppDataError, clean_text_columns, clean_text_series, normalize_columns, remove_blank_rows
from pipeline_utils import (  # type: ignore
    PRODUCT_EXPECTED_FIELDS,
    assign_missing_public_ids,
    derive_inventory_band,
    derive_price_band,
    detect_product_sheet_and_header,
    parse_numeric_series,
)
from shared.contracts import load_contract, validate_dataframe
from shared.quarantine import combine_quarantine, quarantine_totals, summarize_quarantine

PRODUCT_MASTER_CONTRACT = load_contract("product_master.yml")


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


def apply_product_aliases(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for source, target in ADVANCED_PRODUCT_ALIASES.items():
        if source in df.columns and target not in df.columns:
            df[target] = df[source]
    return df


def clean_product_master_file(input_path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    if input_path.suffix.lower() not in {".xlsx", ".xls"}:
        raise AppDataError("The product master must be an Excel file with .xlsx or .xls extension.")
    if not input_path.exists():
        raise AppDataError("The uploaded product master file could not be found in the local session.")

    try:
        sheet_name, header_row = detect_product_sheet_and_header(input_path)
        df = pd.read_excel(input_path, sheet_name=sheet_name, header=header_row, dtype=str)
    except Exception as exc:
        raise AppDataError(
            "The product master could not be read. Please upload the prepared listing workbook."
        ) from exc

    df = normalize_columns(df)
    df = apply_product_aliases(df)
    df = remove_blank_rows(clean_text_columns(df))
    if "seller_sku" not in df.columns:
        raise AppDataError(
            "The uploaded product master does not contain a recognizable seller SKU column. "
            "Please check the file and upload again."
        )

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
        df[col] = clean_text_series(df[col])

    missing_brand_count = int(df["brand"].isna().sum())
    missing_category_count = int(df["category"].isna().sum())
    missing_product_group_count = int(df["product_group"].isna().sum())

    df["brand"] = df["brand"].fillna("Unmapped")
    df["category"] = df["category"].fillna("Unmapped")
    df["subcategory"] = df["subcategory"].fillna("Unmapped")
    df["product_group"] = df["product_group"].fillna("Unmapped Product")
    df["mapping_status"] = df["mapping_status"].fillna("Unmatched")
    df["margin_band_public"] = df["margin_band_public"].fillna("Unknown")
    df["profitability_band_public"] = df["profitability_band_public"].fillna("Unknown")
    df["restock_priority"] = df["restock_priority"].fillna("Monitor")
    df["origin_country"] = df["origin_country"].fillna("Unknown")
    df["imported_flag"] = df["imported_flag"].fillna("Unknown")

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

    # Contract validation — the LAST step, after header/sheet detection,
    # aliasing, cleaning, numeric parsing, and band derivation have already
    # run. seller_sku uniqueness/non-nullness is already procedurally
    # guaranteed above (dropna + drop_duplicates), so this mainly catches
    # out-of-range numeric values and unrecognized inventory bands as
    # warnings — a genuine, live-wired additional gate, not a standalone
    # framework. See shared/contracts.py module docstring.
    rows_before_contract = len(df)
    accepted_df, rejected_records, warning_records = validate_dataframe(
        df, PRODUCT_MASTER_CONTRACT, input_path.name
    )
    quarantine_ledger = combine_quarantine(rejected_records, warning_records)
    quarantine_summary = summarize_quarantine(quarantine_ledger)
    quarantine_totals_dict = quarantine_totals(
        rejected_records, warning_records, rows_before_contract, len(accepted_df)
    )

    if accepted_df.empty and rows_before_contract > 0:
        raise AppDataError(
            "Every row in the uploaded product master failed contract validation "
            f"({quarantine_totals_dict['rejected_rows']} row(s) rejected: missing or "
            "invalid required fields). Please check the file and upload again."
        )
    df = accepted_df

    metrics = {
        "source_file": input_path.name,
        "sheet_name": sheet_name,
        "header_row_zero_based": int(header_row),
        "product_master_row_count": int(len(df)),
        "unique_product_master_skus": int(df["seller_sku"].nunique()),
        "duplicate_sku_count": duplicate_sku_count,
        "missing_brand_count": missing_brand_count,
        "missing_category_count": missing_category_count,
        "missing_product_group_count": missing_product_group_count,
        "cost_columns_detected": int(sum(col in df.columns for col in ADVANCED_NUMERIC_COLUMNS)),
        "contract_total_rows": rows_before_contract,
        "contract_accepted_rows": quarantine_totals_dict["accepted_rows"],
        "contract_rejected_rows": quarantine_totals_dict["rejected_rows"],
        "contract_warning_rows": quarantine_totals_dict["warning_rows"],
        "quarantine_ledger": quarantine_ledger,
        "quarantine_summary": quarantine_summary,
    }
    return df, metrics
