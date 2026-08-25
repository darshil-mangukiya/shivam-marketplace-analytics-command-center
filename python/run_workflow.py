"""CLI entry point for the local operational workflow (BR-23).

Builds/refreshes `artifacts/workflow/exception_queue.json` from the current
`data/public/product_action_review.csv` and
`data/public/inventory_action_review.csv`, preserving the status of any
exception that already exists in the queue. The workflow uses local JSON
and CSV files and requires no external service.

Usage:
    python python/run_workflow.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.workflow import (  # noqa: E402
    EXCEPTION_QUEUE_PATH,
    build_exception_queue,
    load_exception_queue,
    refresh_exception_queue,
    save_exception_queue,
    summarize_workflow,
)

PUBLIC_DIR = ROOT / "data" / "public"


def main() -> int:
    product_path = PUBLIC_DIR / "product_action_review.csv"
    inventory_path = PUBLIC_DIR / "inventory_action_review.csv"

    outputs: dict[str, pd.DataFrame] = {}
    if product_path.exists():
        outputs["product_action_review"] = pd.read_csv(product_path)
    if inventory_path.exists():
        outputs["inventory_action_review"] = pd.read_csv(inventory_path)

    if not outputs:
        print(
            "No public action-review outputs found under data/public/. "
            "Run `make run` (or an equivalent pipeline run) first."
        )
        return 1

    existing_queue = load_exception_queue()
    updated_queue = refresh_exception_queue(outputs, existing_queue)
    save_exception_queue(updated_queue)

    summary = summarize_workflow(updated_queue)
    print(f"Exception queue written to {EXCEPTION_QUEUE_PATH}")
    print(f"Total exceptions: {summary['total']}")
    for status, count in summary.items():
        if status == "total":
            continue
        print(f"  {status}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
