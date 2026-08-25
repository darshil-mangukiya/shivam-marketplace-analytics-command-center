from __future__ import annotations

import math
from typing import Mapping

import streamlit as st

from app.components.style import inject_global_css, status_badge


PERCENT_KPIS = {
    "Join Coverage %",
    "Average Fee % of Gross",
    "Average Refund % of Gross",
    "Average Promotion % of Gross",
    "Average Net-to-Gross %",
}


def inject_kpi_css() -> None:
    inject_global_css()


def format_kpi(label: str, value: object) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "N/A"
    if label in PERCENT_KPIS:
        return f"{float(value):.1f}%"
    if isinstance(value, float):
        return f"{value:,.1f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def render_kpi_card(label: str, value: object, helper_text: str | None = None, status: str | None = None) -> None:
    badge = status_badge(status, status) if status else ""
    helper = f'<div class="kpi-helper">{helper_text}</div>' if helper_text else ""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{format_kpi(label, value)}</div>
            {helper}
            {badge}
        </div>
        """,
        unsafe_allow_html=True,
    )


DEFAULT_HELPERS = {
    "Product Master Rows": "Cleaned listing rows available for product context",
    "Transaction Rows": "Uploaded marketplace transaction rows processed",
    "Order Rows": "Order-type rows in the selected transaction dataset",
    "Join Coverage %": "Rows with SKUs matched to product master",
    "Channel Mapping Status": "Marketplace-channel enrichment is unavailable because the mapping keys are incomplete",
    "Products in Analysis": "Anonymized products represented in the selected dashboard dataset",
    "Products With Transactions": "Anonymized product IDs appearing in the selected transaction dataset",
    "Marketplaces": "Marketplaces represented in the selected dataset",
    "Category Count": "Public category groups represented",
    "Brand Count": "Public brand groups represented",
    "Average Fee % of Gross": "Fee ratio; raw money values hidden",
    "Average Refund % of Gross": "Refund ratio; raw money values hidden",
    "Average Promotion % of Gross": "Promotion ratio; raw money values hidden",
    "Average Net-to-Gross %": "Net quality ratio; raw money values hidden",
    "High Priority Actions": "Action rows marked high priority",
    "Average Margin Risk Score": "0-100 score from fee, refund, promotion, net, and margin signals",
    "Average Revenue Quality Score": "0-100 score summarizing gross-to-net quality",
    "Refund Review Count": "Products flagged for refund review",
    "Promotion Review Count": "Products flagged for promotion review",
    "Fee Review Count": "Products flagged for fee review",
    "Slow Mover Review Count": "Low unit index with high inventory band",
    "Margin Risk Review Count": "Products flagged by margin-risk score",
    "Restock Review Count": "Products flagged for restock review",
}


def render_kpi_cards(
    kpis: Mapping[str, object],
    columns: int = 5,
    helpers: Mapping[str, str] | None = None,
    statuses: Mapping[str, str] | None = None,
) -> None:
    inject_global_css()
    helper_lookup = {**DEFAULT_HELPERS, **(helpers or {})}
    items = list(kpis.items())
    for start in range(0, len(items), columns):
        row = st.columns(columns)
        for col, (label, value) in zip(row, items[start : start + columns]):
            with col:
                render_kpi_card(
                    label,
                    value,
                    helper_text=helper_lookup.get(label),
                    status=(statuses or {}).get(label),
                )
