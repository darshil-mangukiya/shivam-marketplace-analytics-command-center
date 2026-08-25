"""Quarantine framework tests."""

from __future__ import annotations

import pandas as pd
import pytest

from shared.contracts import validate_dataframe
from shared.quarantine import (
    assert_quarantine_is_safe,
    combine_quarantine,
    quarantine_totals,
    summarize_quarantine,
)


def _sample_contract() -> dict:
    return {
        "fields": {
            "sku": {"type": "string", "required": True, "nullable": False},
            "price": {"type": "number", "required": False, "min": 0, "max": 1000},
        },
        "validation_severity": {
            "missing_required_field": "reject",
            "type_mismatch": "reject",
            "out_of_range": "warn",
        },
    }


def test_assert_quarantine_is_safe_passes_for_documented_schema():
    df = pd.DataFrame(
        [{"source_name": "a.csv", "row_number": 1, "error_code": "X", "error_category": "Y", "validation_rule": "z", "reason": "r", "severity": "reject", "timestamp": "now"}]
    )
    assert_quarantine_is_safe(df)  # does not raise


def test_assert_quarantine_is_safe_rejects_extra_columns():
    df = pd.DataFrame([{"source_name": "a.csv", "row_number": 1, "raw_value": "SECRET-SKU-123"}])
    with pytest.raises(ValueError):
        assert_quarantine_is_safe(df)


def test_combine_quarantine_concatenates_and_validates():
    df = pd.DataFrame({"sku": [None, "A2"], "price": [10, 5000]})
    accepted, rejected, warnings = validate_dataframe(df, _sample_contract(), "test.csv")
    combined = combine_quarantine(rejected, warnings)
    assert len(combined) == len(rejected) + len(warnings)


def test_combine_quarantine_handles_all_empty():
    empty = pd.DataFrame(columns=["source_name", "row_number", "error_code", "error_category", "validation_rule", "reason", "severity", "timestamp"])
    combined = combine_quarantine(empty, empty)
    assert combined.empty


def test_summarize_quarantine_groups_by_category_code_severity():
    df = pd.DataFrame({"sku": [None, None, "A3"], "price": [10, 20, 5000]})
    accepted, rejected, warnings = validate_dataframe(df, _sample_contract(), "test.csv")
    combined = combine_quarantine(rejected, warnings)
    summary = summarize_quarantine(combined)
    assert "row_count" in summary.columns
    assert summary["row_count"].sum() == len(combined)


def test_summarize_quarantine_empty_input_returns_empty_frame():
    empty = pd.DataFrame(columns=["source_name", "row_number", "error_code", "error_category", "validation_rule", "reason", "severity", "timestamp"])
    summary = summarize_quarantine(empty)
    assert summary.empty


def test_quarantine_totals_reports_all_four_counts():
    df = pd.DataFrame({"sku": [None, "A2", "A3"], "price": [10, 20, 5000]})
    accepted, rejected, warnings = validate_dataframe(df, _sample_contract(), "test.csv")
    totals = quarantine_totals(rejected, warnings, total_input_rows=3, accepted_rows=len(accepted))
    assert totals["total_input_rows"] == 3
    assert totals["accepted_rows"] == len(accepted)
    assert totals["rejected_rows"] == len(rejected)
    assert totals["warning_rows"] == len(warnings)
    assert totals["accepted_rows"] + totals["rejected_rows"] == 3
