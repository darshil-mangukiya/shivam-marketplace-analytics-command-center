from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd


SENSITIVE_COLUMNS = {
    "asin",
    "asin1",
    "asin_private",
    "seller_sku",
    "seller_sku_private",
    "sku",
    "order_id",
    "listing_id",
    "product_id",
    "item_name",
    "item_name_private",
    "item_description",
    "description",
    "order_postal",
    "postal_code",
    "order_city",
    "gross_sales_private",
    "gross_sales_private_rs",
    "units_private",
    "refund_amount_private",
    "refund_amount_private_rs",
    "promotion_amount_private",
    "promotion_amount_private_rs",
    "amazon_fee_private",
    "total_fee_private_rs",
    "net_amount_private",
    "net_amount_private_rs",
    "product_sales",
    "selling_fees",
    "fba_fees",
    "other_transaction_fees",
    "total",
    "price",
    "listing_price_private_rs",
    "maximum_retail_price",
    "mrp_private_rs",
    "unit_cost_private_rs",
    "landed_cost_private_rs",
    "estimated_profit_private_rs",
    "estimated_gross_profit_private_rs",
}

SENSITIVE_COLUMN_TOKENS = (
    "private",
    "asin",
    "sku",
    "order_id",
    "listing_id",
    "description",
    "postal",
    "raw_",
    "rupee",
    "_rs",
)

ALLOWED_PUBLIC_COLUMNS = {
    "transaction_month",
    "dataset_period",
    "marketplace",
    "channel",
    "public_product_id",
    "brand_group",
    "category_group",
    "subcategory_group",
    "product_group",
    "fulfillment_type",
    "state_group",
    "origin_country_group",
    "imported_flag",
    "listing_price_band",
    "inventory_band",
    "margin_band_public",
    "channel_margin_band_public",
    "profitability_band_public",
    "transaction_type_group",
    "sales_index",
    "units_index",
    "revenue_index",
    "margin_index",
    "estimated_profitability_index",
    "order_count_index",
    "fee_pct_of_gross",
    "refund_pct_of_gross",
    "promotion_pct_of_gross",
    "net_to_gross_pct",
    "avg_fee_pct_of_gross",
    "avg_refund_pct_of_gross",
    "avg_promotion_pct_of_gross",
    "avg_net_to_gross_pct",
    "avg_margin_risk_score",
    "avg_revenue_quality_score",
    "margin_risk_score",
    "margin_risk_band",
    "revenue_quality_score",
    "revenue_quality_band",
    "recommended_action",
    "action_priority",
    "action_reason",
    "mapping_status",
    "product_count",
    "order_count",
    "total_orders",
    "high_priority_action_count",
    "restock_priority",
    "fee_review_flag",
    "refund_review_flag",
    "promotion_review_flag",
    "dataset_file",
    "row_count",
    "public_output_name",
    "check_name",
    "check_status",
    "check_value",
    "expected_value",
    "notes",
}

ASIN_PATTERN = re.compile(r"\bB0[A-Z0-9]{8}\b", re.IGNORECASE)
ORDER_PATTERN = re.compile(r"\b(?:ORDER|ORD|AMZ|FLP|MEE|JIO|WEB)[-_]?[A-Z0-9-]{4,}\b", re.IGNORECASE)
POSTAL_PATTERN = re.compile(r"\b[1-9][0-9]{5}\b")
CURRENCY_PATTERN = re.compile(r"(?:₹|\bINR\b|\bRS\.?\b)", re.IGNORECASE)


def unsafe_columns(columns: Iterable[object]) -> list[str]:
    hits: list[str] = []
    for column in columns:
        name = str(column)
        lowered = name.lower()
        if lowered in SENSITIVE_COLUMNS:
            hits.append(name)
            continue
        if lowered not in ALLOWED_PUBLIC_COLUMNS and any(token in lowered for token in SENSITIVE_COLUMN_TOKENS):
            hits.append(name)
    return sorted(set(hits))


def _known_private_hits(series: pd.Series, known_private_values: set[str]) -> int:
    if not known_private_values:
        return 0
    values = series.astype("string").dropna().str.strip()
    return int(values.isin(known_private_values).sum())


LONG_TITLE_PATTERN = r"\w+\s+\w+\s+\w+\s+\w+\s+\w+"


def _count_pattern(series: pd.Series, pattern: re.Pattern[str]) -> int:
    """Total number of regex occurrences across every cell of a string series."""
    counts = series.str.count(pattern.pattern, flags=pattern.flags)
    return int(pd.to_numeric(counts, errors="coerce").fillna(0).sum())


def content_privacy_scan(
    df: pd.DataFrame,
    *,
    known_private_values: Iterable[object] | None = None,
    max_rows: int | None = None,
) -> dict[str, object]:
    """Scan public cell values for private-looking content.

    By default this scans the FULL frame (every row). ``max_rows`` is an optional
    developer-only performance cap; when left as ``None`` the entire frame is
    scanned, so the documented guarantee is full-frame. Only counts are returned;
    the actual leaked values are never included in the result.
    """
    known_values = {
        str(value).strip()
        for value in (known_private_values or [])
        if value is not None and str(value).strip()
    }
    scoped = df if max_rows is None else df.head(max_rows)
    text = scoped.astype("string")
    counts = {
        "asin_like_values": 0,
        "known_private_identifier_values": 0,
        "order_id_like_values": 0,
        "postal_code_like_values": 0,
        "currency_marker_values": 0,
        "long_title_like_values": 0,
    }
    allowed_long_text = {
        "action_reason",
        "narrative",
        "notes",
        "check_name",
        "expected_value",
        "check_value",
        "brand_group",
        "category_group",
        "subcategory_group",
        "product_group",
        "marketplace",
        "channel",
        "listing_price_band",
        "inventory_band",
        "margin_band_public",
        "profitability_band_public",
    }
    # "narrative" carries deterministic template text that legitimately embeds
    # marketplace names (e.g. "JioMart"), which can otherwise false-positive
    # against ORDER_PATTERN the same way raw "marketplace"/"channel" values
    # already do. ASIN/postal/currency/known-private-identifier scans still
    # run on this column — only the order-ID-shaped-substring heuristic is
    # exempted, same treatment as marketplace/channel.
    order_pattern_exempt_columns = {"marketplace", "channel", "narrative"}
    for column in text.columns:
        series = text[column].dropna()
        if series.empty:
            continue
        raw_series = scoped[column]
        is_numeric = pd.api.types.is_numeric_dtype(raw_series)
        counts["asin_like_values"] += _count_pattern(series, ASIN_PATTERN)
        if column not in order_pattern_exempt_columns:
            counts["order_id_like_values"] += _count_pattern(series, ORDER_PATTERN)
        if not is_numeric:
            counts["postal_code_like_values"] += _count_pattern(series, POSTAL_PATTERN)
        counts["currency_marker_values"] += _count_pattern(series, CURRENCY_PATTERN)
        if not is_numeric:
            counts["known_private_identifier_values"] += _known_private_hits(series, known_values)
        if column not in allowed_long_text:
            title_like = series.str.contains(LONG_TITLE_PATTERN, regex=True, na=False)
            counts["long_title_like_values"] += int(title_like.sum())

    total_hits = int(sum(counts.values()))
    return {
        **counts,
        "total_content_hits": total_hits,
        "is_safe": total_hits == 0,
    }


def scan_public_outputs(
    outputs: dict[str, pd.DataFrame],
    *,
    known_private_values: Iterable[object] | None = None,
) -> dict[str, object]:
    unsafe_by_output: dict[str, list[str]] = {}
    content_by_output: dict[str, dict[str, object]] = {}
    for name, df in outputs.items():
        if name == "validation_summary":
            continue
        column_hits = unsafe_columns(df.columns)
        if column_hits:
            unsafe_by_output[name] = column_hits
        content_scan = content_privacy_scan(df, known_private_values=known_private_values)
        content_by_output[name] = content_scan
    content_hit_count = int(
        sum(int(scan.get("total_content_hits", 0) or 0) for scan in content_by_output.values())
    )
    return {
        "unsafe_columns_by_output": unsafe_by_output,
        "content_scan_by_output": content_by_output,
        "content_hit_count": content_hit_count,
        "is_safe": not unsafe_by_output and content_hit_count == 0,
    }
