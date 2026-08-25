from __future__ import annotations

import pandas as pd

from shared.privacy import SENSITIVE_COLUMNS, content_privacy_scan, unsafe_columns
from shared.public_output_builder import PUBLIC_DASHBOARD_COLUMNS, build_public_dashboard as _build_public_dashboard


def build_public_dashboard(private_master: pd.DataFrame) -> pd.DataFrame:
    return _build_public_dashboard(private_master)


def assert_public_frame_is_safe(df: pd.DataFrame, known_private_values: list[object] | None = None) -> None:
    unsafe = unsafe_columns(df.columns)
    if unsafe:
        raise ValueError(f"Public dataframe contains sensitive column(s): {', '.join(unsafe)}")
    content_scan = content_privacy_scan(df, known_private_values=known_private_values)
    if not content_scan["is_safe"]:
        raise ValueError(
            "Public dataframe contains sensitive-looking values. "
            f"Content hit count: {content_scan['total_content_hits']}"
        )
