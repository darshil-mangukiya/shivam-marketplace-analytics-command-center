from __future__ import annotations

import argparse
from pathlib import Path

from pipeline_utils import (
    DATASET_FILES,
    TRANSACTION_RAW,
    anonymize_and_index_master,
    build_private_master,
    build_public_outputs,
    load_and_clean_product_master,
    load_and_clean_transactions,
    validate_outputs,
)


def resolve_transaction_source(dataset: str, custom_path: str | None) -> tuple[Path, str]:
    if dataset == "custom":
        if not custom_path:
            raise SystemExit("--transactions is required when --dataset custom is used.")
        path = Path(custom_path)
        return path, "custom"

    path = DATASET_FILES[dataset]
    if path.exists():
        return path, dataset

    if TRANSACTION_RAW.exists():
        print(
            f"Warning: expected generated dataset file was not found: {path}. "
            f"Falling back to original May transaction file: {TRANSACTION_RAW}."
        )
        return TRANSACTION_RAW, f"real_may_fallback_for_{dataset}"

    raise SystemExit(
        f"Missing transaction dataset: {path}. Add the generated CSV to data/private_raw/ "
        "or run with --dataset custom --transactions path/to/file.csv."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Shivam public-safe analytics pipeline.")
    parser.add_argument("--dataset", choices=["1m", "3m", "6m", "12m", "custom"], default="12m")
    parser.add_argument("--transactions", help="Transaction CSV path for --dataset custom.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    transaction_path, dataset_period = resolve_transaction_source(args.dataset, args.transactions)

    print("Loading and cleaning product master...")
    product_master = load_and_clean_product_master()
    print(f"Product master rows: {len(product_master):,}")

    print(f"Loading and cleaning transaction report for dataset {dataset_period}...")
    transactions = load_and_clean_transactions(transaction_path)
    print(f"Transaction rows: {len(transactions):,}")

    print("Building private joined master...")
    private_master = build_private_master()
    private_master["dataset_period"] = dataset_period
    private_master.to_csv("data/private_mapping/private_master.csv", index=False)
    print(f"Private master rows: {len(private_master):,}")

    print("Building anonymized transaction-level master...")
    anonymized = anonymize_and_index_master()
    print(f"Anonymized master rows: {len(anonymized):,}")

    print("Building public dashboard-ready outputs...")
    outputs = build_public_outputs()
    for name, df in outputs.items():
        print(f"{name}: {len(df):,} rows")

    print("Running validation checks...")
    validation = validate_outputs()
    failures = validation[validation["check_status"] != "PASS"]
    if not failures.empty:
        print(validation.to_string(index=False))
        raise SystemExit(1)
    print("Validation passed.")


if __name__ == "__main__":
    main()
