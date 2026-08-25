"""Integration tests for contracts and quarantine in the upload workflow.

These tests exercise the real functions the Streamlit app actually calls
(`app.utils.transaction_cleaner.clean_transaction_file`,
`app.utils.product_master_cleaner.clean_product_master_file`,
`app.utils.data_loader.run_analysis_from_uploads_with_options`) end to end
without mocking the integration points.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.utils.data_cleaner import AppDataError
from app.utils.data_loader import run_analysis_from_uploads_with_options
from app.utils.product_master_cleaner import clean_product_master_file
from app.utils.transaction_cleaner import clean_transaction_file
from shared.contracts import REJECTED_ROW_COLUMNS, PublicOutputContractError
from tests.test_app_data_loader import UploadStub, make_product_file, make_transaction_file

HEADER_LINES = [
    '"Includes Amazon Marketplace, Fulfillment by Amazon (FBA), and Amazon Webstore transactions"',
    '"All amounts in INR, unless specified"',
    '"date/time","settlement id","type","order id","Sku","description","quantity","marketplace","fulfillment","order city","order state","order postal","product sales","shipping credits","gift wrap credits","promotional rebates","selling fees","fba fees","other transaction fees","other","total"',
]


def _write_transaction_csv(tmp_path: Path, name: str, data_rows: list[str]) -> Path:
    path = tmp_path / name
    path.write_text("\n".join(HEADER_LINES + data_rows), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 1 & 2: the live upload paths genuinely invoke contract validation
# ---------------------------------------------------------------------------


def test_live_transaction_upload_path_invokes_contract_validation(tmp_path):
    df, metrics = clean_transaction_file(make_transaction_file(tmp_path))
    # These keys only exist if validate_dataframe() actually ran.
    assert "contract_total_rows" in metrics
    assert "contract_accepted_rows" in metrics
    assert "quarantine_ledger" in metrics
    assert list(metrics["quarantine_ledger"].columns) == REJECTED_ROW_COLUMNS or metrics["quarantine_ledger"].empty


def test_live_product_master_upload_path_invokes_contract_validation(tmp_path):
    df, metrics = clean_product_master_file(make_product_file(tmp_path))
    assert "contract_total_rows" in metrics
    assert "contract_accepted_rows" in metrics
    assert "quarantine_ledger" in metrics


# ---------------------------------------------------------------------------
# 3: valid uploads still succeed, unchanged
# ---------------------------------------------------------------------------


def test_valid_uploads_still_succeed_with_zero_rejections(tmp_path):
    result = run_analysis_from_uploads_with_options(
        UploadStub(make_product_file(tmp_path)), UploadStub(make_transaction_file(tmp_path)), dataset_period="custom"
    )
    assert result["quarantine_totals"]["rejected_rows"] == 0
    assert not result["outputs"]["product_performance"].empty


# ---------------------------------------------------------------------------
# 4: a reject-level contract violation produces a controlled AppDataError
# ---------------------------------------------------------------------------


def test_reject_level_violation_produces_controlled_app_data_error(tmp_path, monkeypatch):
    # HONESTY NOTE: by the time contract validation runs (the last step,
    # after the existing cleaning pipeline), sku/marketplace values are
    # already thoroughly defaulted by the upstream cleaning (blank
    # marketplace -> "Unknown" text via standardize_marketplace(), blank
    # numeric fields -> 0.0 via parse_numeric_series()) -- verified against
    # the real 141K-row dataset, which produced zero contract rejections.
    # A genuine, easily-constructed "every row rejected" scenario is
    # therefore hard to produce through real messy input at this late
    # integration point BY DESIGN (the existing cleaning is thorough) — so
    # this test exercises the actual wrapping logic in
    # transaction_cleaner.py directly (accepted_df.empty -> AppDataError)
    # by making validate_dataframe report an all-rejected result, the same
    # way it demonstrably can for a contract with a genuinely still-null
    # required field (see tests/test_contracts.py for the contract-layer
    # reject mechanics in isolation).
    import app.utils.transaction_cleaner as tc

    empty_columns = ["source_name", "row_number", "error_code", "error_category", "validation_rule", "reason", "severity", "timestamp"]

    def _fake_validate_dataframe(df, contract, source_name):
        rejected = pd.DataFrame(
            [{
                "source_name": source_name, "row_number": 0, "error_code": "MISSING_REQUIRED_VALUE",
                "error_category": "VALIDATION_ERROR", "validation_rule": "fields.sku.nullable=false",
                "reason": "Required field 'sku' is missing on this row.", "severity": "reject", "timestamp": "now",
            }],
            columns=empty_columns,
        )
        return df.iloc[0:0], rejected, pd.DataFrame(columns=empty_columns)

    monkeypatch.setattr(tc, "validate_dataframe", _fake_validate_dataframe)
    path = make_transaction_file(tmp_path)
    with pytest.raises(AppDataError) as exc_info:
        clean_transaction_file(path)
    message = str(exc_info.value)
    assert "contract validation" in message.lower()
    assert "rejected" in message.lower()


# ---------------------------------------------------------------------------
# 5: a warning-level violation does NOT stop processing
# ---------------------------------------------------------------------------


def test_warning_level_violation_does_not_stop_processing(tmp_path):
    # "Etsy" is not amazon/flipkart/meesho/jiomart/website-shaped, so
    # standardize_marketplace() title-cases it through unchanged -> it is
    # not in the contract's allowed_values -> UNKNOWN_VALUE warning, not a
    # rejection. The row must still be accepted and processed.
    path = _write_transaction_csv(
        tmp_path,
        "unknown_marketplace.csv",
        [
            '"1 May 2026 10:00:00 am UTC","1","Order","ORDER-1","SKU-1","Private Product One","2","Etsy","Amazon","Mumbai","MAHARASHTRA","400001","1000","0","0","-50","-100","-80","-20","0","750"',
        ],
    )
    df, metrics = clean_transaction_file(path)
    assert len(df) == 1
    assert metrics["contract_rejected_rows"] == 0
    assert metrics["contract_warning_rows"] == 1


# ---------------------------------------------------------------------------
# 6 & 7: quarantine metadata schema + never carries a raw private value
# ---------------------------------------------------------------------------


def test_quarantine_ledger_has_the_documented_safe_schema(tmp_path):
    df, metrics = clean_transaction_file(make_transaction_file(tmp_path))
    ledger = metrics["quarantine_ledger"]
    assert list(ledger.columns) == REJECTED_ROW_COLUMNS


def test_quarantine_never_carries_a_raw_private_value():
    # Direct contract-layer check (the mechanics tests/test_contracts.py
    # already covers in isolation): a row that genuinely fails a
    # non-nullable required field must never leak that row's private value
    # into the quarantine record's reason/validation_rule text.
    from shared.contracts import load_contract, validate_dataframe

    contract = load_contract("marketplace_transactions.yml")
    contract["fields"]["order_id"]["required"] = True
    contract["fields"]["order_id"]["nullable"] = False
    df = pd.DataFrame({"sku": ["SKU-1"], "marketplace": ["Amazon"], "order_id": [None]})
    df.loc[0, "sku"] = "SUPER-SECRET-SKU-999"
    accepted, rejected, warnings = validate_dataframe(df, contract, "test.csv")
    assert not rejected.empty
    reason_text = " ".join(rejected["reason"].astype(str)) + " ".join(rejected["validation_rule"].astype(str))
    assert "SUPER-SECRET-SKU-999" not in reason_text


# ---------------------------------------------------------------------------
# 8 & 9: pre-existing friendly behaviors are unchanged by this integration
# ---------------------------------------------------------------------------


def test_non_csv_binary_file_still_produces_safe_rejection_after_integration(tmp_path):
    path = tmp_path / "fake.csv"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    with pytest.raises(AppDataError) as exc_info:
        clean_transaction_file(path)
    assert "recognizable marketplace transaction columns" in str(exc_info.value)


def test_zero_row_valid_schema_file_still_produces_the_specific_message_after_integration(tmp_path):
    path = _write_transaction_csv(tmp_path, "zero_rows.csv", [])
    with pytest.raises(AppDataError) as exc_info:
        clean_transaction_file(path)
    message = str(exc_info.value)
    assert "no transaction rows" in message.lower()
    # Must not be misattributed to contract validation -- this check fires
    # before the contract is ever consulted.
    assert "contract validation" not in message.lower()


# ---------------------------------------------------------------------------
# 10: public-output contracts are validated where integrated
# ---------------------------------------------------------------------------


EXPECTED_CONTRACTED_PUBLIC_OUTPUTS = {
    "anonymized_master",
    "marketplace_summary",
    "product_performance",
    "inventory_action_review",
    "dataset_profile",
    "validation_summary",
}


def test_public_output_contracts_are_checked_on_a_real_upload_run(tmp_path):
    # 3A: EXACTLY the 6 declared public-output contracts must be checked on
    # a real run -- not a subset. This is the regression guard for the
    # ordering bug where validate_public_outputs() ran before
    # outputs["validation_summary"] existed, silently skipping it every
    # single run with no test failure.
    result = run_analysis_from_uploads_with_options(
        UploadStub(make_product_file(tmp_path)), UploadStub(make_transaction_file(tmp_path)), dataset_period="custom"
    )
    checked = result["public_output_contract_results"]
    assert set(checked.keys()) == EXPECTED_CONTRACTED_PUBLIC_OUTPUTS
    for name, summary in checked.items():
        assert summary["rejected_rows"] == 0, f"{name} unexpectedly failed its contract: {summary}"


def test_validation_summary_is_genuinely_passed_through_validate_public_outputs(tmp_path):
    # Run validation_summary through validate_dataframe() with its row counts.
    # total_rows must match the
    # number of validation-check rows the pipeline produced, and all rows
    # must be accepted (0 rejected) on a legitimate run.
    result = run_analysis_from_uploads_with_options(
        UploadStub(make_product_file(tmp_path)), UploadStub(make_transaction_file(tmp_path)), dataset_period="custom"
    )
    summary_result = result["public_output_contract_results"]["validation_summary"]
    real_row_count = len(result["outputs"]["validation_summary"])
    assert real_row_count > 0
    assert summary_result["total_rows"] == real_row_count
    assert summary_result["accepted_rows"] == real_row_count
    assert summary_result["rejected_rows"] == 0


def test_invalid_validation_summary_dataframe_fails_closed():
    # 3C: force a reject-level violation directly on the validation_summary
    # contract (missing required check_status column) and prove
    # validate_public_outputs() raises PublicOutputContractError -- the
    # same fail-closed behavior already proven for the other 5 outputs,
    # now proven for validation_summary specifically.
    from shared.contracts import validate_public_outputs

    bad_validation_summary = pd.DataFrame(
        {
            "check_name": ["Raw product master loaded"],
            "check_value": ["1"],
            "expected_value": ["> 0"],
            # check_status intentionally omitted -- required, non-nullable
        }
    )
    with pytest.raises(PublicOutputContractError, match="validation_summary"):
        validate_public_outputs({"validation_summary": bad_validation_summary})


def test_other_uncontracted_public_outputs_remain_unaffected(tmp_path):
    # 3E: the 11 outputs with no declared contract must never appear in the
    # contract results and must be present, unmodified, in the outputs dict.
    result = run_analysis_from_uploads_with_options(
        UploadStub(make_product_file(tmp_path)), UploadStub(make_transaction_file(tmp_path)), dataset_period="custom"
    )
    checked = set(result["public_output_contract_results"].keys())
    all_outputs = set(result["outputs"].keys())
    uncontracted = all_outputs - EXPECTED_CONTRACTED_PUBLIC_OUTPUTS
    assert len(all_outputs) == 17
    assert len(uncontracted) == 11
    assert checked.isdisjoint(uncontracted)
    assert checked == EXPECTED_CONTRACTED_PUBLIC_OUTPUTS


def test_public_output_contract_error_is_a_distinct_importable_exception():
    # Confirms the fail-closed exception type exists and is distinct from
    # the generic AppDataError used for upload-side problems -- a
    # PublicOutputContractError signals a pipeline bug, not a user error.
    assert issubclass(PublicOutputContractError, Exception)
    assert PublicOutputContractError is not AppDataError


# ---------------------------------------------------------------------------
# 12: integration does not alter public-output schemas unexpectedly
# ---------------------------------------------------------------------------


def test_integration_does_not_change_public_output_columns(tmp_path):
    result = run_analysis_from_uploads_with_options(
        UploadStub(make_product_file(tmp_path)), UploadStub(make_transaction_file(tmp_path)), dataset_period="custom"
    )
    expected_product_performance_columns = {
        "public_product_id", "marketplace", "brand_group", "category_group", "subcategory_group",
        "product_group", "fulfillment_type", "listing_price_band", "inventory_band", "margin_band_public",
        "profitability_band_public", "sales_index", "units_index", "fee_pct_of_gross", "refund_pct_of_gross",
        "promotion_pct_of_gross", "net_to_gross_pct", "margin_index", "estimated_profitability_index",
        "margin_risk_score", "margin_risk_band", "revenue_quality_score", "revenue_quality_band",
        "recommended_action", "action_priority", "action_reason",
    }
    assert set(result["outputs"]["product_performance"].columns) == expected_product_performance_columns
