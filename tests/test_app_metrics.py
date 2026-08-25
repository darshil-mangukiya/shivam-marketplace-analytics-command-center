from pathlib import Path

from app.utils.joiner import join_transactions_to_product_master
from app.utils.metrics import build_public_outputs_from_private, compute_kpis
from app.utils.product_master_cleaner import clean_product_master_file
from app.utils.transaction_cleaner import clean_transaction_file
from tests.test_app_data_loader import make_product_file, make_transaction_file


def build_outputs(tmp_path: Path):
    products, product_metrics = clean_product_master_file(make_product_file(tmp_path))
    transactions, _ = clean_transaction_file(make_transaction_file(tmp_path))
    private_master, join_metrics = join_transactions_to_product_master(transactions, products, product_metrics)
    return build_public_outputs_from_private(private_master), join_metrics


def test_indexes_and_ratios_are_generated(tmp_path: Path):
    outputs, _ = build_outputs(tmp_path)
    product = outputs["product_performance"]
    assert {"sales_index", "units_index"} <= set(product.columns)
    assert {"fee_pct_of_gross", "refund_pct_of_gross", "promotion_pct_of_gross", "net_to_gross_pct"} <= set(product.columns)
    assert product["sales_index"].between(0, 100).all()
    assert product["units_index"].between(0, 100).all()


def test_recommendations_and_kpis_are_generated(tmp_path: Path):
    outputs, join_metrics = build_outputs(tmp_path)
    action = outputs["product_action_review"]
    assert "recommended_action" in action.columns
    assert action["recommended_action"].notna().all()
    kpis = compute_kpis(outputs, join_metrics)
    assert kpis["Transaction Rows"] == 2
    assert "Join Coverage %" in kpis
