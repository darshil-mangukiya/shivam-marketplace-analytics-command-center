from pathlib import Path

from app.utils.joiner import join_transactions_to_product_master
from app.utils.metrics import build_public_outputs_from_private
from app.utils.product_master_cleaner import clean_product_master_file
from app.utils.transaction_cleaner import clean_transaction_file
from app.utils.validation import build_validation_summary, scan_public_outputs
from tests.test_app_data_loader import make_product_file, make_transaction_file


def test_validation_summary_is_created(tmp_path: Path):
    products, product_metrics = clean_product_master_file(make_product_file(tmp_path))
    transactions, transaction_metrics = clean_transaction_file(make_transaction_file(tmp_path))
    private_master, join_metrics = join_transactions_to_product_master(transactions, products, product_metrics)
    outputs = build_public_outputs_from_private(private_master)
    validation = build_validation_summary(outputs, product_metrics, transaction_metrics, join_metrics)
    assert not validation.empty
    assert "Recommended actions generated" in set(validation["check_name"])
    assert validation["check_status"].isin({"PASS", "WARN", "FAIL"}).all()


def test_privacy_scan_passes(tmp_path: Path):
    products, product_metrics = clean_product_master_file(make_product_file(tmp_path))
    transactions, _ = clean_transaction_file(make_transaction_file(tmp_path))
    private_master, _ = join_transactions_to_product_master(transactions, products, product_metrics)
    outputs = build_public_outputs_from_private(private_master)
    scan = scan_public_outputs(outputs)
    assert scan["is_safe"]
