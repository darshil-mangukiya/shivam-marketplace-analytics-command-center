"""Local operational-workflow layer (BR-23, BR-24, BR-25).

This module turns a high-priority recommendation
(already produced by `shared/recommendations.py` and surfaced on
`product_action_review.csv` / `inventory_action_review.csv`) into a
trackable exception with an explicit status lifecycle, and records every
status change to a local, append-only audit log.

Privacy: an exception record carries only already-public, already
privacy-scanned fields (`public_product_id`, `marketplace`,
`recommended_action`, `action_priority`, `action_reason`, `source_output`)
-- never a raw SKU/ASIN/order ID or any value that has not already passed
`shared/privacy.py`'s content scan as part of the outputs it was built
from.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

EXCEPTION_QUEUE_PATH = Path(__file__).resolve().parents[1] / "artifacts" / "workflow" / "exception_queue.json"
ACTION_LOG_PATH = Path(__file__).resolve().parents[1] / "artifacts" / "workflow" / "action_log.csv"

ACTION_LOG_COLUMNS = [
    "action_id",
    "exception_id",
    "previous_status",
    "new_status",
    "reviewer_persona",
    "reason",
    "timestamp",
]

STATUSES = (
    "New",
    "Under Review",
    "Analysis Required",
    "Approved",
    "Rejected",
    "Actioned Externally",
    "Closed",
)

# Allowed forward transitions. A terminal status ("Closed") has no outgoing
# transitions. This is intentionally conservative -- BR-25 requires an
# invalid/out-of-sequence transition to be rejected, not silently applied.
VALID_TRANSITIONS: dict[str, set[str]] = {
    "New": {"Under Review", "Analysis Required", "Rejected"},
    "Under Review": {"Analysis Required", "Approved", "Rejected"},
    "Analysis Required": {"Under Review", "Approved", "Rejected"},
    "Approved": {"Actioned Externally", "Closed"},
    "Rejected": {"Closed"},
    "Actioned Externally": {"Closed"},
    "Closed": set(),
}

# Recommendations at these priorities become trackable exceptions. "Low"
# priority and "Monitor" (no action threshold triggered) are intentionally
# excluded -- the workflow layer is for genuine exceptions, not every row.
TRACKED_PRIORITIES = {"High", "Medium"}

SOURCE_OUTPUTS = ("product_action_review", "inventory_action_review")


class WorkflowError(Exception):
    """Raised for an invalid workflow operation: unknown exception_id, or a
    status transition that is not in VALID_TRANSITIONS. Never silently
    applied -- callers must handle this explicitly (BR-25)."""


def _now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat(timespec="seconds")


def _exception_id(source_output: str, row_index: int, public_product_id: str, marketplace: str) -> str:
    # Deterministic, not a UUID -- reproducible across runs of the same
    # input, consistent with this project's surrogate-key philosophy
    # (see shared/sqlserver_star_schema.py).
    prefix = "PAR" if source_output == "product_action_review" else "IAR"
    return f"{prefix}-{public_product_id}-{marketplace}".replace(" ", "_")


def build_exception_queue(outputs: Mapping[str, pd.DataFrame]) -> list[dict[str, Any]]:
    """Build a fresh exception queue from the current action-review public
    outputs. Deterministic: the same outputs always produce the same
    exception_id set with status "New" for any exception not already
    present in an existing queue (existing statuses are preserved by
    `refresh_exception_queue`, not this function -- this is the pure
    build step)."""
    records: list[dict[str, Any]] = []
    for source_output in SOURCE_OUTPUTS:
        frame = outputs.get(source_output)
        if frame is None or frame.empty:
            continue
        required_cols = {"public_product_id", "marketplace", "recommended_action", "action_priority"}
        if not required_cols.issubset(frame.columns):
            continue
        flagged = frame[frame["action_priority"].isin(TRACKED_PRIORITIES)]
        for idx, row in flagged.iterrows():
            public_product_id = str(row["public_product_id"])
            marketplace = str(row["marketplace"])
            exception_id = _exception_id(source_output, int(idx), public_product_id, marketplace)
            records.append(
                {
                    "exception_id": exception_id,
                    "source_output": source_output,
                    "public_product_id": public_product_id,
                    "marketplace": marketplace,
                    "recommended_action": str(row["recommended_action"]),
                    "action_priority": str(row["action_priority"]),
                    "action_reason": str(row.get("action_reason", "")),
                    "status": "New",
                    "created_at": _now_iso(),
                    "updated_at": _now_iso(),
                }
            )
    # De-duplicate: the same product can appear in both action-review
    # outputs; keep the first (product_action_review is checked first).
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for record in records:
        if record["exception_id"] in seen:
            continue
        seen.add(record["exception_id"])
        deduped.append(record)
    return deduped


def refresh_exception_queue(
    outputs: Mapping[str, pd.DataFrame], existing_queue: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Rebuild the exception queue from current outputs, preserving the
    status/timestamps of any exception that already exists in
    `existing_queue` (so re-running the workflow build never resets a
    reviewer's progress) and adding any newly-flagged exception as "New"."""
    fresh = build_exception_queue(outputs)
    existing_by_id = {record["exception_id"]: record for record in (existing_queue or [])}
    merged: list[dict[str, Any]] = []
    for record in fresh:
        prior = existing_by_id.get(record["exception_id"])
        if prior is not None:
            merged_record = dict(record)
            merged_record["status"] = prior.get("status", "New")
            merged_record["created_at"] = prior.get("created_at", record["created_at"])
            merged_record["updated_at"] = prior.get("updated_at", record["updated_at"])
            merged.append(merged_record)
        else:
            merged.append(record)
    return merged


def transition_exception(
    queue: list[dict[str, Any]],
    exception_id: str,
    new_status: str,
    reviewer_persona: str,
    reason: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply a status transition to one exception in `queue`. Returns
    (updated_queue, action_log_row). Raises WorkflowError -- and leaves
    `queue` conceptually unusable by the caller until they discard the
    attempt -- if the exception_id is unknown or the transition is not
    allowed from the exception's current status."""
    if new_status not in STATUSES:
        raise WorkflowError(f"'{new_status}' is not a recognized workflow status.")

    match = None
    match_index = None
    for i, record in enumerate(queue):
        if record["exception_id"] == exception_id:
            match = record
            match_index = i
            break
    if match is None:
        raise WorkflowError(f"No exception found with id '{exception_id}'.")

    previous_status = match["status"]
    allowed = VALID_TRANSITIONS.get(previous_status, set())
    if new_status not in allowed:
        raise WorkflowError(
            f"Invalid transition for '{exception_id}': '{previous_status}' -> '{new_status}' "
            f"is not allowed. Allowed next status(es) from '{previous_status}': "
            f"{sorted(allowed) or 'none (terminal status)'}."
        )

    updated = dict(match)
    updated["status"] = new_status
    updated["updated_at"] = _now_iso()
    updated_queue = list(queue)
    updated_queue[match_index] = updated

    log_row = {
        "action_id": f"ACT-{exception_id}-{previous_status}-{new_status}-"
        f"{_dt.datetime.now(tz=_dt.timezone.utc).strftime('%Y%m%dT%H%M%S%f')}".replace(" ", "_"),
        "exception_id": exception_id,
        "previous_status": previous_status,
        "new_status": new_status,
        "reviewer_persona": reviewer_persona,
        "reason": reason,
        "timestamp": _now_iso(),
    }
    return updated_queue, log_row


def summarize_workflow(queue: list[dict[str, Any]]) -> dict[str, int]:
    """Safe aggregate counts by status -- no exception detail, suitable for
    display on a dashboard page."""
    summary = {status: 0 for status in STATUSES}
    for record in queue:
        status = record.get("status", "New")
        summary[status] = summary.get(status, 0) + 1
    summary["total"] = len(queue)
    return summary


def save_exception_queue(queue: list[dict[str, Any]], path: Path = EXCEPTION_QUEUE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(queue, indent=2, sort_keys=False), encoding="utf-8")


def load_exception_queue(path: Path = EXCEPTION_QUEUE_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def append_action_log(log_row: dict[str, Any], path: Path = ACTION_LOG_PATH) -> None:
    """Append one row to the action log. Logically append-only: existing
    rows are never edited or removed. Implemented as read-existing +
    write-whole-file (rather than an OS-level file-append) so this works
    identically under restricted-filesystem sandboxes that disallow
    opening an existing file in append mode."""
    path.parent.mkdir(parents=True, exist_ok=True)
    new_row_df = pd.DataFrame([log_row], columns=ACTION_LOG_COLUMNS)
    if path.exists():
        existing = pd.read_csv(path)
        combined = pd.concat([existing, new_row_df], ignore_index=True)
    else:
        combined = new_row_df
    combined.to_csv(path, mode="w", header=True, index=False)


def load_action_log(path: Path = ACTION_LOG_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=ACTION_LOG_COLUMNS)
    return pd.read_csv(path)
