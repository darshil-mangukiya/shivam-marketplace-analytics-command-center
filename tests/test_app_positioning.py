from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
STYLE_SOURCE = (ROOT / "app" / "components" / "style.py").read_text(encoding="utf-8")


def test_upload_mode_is_default():
    assert 'ANALYSIS_MODES = ["Upload 2 Files", "Sample Demo"]' in APP_SOURCE
    assert "index=0" in APP_SOURCE
    assert "Upload a product master and transaction report to automatically generate privacy-safe marketplace analytics" in APP_SOURCE


def test_run_full_analysis_is_main_landing_cta():
    assert '"Run Full Analysis"' in APP_SOURCE
    assert "main_run_full_analysis" in APP_SOURCE
    assert "disabled=not all_files_ready" in APP_SOURCE
    assert "Upload both required files to run the full analysis." in APP_SOURCE


def test_demo_button_is_not_in_main_content_when_upload_mode_is_active():
    assert "Load Sample Demo Dashboard" not in APP_SOURCE
    assert "Launch Sample Demo Dashboard" in APP_SOURCE
    assert "sidebar_launch_sample" in APP_SOURCE
    assert "main_load_sample" not in APP_SOURCE


def test_sample_demo_success_message_is_only_for_demo_loader():
    message = "Sample public dashboard loaded. Dashboard pages are ready."
    assert message in APP_SOURCE
    message_index = APP_SOURCE.index(message)
    launch_fn_index = APP_SOURCE.index("def launch_sample_dashboard")
    upload_run_index = APP_SOURCE.index('if analysis_mode == "Upload 2 Files" and (run_clicked or main_run_clicked):')
    assert launch_fn_index < message_index < upload_run_index


def test_landing_page_clearly_references_two_file_upload_workflow():
    assert "PROJECT_TITLE" in APP_SOURCE
    assert "Product / Cost / Marketplace Master" in APP_SOURCE
    assert "Marketplace Transaction Report" in APP_SOURCE
    assert "Status: {status}" in APP_SOURCE
    assert "What happens after upload?" in APP_SOURCE
    assert 'render_workflow_strip(["Upload", "Clean", "Join", "Anonymize", "Validate", "Analyze", "Export"])' in APP_SOURCE
    assert "Waiting for files" in STYLE_SOURCE
    assert "Upload both required files from the sidebar to run the full analysis." in STYLE_SOURCE


def test_sidebar_contains_demo_mode_option():
    assert "st.sidebar.radio" in APP_SOURCE
    assert '"Sample Demo"' in APP_SOURCE
    assert "Launch Sample Demo Dashboard" in APP_SOURCE
    assert "Select Sample Demo in the sidebar." in APP_SOURCE


def test_landing_page_does_not_make_generated_files_look_mandatory():
    hardcoded_samples = [
        "Shivam_Transactions_1_Month_10K_Orders.csv",
        "Shivam_Transactions_3_Months_30K_Orders.csv",
        "Shivam_Transactions_6_Months_60K_Orders.csv",
        "Shivam_Transactions_12_Months_120K_Orders.csv",
    ]
    assert all(sample not in APP_SOURCE for sample in hardcoded_samples)
    assert "Business Context" not in APP_SOURCE
    assert "Required Uploads" not in APP_SOURCE
    assert "Analytics Workflow" not in APP_SOURCE
    assert "Upload Workflow" not in APP_SOURCE


def test_supported_transaction_dataset_labels_are_samples():
    assert "Sample: 1 Month / 10K Orders" in APP_SOURCE
    assert "Sample: 3 Months / 30K Orders" in APP_SOURCE
    assert "Sample: 6 Months / 60K Orders" in APP_SOURCE
    assert "Sample: 12 Months / 120K Orders" in APP_SOURCE
