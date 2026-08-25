"""Data contract validation tests."""

from __future__ import annotations

import pandas as pd
import pytest

from shared.contracts import ContractError, load_contract, validate_dataframe


def test_load_contract_reads_real_contract_files():
    contract = load_contract("product_master.yml")
    assert contract["dataset"] == "product_master"
    assert "seller_sku" in contract["fields"]


def test_load_contract_missing_file_raises():
    with pytest.raises(ContractError):
        load_contract("does_not_exist.yml")


def _sample_contract() -> dict:
    return {
        "dataset": "sample",
        "fields": {
            "sku": {"type": "string", "required": True, "nullable": False},
            "price": {"type": "number", "required": False, "min": 0, "max": 1000},
            "marketplace": {
                "type": "string",
                "required": True,
                "nullable": False,
                "allowed_values": ["Amazon", "Flipkart"],
            },
        },
        "forbidden_fields": ["asin"],
        "validation_severity": {
            "missing_required_field": "reject",
            "type_mismatch": "reject",
            "out_of_range": "warn",
            "unknown_value": "warn",
            "forbidden_field_present": "reject",
        },
    }


def test_missing_required_value_is_rejected():
    df = pd.DataFrame({"sku": ["A1", None], "marketplace": ["Amazon", "Amazon"], "price": [10, 20]})
    accepted, rejected, warnings = validate_dataframe(df, _sample_contract(), "test.csv")
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected.iloc[0]["error_code"] == "MISSING_REQUIRED_VALUE"
    assert rejected.iloc[0]["error_category"] == "VALIDATION_ERROR"


def test_missing_required_column_is_rejected_for_whole_frame():
    df = pd.DataFrame({"price": [10, 20]})  # sku and marketplace entirely absent
    accepted, rejected, warnings = validate_dataframe(df, _sample_contract(), "test.csv")
    assert accepted.empty
    codes = set(rejected["error_code"])
    assert "MISSING_REQUIRED_COLUMN" in codes


def test_type_mismatch_is_rejected():
    df = pd.DataFrame({"sku": ["A1", "A2"], "marketplace": ["Amazon", "Amazon"], "price": [10, "not-a-number"]})
    accepted, rejected, warnings = validate_dataframe(df, _sample_contract(), "test.csv")
    assert len(accepted) == 1
    assert rejected.iloc[0]["error_code"] == "TYPE_MISMATCH"


def test_out_of_range_is_a_warning_not_a_rejection():
    df = pd.DataFrame({"sku": ["A1", "A2"], "marketplace": ["Amazon", "Amazon"], "price": [10, 5000]})
    accepted, rejected, warnings = validate_dataframe(df, _sample_contract(), "test.csv")
    assert len(accepted) == 2  # both rows accepted; the second is only warned
    assert rejected.empty
    assert len(warnings) == 1
    assert warnings.iloc[0]["error_code"] == "OUT_OF_RANGE"


def test_unknown_value_is_a_warning():
    df = pd.DataFrame({"sku": ["A1"], "marketplace": ["Meesho"], "price": [10]})
    accepted, rejected, warnings = validate_dataframe(df, _sample_contract(), "test.csv")
    assert len(accepted) == 1
    assert len(warnings) == 1
    assert warnings.iloc[0]["error_code"] == "UNKNOWN_VALUE"


def test_forbidden_field_present_rejects_entire_frame():
    df = pd.DataFrame({"sku": ["A1"], "marketplace": ["Amazon"], "asin": ["B0123456789"]})
    accepted, rejected, warnings = validate_dataframe(df, _sample_contract(), "test.csv")
    assert accepted.empty
    assert rejected.iloc[0]["error_code"] == "FORBIDDEN_FIELD_PRESENT"
    assert rejected.iloc[0]["error_category"] == "PRIVACY_ERROR"


def test_rejected_records_never_contain_raw_cell_values():
    df = pd.DataFrame({"sku": ["SUPER-SECRET-SKU-999", None], "marketplace": ["Amazon", "Amazon"], "price": [10, 20]})
    accepted, rejected, warnings = validate_dataframe(df, _sample_contract(), "test.csv")
    reason_text = " ".join(rejected["reason"].astype(str))
    validation_rule_text = " ".join(rejected["validation_rule"].astype(str))
    assert "SUPER-SECRET-SKU-999" not in reason_text
    assert "SUPER-SECRET-SKU-999" not in validation_rule_text


def test_rejected_and_warning_frames_have_the_documented_schema():
    df = pd.DataFrame({"sku": ["A1", None], "marketplace": ["Meesho", "Amazon"], "price": [5000, 20]})
    accepted, rejected, warnings = validate_dataframe(df, _sample_contract(), "test.csv")
    expected_columns = {"source_name", "row_number", "error_code", "error_category", "validation_rule", "reason", "severity", "timestamp"}
    assert expected_columns <= set(rejected.columns)
    assert expected_columns <= set(warnings.columns)


def test_empty_dataframe_returns_empty_results_without_error():
    df = pd.DataFrame({"sku": [], "marketplace": [], "price": []})
    accepted, rejected, warnings = validate_dataframe(df, _sample_contract(), "test.csv")
    assert accepted.empty
    assert rejected.empty
    assert warnings.empty


def test_duplicate_primary_key_is_flagged():
    contract = _sample_contract()
    contract["fields"]["sku"]["unique"] = True
    df = pd.DataFrame({"sku": ["A1", "A1"], "marketplace": ["Amazon", "Amazon"], "price": [10, 20]})
    accepted, rejected, warnings = validate_dataframe(df, contract, "test.csv")
    assert len(warnings) == 1
    assert warnings.iloc[0]["error_code"] == "DUPLICATE_KEY"
