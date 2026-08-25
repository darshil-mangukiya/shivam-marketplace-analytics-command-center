from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "data" / "public"


def public_csvs():
    return sorted(path for path in PUBLIC.glob("*.csv") if path.name != "validation_summary.csv")


def test_public_files_do_not_expose_sensitive_columns():
    banned = {
        "asin",
        "asin1",
        "seller_sku",
        "sku",
        "order_id",
        "listing_id",
        "product_id",
        "item_name",
        "item_description",
        "description",
        "order_postal",
        "product_sales",
        "selling_fees",
        "fba_fees",
        "other_transaction_fees",
        "gross_sales_private",
        "refund_amount_private",
        "promotion_amount_private",
        "amazon_fee_private",
        "net_amount_private",
        "total",
    }
    assert public_csvs(), "Run python python/run_pipeline.py before tests."
    for path in public_csvs():
        columns = set(pd.read_csv(path, nrows=1).columns)
        assert not columns & banned, f"{path.name} exposes sensitive columns: {columns & banned}"


def test_public_master_uses_public_ids_only():
    master = pd.read_csv(PUBLIC / "anonymized_master.csv")
    assert "public_product_id" in master.columns
    assert "sku" not in master.columns
    assert "order_id" not in master.columns
    assert master["public_product_id"].notna().all()
