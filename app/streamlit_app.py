from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components.kpi_cards import render_kpi_cards  # noqa: E402
from app.components.style import (  # noqa: E402
    PROJECT_TITLE,
    inject_global_css,
    render_empty_state,
    render_footer,
    render_insight_box,
    render_sidebar_status,
    render_value_card,
    render_workflow_strip,
)
from app.components.tables import render_table_section  # noqa: E402
from app.components.upload_panel import render_upload_panel  # noqa: E402
from app.utils.data_cleaner import AppDataError  # noqa: E402
from app.utils.data_loader import build_demo_result, run_analysis_from_uploads_with_options  # noqa: E402
from app.utils.export_utils import dataframe_to_csv_bytes  # noqa: E402


st.set_page_config(
    page_title="Shivam Multi-Marketplace Analytics",
    layout="wide",
)


ANALYSIS_MODES = ["Upload 2 Files", "Sample Demo"]
SAMPLE_DEMO_OPTIONS = {
    "Sample: 1 Month / 10K Orders": "1m",
    "Sample: 3 Months / 30K Orders": "3m",
    "Sample: 6 Months / 60K Orders": "6m",
    "Sample: 12 Months / 120K Orders": "12m",
}


def render_downloads(result: dict[str, object]) -> None:
    outputs = result["outputs"]
    st.subheader("Download Public Outputs")
    st.caption("Exports include only privacy-safe public CSVs. Private raw files and mappings are never included.")
    st.download_button(
        "Download All Public Outputs as ZIP",
        data=result["zip_bytes"],
        file_name="shivam_public_outputs.zip",
        mime="application/zip",
        use_container_width=True,
        key="main_download_all_public_outputs_zip",
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
                label,
                data=dataframe_to_csv_bytes(df),
                file_name=f"{name}.csv",
                mime="text/csv",
                use_container_width=True,
                key=f"main_quick_download_{name}",
            )

    names = [
        "anonymized_master",
        "marketplace_summary",
        "marketplace_channel_performance",
        "product_performance",
        "category_performance",
        "brand_performance",
        "profitability_summary",
        "margin_risk_review",
        "inventory_action_review",
        "fee_refund_summary",
        "fulfillment_comparison",
        "product_action_review",
        "dataset_profile",
        "validation_summary",
    ]
    with st.expander("All individual public CSV downloads", expanded=False):
        for start in range(0, len(names), 3):
            cols = st.columns(3)
            for col, name in zip(cols, names[start : start + 3]):
                df = outputs.get(name)
                if df is not None:
                    col.download_button(
                        label=f"{name}.csv",
                        data=dataframe_to_csv_bytes(df),
                        file_name=f"{name}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key=f"main_individual_download_{name}",
                    )


def launch_sample_dashboard(dataset_period: str) -> None:
    st.session_state["analysis_result"] = build_demo_result(dataset_period=dataset_period)
    st.success("Sample public dashboard loaded. Dashboard pages are ready.")


def render_upload_card(step: str, title: str, body: str, status: str) -> None:
    status_class = {
        "Ready": "status-pass",
        "Uploaded": "status-info",
        "Missing": "status-warn",
    }.get(status, "status-muted")
    step_label = step if step.endswith(":") else f"{step}:"
    st.markdown(
        f"""
        <div class="upload-card">
            <div class="upload-card-step">{step_label}</div>
            <div class="upload-card-title">{title}</div>
            <div class="upload-card-body">{body}</div>
            <span class="status-badge {status_class}">Status: {status}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    inject_global_css()
    st.sidebar.markdown("### Analysis Mode")
    analysis_mode = st.sidebar.radio(
        "Choose analysis mode",
        ANALYSIS_MODES,
        index=0,
        label_visibility="collapsed",
    )
    product_upload = None
    transaction_upload = None
    run_clicked = False
    main_run_clicked = False
    sample_label = "Sample: 12 Months / 120K Orders"
    sample_period = SAMPLE_DEMO_OPTIONS[sample_label]
    if analysis_mode == "Upload 2 Files":
        with st.sidebar:
            product_upload, transaction_upload, run_clicked = render_upload_panel()
    else:
        with st.sidebar.expander("Sample Demo", expanded=True):
            st.caption("Loads the currently generated privacy-safe public outputs for screenshots and testing.")
            if st.button("Launch Sample Demo Dashboard", use_container_width=True, key="sidebar_launch_sample"):
                try:
                    launch_sample_dashboard(sample_period)
                except AppDataError as exc:
                    st.error(str(exc))

    st.markdown(
        f"""
        <div class="hero">
            <div class="eyebrow">Local privacy-safe analytics dashboard</div>
            <div class="hero-title">{PROJECT_TITLE}</div>
            <div class="hero-subtitle">Upload a product master and transaction report to automatically generate privacy-safe marketplace analytics across sales quality, fees, refunds, profitability signals, inventory review, and action recommendations.</div>
            <div class="hero-description">Private identifiers and raw financial values are removed or converted into indexes, ratios, scores, and bands before public reporting.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    value_cols = st.columns(4)
    value_cards = [
        ("2-File Upload", "Product master + transaction report."),
        ("Privacy-Safe", "No ASINs, SKUs, order IDs, titles, or raw rupee values in public outputs."),
        ("5-Marketplace Ready", "Amazon, Flipkart, Meesho, JioMart, Website."),
        ("Action Recommendations", "Fee, refund, promotion, margin-risk, restock, and slow-mover review."),
    ]
    for col, (title, body) in zip(value_cols, value_cards):
        with col:
            render_value_card(title, body)

    product_ready = bool(product_upload)
    transaction_ready = bool(transaction_upload)
    all_files_ready = product_ready and transaction_ready
    product_status = "Ready" if all_files_ready else "Uploaded" if product_ready else "Missing"
    transaction_status = "Ready" if all_files_ready else "Uploaded" if transaction_ready else "Missing"
    card_cols = st.columns(2)
    with card_cols[0]:
        render_upload_card(
            "Step 1",
            "Product / Cost / Marketplace Master",
            "Excel workbook with product attributes, inventory bands, margin bands, and 5-marketplace mapping.",
            product_status,
        )
    with card_cols[1]:
        render_upload_card(
            "Step 2",
            "Marketplace Transaction Report",
            "CSV export with orders, refunds, fees, fulfillment, promotions, and settlement activity.",
            transaction_status,
        )
    main_run_clicked = st.button(
        "Run Full Analysis",
        type="primary",
        use_container_width=True,
        disabled=not all_files_ready or analysis_mode != "Upload 2 Files",
        key="main_run_full_analysis",
    )
    if analysis_mode == "Upload 2 Files" and not all_files_ready:
        st.info("Upload both required files to run the full analysis.")

    st.subheader("What happens after upload?")
    render_workflow_strip(["Upload", "Clean", "Join", "Anonymize", "Validate", "Analyze", "Export"])
    st.caption(
        "The app turns private marketplace files into dashboard-ready public outputs using indexes, ratios, scores, and bands."
    )

    if analysis_mode == "Upload 2 Files" and (run_clicked or main_run_clicked):
        try:
            with st.spinner("Running full local analysis and privacy checks..."):
                st.session_state["analysis_result"] = run_analysis_from_uploads_with_options(
                    product_upload,
                    transaction_upload,
                    dataset_period="custom_upload",
                )
            st.success("Analysis complete. Dashboard pages are ready.")
        except AppDataError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Analysis failed: {exc}")

    result = st.session_state.get("analysis_result")
    render_sidebar_status(
        product_upload=product_upload,
        transaction_upload=transaction_upload,
        result=result,
        analysis_mode=analysis_mode,
    )
    if result:
        st.sidebar.caption(f"Dataset label: {result.get('dataset_label', result.get('dataset_period', 'custom_upload'))}")
        st.divider()
        st.subheader("Analysis Snapshot")
        render_kpi_cards(
            result["kpis"],
            columns=5,
            statuses={
                "Join Coverage %": "Passed",
                "High Priority Actions": "Ready",
            },
        )
        render_insight_box(result["summary_text"])

        with st.expander("Validation Summary", expanded=False):
            render_table_section(
                "Validation Summary",
                "Safety checks confirm public outputs exclude private identifiers and raw financial values.",
                result["validation_summary"],
                height=360,
                download_name="validation_summary",
            )

        render_downloads(result)
    else:
        render_empty_state()

    st.markdown(
        """
        <div class="muted-demo-note">
            <strong>Want to explore without private files?</strong><br>
            Select Sample Demo in the sidebar.
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_footer()


if __name__ == "__main__":
    main()
