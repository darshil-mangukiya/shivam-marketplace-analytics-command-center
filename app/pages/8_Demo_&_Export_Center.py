from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components.kpi_cards import render_kpi_cards  # noqa: E402
from app.components.style import inject_global_css, render_footer, render_insight_box, render_mode_badge, render_page_header, render_sidebar_status  # noqa: E402
from app.components.tables import render_table_section  # noqa: E402
from app.utils.data_cleaner import AppDataError  # noqa: E402
from app.utils.data_loader import build_demo_result  # noqa: E402
from app.utils.export_utils import dataframe_to_csv_bytes  # noqa: E402


st.set_page_config(page_title="Demo & Export Center", layout="wide")
inject_global_css()
render_page_header(
    "Demo & Export Center",
    "Load sample public outputs, export privacy-safe CSVs, and review screenshot-ready dashboard outputs.",
)

result = st.session_state.get("analysis_result")
render_sidebar_status(result=result)

demo_options = {
    "Sample: 1 Month / 10K Orders": "1m",
    "Sample: 3 Months / 30K Orders": "3m",
    "Sample: 6 Months / 60K Orders": "6m",
    "Sample: 12 Months / 120K Orders": "12m",
}
sample_catalog = pd.DataFrame(
    [{"sample_dataset_label": label, "dataset_period_code": period} for label, period in demo_options.items()]
)

if not result:
    left, right = st.columns([1, 2])
    with left:
        if st.button("Launch Sample Dashboard", use_container_width=True):
            try:
                st.session_state["analysis_result"] = build_demo_result(dataset_period="latest")
                st.success("Sample public outputs loaded.")
                st.rerun()
            except AppDataError as exc:
                st.error(str(exc))
    with right:
        st.caption(
            "Sample datasets are generated from marketplace-report patterns for screenshots, testing, and scalability checks. "
            "The loaded dashboard uses the currently generated public outputs."
        )
    render_table_section(
        "Supported Sample Dataset Labels",
        "Examples used for generated demo transaction datasets. Upload mode remains the primary workflow.",
        sample_catalog,
        height=220,
        download_name="sample_dataset_labels",
    )
    st.info("No active result yet. Load sample public outputs above or upload two files from the main page.")
    st.stop()
render_mode_badge(result)

outputs = result["outputs"]
profile_source = outputs.get("dataset_profile", pd.DataFrame())
profile_rows = profile_source.to_dict("records") if not profile_source.empty else []
profile_names = {str(row.get("public_output_name", "")) for row in profile_rows}
for output_name, output_df in outputs.items():
    if output_name not in profile_names:
        profile_rows.append(
            {
                "public_output_name": output_name,
                "row_count": len(output_df) if hasattr(output_df, "__len__") else 0,
                "dataset_period": result.get("dataset_period", ""),
                "dataset_label": result.get("dataset_label", ""),
            }
        )
profile = pd.DataFrame(profile_rows)
validation = result.get("validation_summary", pd.DataFrame())
privacy_status = "Passed"
if not validation.empty and "check_status" in validation.columns:
    if validation["check_status"].eq("FAIL").any():
        privacy_status = "Failed"
    elif validation["check_status"].eq("WARN").any():
        privacy_status = "Warning"

render_kpi_cards(
    {
        "Demo Dataset": result.get("dataset_label", result.get("dataset_period", "latest")),
        "Public Outputs": f"{len(outputs)} CSV Files",
        "Privacy Status": privacy_status,
    },
    columns=3,
)
render_insight_box(
    "Demo mode loads privacy-safe public outputs for demo screenshots and testing. Upload mode remains the primary workflow for custom analysis."
)

st.subheader("Download Public Outputs")
st.download_button(
    "Download All Public Outputs as ZIP",
    data=result["zip_bytes"],
    file_name="shivam_public_outputs.zip",
    mime="application/zip",
    use_container_width=True,
    key="export_center_download_all_public_outputs_zip",
)
quick_downloads = [
    ("Download Product Performance CSV", "product_performance"),
    ("Download Marketplace Performance CSV", "marketplace_channel_performance"),
    ("Download Profitability Summary CSV", "profitability_summary"),
    ("Download Validation Summary CSV", "validation_summary"),
]
cols = st.columns(4)
for col, (label, name) in zip(cols, quick_downloads):
    df = outputs.get(name)
    if df is not None:
        col.download_button(
            label=label,
            data=dataframe_to_csv_bytes(df),
            file_name=f"{name}.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"export_center_quick_download_{name}",
        )

render_table_section(
    "Public Output Inventory",
    "Public CSV files available for Power BI, Excel, Streamlit, and documentation screenshots.",
    profile,
    height=420,
    download_name="dataset_profile",
)

screenshot_checklist = pd.DataFrame(
    [
        {"step": "Executive overview", "screenshot_focus": "KPIs, trend, action priority"},
        {"step": "Marketplace performance page", "screenshot_focus": "Marketplace comparison charts"},
        {"step": "Profitability page", "screenshot_focus": "Margin risk and estimated profitability indexes"},
        {"step": "Inventory action page", "screenshot_focus": "Restock and slow-mover recommendations"},
        {"step": "Validation page", "screenshot_focus": "Privacy scan and PASS/WARN/FAIL checks"},
    ]
)
render_table_section(
    "Screenshot Checklist",
    "Use these views for README and documentation screenshots.",
    screenshot_checklist,
    height=300,
    download_name="screenshot_checklist",
)

with st.expander("View supported sample dataset labels", expanded=False):
    left, right = st.columns([1, 2])
    with left:
        if st.button("Reload Sample Dashboard", use_container_width=True):
            try:
                st.session_state["analysis_result"] = build_demo_result(dataset_period="latest")
                st.success("Sample public outputs reloaded.")
                st.rerun()
            except AppDataError as exc:
                st.error(str(exc))
    with right:
        st.caption(
            "Generated sample datasets are included for screenshots, testing, and scale checks. Upload mode remains the primary workflow."
        )
    render_table_section(
        "Supported Sample Dataset Labels",
        "Examples used for generated demo transaction datasets.",
        sample_catalog,
        height=220,
        download_name="sample_dataset_labels",
    )

with st.expander("All individual public CSV downloads", expanded=False):
    for name, df in outputs.items():
        st.download_button(
            label=f"{name}.csv",
            data=dataframe_to_csv_bytes(df),
            file_name=f"{name}.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"export_center_individual_download_{name}",
        )
render_footer()
