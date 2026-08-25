from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def outputs_to_zip_bytes(outputs: dict[str, pd.DataFrame]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, df in outputs.items():
            archive.writestr(f"{name}.csv", df.to_csv(index=False))
    return buffer.getvalue()
