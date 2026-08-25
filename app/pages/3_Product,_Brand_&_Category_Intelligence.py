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
from app.utils.filters import apply_dashboard_filters, apply_marketplace_product_filter, filter_source_from_outputs, has_active_filters, render_marketplace_product_filters, render_sidebar_filters  # noqa: E402


st.set_page_config(page_title="Product, Brand & Category Intelligence", layout="wide")
inject_global_css()
render_page_header(
    "Product, Brand & Category Intelligence",
    "Analyze products, brands, categories, imported status, price bands, and inventory bands with public-safe fields only.",
)

result = st.session_state.get("analysis_result")
render_sidebar_status(result=result)
if not result:
    st.info("Load demo public outputs or upload files on the main page first.")
    st.stop()
render_mode_badge(result)

product = result["outputs"].get("product_performance", pd.DataFrame())
master = result["outputs"].get("anonymized_master", pd.DataFrame())

dashboard_filters = render_sidebar_filters(filter_source_from_outputs(result["outputs"]))
filtered = apply_dashboard_filters(product, dashboard_filters)
filtered_master = apply_dashboard_filters(master, dashboard_filters)

st.markdown("#### Marketplace & Product Filters")
selected_marketplace, selected_product_id = render_marketplace_product_filters(
    product, key_prefix="product_brand_category"
)
filtered = apply_marketplace_product_filter(filtered, selected_marketplace, selected_product_id)
filtered_master = apply_marketplace_product_filter(filtered_master, selected_marketplace, selected_product_id)

any_filter_active = (
    has_active_filters(dashboard_filters)
    or selected_marketplace != "All"
    or selected_product_id != "All"
)
if any_filter_active and filtered.empty:
    st.info("No records match the selected filters.")

render_kpi_cards(
    {
        "Products With Transactions": int(filtered["public_product_id"].nunique()) if "public_product_id" in filtered.columns else 0,
        "Products in Analysis": int(filtered["public_product_id"].nunique()) if "public_product_id" in filtered.columns else 0,
        "Category Count": int(filtered["category_group"].nunique()) if "category_group" in filtered.columns else 0,
        "Brand Count": int(filtered["brand_group"].nunique()) if "brand_group" in filtered.columns else 0,
        "Average Net-to-Gross %": round(float(filtered["net_to_gross_pct"].mean() or 0), 1) if not filtered.empty else 0,
        "Average Revenue Quality Score": round(float(filtered["revenue_quality_score"].mean() or 0), 1) if not filtered.empty else 0,
    },
    columns=3,
)
render_insight_box("Filters let you compare product groups across marketplaces while keeping exact titles and identifiers private.")

left, right = st.columns(2)
with left:
    st.plotly_chart(bar_chart(filtered, "product_group", "sales_index", "Top Product Groups", agg="mean", top_n=15), use_container_width=True)
with right:
    st.plotly_chart(bar_chart(filtered, "brand_group", "sales_index", "Top Brand Groups", agg="mean", top_n=15), use_container_width=True)

left, right = st.columns(2)
with left:
    st.plotly_chart(bar_chart(filtered, "category_group", "sales_index", "Category Sales Index", agg="mean", top_n=12), use_container_width=True)
with right:
    imported = (
        filtered_master.groupby("imported_flag", dropna=False)
        .agg(sales_index=("sales_index", "mean"), units_index=("units_index", "mean"))
        .reset_index()
        if "imported_flag" in filtered_master.columns
        else pd.DataFrame()
    )
    st.plotly_chart(bar_chart(imported, "imported_flag", "sales_index", "Imported vs Non-Imported Sales Index", top_n=8), use_container_width=True)

st.plotly_chart(
    scatter_chart(
        filtered,
        "sales_index",
        "net_to_gross_pct",
        "Sales Index vs Net-to-Gross %",
        color="category_group",
        hover_name="public_product_id",
    ),
    use_container_width=True,
)

low_sales = (
    filtered.groupby(["marketplace", "product_group"], dropna=False)
    .agg(
        product_count=("public_product_id", "nunique"),
        sales_index=("sales_index", "mean"),
        units_index=("units_index", "mean"),
        net_to_gross_pct=("net_to_gross_pct", "mean"),
    )
    .reset_index()
    .query("sales_index < 10")
    .sort_values(["sales_index", "units_index"], ascending=True)
    if not filtered.empty
    else pd.DataFrame()
)
render_table_section(
    "Product Performance",
    "Filtered public product table with anonymized IDs, indexes, ratios, scores, and action labels.",
    filtered,
    height=520,
    download_name="filtered_product_performance",
)
render_table_section(
    "Low-Sales Product Groups",
    "Product groups with low indexed sales activity for pricing, listing, or assortment review.",
    low_sales,
    height=360,
    download_name="low_sales_product_groups",
)
render_footer()
