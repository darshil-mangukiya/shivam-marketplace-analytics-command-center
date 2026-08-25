from __future__ import annotations

from typing import Mapping


DATASET_LABELS = {
    "1m": "1M / 10K Orders",
    "3m": "3M / 30K Orders",
    "6m": "6M / 60K Orders",
    "12m": "12M / 120K Orders",
    "custom": "Custom Upload",
    "custom_upload": "Custom Upload",
}


def normalize_dataset_period(value: object) -> str:
    text = str(value or "").strip().lower().replace(" ", "")
    aliases = {
        "1month": "1m",
        "one-month": "1m",
        "3months": "3m",
        "three-months": "3m",
        "6months": "6m",
        "six-months": "6m",
        "12months": "12m",
        "twelve-months": "12m",
        "latest": "",
        "demo": "",
        "sample": "",
    }
    return aliases.get(text, text)


def infer_dataset_period_from_counts(transaction_rows: object = 0, order_rows: object = 0) -> str:
    try:
        transactions = int(float(transaction_rows or 0))
    except (TypeError, ValueError):
        transactions = 0
    try:
        orders = int(float(order_rows or 0))
    except (TypeError, ValueError):
        orders = 0

    if orders >= 100_000 or transactions >= 100_000:
        return "12m"
    if orders >= 60_000 or transactions >= 60_000:
        return "6m"
    if orders >= 30_000 or transactions >= 30_000:
        return "3m"
    if orders >= 10_000 or transactions >= 10_000:
        return "1m"
    return "custom_upload"


def dataset_label(
    dataset_period: object,
    *,
    transaction_rows: object = 0,
    order_rows: object = 0,
) -> str:
    normalized = normalize_dataset_period(dataset_period)
    if not normalized:
        normalized = infer_dataset_period_from_counts(transaction_rows, order_rows)
    return DATASET_LABELS.get(normalized, str(dataset_period or "Custom Upload"))


def dataset_mode_badge(mode: object, dataset_period: object, *, transaction_rows: object = 0, order_rows: object = 0) -> str:
    mode_text = str(mode or "").lower()
    label = dataset_label(dataset_period, transaction_rows=transaction_rows, order_rows=order_rows)
    if "demo" in mode_text or "sample" in mode_text:
        return f"SAMPLE DEMO: {label}"
    if label == "Custom Upload":
        return "CUSTOM UPLOAD ANALYSIS"
    return "UPLOAD ANALYSIS"


def dataset_period_from_profile(
    profile_rows: object,
    *,
    fallback: str = "",
    transaction_rows: object = 0,
    order_rows: object = 0,
) -> str:
    if hasattr(profile_rows, "columns") and "dataset_period" in profile_rows.columns and not profile_rows.empty:
        values = profile_rows["dataset_period"].dropna().astype(str).str.strip()
        values = values[values != ""]
        if not values.empty:
            return normalize_dataset_period(values.iloc[0]) or infer_dataset_period_from_counts(transaction_rows, order_rows)
    normalized = normalize_dataset_period(fallback)
    return normalized or infer_dataset_period_from_counts(transaction_rows, order_rows)


def dataset_label_from_outputs(
    outputs: Mapping[str, object],
    *,
    fallback: str = "",
    transaction_rows: object = 0,
    order_rows: object = 0,
) -> str:
    period = dataset_period_from_profile(
        outputs.get("dataset_profile"),
        fallback=fallback,
        transaction_rows=transaction_rows,
        order_rows=order_rows,
    )
    return dataset_label(period, transaction_rows=transaction_rows, order_rows=order_rows)
