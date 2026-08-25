"""Regression guard for incomplete marketplace-channel mapping."""

from pathlib import Path

import pandas as pd

from app.utils.metrics import compute_kpis
from app.utils.recommendations import executive_summary_text

ROOT = Path(__file__).resolve().parents[1]


def _minimal_outputs() -> dict[str, pd.DataFrame]:
    product = pd.DataFrame(
        {
            "public_product_id": ["P0001", "P0002"],
            "marketplace": ["Amazon", "Flipkart"],
            "category_group": ["A", "B"],
            "brand_group": ["X", "Y"],
            "fee_pct_of_gross": [10.0, 12.0],
            "refund_pct_of_gross": [1.0, 2.0],
            "promotion_pct_of_gross": [1.0, 1.0],
            "net_to_gross_pct": [80.0, 85.0],
            "revenue_quality_score": [70.0, 75.0],
        }
    )
    action = pd.DataFrame({"recommended_action": ["Monitor", "Fee Review"], "action_priority": ["Low", "High"]})
    channel = pd.DataFrame({"marketplace": ["Amazon", "Flipkart"], "channel": ["Marketplace", "Marketplace"]})
    return {"product_performance": product, "product_action_review": action, "marketplace_channel_performance": channel}


def test_compute_kpis_has_no_channel_coverage_percentage():
    kpis = compute_kpis(_minimal_outputs(), {"channel_mapping_status": "Unavailable"})
    assert "Marketplace Join Coverage %" not in kpis
    assert kpis.get("Channel Mapping Status") == "Unavailable"
    assert "Passed" not in str(kpis.get("Channel Mapping Status"))


def test_compute_kpis_never_hardcodes_100_from_file_presence():
    kpis = compute_kpis(_minimal_outputs(), {"marketplace_join_coverage_pct": 100.0})
    assert "Marketplace Join Coverage %" not in kpis
    assert kpis.get("Channel Mapping Status") == "Unavailable"


def test_executive_summary_reports_unavailable_channel_mapping():
    text = executive_summary_text(_minimal_outputs(), {"join_coverage_pct": 100.0, "channel_mapping_status": "Unavailable"})
    low = text.lower()
    assert "marketplace-channel coverage is 100" not in low
    assert "channel coverage is 100" not in low
    assert "unavailable" in low


def test_demo_result_reports_honest_channel_status():
    from app.utils.data_loader import build_demo_result

    public_dir = ROOT / "data" / "public"
    if not (public_dir / "anonymized_master.csv").exists():
        import pytest

        pytest.skip("public demo outputs not present")
    result = build_demo_result()
    jm = result["join_metrics"]
    assert jm.get("marketplace_join_coverage_pct") != 100.0
    assert jm.get("channel_mapping_status") == "Unavailable"
    assert "Marketplace Join Coverage %" not in result["kpis"]
    assert result["kpis"].get("Channel Mapping Status") == "Unavailable"
    assert "coverage is 100" not in result["summary_text"].lower()
    assert "unavailable" in result["summary_text"].lower()
