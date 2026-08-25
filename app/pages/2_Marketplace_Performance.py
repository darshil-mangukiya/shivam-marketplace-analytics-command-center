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


st.set_page_config(page_title="Marketplace Performance", layout="wide")
inject_global_css()
render_page_header(
    "Marketplace Performance",
    "Compare Amazon, Flipkart, Meesho, JioMart, and Website at the marketplace level using public indexes, ratios, and scores. Channel-level mapping is not validated, so figures are marketplace-level.",
)

result = st.session_state.get("analysis_result")
render_sidebar_status(result=result)
if not result:
    st.info("Load demo public outputs or upload files on the main page first.")
    st.stop()
render_mode_badge(result)

channel = result["outputs"].get("marketplace_channel_performance", pd.DataFrame())
product = result["outputs"].get("product_performance", pd.DataFrame())

dashboard_filters = render_sidebar_filters(filter_source_from_outputs(result["outputs"]))
filtered = apply_dashboard_filters(channel, dashboard_filters)
product_scope = apply_dashboard_filters(product, dashboard_filters)
if (
    not product_scope.empty
    and "marketplace" in product_scope.columns
    and "marketplace" in filtered.columns
    and has_active_filters(dashboard_filters)
):
    filtered = filtered[filtered["marketplace"].isin(product_scope["marketplace"].dropna().unique())]
if has_active_filters(dashboard_filters) and filtered.empty and product_scope.empty:
    st.info("No records match the selected filters.")

render_kpi_cards(
    {
        "Marketplaces": int(filtered["marketplace"].nunique()) if "marketplace" in filtered.columns else 0,
        "Products With Transactions": int(product_scope["public_product_id"].nunique()) if "public_product_id" in product_scope.columns else 0,
        "Average Fee % of Gross": round(float(filtered["avg_fee_pct_of_gross"].mean() or 0), 1) if not filtered.empty else 0,
        "Average Net-to-Gross %": round(float(filtered["avg_net_to_gross_pct"].mean() or 0), 1) if not filtered.empty else 0,
        "Average Margin Risk Score": round(float(filtered["avg_margin_risk_score"].mean() or 0), 1) if not filtered.empty else 0,
        "Average Revenue Quality Score": round(float(filtered["avg_revenue_quality_score"].mean() or 0), 1) if not filtered.empty else 0,
    },
    columns=3,
)
render_insight_box(
    "This page compares marketplace-level performance without exposing SKUs, ASINs, order IDs, raw revenue, raw fees, or private cost values."
)

left, right = st.columns(2)
with left:
    st.plotly_chart(bar_chart(filtered, "marketplace", "sales_index", "Sales Index by Marketplace", agg="mean", top_n=10), use_container_width=True)
with right:
    st.plotly_chart(bar_chart(filtered, "marketplace", "units_index", "Units Index by Marketplace", agg="mean", top_n=10), use_container_width=True)

left, right = st.columns(2)
with left:
    st.plotly_chart(bar_chart(filtered, "marketplace", "avg_net_to_gross_pct", "Net-to-Gross % by Marketplace", agg="mean", top_n=10), use_container_width=True)
with right:
    st.plotly_chart(bar_chart(filtered, "marketplace", "avg_fee_pct_of_gross", "Fee % of Gross by Marketplace", agg="mean", top_n=10), use_container_width=True)

marketplace_preview_columns = [
    "marketplace",
    "channel",
    "products_in_analysis",
    "sales_index",
    "units_index",
    "avg_fee_pct_of_gross",
    "avg_net_to_gross_pct",
    "avg_margin_risk_score",
    "avg_revenue_quality_score",
]
marketplace_preview = (
    filtered.rename(columns={"product_count": "products_in_analysis"})
    .sort_values(["sales_index", "units_index"], ascending=False)
    .head(10)
    if not filtered.empty
    else pd.DataFrame()
)
render_table_section(
    "Marketplace Performance Table",
    "Top marketplace rows ranked by indexed sales and units, with ratio metrics only.",
    marketplace_preview[[col for col in marketplace_preview_columns if col in marketplace_preview.columns]],
    height=280,
)

st.plotly_chart(
    scatter_chart(
        product_scope,
        "sales_index",
        "margin_risk_score",
        "Product Sales Index vs Margin Risk Score",
        color="marketplace",
        hover_name="public_product_id",
    ),
    use_container_width=True,
)

render_table_section(
    "Marketplace Performance",
    "Public marketplace comparison table with indexed order, sales, units, ratio, and score metrics.",
    filtered,
    height=520,
    download_name="filtered_marketplace_channel_performance",
)
render_footer()
