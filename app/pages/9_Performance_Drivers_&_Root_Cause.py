from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components.charts import horizontal_bar_chart  # noqa: E402
from app.components.kpi_cards import render_kpi_cards  # noqa: E402
from app.components.style import inject_global_css, render_footer, render_insight_box, render_mode_badge, render_page_header, render_sidebar_status  # noqa: E402
from app.components.tables import render_table_section  # noqa: E402
from shared.variance_engine import METRIC_LABELS, format_excluded_trailing_message  # noqa: E402


st.set_page_config(page_title="Performance Drivers & Root Cause", layout="wide")
inject_global_css()
render_page_header(
    "Performance Drivers & Root Cause",
    "Deterministic, descriptive period-over-period variance decomposition — not a causal model. "
    "Explanations use \"associated with\"/\"contributed to\" language and never claim a metric "
    "was \"caused by\" a single factor.",
)

result = st.session_state.get("analysis_result")
render_sidebar_status(result=result)
if not result:
    st.info("Load demo public outputs or upload files on the main page first.")
    st.stop()
render_mode_badge(result)

outputs = result["outputs"]
driver_summary = outputs.get("mart_performance_driver_summary", pd.DataFrame())
marketplace_drivers = outputs.get("mart_marketplace_variance_drivers", pd.DataFrame())
product_contributors = outputs.get("mart_product_variance_contributors", pd.DataFrame())

if driver_summary.empty:
    st.info(
        "No performance-driver mart is available for this dataset. Run the pipeline or upload "
        "files with at least two distinct transaction months to enable root-cause analysis."
    )
    render_footer()
    st.stop()

if len(driver_summary) == 1 and driver_summary.iloc[0]["movement"] == "Insufficient Periods":
    st.warning(driver_summary.iloc[0]["narrative"])
    render_insight_box(
        "This page requires at least two distinct transaction months in the loaded dataset. "
        "With a single-period dataset, no period-over-period comparison is fabricated — this "
        "is a deliberate design choice (see docs/business_rules.md, rule BR-16)."
    )
    render_footer()
    st.stop()

previous_period = driver_summary.iloc[0]["previous_period"]
current_period = driver_summary.iloc[0]["current_period"]
st.caption(
    f"Comparing **{previous_period}** (previous) to **{current_period}** (current) — the two most "
    "recent VALID transaction months with recorded activity in this dataset."
)

# A trailing calendar month with zero recorded activity (e.g. an
# in-progress or not-yet-populated month) is safely excluded from the
# comparison above rather than compared against — this message only
# appears when such a period actually exists (Requirement 7).
excluded_periods_value = driver_summary.iloc[0].get("excluded_trailing_periods", "")
if excluded_periods_value:
    excluded_periods_list = [p.strip() for p in str(excluded_periods_value).split(",") if p.strip()]
    st.info(format_excluded_trailing_message(excluded_periods_list))

available_metrics = [m for m in driver_summary["metric"].tolist() if m in METRIC_LABELS]
metric_labels = {m: METRIC_LABELS.get(m, m) for m in available_metrics}
selected_metric = st.selectbox(
    "Metric to investigate",
    options=available_metrics,
    format_func=lambda m: metric_labels.get(m, m),
    index=0,
)

metric_row = driver_summary[driver_summary["metric"] == selected_metric].iloc[0]
abs_variance = metric_row["total_abs_variance"]
pct_variance = metric_row["total_pct_variance"]
movement = metric_row["movement"]

render_kpi_cards(
    {
        "Previous Period": previous_period,
        "Current Period": current_period,
        "Absolute Variance": round(float(abs_variance), 1) if pd.notna(abs_variance) else "n/a",
        "Percentage Variance": (f"{float(pct_variance):.1f}%" if pd.notna(pct_variance) else "n/a (previous was zero)"),
        "Movement": movement,
    },
    columns=3,
)

render_insight_box(metric_row["narrative"], title="Deterministic Narrative")

st.subheader("Marketplace Contribution")
marketplace_metric_rows = marketplace_drivers[marketplace_drivers["metric"] == selected_metric].copy()
if marketplace_metric_rows.empty:
    st.info("No marketplace-level breakdown is available for this metric.")
else:
    marketplace_metric_rows = marketplace_metric_rows.sort_values(
        "abs_variance", key=lambda s: s.abs(), ascending=False
    )
    # horizontal_bar_chart ranks by raw (signed) value, so chart magnitude
    # separately from the signed value shown in the table below — otherwise a
    # large negative (deteriorating) variance would rank at the bottom, not
    # the top, of a "top contributor" chart.
    marketplace_metric_rows["abs_variance_magnitude"] = marketplace_metric_rows["abs_variance"].abs()
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            horizontal_bar_chart(
                marketplace_metric_rows,
                "abs_variance_magnitude",
                "marketplace",
                f"{metric_labels[selected_metric]} — Absolute Variance Magnitude by Marketplace",
                top_n=10,
            ),
            use_container_width=True,
        )
    with right:
        st.plotly_chart(
            horizontal_bar_chart(
                marketplace_metric_rows,
                "contribution_share_pct",
                "marketplace",
                f"{metric_labels[selected_metric]} — Contribution Share % by Marketplace",
                top_n=10,
            ),
            use_container_width=True,
        )
    render_table_section(
        "Marketplace Variance Detail",
        "Previous value, current value, absolute/percentage variance, contribution share, and movement direction per marketplace.",
        marketplace_metric_rows[
            ["marketplace", "previous_value", "current_value", "abs_variance", "pct_variance", "contribution_share_pct", "movement"]
        ],
        height=280,
        download_name=f"marketplace_variance_{selected_metric}",
    )

st.subheader("Top Product Contributors")
product_metric_rows = product_contributors[product_contributors["metric"] == selected_metric].copy()
if product_metric_rows.empty:
    st.info("No product-level breakdown is available for this metric.")
else:
    product_metric_rows = product_metric_rows.sort_values(
        "abs_variance", key=lambda s: s.abs(), ascending=False
    ).head(25)
    render_table_section(
        "Product Variance Contributors (Top 25 by Absolute Variance)",
        "Ranked, deterministic contribution of each product to the selected metric's period-over-period movement. "
        "No SKUs, ASINs, order IDs, or raw currency values are shown — only anonymized public product IDs.",
        product_metric_rows[
            [
                "public_product_id",
                "marketplace",
                "brand_group",
                "category_group",
                "previous_value",
                "current_value",
                "abs_variance",
                "pct_variance",
                "contribution_share_pct",
                "movement",
            ]
        ],
        height=420,
        download_name=f"product_variance_contributors_{selected_metric}",
    )

st.subheader("All Headline Metrics — Driver Summary")
render_table_section(
    "Performance Driver Summary",
    "One row per headline metric: previous/current period totals, variance, movement, and the deterministic narrative shown above for the selected metric.",
    driver_summary[["metric_label", "previous_period", "current_period", "total_abs_variance", "total_pct_variance", "movement", "narrative", "excluded_trailing_periods"]],
    height=360,
    download_name="performance_driver_summary",
)

render_footer()
