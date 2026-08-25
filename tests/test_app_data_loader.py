from pathlib import Path

import pandas as pd

from app.utils.data_loader import _known_private_values, run_analysis_from_uploads
from app.utils.product_master_cleaner import clean_product_master_file
from app.utils.transaction_cleaner import clean_transaction_file


class UploadStub:
    def __init__(self, path: Path):
        self.name = path.name
        self._bytes = path.read_bytes()

    def getvalue(self) -> bytes:
        return self._bytes


def make_product_file(tmp_path: Path) -> Path:
    path = tmp_path / "product_master.xlsx"
    df = pd.DataFrame(
        [
            {
                "seller-sku": "SKU-1",
                "asin1": "BPRIVATE1",
                "item-name": "Private Product One",
                "item-description": "Do not publish",
                "listing-id": "LIST-1",
                "price": "999",
                "quantity": "60",
                "brand": "Brand A",
                "category": "Skin Care",
                "subcategory": "Sunscreen",
                "product_group": "Sunscreen",
                "public_product_id": "P0001",
                "listing_price_band": "500-999",
                "inventory_band": "Very High / 100+",
                "mapping_status": "Mapped",
            },
            {
                "seller-sku": "SKU-2",
                "asin1": "BPRIVATE2",
                "item-name": "Private Product Two",
                "item-description": "Do not publish",
                "listing-id": "LIST-2",
                "price": "1999",
                "quantity": "2",
                "brand": "Brand B",
                "category": "Hair Care",
                "subcategory": "Shampoo",
                "product_group": "Shampoo",
                "public_product_id": "P0002",
                "listing_price_band": "1500-1999",
                "inventory_band": "Very Low / 1-5",
                "mapping_status": "Mapped",
            },
        ]
    )
    df.to_excel(path, index=False, sheet_name="Enriched_Listings")
    return path


def make_transaction_file(tmp_path: Path) -> Path:
    path = tmp_path / "transactions.csv"
    path.write_text(
        "\n".join(
            [
                '"Includes Amazon Marketplace, Fulfillment by Amazon (FBA), and Amazon Webstore transactions"',
                '"All amounts in INR, unless specified"',
                '"date/time","settlement id","type","order id","Sku","description","quantity","marketplace","fulfillment","order city","order state","order postal","product sales","shipping credits","gift wrap credits","promotional rebates","selling fees","fba fees","other transaction fees","other","total"',
                '"1 May 2026 10:00:00 am UTC","1","Order","ORDER-1","SKU-1","Private Product One","2","amazon.in","Amazon","Mumbai","MAHARASHTRA","400001","1000","0","0","-50","-100","-80","-20","0","750"',
                '"1 May 2026 11:00:00 am UTC","1","Refund","ORDER-2","SKU-2","Private Product Two","1","amazon.in","Amazon","Pune","MAHARASHTRA","411001","-300","0","0","0","0","0","0","0","-300"',
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_product_master_loads(tmp_path):
    df, metrics = clean_product_master_file(make_product_file(tmp_path))
    assert len(df) == 2
    assert metrics["product_master_row_count"] == 2
    assert "seller_sku" in df.columns


def test_transaction_file_loads(tmp_path):
    df, metrics = clean_transaction_file(make_transaction_file(tmp_path))
    assert len(df) == 2
    assert metrics["transaction_row_count"] == 2
    assert {"sku", "gross_sales_private", "refund_amount_private"} <= set(df.columns)


def test_uploaded_analysis_runs(tmp_path):
    result = run_analysis_from_uploads(UploadStub(make_product_file(tmp_path)), UploadStub(make_transaction_file(tmp_path)))
    assert "outputs" in result
    assert result["join_metrics"]["matched_skus"] == 2
    assert not result["outputs"]["product_performance"].empty


def test_known_private_values_exclude_generic_transaction_labels_and_counts():
    products = pd.DataFrame(
        {
            "seller_sku": ["SKU-12345"],
            "asin1": ["B0ABCDEF12"],
            "item_name": ["Private Long Product Name Should Not Publish"],
            "item_description": ["Short"],
            "product_id": ["12"],
        }
    )
    transactions = pd.DataFrame(
        {
            "sku": ["SKU-12345"],
            "order_id": ["ORDER-12345"],
            "description": ["Transfer"],
            "order_postal": ["141000"],
        }
    )

    known = set(_known_private_values(products, transactions))

    assert "SKU-12345" in known
    assert "ORDER-12345" in known
    assert "B0ABCDEF12" in known
    assert "Private Long Product Name Should Not Publish" in known
    assert "Transfer" not in known
    assert "12" not in known
