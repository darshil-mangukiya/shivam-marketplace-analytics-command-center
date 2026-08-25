import json

import pandas as pd

from shared.privacy import content_privacy_scan


def _frame_with_late_leak(leaked_value: str, n: int = 6000, leak_row: int = 5500) -> pd.DataFrame:
    values = ["SafeGroup"] * n
    values[leak_row] = leaked_value
    return pd.DataFrame({"public_product_id": values})


def test_default_scan_detects_value_after_row_5000():
    df = _frame_with_late_leak("B0ABCDEF12")  # ASIN-like, well past row 5000
    scan = content_privacy_scan(df)
    assert scan["asin_like_values"] >= 1
    assert scan["is_safe"] is False


def test_scan_reports_counts_without_exposing_value():
    leaked = "B0ABCDEF12"
    df = _frame_with_late_leak(leaked)
    scan = content_privacy_scan(df)
    # Only counts are returned; the actual leaked value must never appear.
    assert leaked not in json.dumps(scan, default=str)


def test_optional_cap_is_opt_in_and_default_is_full_frame():
    df = _frame_with_late_leak("B0ABCDEF12")
    # An explicit developer cap below the leak row misses it...
    capped = content_privacy_scan(df, max_rows=5000)
    assert capped["asin_like_values"] == 0
    # ...but the default (max_rows=None) scans the whole frame and catches it.
    full = content_privacy_scan(df)
    assert full["asin_like_values"] >= 1


def test_order_id_pattern_still_detected_full_frame():
    df = pd.DataFrame({"notes": ["ok"] * 5999 + ["ORDER-99887766"]})
    scan = content_privacy_scan(df)
    assert scan["order_id_like_values"] >= 1
    assert scan["is_safe"] is False
