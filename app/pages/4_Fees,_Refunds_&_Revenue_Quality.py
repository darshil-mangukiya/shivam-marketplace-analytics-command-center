from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components.charts import bar_chart  # noqa: E402
from app.components.kpi_cards import render_kpi_cards  # noqa: E402
from app.components.style import inject_global_css, render_footer, render_insight_box, render_mode_badge, render_page_header, render_sidebar_status  # noqa: E402
from app.components.tables import render_table_section  # noqa: E402
from app.utils.filters import apply_dashboard_filters, filter_source_from_outputs, has_active_filters, render_sidebar_filters  # noqa: E402


st.set_page_config(page_title="Fees, Refunds & Revenue Quality", layout="wide")
inject_global_css()
render_page_header(
    "Fees, Refunds & Revenue Quality",
    "Find products and categories with elevated fee, refund, promotion, or gross-to-net quality pressure.",
)

result = st.session_state.get("analysis_result")
render_sidebar_status(result=result)
if not result:
    st.info("Load demo public outputs or upload files on the main page first.")
    st.stop()
render_mode_badge(result)

product = result["outputs"].get("product_performance", pd.DataFrame())
category = result["outputs"].get("category_performance", pd.DataFrame())
action = result["outputs"].get("product_action_review", pd.DataFrame())
dashboard_filters = render_sidebar_filters(filter_source_from_outputs(result["outputs"]))
product = apply_dashboard_filters(product, dashboard_filters)
category = apply_dashboard_filters(category, dashboard_filters)
action = apply_dashboard_filters(action, dashboard_filters)
if has_active_filters(dashboard_filters) and product.empty and action.empty:
    st.info("No records match the selected filters.")

render_kpi_cards(
    {
        "Average Fee % of Gross": round(float(product["fee_pct_of_gross"].mean() or 0), 1) if "fee_pct_of_gross" in product.columns and not product.empty else 0,
        "Average Refund % of Gross": round(float(product["refund_pct_of_gross"].mean() or 0), 1) if "refund_pct_of_gross" in product.columns and not product.empty else 0,
        "Average Promotion % of Gross": round(float(product["promotion_pct_of_gross"].mean() or 0), 1) if "promotion_pct_of_gross" in product.columns and not product.empty else 0,
        "Average Net-to-Gross %": round(float(product["net_to_gross_pct"].mean() or 0), 1) if "net_to_gross_pct" in product.columns and not product.empty else 0,
        "Average Revenue Quality Score": round(float(product["revenue_quality_score"].mean() or 0), 1) if "revenue_quality_score" in product.columns and not product.empty else 0,
    },
    columns=5,
)
render_insight_box(
    "This page uses ratios and scores instead of raw money values to protect business confidentiality."
)

left, right = st.columns(2)
with left:
    st.plotly_chart(bar_chart(product, "product_group", "fee_pct_of_gross", "Fee % of Gross by Product Group", agg="mean", top_n=15), use_container_width=True)
with right:
    st.plotly_chart(bar_chart(product, "product_group", "refund_pct_of_gross", "Refund % of Gross by Product Group", agg="mean", top_n=15), use_container_width=True)

left, right = st.columns(2)
with left:
    st.plotly_chart(bar_chart(product, "product_group", "promotion_pct_of_gross", "Promotion % of Gross by Product Group", agg="mean", top_n=15), use_container_width=True)
with right:
    st.plotly_chart(bar_chart(category, "category_group", "revenue_quality_score", "Revenue Quality Score by Category", agg="mean", top_n=12), use_container_width=True)

candidate_columns = [
    "public_product_id",
    "marketplace",
    "category_group",
    "product_group",
    "recommended_action",
    "action_priority",
    "sales_index",
    "fee_pct_of_gross",
    "refund_pct_of_gross",
    "promotion_pct_of_gross",
    "net_to_gross_pct",
    "revenue_quality_score",
    "margin_risk_score",
]
fee_candidates = (
    product[product["fee_pct_of_gross"] >= 25].sort_values(["fee_pct_of_gross", "sales_index"], ascending=False).head(10)
    if not product.empty and "fee_pct_of_gross" in product.columns
    else pd.DataFrame()
)
refund_candidates = (
    action[action["recommended_action"].eq("Refund Review")]
    .sort_values(["refund_pct_of_gross", "sales_index"], ascending=False)
    .head(10)
    if "recommended_action" in action.columns and "refund_pct_of_gross" in action.columns
    else pd.DataFrame()
)
promotion_candidates = (
    action[action["recommended_action"].eq("Promotion Review")]
    .sort_values(["promotion_pct_of_gross", "sales_index"], ascending=False)
    .head(10)
    if "recommended_action" in action.columns and "promotion_pct_of_gross" in action.columns
    else pd.DataFrame()
)
weak_quality = product[product["revenue_quality_score"] < 45].sort_values(["revenue_quality_score", "sales_index"], ascending=[True, False]) if "revenue_quality_score" in product.columns else pd.DataFrame()

render_table_section(
    "High Fee Review Candidates",
    "Products whose fee percentage crosses the review threshold. Values are ratios, not raw fees.",
    fee_candidates[[col for col in candidate_columns if col in fee_candidates.columns]],
    height=360,
    download_name="high_fee_review_candidates",
)
render_table_section(
    "Refund Review Candidates",
    "Products flagged by indexed sales and refund-ratio rules for business review.",
    refund_candidates[[col for col in candidate_columns if col in refund_candidates.columns]],
    height=360,
    download_name="refund_review_candidates",
)
render_table_section(
    "Promotion Review Candidates",
    "Products with promotion pressure and weaker net-to-gross quality.",
    promotion_candidates[[col for col in candidate_columns if col in promotion_candidates.columns]],
    height=360,
    download_name="promotion_review_candidates",
)
render_table_section(
    "Weak Revenue Quality Candidates",
    "Products with lower revenue quality score for gross-to-net review.",
    weak_quality,
    height=360,
    download_name="weak_revenue_quality_candidates",
)
render_footer()
