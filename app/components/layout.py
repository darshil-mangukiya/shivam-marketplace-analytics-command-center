from __future__ import annotations

import streamlit as st

from app.components.style import render_insight_box, render_page_header, render_sidebar_status


def require_result(page_title: str, purpose: str) -> dict[str, object]:
    render_page_header(page_title, purpose)
    result = st.session_state.get("analysis_result")
    render_sidebar_status(result=result)
    if not result:
        st.info("Load demo public outputs or upload files on the main page first.")
        st.stop()
    return result


def insight(text: str, title: str = "Insight Summary") -> None:
    render_insight_box(text, title)

