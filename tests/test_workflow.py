"""Tests for the local operational-workflow layer (shared/workflow.py),
covering BR-23 (exceptions), BR-24 (audit log), BR-25 (invalid transitions
rejected)."""

from __future__ import annotations

import pandas as pd
import pytest

from shared.workflow import (
    STATUSES,
    VALID_TRANSITIONS,
    WorkflowError,
    append_action_log,
    build_exception_queue,
    load_action_log,
    load_exception_queue,
    refresh_exception_queue,
    save_exception_queue,
    summarize_workflow,
    transition_exception,
)


def _sample_outputs() -> dict[str, pd.DataFrame]:
    product_action_review = pd.DataFrame(
        {
            "public_product_id": ["P0001", "P0002", "P0003"],
            "marketplace": ["Amazon", "Flipkart", "Amazon"],
            "recommended_action": ["Restock Review", "Fee Review", "Monitor"],
            "action_priority": ["High", "Medium", "Low"],
            "action_reason": ["Low inventory, high demand", "Elevated fee %", "No action threshold triggered"],
        }
    )
    inventory_action_review = pd.DataFrame(
        {
            "public_product_id": ["P0004"],
            "marketplace": ["Meesho"],
            "recommended_action": ["Restock Review"],
            "action_priority": ["High"],
            "action_reason": ["High units index, low inventory band"],
        }
    )
    return {
        "product_action_review": product_action_review,
        "inventory_action_review": inventory_action_review,
    }


# ---------------------------------------------------------------------------
# BR-23: high-priority recommendations become trackable exceptions
# ---------------------------------------------------------------------------


def test_build_exception_queue_only_includes_tracked_priorities():
    queue = build_exception_queue(_sample_outputs())
    priorities = {record["action_priority"] for record in queue}
    assert priorities == {"High", "Medium"}
    assert len(queue) == 3  # P0001 (High), P0002 (Medium), P0004 (High) -- P0003 (Low) excluded


def test_build_exception_queue_starts_every_exception_as_new():
    queue = build_exception_queue(_sample_outputs())
    assert all(record["status"] == "New" for record in queue)


def test_exception_queue_is_privacy_safe():
    queue = build_exception_queue(_sample_outputs())
    allowed_keys = {
        "exception_id", "source_output", "public_product_id", "marketplace",
        "recommended_action", "action_priority", "action_reason", "status",
        "created_at", "updated_at",
    }
    for record in queue:
        assert set(record.keys()) <= allowed_keys
        # public_product_id must be the anonymized public ID shape, never a raw SKU/ASIN.
        assert record["public_product_id"].startswith("P")


def test_build_exception_queue_is_deterministic():
    outputs = _sample_outputs()
    queue_a = build_exception_queue(outputs)
    queue_b = build_exception_queue(outputs)
    assert queue_a == queue_b


def test_refresh_exception_queue_preserves_existing_status():
    outputs = _sample_outputs()
    initial_queue = build_exception_queue(outputs)
    exception_id = initial_queue[0]["exception_id"]
    updated_queue, _ = transition_exception(initial_queue, exception_id, "Under Review", "BI Manager", "Investigating")

    refreshed = refresh_exception_queue(outputs, updated_queue)
    refreshed_record = next(r for r in refreshed if r["exception_id"] == exception_id)
    assert refreshed_record["status"] == "Under Review"


# ---------------------------------------------------------------------------
# BR-24: every status change is recorded in an auditable log
# ---------------------------------------------------------------------------


def test_transition_exception_produces_a_complete_log_row():
    queue = build_exception_queue(_sample_outputs())
    exception_id = queue[0]["exception_id"]
    updated_queue, log_row = transition_exception(queue, exception_id, "Under Review", "Inventory Planner", "Reviewing restock signal")

    assert log_row["exception_id"] == exception_id
    assert log_row["previous_status"] == "New"
    assert log_row["new_status"] == "Under Review"
    assert log_row["reviewer_persona"] == "Inventory Planner"
    assert log_row["reason"] == "Reviewing restock signal"
    assert log_row["timestamp"]

    updated_record = next(r for r in updated_queue if r["exception_id"] == exception_id)
    assert updated_record["status"] == "Under Review"


def test_action_log_round_trips_through_csv(tmp_path):
    log_path = tmp_path / "action_log.csv"
    queue = build_exception_queue(_sample_outputs())
    exception_id = queue[0]["exception_id"]
    _, log_row = transition_exception(queue, exception_id, "Under Review", "BI Manager", "test reason")

    append_action_log(log_row, path=log_path)
    loaded = load_action_log(path=log_path)
    assert len(loaded) == 1
    assert loaded.iloc[0]["exception_id"] == exception_id
    assert loaded.iloc[0]["new_status"] == "Under Review"


def test_action_log_is_append_only(tmp_path):
    log_path = tmp_path / "action_log.csv"
    queue = build_exception_queue(_sample_outputs())
    exception_id = queue[0]["exception_id"]

    queue, log_row_1 = transition_exception(queue, exception_id, "Under Review", "BI Manager", "step 1")
    append_action_log(log_row_1, path=log_path)
    queue, log_row_2 = transition_exception(queue, exception_id, "Approved", "Operations Director", "step 2")
    append_action_log(log_row_2, path=log_path)

    loaded = load_action_log(path=log_path)
    assert len(loaded) == 2
    assert list(loaded["new_status"]) == ["Under Review", "Approved"]


# ---------------------------------------------------------------------------
# BR-25: invalid/out-of-sequence transitions are rejected, not applied
# ---------------------------------------------------------------------------


def test_invalid_transition_is_rejected():
    queue = build_exception_queue(_sample_outputs())
    exception_id = queue[0]["exception_id"]
    # New -> Closed directly is not an allowed transition.
    with pytest.raises(WorkflowError, match="not allowed"):
        transition_exception(queue, exception_id, "Closed", "BI Manager", "skip ahead")


def test_transition_from_terminal_status_is_rejected():
    queue = build_exception_queue(_sample_outputs())
    exception_id = queue[0]["exception_id"]
    queue, _ = transition_exception(queue, exception_id, "Rejected", "BI Manager", "not a real exception")
    queue, _ = transition_exception(queue, exception_id, "Closed", "BI Manager", "closing out")
    with pytest.raises(WorkflowError):
        transition_exception(queue, exception_id, "Under Review", "BI Manager", "reopen attempt")


def test_unknown_exception_id_is_rejected():
    queue = build_exception_queue(_sample_outputs())
    with pytest.raises(WorkflowError, match="No exception found"):
        transition_exception(queue, "DOES-NOT-EXIST", "Under Review", "BI Manager", "reason")


def test_unknown_status_value_is_rejected():
    queue = build_exception_queue(_sample_outputs())
    exception_id = queue[0]["exception_id"]
    with pytest.raises(WorkflowError, match="not a recognized workflow status"):
        transition_exception(queue, exception_id, "Made Up Status", "BI Manager", "reason")


def test_valid_transitions_table_has_no_outgoing_edges_from_closed():
    assert VALID_TRANSITIONS["Closed"] == set()


def test_every_status_is_reachable_in_the_transition_table():
    reachable = {"New"}
    for targets in VALID_TRANSITIONS.values():
        reachable |= targets
    assert reachable == set(STATUSES)


# ---------------------------------------------------------------------------
# Summary / persistence
# ---------------------------------------------------------------------------


def test_summarize_workflow_counts_by_status():
    queue = build_exception_queue(_sample_outputs())
    summary = summarize_workflow(queue)
    assert summary["total"] == len(queue)
    assert summary["New"] == len(queue)
    assert summary["Closed"] == 0


def test_exception_queue_round_trips_through_json(tmp_path):
    queue_path = tmp_path / "exception_queue.json"
    queue = build_exception_queue(_sample_outputs())
    save_exception_queue(queue, path=queue_path)
    loaded = load_exception_queue(path=queue_path)
    assert loaded == queue


def test_load_exception_queue_returns_empty_list_when_missing(tmp_path):
    missing_path = tmp_path / "does_not_exist.json"
    assert load_exception_queue(path=missing_path) == []


def test_empty_outputs_produce_an_empty_queue():
    assert build_exception_queue({}) == []
    assert build_exception_queue({"product_action_review": pd.DataFrame()}) == []
