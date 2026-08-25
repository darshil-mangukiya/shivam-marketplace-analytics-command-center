from __future__ import annotations

import pandas as pd
import streamlit as st

from app.utils.export_utils import dataframe_to_csv_bytes


PCT_COLUMNS = {
    "fee_pct_of_gross",
    "refund_pct_of_gross",
    "promotion_pct_of_gross",
    "net_to_gross_pct",
    "avg_fee_pct_of_gross",
    "avg_refund_pct_of_gross",
    "avg_promotion_pct_of_gross",
    "avg_net_to_gross_pct",
    "join_coverage_pct",
    "marketplace_join_coverage_pct",
}


def render_dataframe(df: pd.DataFrame, *, height: int = 420) -> None:
    if df.empty:
        st.info("No records match the selected filters.")
        return
    column_config = {
        col: st.column_config.NumberColumn(col, format="%.1f")
        for col in df.columns
        if col.endswith("_index") or col.endswith("_score") or col in PCT_COLUMNS
    }
    if "action_priority" in df.columns:
        column_config["action_priority"] = st.column_config.TextColumn("action_priority", help="High, Medium, or Low priority")
    if "recommended_action" in df.columns:
        column_config["recommended_action"] = st.column_config.TextColumn("recommended_action", help="Rule-based public action label")
    st.dataframe(df, use_container_width=True, height=height, hide_index=True, column_config=column_config)


def render_table_section(
    title: str,
    explanation: str,
    df: pd.DataFrame,
    *,
    height: int = 420,
    download_name: str | None = None,
) -> None:
    st.markdown(
        f"""
        <div class="table-card">
            <div class="table-title">{title}</div>
            <div class="table-caption">{explanation}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_dataframe(df, height=height)
    if download_name and not df.empty:
        st.download_button(
            label=f"Download {download_name}.csv",
            data=dataframe_to_csv_bytes(df),
            file_name=f"{download_name}.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"table_download_{download_name}",
        )


def filter_dataframe(df: pd.DataFrame, filters: dict[str, list[str]]) -> pd.DataFrame:
    filtered = df.copy()
    for col, selected in filters.items():
        if col in filtered.columns and selected:
            filtered = filtered[filtered[col].astype(str).isin(selected)]
    return filtered
