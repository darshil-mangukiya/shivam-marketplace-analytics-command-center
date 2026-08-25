from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components.charts import bar_chart, donut_chart, scatter_chart  # noqa: E402
from app.components.kpi_cards import render_kpi_cards  # noqa: E402
from app.components.style import inject_global_css, render_footer, render_insight_box, render_mode_badge, render_page_header, render_sidebar_status  # noqa: E402
from app.components.tables import render_table_section  # noqa: E402
from app.utils.filters import apply_dashboard_filters, filter_source_from_outputs, has_active_filters, render_sidebar_filters  # noqa: E402
from app.utils.recommendations import action_counts, priority_counts  # noqa: E402


st.set_page_config(page_title="Inventory, Restock & Action Review", layout="wide")
inject_global_css()
render_page_header(
    "Inventory, Restock & Action Review",
    "Prioritize restock, slow-mover, margin-risk, fee, refund, promotion, and pricing review candidates.",
)

result = st.session_state.get("analysis_result")
render_sidebar_status(result=result)
if not result:
    st.info("Load demo public outputs or upload files on the main page first.")
    st.stop()
render_mode_badge(result)

inventory = result["outputs"].get("inventory_action_review", pd.DataFrame())
action = result["outputs"].get("product_action_review", pd.DataFrame())

dashboard_filters = render_sidebar_filters(filter_source_from_outputs(result["outputs"]))
filtered = apply_dashboard_filters(inventory, dashboard_filters)
if has_active_filters(dashboard_filters) and filtered.empty:
    st.info("No records match the selected filters.")

render_kpi_cards(
    {
        "High Priority Actions": int((filtered["action_priority"] == "High").sum()) if not filtered.empty else 0,
        "Restock Review Count": int((filtered["recommended_action"] == "Restock Review").sum()) if "recommended_action" in filtered.columns else 0,
        "Slow Mover Review Count": int((filtered["recommended_action"] == "Slow Mover Review").sum()) if "recommended_action" in filtered.columns else 0,
        "Margin Risk Review Count": int((filtered["recommended_action"] == "Margin Risk Review").sum()) if "recommended_action" in filtered.columns else 0,
    },
    columns=4,
)
render_insight_box("Inventory action review combines indexed unit movement, inventory bands, restock priority, revenue quality, and margin risk.")

left, right = st.columns(2)
with left:
    st.plotly_chart(donut_chart(action_counts(filtered), "recommended_action", "count", "Recommended Action Count"), use_container_width=True)
with right:
    st.plotly_chart(donut_chart(priority_counts(filtered), "action_priority", "count", "Action Priority Count"), use_container_width=True)

left, right = st.columns(2)
with left:
    st.plotly_chart(bar_chart(filtered, "inventory_band", "units_index", "Units Index by Inventory Band", agg="mean", top_n=10), use_container_width=True)
with right:
    st.plotly_chart(bar_chart(filtered, "restock_priority", "sales_index", "Sales Index by Restock Priority", agg="mean", top_n=10), use_container_width=True)

st.plotly_chart(
    scatter_chart(
        filtered,
        "units_index",
        "sales_index",
        "Units Index vs Sales Index",
        color="recommended_action",
        hover_name="public_product_id",
    ),
    use_container_width=True,
)

inventory_preview = (
    filtered.assign(
        _priority_rank=filtered.get("action_priority", pd.Series(dtype=str)).map({"High": 1, "Medium": 2, "Low": 3}).fillna(4)
    )
    .sort_values(["_priority_rank", "sales_index", "units_index"], ascending=[True, False, False])
    .drop(columns=["_priority_rank"], errors="ignore")
    .head(10)
    if not filtered.empty
    else pd.DataFrame()
)
inventory_preview_columns = [
    "public_product_id",
    "marketplace",
    "category_group",
    "brand_group",
    "product_group",
    "inventory_band",
    "units_index",
    "sales_index",
    "restock_priority",
    "recommended_action",
    "action_priority",
]
render_table_section(
    "Inventory Action Review Table",
    "Top filtered action rows for restock, slow-mover, margin-risk, fee, refund, and promotion review.",
    inventory_preview[[col for col in inventory_preview_columns if col in inventory_preview.columns]],
    height=300,
)

slow_movers = filtered[
    (filtered["units_index"] < 10) & (filtered["inventory_band"].astype(str).str.contains("High", case=False, na=False))
] if not filtered.empty and "inventory_band" in filtered.columns else pd.DataFrame()
restock_candidates = filtered[
    (filtered["units_index"] >= 50) & (
        filtered["inventory_band"].astype(str).str.contains("Low|Out of Stock", case=False, regex=True, na=False)
        | filtered.get("restock_priority", pd.Series(dtype=str)).astype(str).str.contains("High", case=False, na=False)
    )
] if not filtered.empty and "inventory_band" in filtered.columns else pd.DataFrame()
restock_candidates = restock_candidates.head(10)
slow_movers = slow_movers.head(10)

render_table_section(
    "Inventory Action Review",
    "Anonymized action table with public IDs, grouped context, indexes, inventory bands, and action reasons.",
    filtered,
    height=620,
    download_name="filtered_inventory_action_review",
)
render_table_section(
    "Restock Review Candidates",
    "Low inventory or high restock-priority products with strong indexed unit movement.",
    restock_candidates[[col for col in inventory_preview_columns if col in restock_candidates.columns]],
    height=360,
    download_name="restock_review_candidates",
)
render_table_section(
    "Slow Mover Review Candidates",
    "High inventory-band products with low indexed unit activity.",
    slow_movers[[col for col in inventory_preview_columns if col in slow_movers.columns]],
    height=360,
    download_name="slow_mover_candidates",
)
render_footer()
