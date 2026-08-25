from __future__ import annotations

from pathlib import Path

from app.components import charts


ROOT = Path(__file__).resolve().parents[1]


def test_chart_color_constants_exist():
    assert charts.COLOR_SALES == "#2563EB"
    assert charts.COLOR_HEALTHY == "#0F766E"
    assert charts.COLOR_WARNING == "#F59E0B"
    assert charts.COLOR_RISK == "#DC2626"
    assert charts.COLOR_SUCCESS == "#16A34A"
    assert charts.COLOR_NEUTRAL == "#64748B"


def test_metric_color_mapping_uses_business_semantics():
    assert charts._metric_color("sales_index") == charts.COLOR_SALES
    assert charts._metric_color("units_index") == charts.COLOR_SALES
    assert charts._metric_color("revenue_quality_score") == charts.COLOR_HEALTHY
    assert charts._metric_color("margin_risk_score") == charts.COLOR_WARNING
    assert charts._metric_color("refund_pct_of_gross") == charts.COLOR_RISK


def test_demo_badge_is_less_prominent_but_sidebar_keeps_demo_indicator():
    style_source = (ROOT / "app" / "components" / "style.py").read_text(encoding="utf-8")
    render_mode_source = style_source.split("def render_mode_badge", 1)[1].split("def render_insight_box", 1)[0]
    render_sidebar_source = style_source.split("def render_sidebar_status", 1)[1]

    assert "Dataset:" in render_mode_source
    assert "mode_badge" not in render_mode_source
    assert "Sample Demo:" in render_sidebar_source
