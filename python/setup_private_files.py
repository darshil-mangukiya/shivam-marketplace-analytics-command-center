from __future__ import annotations

import argparse
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = PROJECT_ROOT.parent
DEFAULT_DESTINATION_DIR = PROJECT_ROOT / "data" / "private_raw"

PRIVATE_FILENAMES = [
    "Shivam_5_Marketplace_Product_Cost_Channel_Master_READY.xlsx",
    "Shivam_Transactions_1_Month_10K_Orders.csv",
    "Shivam_Transactions_3_Months_30K_Orders.csv",
    "Shivam_Transactions_6_Months_60K_Orders.csv",
    "Shivam_Transactions_12_Months_120K_Orders.csv",
    "2026MayMonthlyUnifiedTransaction.csv",
]


def should_copy(source: Path, destination: Path) -> bool:
    if not destination.exists():
        return True
    return source.stat().st_mtime > destination.stat().st_mtime


def copy_private_files(source_dir: Path, destination_dir: Path) -> dict[str, list[str]]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, list[str]] = {"copied": [], "skipped": [], "missing": []}

    for filename in PRIVATE_FILENAMES:
        source = source_dir / filename
        destination = destination_dir / filename
        if not source.is_file():
            summary["missing"].append(filename)
            continue
        if should_copy(source, destination):
            shutil.copy2(source, destination)
            summary["copied"].append(filename)
        else:
            summary["skipped"].append(filename)

    return summary


def print_summary(summary: dict[str, list[str]], destination_dir: Path) -> None:
    print(f"Copied: {len(summary['copied'])} files")
    print(f"Skipped: {len(summary['skipped'])} files")
    print(f"Missing: {len(summary['missing'])} files")
    print("Destination: data/private_raw/")

    for label in ("copied", "skipped", "missing"):
        files = summary[label]
        if files:
            print(f"{label.title()}: {', '.join(files)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Copy local private source files into data/private_raw/.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_DIR, help="Folder containing local private files.")
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION_DIR, help="Private raw data folder.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = copy_private_files(args.source, args.destination)
    print_summary(summary, args.destination)


if __name__ == "__main__":
    main()
