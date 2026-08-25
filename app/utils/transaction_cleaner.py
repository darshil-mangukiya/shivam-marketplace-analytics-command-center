from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app.utils.data_cleaner import AppDataError, clean_text_columns, clean_text_series, normalize_columns, remove_blank_rows
from pipeline_utils import (  # type: ignore
    TRANSACTION_EXPECTED_FIELDS,
    detect_transaction_header_row,
    parse_datetime_series,
    parse_numeric_series,
    standardize_fulfillment,
    standardize_marketplace,
    standardize_state,
    standardize_transaction_type,
)
from shared.contracts import load_contract, validate_dataframe
from shared.quarantine import combine_quarantine, quarantine_totals, summarize_quarantine

TRANSACTION_CONTRACT = load_contract("marketplace_transactions.yml")


def clean_transaction_file(input_path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    if input_path.suffix.lower() != ".csv":
        raise AppDataError("The monthly transaction report must be a CSV file.")
    if not input_path.exists():
        raise AppDataError("The uploaded transaction report could not be found in the local session.")

    try:
        header_row = detect_transaction_header_row(input_path)
        df = pd.read_csv(input_path, skiprows=header_row, dtype=str, encoding="utf-8-sig")
    except Exception as exc:
        raise AppDataError(
            "The uploaded transaction file does not contain recognizable marketplace transaction columns. "
            "Please check the file and upload again."
        ) from exc

    df = normalize_columns(df)
    df = remove_blank_rows(clean_text_columns(df))

    if "sku" not in df.columns:
        raise AppDataError(
            "The uploaded transaction file does not contain a recognizable SKU column. "
            "Please check the file and upload again."
        )
    if "date_time" not in df.columns and "date" not in df.columns:
        raise AppDataError(
            "The uploaded transaction file does not contain a recognizable transaction date column."
        )
    if not {"product_sales", "total"} & set(df.columns):
        raise AppDataError(
            "The uploaded transaction file does not contain recognizable financial columns such as product sales or total."
        )

    # The header/schema is now confirmed valid (SKU, date, and financial
    # columns were all recognized above). Check for a zero-row file HERE —
    # before date parsing or any other downstream transformation — so a
    # structurally valid file with no transaction data rows gets its own
    # clear message instead of falling through to date parsing, where an
    # empty date series would otherwise trivially satisfy `notna().sum() ==
    # 0` and produce the misleading "date column could not be parsed" error.
    if df.empty:
        raise AppDataError(
            "The uploaded transaction file contains no transaction rows. "
            "Please upload a file with at least one transaction record."
        )

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
    if transaction_dt.notna().sum() == 0:
        raise AppDataError("The transaction date column could not be parsed. Please check the uploaded CSV.")

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

    # Contract validation — the LAST step, after every existing
    # header-detection, cleaning, normalization, and standardization step
    # above has already run. This is a genuine, live-wired gate (not a
    # standalone/unused framework): rows whose sku is missing/blank, whose
    # marketplace isn't a recognized value, or whose numeric fields fall
    # outside the contract's declared range are rejected or warned per
    # contracts/marketplace_transactions.yml's declared severities. Reject-
    # level rows are excluded from the returned DataFrame (quarantined, not
    # silently kept); warn-level rows are kept and only logged. See
    # shared/contracts.py module docstring for the full integration note.
    rows_before_contract = len(df)
    accepted_df, rejected_records, warning_records = validate_dataframe(
        df, TRANSACTION_CONTRACT, input_path.name
    )
    quarantine_ledger = combine_quarantine(rejected_records, warning_records)
    quarantine_summary = summarize_quarantine(quarantine_ledger)
    quarantine_totals_dict = quarantine_totals(
        rejected_records, warning_records, rows_before_contract, len(accepted_df)
    )

    if accepted_df.empty and rows_before_contract > 0:
        # Every row failed contract validation (e.g. every row has a blank
        # SKU) -- distinct from the earlier "file has zero rows" check,
        # which fires before any contract logic even runs.
        raise AppDataError(
            "Every row in the uploaded transaction file failed contract validation "
            f"({quarantine_totals_dict['rejected_rows']} row(s) rejected: missing or "
            "invalid required fields). Please check the file and upload again."
        )
    df = accepted_df

    metrics = {
        "source_file": input_path.name,
        "header_row_zero_based": int(header_row),
        "transaction_row_count": int(len(df)),
        "order_row_count": int(df["transaction_type_group"].eq("Order").sum()),
        "transaction_rows_with_sku": int(df["sku"].notna().sum()),
        "unique_transaction_skus": int(df["sku"].dropna().nunique()),
        "marketplace_count": int(df["marketplace"].nunique()),
        "transaction_months": sorted(df["transaction_month"].dropna().unique().tolist()),
        "contract_total_rows": rows_before_contract,
        "contract_accepted_rows": quarantine_totals_dict["accepted_rows"],
        "contract_rejected_rows": quarantine_totals_dict["rejected_rows"],
        "contract_warning_rows": quarantine_totals_dict["warning_rows"],
        "quarantine_ledger": quarantine_ledger,
        "quarantine_summary": quarantine_summary,
    }
    return df, metrics
