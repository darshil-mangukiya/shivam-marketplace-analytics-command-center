from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOTS = ROOT / "app" / "screenshots"

EXPECTED = [
    "01_executive_overview.png",
    "02_marketplace_performance.png",
    "03_product_intelligence_filters.png",
    "04_fees_refunds_revenue_quality.png",
    "05_profitability_margin_intelligence.png",
    "06_inventory_restock_actions.png",
    "07_performance_drivers_root_cause.png",
    "09_upload_workflow.png",
]

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_expected_screenshots_exist():
    for name in EXPECTED:
        assert (SCREENSHOTS / name).exists(), f"Missing screenshot: {name}"


def test_png_extension_matches_signature():
    for name in EXPECTED:
        head = (SCREENSHOTS / name).read_bytes()[:8]
        assert head == PNG_SIGNATURE, f"{name} has a .png extension but is not a real PNG"


def test_screenshot_readme_references_actual_files():
    readme = (SCREENSHOTS / "README.md").read_text(encoding="utf-8")
    for name in EXPECTED:
        assert name in readme, f"screenshots/README.md does not reference {name}"


def test_no_stale_screenshot_names_remain_tracked():
    stale_names = {
        "00_landing_upload_workflow.png",
        "02_marketplace_channel_performance.png",
        "03_product_brand_category_intelligence.png",
        "06_inventory_restock_action_review.png",
        "07_data_validation_privacy_checks.png",
        "08_demo_export_center.png",
    }
    present = {p.name for p in SCREENSHOTS.glob("*.png")}
    assert present.isdisjoint(stale_names), f"Stale screenshot files still present: {present & stale_names}"
