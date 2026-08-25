from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
STYLE_SOURCE = (ROOT / "app" / "components" / "style.py").read_text(encoding="utf-8")
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
SETUP_SCRIPT = ROOT / "python" / "setup_private_files.py"


def load_setup_module():
    spec = importlib.util.spec_from_file_location("setup_private_files", SETUP_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_landing_page_contains_upload_first_message_and_cards():
    assert "Upload a product master and transaction report to automatically generate privacy-safe marketplace analytics" in APP_SOURCE
    assert "Product / Cost / Marketplace Master" in APP_SOURCE
    assert "Marketplace Transaction Report" in APP_SOURCE
    assert "Privacy-Safe" in APP_SOURCE
    assert "5-Marketplace Ready" in APP_SOURCE


def test_landing_page_removes_long_manual_sections():
    removed_sections = [
        "Business Context",
        "Required Uploads",
        "Analytics Workflow",
        "Upload Workflow",
        "**Upload Reports:**",
        "**Clean & Join:**",
    ]
    assert all(section not in APP_SOURCE for section in removed_sections)


def test_demo_loader_is_sidebar_only_and_upload_mode_default():
    assert 'ANALYSIS_MODES = ["Upload 2 Files", "Sample Demo"]' in APP_SOURCE
    assert "index=0" in APP_SOURCE
    assert "with st.sidebar.expander(\"Sample Demo\"" in APP_SOURCE
    assert "Launch Sample Demo Dashboard" in APP_SOURCE
    assert "main_load_sample" not in APP_SOURCE
    assert "Load Sample Demo Dashboard" not in APP_SOURCE


def test_empty_state_and_visual_css_are_present():
    assert "Waiting for files" in STYLE_SOURCE
    assert "Upload both required files from the sidebar to run the full analysis." in STYLE_SOURCE
    assert ".hero-action-card" in STYLE_SOURCE
    assert ".upload-card" in STYLE_SOURCE
    assert ".workflow-step" in STYLE_SOURCE


def test_setup_private_files_script_and_makefile_target_exist():
    assert SETUP_SCRIPT.exists()
    assert "setup-files:" in MAKEFILE
    assert "\tpython python/setup_private_files.py" in MAKEFILE


def test_setup_private_files_copies_only_expected_newer_files(tmp_path: Path):
    setup_private_files = load_setup_module()
    source_dir = tmp_path / "source"
    destination_dir = tmp_path / "destination"
    source_dir.mkdir()
    destination_dir.mkdir()

    expected_file = "Shivam_Transactions_1_Month_10K_Orders.csv"
    screenshot = "landing_page.png"
    (source_dir / expected_file).write_text("new transaction data", encoding="utf-8")
    (source_dir / screenshot).write_text("not copied", encoding="utf-8")

    summary = setup_private_files.copy_private_files(source_dir, destination_dir)

    assert expected_file in summary["copied"]
    assert (destination_dir / expected_file).read_text(encoding="utf-8") == "new transaction data"
    assert not (destination_dir / screenshot).exists()
    assert "Shivam_Transactions_12_Months_120K_Orders.csv" in summary["missing"]
