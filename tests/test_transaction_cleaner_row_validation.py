"""Regression tests for UAT-03: a structurally valid transaction CSV (real
Amazon-style preamble + real header row) that contains zero data rows must
get a clear, specific "no transaction rows" message — not the misleading
"transaction date column could not be parsed" error that a genuinely
malformed date column should still trigger.

See app/utils/transaction_cleaner.py:clean_transaction_file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.utils.data_cleaner import AppDataError
from app.utils.transaction_cleaner import clean_transaction_file

HEADER_LINES = [
    '"Includes Amazon Marketplace, Fulfillment by Amazon (FBA), and Amazon Webstore transactions"',
    '"Date Range: 01 May 2026 - 31 May 2026"',
    '"Generated: 01 Jun 2026"',
    '"Report Type: Unified Transaction Report"',
    '"Currency: INR"',
    '"Marketplace: Amazon.in"',
    '"Seller ID: A1B2C3D4E5"',
    '"Merchant Token: TOKEN-XYZ"',
    '""',
    '"Column definitions available at seller central help"',
    '""',
    '"All amounts in INR, unless specified"',
    '""',
    '"date/time","settlement id","type","order id","Sku","description","quantity","marketplace","fulfillment","order city","order state","order postal","product sales","shipping credits","gift wrap credits","promotional rebates","selling fees","fba fees","other transaction fees","other","total"',
]


def _write_csv(tmp_path: Path, name: str, data_rows: list[str]) -> Path:
    path = tmp_path / name
    path.write_text("\n".join(HEADER_LINES + data_rows), encoding="utf-8")
    return path


def make_zero_row_transaction_file(tmp_path: Path) -> Path:
    """Valid 14-line preamble + real header row, then nothing at all —
    exactly the scenario reported for UAT-03."""
    return _write_csv(tmp_path, "zero_row_transactions.csv", [])


def make_valid_transaction_file(tmp_path: Path) -> Path:
    return _write_csv(
        tmp_path,
        "valid_transactions.csv",
        [
            '"1 May 2026 10:00:00 am UTC","1","Order","ORDER-1","SKU-1","Private Product One","2","amazon.in","Amazon","Mumbai","MAHARASHTRA","400001","1000","0","0","-50","-100","-80","-20","0","750"',
            '"1 May 2026 11:00:00 am UTC","1","Refund","ORDER-2","SKU-2","Private Product Two","1","amazon.in","Amazon","Pune","MAHARASHTRA","411001","-300","0","0","0","0","0","0","0","-300"',
        ],
    )


def make_malformed_date_transaction_file(tmp_path: Path) -> Path:
    """Real rows present, but every date/time value is unparsable garbage —
    this must still hit the existing date-specific error."""
    return _write_csv(
        tmp_path,
        "malformed_date_transactions.csv",
        [
            '"NOT-A-DATE","1","Order","ORDER-1","SKU-1","Private Product One","2","amazon.in","Amazon","Mumbai","MAHARASHTRA","400001","1000","0","0","-50","-100","-80","-20","0","750"',
            '"###ALSO-NOT-A-DATE###","1","Refund","ORDER-2","SKU-2","Private Product Two","1","amazon.in","Amazon","Pune","MAHARASHTRA","411001","-300","0","0","0","0","0","0","0","-300"',
        ],
    )


def test_zero_row_transaction_file_gives_clear_no_rows_message(tmp_path):
    path = make_zero_row_transaction_file(tmp_path)
    with pytest.raises(AppDataError) as exc_info:
        clean_transaction_file(path)

    message = str(exc_info.value)
    assert "no transaction rows" in message.lower()
    assert "at least one transaction record" in message.lower()
    # It must NOT be misattributed to the date column.
    assert "date column could not be parsed" not in message


def test_zero_row_transaction_file_error_is_an_app_data_error_not_a_traceback(tmp_path):
    # AppDataError is the app's user-facing exception boundary; catching it
    # here (rather than some lower-level pandas/ValueError) confirms the
    # Streamlit layer will render a friendly message, not a raw traceback.
    path = make_zero_row_transaction_file(tmp_path)
    with pytest.raises(AppDataError):
        clean_transaction_file(path)


def test_valid_schema_with_valid_rows_still_loads_normally(tmp_path):
    path = make_valid_transaction_file(tmp_path)
    df, metrics = clean_transaction_file(path)
    assert len(df) == 2
    assert metrics["transaction_row_count"] == 2
    assert {"sku", "gross_sales_private", "refund_amount_private"} <= set(df.columns)


def test_malformed_date_column_with_real_rows_still_gives_date_specific_error(tmp_path):
    path = make_malformed_date_transaction_file(tmp_path)
    with pytest.raises(AppDataError) as exc_info:
        clean_transaction_file(path)

    message = str(exc_info.value)
    assert "date column could not be parsed" in message
    # And must NOT be misattributed to the (false) zero-rows case, since
    # rows genuinely exist here -- only their date values are bad.
    assert "no transaction rows" not in message.lower()


# ---------------------------------------------------------------------------
# Regression coverage for UAT-02 (missing required column) and UAT-04
# (non-CSV payload renamed .csv) -- these UAT cases were already executed
# (UAT-02 automated, UAT-04 manually by the project owner), but no
# dedicated automated test actually exercised this exact scenario before.
# Added here so the citations in docs/uat/uat_test_cases.csv are backed by
# a real, specific test rather than an unrelated file (Priority 3 review).
# ---------------------------------------------------------------------------


def make_transaction_file_missing_sku_column(tmp_path: Path) -> Path:
    """Same valid preamble/header shape as a real export, but the SKU
    column itself is absent from the header row."""
    header_without_sku = [line for line in HEADER_LINES[:-1]]
    header_without_sku.append(
        '"date/time","settlement id","type","order id","description","quantity","marketplace","fulfillment","order city","order state","order postal","product sales","shipping credits","gift wrap credits","promotional rebates","selling fees","fba fees","other transaction fees","other","total"'
    )
    path = tmp_path / "missing_sku_transactions.csv"
    data_row = '"1 May 2026 10:00:00 am UTC","1","Order","ORDER-1","Private Product One","2","amazon.in","Amazon","Mumbai","MAHARASHTRA","400001","1000","0","0","-50","-100","-80","-20","0","750"'
    path.write_text("\n".join(header_without_sku + [data_row]), encoding="utf-8")
    return path


def test_missing_sku_column_gives_specific_error(tmp_path):
    # detect_transaction_header_row() itself requires a SKU-shaped column
    # to recognize a row as the real header (alongside date/finance/order
    # columns) -- so a file whose header genuinely lacks a SKU column never
    # gets treated as having a valid header at all, and surfaces the same
    # "does not contain recognizable marketplace transaction columns"
    # message as a non-CSV file (both are schema-recognition failures).
    # This is documented here as the real, verified behavior rather than
    # assumed.
    path = make_transaction_file_missing_sku_column(tmp_path)
    with pytest.raises(AppDataError) as exc_info:
        clean_transaction_file(path)
    message = str(exc_info.value)
    assert "recognizable marketplace transaction columns" in message
    assert "check the file and upload again" in message.lower()


def make_non_csv_payload_renamed_csv(tmp_path: Path) -> Path:
    """A binary PNG-like payload saved with a .csv extension -- no
    recognizable header row anywhere in the file."""
    path = tmp_path / "not_actually_a_csv.csv"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64 + b"this is not a transaction report at all")
    return path


def test_non_csv_payload_renamed_csv_gives_clear_message_not_a_traceback(tmp_path):
    path = make_non_csv_payload_renamed_csv(tmp_path)
    with pytest.raises(AppDataError) as exc_info:
        clean_transaction_file(path)
    message = str(exc_info.value)
    assert "recognizable marketplace transaction columns" in message
    assert "check the file and upload again" in message.lower()
