from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PYTHON_DIR = ROOT / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from pipeline_utils import (  # noqa: E402
    clean_text_columns,
    clean_text_series,
    normalize_column_name,
    normalize_columns,
    parse_datetime_series,
    parse_numeric_series,
    remove_blank_rows,
)


class AppDataError(ValueError):
    """Friendly exception for upload and data-shape problems."""


def require_columns(columns: set[str], required: set[str], label: str) -> None:
    missing = sorted(required - columns)
    if missing:
        raise AppDataError(
            f"The uploaded {label} file is missing required column(s): {', '.join(missing)}. "
            "Please check the file and upload again."
        )
