from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "data" / "public"


EXPECTED_FILES = {
    "anonymized_master.csv",
    "marketplace_summary.csv",
    "marketplace_channel_performance.csv",
    "product_performance.csv",
    "category_performance.csv",
    "brand_performance.csv",
    "profitability_summary.csv",
    "margin_risk_review.csv",
    "inventory_action_review.csv",
    "fee_refund_summary.csv",
    "fulfillment_comparison.csv",
    "product_action_review.csv",
    "mart_marketplace_variance_drivers.csv",
    "mart_product_variance_contributors.csv",
    "mart_performance_driver_summary.csv",
    "dataset_profile.csv",
    "validation_summary.csv",
}


def test_expected_public_outputs_exist_and_are_populated():
    existing = {path.name for path in PUBLIC.glob("*.csv")}
    assert EXPECTED_FILES <= existing
    for filename in EXPECTED_FILES:
        df = pd.read_csv(PUBLIC / filename)
        assert len(df) > 0, f"{filename} is empty"


def test_indexes_are_between_zero_and_one_hundred():
    for path in PUBLIC.glob("*.csv"):
        df = pd.read_csv(path)
        for col in [column for column in df.columns if column.endswith("_index")]:
            values = pd.to_numeric(df[col], errors="coerce").dropna()
            assert (values >= 0).all(), f"{path.name}:{col} has negative index values"
            assert (values <= 100).all(), f"{path.name}:{col} has index values above 100"


def test_product_actions_are_populated():
    actions = pd.read_csv(PUBLIC / "product_action_review.csv")
    assert actions["recommended_action"].notna().all()
    assert actions["action_priority"].isin({"High", "Medium", "Low"}).all()
    assert actions["action_reason"].notna().all()
