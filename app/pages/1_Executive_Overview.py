from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components.charts import bar_chart, donut_chart, line_chart  # noqa: E402
from app.components.kpi_cards import render_kpi_cards  # noqa: E402
from app.components.style import inject_global_css, render_footer, render_insight_box, render_mode_badge, render_page_header, render_sidebar_status  # noqa: E402
from app.components.tables import render_table_section  # noqa: E402
from app.utils.business_outcomes import OUTCOME_HELPER_TEXT, build_business_outcomes  # noqa: E402
from app.utils.filters import apply_dashboard_filters, filter_source_from_outputs, has_active_filters  # noqa: E402
from app.utils.filters import render_sidebar_filters  # noqa: E402
from app.utils.recommendations import priority_counts  # noqa: E402


st.set_page_config(page_title="Executive Overview", layout="wide")
inject_global_css()
render_page_header(
    "Executive Overview",
    "Marketplace performance using privacy-safe indexes, ratios, scores, and action signals.",
)

result = st.session_state.get("analysis_result")
render_sidebar_status(result=result)
if not result:
    st.info("Load demo public outputs or upload files on the main page first.")
    st.stop()
render_mode_badge(result)

outputs = result["outputs"]
product = outputs.get("product_performance", pd.DataFrame())
category = outputs.get("category_performance", pd.DataFrame())
marketplace = outputs.get("marketplace_summary", pd.DataFrame())
channel = outputs.get("marketplace_channel_performance", pd.DataFrame())
action = outputs.get("product_action_review", pd.DataFrame())
dashboard_filters = render_sidebar_filters(filter_source_from_outputs(outputs))
product = apply_dashboard_filters(product, dashboard_filters)
category = apply_dashboard_filters(category, dashboard_filters)
marketplace = apply_dashboard_filters(marketplace, dashboard_filters)
channel = apply_dashboard_filters(channel, dashboard_filters)
action = apply_dashboard_filters(action, dashboard_filters)
filtered_outputs = {
    "product_performance": product,
    "category_performance": category,
    "marketplace_summary": marketplace,
    "marketplace_channel_performance": channel,
    "product_action_review": action,
}
if has_active_filters(dashboard_filters) and product.empty and action.empty:
    st.info("No records match the selected filters.")

overview_kpis = {
    "Dataset": result.get("dataset_label", result.get("dataset_period", "custom")),
    "Product Master Rows": result["kpis"].get("Product Master Rows", 0),
    "Transaction Rows": result["kpis"].get("Transaction Rows", 0),
    "Order Rows": result["kpis"].get("Order Rows", 0),
    "Products in Analysis": result["kpis"].get("Products in Analysis", 0),
    "Products With Transactions": result["kpis"].get("Products With Transactions", 0),
    "Marketplaces": result["kpis"].get("Marketplaces", 0),
    "Join Coverage %": result["kpis"].get("Join Coverage %", 0),
    "Channel Mapping Status": result["kpis"].get("Channel Mapping Status", "Unavailable"),
    "High Priority Actions": result["kpis"].get("High Priority Actions", 0),
}
render_kpi_cards(
    overview_kpis,
    columns=5,
    statuses={
        "Join Coverage %": "Passed",
        "High Priority Actions": "Ready",
    },
)
render_insight_box(result.get("summary_text", "Public outputs loaded. Explore the dashboard pages for details."))
render_kpi_cards(
    build_business_outcomes(filtered_outputs),
    columns=5,
    helpers={label: OUTCOME_HELPER_TEXT for label in build_business_outcomes(filtered_outputs)},
)
st.caption(OUTCOME_HELPER_TEXT)

left, right = st.columns(2)
with left:
    st.plotly_chart(
        line_chart(marketplace, "transaction_month", "sales_index", "Sales Index Trend by Marketplace", color="marketplace"),
        use_container_width=True,
    )
with right:
    st.plotly_chart(
        bar_chart(channel, "marketplace", "sales_index", "Channel Sales Index", agg="mean", top_n=10),
        use_container_width=True,
    )

left, right = st.columns(2)
with left:
    st.plotly_chart(
        bar_chart(product, "product_group", "sales_index", "Sales Index by Product Group", agg="mean", top_n=15),
        use_container_width=True,
    )
with right:
    st.plotly_chart(
        bar_chart(category, "category_group", "revenue_quality_score", "Revenue Quality by Category", agg="mean", top_n=12),
        use_container_width=True,
    )

priority_df = priority_counts(action)
st.plotly_chart(donut_chart(priority_df, "action_priority", "count", "Action Priority Breakdown"), use_container_width=True)

top_action_candidates = (
    action.assign(
        _priority_rank=action.get("action_priority", pd.Series(dtype=str)).map({"High": 1, "Medium": 2, "Low": 3}).fillna(4)
    )
    .sort_values(["_priority_rank", "sales_index", "margin_risk_score"], ascending=[True, False, False])
    .drop(columns=["_priority_rank"], errors="ignore")
    .head(10)
    if not action.empty
    else pd.DataFrame()
)
top_action_columns = [
    "public_product_id",
    "marketplace",
    "category_group",
    "product_group",
    "recommended_action",
    "action_priority",
    "sales_index",
    "margin_risk_score",
    "revenue_quality_score",
]
render_table_section(
    "Top Action Candidates",
    "Highest-priority anonymized product rows for fee, restock, refund, margin, or monitoring review.",
    top_action_candidates[[col for col in top_action_columns if col in top_action_candidates.columns]],
    height=280,
)

top_groups = (
    product.groupby(["marketplace", "product_group"], dropna=False)
    .agg(
        product_count=("public_product_id", "nunique"),
        sales_index=("sales_index", "mean"),
        units_index=("units_index", "mean"),
        net_to_gross_pct=("net_to_gross_pct", "mean"),
        margin_risk_score=("margin_risk_score", "mean"),
        revenue_quality_score=("revenue_quality_score", "mean"),
    )
    .reset_index()
    .sort_values(["sales_index", "units_index"], ascending=False)
    .head(20)
)
render_table_section(
    "Top Product Groups by Sales Index",
    "Grouped public product performance ranked by indexed sales activity. No raw revenue values are displayed.",
    top_groups,
    height=520,
    download_name="top_product_groups_by_sales_index",
)
render_footer()
