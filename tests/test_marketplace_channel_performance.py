from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "data" / "public"


def test_no_zero_activity_duplicate_channel_rows():
    channel = pd.read_csv(PUBLIC / "marketplace_channel_performance.csv")
    # Every published channel row must carry products or sales activity. The old
    # "Amazon, Amazon" all-zero noise rows must be gone.
    assert ((channel["product_count"] > 0) | (channel["sales_index"] > 0)).all()
    zero_dupes = channel[
        (channel["marketplace"] == channel["channel"])
        & (channel["product_count"] == 0)
        & (channel["sales_index"] == 0)
    ]
    assert zero_dupes.empty


def test_one_meaningful_row_per_marketplace():
    channel = pd.read_csv(PUBLIC / "marketplace_channel_performance.csv")
    # 5 marketplaces, one meaningful channel row each, no duplicates.
    assert len(channel) == channel["marketplace"].nunique()
    assert channel["marketplace"].nunique() == 5


def test_average_scores_are_rounded():
    channel = pd.read_csv(PUBLIC / "marketplace_channel_performance.csv")
    for col in ["avg_margin_risk_score", "avg_revenue_quality_score"]:
        values = pd.to_numeric(channel[col], errors="coerce").dropna()
        assert (values.round(1) == values).all(), f"{col} is not rounded to 1 decimal"
