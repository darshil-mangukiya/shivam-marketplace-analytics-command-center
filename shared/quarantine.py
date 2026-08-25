"""Rejected-row quarantine framework.

Wraps the row-level rejection records produced by `shared/contracts.py` into
a summarized quarantine report and enforces the safety guarantee that no
quarantine record ever carries a private cell value — only the safe
metadata columns defined in `shared.contracts.REJECTED_ROW_COLUMNS`.

Quarantine records live in memory for the request/session and are summarized
for display.
"""

from __future__ import annotations

import pandas as pd

from shared.contracts import REJECTED_ROW_COLUMNS

SAFE_METADATA_COLUMNS = set(REJECTED_ROW_COLUMNS)


def assert_quarantine_is_safe(rejected_df: pd.DataFrame) -> None:
    """Defense-in-depth guard: raise if a quarantine frame ever grows a
    column beyond the documented safe-metadata schema. This catches an
    accidental future change that starts smuggling raw cell values into the
    quarantine ledger before it ever reaches a user-facing surface."""
    extra_columns = set(rejected_df.columns) - SAFE_METADATA_COLUMNS
    if extra_columns:
        raise ValueError(
            f"Quarantine frame contains non-whitelisted columns: {sorted(extra_columns)}. "
            "Quarantine records must only ever carry safe metadata "
            f"({sorted(SAFE_METADATA_COLUMNS)})."
        )


def combine_quarantine(*frames: pd.DataFrame) -> pd.DataFrame:
    """Concatenate one or more rejected/warning-record frames into a single
    quarantine ledger, validating safety on the way in."""
    cleaned = []
    for frame in frames:
        if frame is None or frame.empty:
            continue
        assert_quarantine_is_safe(frame)
        cleaned.append(frame)
    if not cleaned:
        return pd.DataFrame(columns=REJECTED_ROW_COLUMNS)
    return pd.concat(cleaned, ignore_index=True)


def summarize_quarantine(rejected_df: pd.DataFrame) -> pd.DataFrame:
    """One row per (error_category, error_code, severity) with a count —
    the shape shown in the Data Validation & Privacy Checks page and rolled
    into validation_summary."""
    if rejected_df.empty:
        return pd.DataFrame(columns=["error_category", "error_code", "severity", "row_count"])
    assert_quarantine_is_safe(rejected_df)
    summary = (
        rejected_df.groupby(["error_category", "error_code", "severity"], dropna=False)
        .size()
        .reset_index(name="row_count")
        .sort_values("row_count", ascending=False)
        .reset_index(drop=True)
    )
    return summary


def quarantine_totals(rejected_df: pd.DataFrame, warning_df: pd.DataFrame, total_input_rows: int, accepted_rows: int) -> dict[str, int]:
    """Return validation-page counts for input, accepted, rejected, and warning rows."""
    return {
        "total_input_rows": int(total_input_rows),
        "accepted_rows": int(accepted_rows),
        "rejected_rows": int(len(rejected_df)),
        "warning_rows": int(len(warning_df)),
    }
