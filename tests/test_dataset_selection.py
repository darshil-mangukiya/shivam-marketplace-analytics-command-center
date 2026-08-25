from pathlib import Path

from run_pipeline import resolve_transaction_source


def test_custom_dataset_selection_uses_supplied_path(tmp_path: Path):
    path = tmp_path / "transactions.csv"
    path.write_text("date/time,Sku,total\n", encoding="utf-8")
    selected, label = resolve_transaction_source("custom", str(path))
    assert selected == path
    assert label == "custom"
