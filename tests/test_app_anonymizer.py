from pathlib import Path

from app.utils.anonymizer import SENSITIVE_COLUMNS, build_public_dashboard
from app.utils.joiner import join_transactions_to_product_master
from app.utils.product_master_cleaner import clean_product_master_file
from app.utils.transaction_cleaner import clean_transaction_file
from tests.test_app_data_loader import make_product_file, make_transaction_file


def test_public_output_excludes_sensitive_columns(tmp_path: Path):
    products, product_metrics = clean_product_master_file(make_product_file(tmp_path))
    transactions, _ = clean_transaction_file(make_transaction_file(tmp_path))
    private_master, _ = join_transactions_to_product_master(transactions, products, product_metrics)
    public = build_public_dashboard(private_master)
    assert not (set(public.columns) & SENSITIVE_COLUMNS)
    assert "public_product_id" in public.columns
    assert "seller_sku" not in public.columns
    assert "order_id" not in public.columns


def test_financial_raw_amount_columns_are_removed(tmp_path: Path):
    products, product_metrics = clean_product_master_file(make_product_file(tmp_path))
    transactions, _ = clean_transaction_file(make_transaction_file(tmp_path))
    private_master, _ = join_transactions_to_product_master(transactions, products, product_metrics)
    public = build_public_dashboard(private_master)
    raw_amount_cols = {
        "gross_sales_private",
        "refund_amount_private",
        "promotion_amount_private",
        "amazon_fee_private",
        "net_amount_private",
        "product_sales",
        "total",
    }
    assert not (set(public.columns) & raw_amount_cols)
