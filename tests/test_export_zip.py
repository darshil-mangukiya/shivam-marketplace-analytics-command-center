import zipfile
from io import BytesIO

import pandas as pd

from app.utils.export_utils import outputs_to_zip_bytes


def test_outputs_to_zip_bytes_contains_csvs():
    data = outputs_to_zip_bytes({"sample": pd.DataFrame({"a": [1]})})
    with zipfile.ZipFile(BytesIO(data)) as archive:
        assert "sample.csv" in archive.namelist()


def test_public_zip_names_exclude_private_paths():
    data = outputs_to_zip_bytes(
        {
            "product_performance": pd.DataFrame({"public_product_id": ["P0001"]}),
            "validation_summary": pd.DataFrame({"check_status": ["PASS"]}),
        }
    )
    with zipfile.ZipFile(BytesIO(data)) as archive:
        names = archive.namelist()
    assert all("private" not in name.lower() for name in names)
    assert all("raw" not in name.lower() for name in names)

