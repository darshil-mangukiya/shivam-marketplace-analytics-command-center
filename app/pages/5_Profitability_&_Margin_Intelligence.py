from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components.charts import bar_chart, scatter_chart  # noqa: E402
from app.components.kpi_cards import render_kpi_cards  # noqa: E402
from app.components.style import inject_global_css, render_footer, render_insight_box, render_mode_badge, render_page_header, render_sidebar_status  # noqa: E402
from app.components.tables import render_table_section  # noqa: E402
from app.utils.filters import apply_dashboard_filters, filter_source_from_outputs, has_active_filters, render_sidebar_filters  # noqa: E402


st.set_page_config(page_title="Profitability & Margin Intelligence", layout="wide")
inject_global_css()
render_page_header(
    "Profitability & Margin Intelligence",
    "Estimated margin-band and margin-risk analysis using private cost assumptions internally and public-safe scores externally.",
)

result = st.session_state.get("analysis_result")
render_sidebar_status(result=result)
if not result:
    st.info("Load demo public outputs or upload files on the main page first.")
    st.stop()
render_mode_badge(result)

profitability = result["outputs"].get("profitability_summary", pd.DataFrame())
margin_risk = result["outputs"].get("margin_risk_review", pd.DataFrame())
channel = result["outputs"].get("marketplace_channel_performance", pd.DataFrame())
dashboard_filters = render_sidebar_filters(filter_source_from_outputs(result["outputs"]))
profitability = apply_dashboard_filters(profitability, dashboard_filters)
margin_risk = apply_dashboard_filters(margin_risk, dashboard_filters)
channel = apply_dashboard_filters(channel, dashboard_filters)
if has_active_filters(dashboard_filters) and profitability.empty and margin_risk.empty:
    st.info("No records match the selected filters.")

render_kpi_cards(
    {
        "Average Margin Risk Score": round(float(margin_risk["margin_risk_score"].mean() or 0), 1) if "margin_risk_score" in margin_risk.columns and not margin_risk.empty else 0,
        "Average Revenue Quality Score": round(float(margin_risk["revenue_quality_score"].mean() or 0), 1) if "revenue_quality_score" in margin_risk.columns and not margin_risk.empty else 0,
        "Margin Risk Review Count": int((margin_risk["recommended_action"] == "Margin Risk Review").sum()) if "recommended_action" in margin_risk.columns else 0,
        "High Priority Actions": int((margin_risk["action_priority"] == "High").sum()) if "action_priority" in margin_risk.columns else 0,
    },
    columns=4,
)
render_insight_box(
    "This dashboard uses private estimated cost assumptions internally and publishes only bands, indexes, and scores. "
    "Interpret it as estimated profitability analysis, not audited accounting profit."
)

left, right = st.columns(2)
with left:
    st.plotly_chart(bar_chart(profitability, "product_group", "margin_index", "Margin Index by Product Group", agg="mean", top_n=15), use_container_width=True)
with right:
    st.plotly_chart(bar_chart(profitability, "marketplace", "estimated_profitability_index", "Estimated Profitability Index by Marketplace", agg="mean", top_n=10), use_container_width=True)

left, right = st.columns(2)
with left:
    st.plotly_chart(bar_chart(margin_risk, "product_group", "margin_risk_score", "Margin Risk Score by Product Group", agg="mean", top_n=15), use_container_width=True)
with right:
    st.plotly_chart(bar_chart(channel, "marketplace", "avg_margin_risk_score", "Channel Margin Risk Score", agg="mean", top_n=10), use_container_width=True)

st.plotly_chart(
    scatter_chart(
        margin_risk,
        "sales_index",
        "margin_risk_score",
        "High-Sales / High-Margin-Risk Products",
        color="margin_risk_band",
        hover_name="public_product_id",
    ),
    use_container_width=True,
)

top_margin_risk = (
    margin_risk.sort_values(["margin_risk_score", "sales_index"], ascending=[False, False]).head(10)
    if not margin_risk.empty
    else pd.DataFrame()
)
margin_risk_columns = [
    "public_product_id",
    "marketplace",
    "category_group",
    "product_group",
    "margin_risk_score",
    "margin_risk_band",
    "revenue_quality_score",
    "recommended_action",
    "action_priority",
]
render_table_section(
    "Top Margin Risk Candidates",
    "Highest margin-risk anonymized product rows for pricing, fee, fulfillment, or assortment review.",
    top_margin_risk[[col for col in margin_risk_columns if col in top_margin_risk.columns]],
    height=300,
)

high_sales_low_margin = (
    margin_risk[(margin_risk["sales_index"] >= 50) & (margin_risk["margin_risk_score"] >= 45)]
    .sort_values(["margin_risk_score", "sales_index"], ascending=[False, False])
    if not margin_risk.empty
    else pd.DataFrame()
)
render_table_section(
    "Profitability Summary",
    "Public profitability table with margin bands, indexes, and risk scores. No raw cost or profit amounts are shown.",
    profitability,
    height=520,
    download_name="profitability_summary",
)
render_table_section(
    "High-Sales Low-Margin / High-Risk Review",
    "Products with strong indexed sales and elevated margin-risk score.",
    high_sales_low_margin,
    height=420,
    download_name="high_sales_margin_risk_review",
)
render_footer()
