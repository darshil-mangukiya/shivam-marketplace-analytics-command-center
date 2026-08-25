from __future__ import annotations

from html import escape
from typing import Mapping

import streamlit as st

from shared.dataset_labels import dataset_label, dataset_mode_badge


PROJECT_TITLE = "Shivam Multi-Marketplace Analytics Command Center"
PROJECT_SUBTITLE = (
    "Upload product and transaction reports to generate privacy-safe marketplace performance, "
    "profitability, inventory, and product action insights."
)
STATUS_CLASS = {
    "not uploaded": "status-muted",
    "ready": "status-info",
    "processing": "status-info",
    "passed": "status-pass",
    "pass": "status-pass",
    "warning": "status-warn",
    "warn": "status-warn",
    "failed": "status-fail",
    "fail": "status-fail",
    "upload mode": "status-info",
    "demo mode": "status-warn",
}


def inject_global_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --navy: #0f172a;
            --blue: #2563eb;
            --teal: #0f766e;
            --slate: #475569;
            --muted: #64748b;
            --line: #dbe3ef;
            --card-line: #e2e8f0;
            --soft: #f8fafc;
            --soft-teal: #ecfdf5;
            --amber-soft: #fffbeb;
            --red-soft: #fef2f2;
        }
        .stApp {
            background: #f6f8fb;
            color: var(--navy);
        }
        .block-container {
            padding-top: 1.35rem;
            padding-bottom: 2.5rem;
            max-width: 1420px;
        }
        h1, h2, h3 {
            color: var(--navy);
            letter-spacing: 0;
        }
        h1 {
            font-size: 2rem;
            font-weight: 760;
        }
        h2 {
            font-size: 1.3rem;
            margin-top: 1.2rem;
        }
        h3 {
            font-size: 1rem;
        }
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--line);
        }
        [data-testid="stSidebarNav"]::before {
            content: "Shivam Multi-Marketplace\\A Analytics Command Center\\A Privacy-safe local BI dashboard";
            white-space: pre-line;
            display: block;
            color: var(--navy);
            font-weight: 820;
            line-height: 1.25;
            padding: 0.55rem 0.95rem 0.8rem 0.95rem;
            border-bottom: 1px solid var(--line);
            margin-bottom: 0.4rem;
        }
        [data-testid="stSidebarNav"] ul li:first-child {
            display: none;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: var(--slate);
            font-size: 0.9rem;
        }
        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button {
            border-radius: 7px;
            border: 1px solid #bfdbfe;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
        }
        div[data-testid="stButton"] > button[kind="primary"] {
            background: #1d4ed8;
            border-color: #1d4ed8;
        }
        div[data-testid="stButton"] > button:disabled {
            background: #e2e8f0 !important;
            color: #64748b !important;
            border-color: #cbd5e1 !important;
            box-shadow: none !important;
        }
        .hero {
            background: linear-gradient(135deg, #ffffff 0%, #f8fbff 62%, #eef6ff 100%);
            border: 1px solid var(--card-line);
            border-radius: 12px;
            padding: 1.55rem 1.6rem;
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.08);
            margin-bottom: 1rem;
        }
        .eyebrow {
            color: #0f766e;
            font-size: 0.78rem;
            font-weight: 760;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.45rem;
        }
        .hero-title {
            color: var(--navy);
            font-size: 2.25rem;
            line-height: 1.08;
            font-weight: 800;
            margin-bottom: 0.6rem;
        }
        .hero-subtitle {
            color: #1e40af;
            font-size: 1.15rem;
            line-height: 1.4;
            font-weight: 740;
            margin-bottom: 0.35rem;
        }
        .hero-description {
            color: var(--slate);
            font-size: 0.98rem;
            line-height: 1.5;
            max-width: 920px;
        }
        .hero-actions {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.75rem;
            margin-top: 1rem;
            max-width: 760px;
        }
        .hero-action-card {
            background: #ffffff;
            border: 1px solid #dbeafe;
            border-radius: 10px;
            color: var(--navy);
            font-weight: 780;
            padding: 0.78rem 0.85rem;
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
        }
        .hero-action-card span {
            display: block;
            color: var(--muted);
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.2rem;
        }
        .hero-action-primary {
            border-color: #93c5fd;
            background: #eff6ff;
        }
        .page-title {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1rem 1.15rem;
            box-shadow: 0 6px 20px rgba(15, 23, 42, 0.045);
            margin-bottom: 0.85rem;
        }
        .page-title h1 {
            margin: 0 0 0.28rem 0;
            font-size: 1.85rem;
        }
        .page-title p {
            margin: 0;
            color: var(--slate);
            line-height: 1.5;
        }
        .value-card, .panel-card, .empty-state, .insight-box, .table-card {
            background: #ffffff;
            border: 1px solid var(--card-line);
            border-radius: 10px;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
        }
        .value-card {
            padding: 1rem 1rem;
            min-height: 116px;
        }
        .value-card-title {
            color: var(--navy);
            font-size: 0.98rem;
            font-weight: 820;
            margin-bottom: 0.35rem;
        }
        .value-card-body {
            color: var(--slate);
            font-size: 0.88rem;
            line-height: 1.45;
        }
        .upload-card {
            background: #ffffff;
            border: 1px solid var(--card-line);
            border-radius: 12px;
            box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
            padding: 1.15rem 1.2rem;
            min-height: 166px;
        }
        .upload-card-step {
            color: #2563eb;
            font-size: 0.75rem;
            font-weight: 820;
            letter-spacing: 0;
            margin-bottom: 0.35rem;
        }
        .upload-card-title {
            color: var(--navy);
            font-size: 1.08rem;
            font-weight: 800;
            line-height: 1.25;
            margin-bottom: 0.45rem;
        }
        .upload-card-body {
            color: var(--slate);
            font-size: 0.9rem;
            line-height: 1.45;
            margin-bottom: 0.7rem;
        }
        .muted-demo-note {
            background: #f8fafc;
            border: 1px dashed #cbd5e1;
            border-radius: 10px;
            padding: 0.85rem 0.95rem;
            color: var(--slate);
            font-size: 0.9rem;
            line-height: 1.45;
            margin-top: 1rem;
        }
        .workflow-strip {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            align-items: center;
            background: #ffffff;
            border: 1px solid var(--card-line);
            border-radius: 12px;
            padding: 0.82rem;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.045);
            margin: 0.7rem 0 1rem 0;
        }
        .workflow-step {
            color: #1e3a8a;
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 999px;
            padding: 0.35rem 0.6rem;
            font-size: 0.82rem;
            font-weight: 700;
            white-space: nowrap;
        }
        .workflow-arrow {
            color: #64748b;
            font-weight: 700;
        }
        .kpi-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.95rem 1rem;
            background: #ffffff;
            min-height: 126px;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.045);
        }
        .kpi-label {
            color: var(--slate);
            font-size: 0.76rem;
            line-height: 1.25;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
            letter-spacing: 0.045em;
            font-weight: 740;
        }
        .kpi-value {
            color: var(--navy);
            font-size: 1.55rem;
            font-weight: 800;
            line-height: 1.05;
        }
        .kpi-helper {
            color: var(--muted);
            font-size: 0.78rem;
            line-height: 1.35;
            margin-top: 0.45rem;
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.18rem 0.48rem;
            font-size: 0.72rem;
            font-weight: 800;
            border: 1px solid transparent;
            margin-top: 0.45rem;
        }
        .status-pass {
            color: #065f46;
            background: #d1fae5;
            border-color: #a7f3d0;
        }
        .status-info {
            color: #1e3a8a;
            background: #dbeafe;
            border-color: #bfdbfe;
        }
        .status-warn {
            color: #92400e;
            background: #fef3c7;
            border-color: #fde68a;
        }
        .status-fail {
            color: #991b1b;
            background: #fee2e2;
            border-color: #fecaca;
        }
        .status-muted {
            color: #475569;
            background: #f1f5f9;
            border-color: #e2e8f0;
        }
        .insight-box {
            border-left: 4px solid var(--teal);
            background: #f8fffc;
            padding: 0.85rem 1rem;
            color: #134e4a;
            line-height: 1.5;
            margin: 0.65rem 0 1rem 0;
        }
        .safe-note {
            border-left: 4px solid var(--teal);
            background: #f0fdfa;
            color: #134e4a;
            padding: 0.8rem 0.95rem;
            border-radius: 8px;
            margin: 0.55rem 0 1rem 0;
        }
        .mode-badge-row {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            align-items: center;
            margin: -0.25rem 0 0.85rem 0;
        }
        .empty-state {
            padding: 1.25rem 1.35rem;
            text-align: left;
            margin-top: 1rem;
            border-style: dashed;
        }
        .empty-state h3 {
            margin: 0 0 0.45rem 0;
            font-size: 1.1rem;
        }
        .empty-state p, .empty-state li {
            color: var(--slate);
            font-size: 0.92rem;
            line-height: 1.45;
        }
        .sidebar-brand {
            padding: 0.7rem 0 0.4rem 0;
            border-bottom: 1px solid var(--line);
            margin-bottom: 0.75rem;
        }
        .sidebar-brand-title {
            color: var(--navy);
            font-size: 1rem;
            font-weight: 820;
            line-height: 1.25;
        }
        .sidebar-brand-note {
            color: var(--slate);
            font-size: 0.78rem;
            line-height: 1.35;
            margin-top: 0.35rem;
        }
        .sidebar-row {
            display: flex;
            justify-content: space-between;
            gap: 0.5rem;
            align-items: center;
            margin: 0.3rem 0;
            color: var(--slate);
            font-size: 0.8rem;
        }
        .sidebar-file {
            color: var(--navy);
            font-size: 0.78rem;
            line-height: 1.3;
            word-break: break-word;
            margin: 0.2rem 0 0.5rem 0;
        }
        .table-card {
            padding: 0.85rem 0.95rem 0.95rem 0.95rem;
            margin: 0.75rem 0 1rem 0;
        }
        .table-title {
            color: var(--navy);
            font-size: 1rem;
            font-weight: 780;
            margin-bottom: 0.2rem;
        }
        .table-caption {
            color: var(--muted);
            font-size: 0.85rem;
            margin-bottom: 0.65rem;
        }
        .footer {
            color: #64748b;
            font-size: 0.82rem;
            padding: 1.2rem 0 0.3rem 0;
            margin-top: 1rem;
            border-top: 1px solid var(--line);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def status_badge(label: str, status: str = "ready") -> str:
    status_key = status.strip().lower()
    css_class = STATUS_CLASS.get(status_key, "status-muted")
    return f'<span class="status-badge {css_class}">{escape(label)}</span>'


def render_page_header(title: str, purpose: str) -> None:
    st.markdown(
        f"""
        <div class="page-title">
            <h1>{escape(title)}</h1>
            <p>{escape(purpose)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_mode_badge(result: Mapping[str, object]) -> None:
    dataset = str(result.get("dataset_label") or dataset_label(result.get("dataset_period")))
    st.markdown(
        f"""
        <div class="mode-badge-row">
            {status_badge(f"Dataset: {dataset}", "ready")}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_insight_box(text: str, title: str = "Insight Summary") -> None:
    st.markdown(
        f"""
        <div class="insight-box">
            <strong>{escape(title)}:</strong> {escape(text)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        """
        <div class="footer">
        Built as a privacy-safe local analytics dashboard for Shivam Enterprise marketplace reporting.
        Raw files and private identifiers are excluded from public outputs.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_value_card(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="value-card">
            <div class="value-card-title">{escape(title)}</div>
            <div class="value-card-body">{escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workflow_strip(steps: list[str]) -> None:
    chunks: list[str] = []
    for index, step in enumerate(steps):
        chunks.append(f'<span class="workflow-step">{escape(step)}</span>')
        if index < len(steps) - 1:
            chunks.append('<span class="workflow-arrow">&rarr;</span>')
    st.markdown(f'<div class="workflow-strip">{"".join(chunks)}</div>', unsafe_allow_html=True)


def render_empty_state() -> None:
    st.markdown(
        """
        <div class="empty-state">
            <h3>Waiting for files</h3>
            <p>Upload both required files from the sidebar to run the full analysis.</p>
            <p>□ Product / Cost / Channel Master Excel<br>□ Marketplace Transaction CSV</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_status(
    *,
    product_upload: object | None = None,
    transaction_upload: object | None = None,
    result: Mapping[str, object] | None = None,
    analysis_mode: str | None = None,
) -> None:
    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">Shivam Multi-Marketplace Analytics</div>
            <div class="sidebar-brand-note">Privacy-safe marketplace BI dashboard</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    product_name = getattr(product_upload, "name", None)
    transaction_name = getattr(transaction_upload, "name", None)
    if result:
        mode_text = str(result.get("mode", analysis_mode or "Upload Analysis"))
        is_demo = "demo" in mode_text.lower() or "sample" in mode_text.lower()
        mode_label = result.get("mode_badge") or ("Sample Demo" if is_demo else "Upload Mode")
        mode_label = str(mode_label).replace("SAMPLE DEMO:", "Sample Demo:").replace("CUSTOM UPLOAD ANALYSIS", "Upload Analysis")
        mode_badge = status_badge(str(mode_label), "demo mode" if is_demo else "upload mode")
        product_metrics = result.get("product_metrics", {})
        transaction_metrics = result.get("transaction_metrics", {})
        join_metrics = result.get("join_metrics", {})
        validation = result.get("validation_summary")
        validation_failed = bool(getattr(validation, "empty", True) is False and (validation["check_status"] == "FAIL").any())
        validation_warn = bool(getattr(validation, "empty", True) is False and (validation["check_status"] == "WARN").any())
        validation_status = "Failed" if validation_failed else "Warning" if validation_warn else "Passed"

        st.sidebar.markdown("### Data Status")
        st.sidebar.markdown(mode_badge, unsafe_allow_html=True)
        st.sidebar.markdown(status_badge("READY", "ready"), unsafe_allow_html=True)
        st.sidebar.markdown(
            f"""
            <div class="sidebar-row"><span>Product rows</span><strong>{int(product_metrics.get("product_master_row_count", 0)):,}</strong></div>
            <div class="sidebar-row"><span>Transaction rows</span><strong>{int(transaction_metrics.get("transaction_row_count", 0)):,}</strong></div>
            <div class="sidebar-row"><span>SKU join coverage</span><strong>{float(join_metrics.get("join_coverage_pct", 0)):.1f}%</strong></div>
            """,
            unsafe_allow_html=True,
        )
        st.sidebar.markdown("### Validation Status")
        st.sidebar.markdown(
            status_badge(validation_status.upper(), "failed" if validation_failed else "warning" if validation_warn else "passed"),
            unsafe_allow_html=True,
        )
        st.sidebar.markdown("### Export Outputs")
        st.sidebar.markdown(status_badge("READY", "ready"), unsafe_allow_html=True)
        st.sidebar.caption("Navigation: open each dashboard page from the page list above.")
        return

    product_ready = bool(product_name)
    transaction_ready = bool(transaction_name)
    st.sidebar.markdown("### Data Status")
    st.sidebar.markdown(status_badge("UPLOAD MODE", "upload mode"), unsafe_allow_html=True)
    st.sidebar.markdown(status_badge("READY" if product_ready and transaction_ready else "MISSING", "ready" if product_ready and transaction_ready else "not uploaded"), unsafe_allow_html=True)
    st.sidebar.markdown(
        f"""
        <div class="sidebar-row"><span>Product master</span><strong>{'READY' if product_ready else 'MISSING'}</strong></div>
        <div class="sidebar-file">{escape(product_name or 'No file uploaded')}</div>
        <div class="sidebar-row"><span>Transaction report</span><strong>{'READY' if transaction_ready else 'MISSING'}</strong></div>
        <div class="sidebar-file">{escape(transaction_name or 'No file uploaded')}</div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("### Validation Status")
    st.sidebar.markdown(status_badge("MISSING", "not uploaded"), unsafe_allow_html=True)
    st.sidebar.markdown("### Export Outputs")
    st.sidebar.markdown(status_badge("MISSING", "not uploaded"), unsafe_allow_html=True)
    st.sidebar.caption("Upload both files, then click Run Full Analysis.")
