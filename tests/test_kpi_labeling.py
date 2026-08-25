from __future__ import annotations

from pathlib import Path

from app.utils.metrics import compute_kpis


ROOT = Path(__file__).resolve().parents[1]
OLD_PRODUCT_LABEL = "Public " + "Product Groups"
OLD_PRIORITY_LABEL = "High Priority Action " + "Count"


def _read_sources(paths: list[Path]) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in paths if path.exists())


def test_compute_kpis_uses_clear_portfolio_labels():
    kpis = compute_kpis({}, {"product_master_row_count": 1264, "transaction_row_count": 141000})

    assert "Products in Analysis" in kpis
    assert "High Priority Actions" in kpis
    assert OLD_PRODUCT_LABEL not in kpis
    assert OLD_PRIORITY_LABEL not in kpis


def test_user_facing_app_sources_do_not_use_old_product_group_label():
    app_sources = list((ROOT / "app").rglob("*.py"))
    combined = _read_sources(app_sources)

    assert OLD_PRODUCT_LABEL not in combined
    assert OLD_PRIORITY_LABEL not in combined
