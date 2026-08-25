from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_validation_reports_join_coverage():
    validation = pd.read_csv(ROOT / "data" / "public" / "validation_summary.csv")
    row = validation.loc[validation["check_name"].eq("join coverage percentage is calculated")]
    assert not row.empty
    assert row.iloc[0]["check_status"] == "PASS"
    assert row.iloc[0]["check_value"] != "missing"


def test_validation_reports_unmatched_skus_and_duplicate_skus():
    validation = pd.read_csv(ROOT / "data" / "public" / "validation_summary.csv")
    expected_checks = {
        "duplicate SKU count is reported",
        "unmatched transaction SKU count is reported",
    }
    present = set(validation["check_name"])
    assert expected_checks <= present
    assert validation[validation["check_name"].isin(expected_checks)]["check_status"].eq("PASS").all()
