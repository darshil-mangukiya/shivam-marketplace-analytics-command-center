from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


NOT_AVAILABLE = "Not Available"
OUTCOME_LABELS = (
    "Top Marketplace",
    "Top Product Group",
    "Highest Review Area",
    "Top Revenue Quality Segment",
    "Most Common Action",
)
OUTCOME_HELPER_TEXT = "Business-facing summary generated from privacy-safe indexed metrics, ratios, and action signals."


def _top_value(df: pd.DataFrame, label_col: str, value_col: str, *, agg: str = "mean") -> str:
    if df.empty or label_col not in df.columns or value_col not in df.columns:
        return NOT_AVAILABLE
    grouped = (
        df[[label_col, value_col]]
        .dropna()
        .assign(**{value_col: pd.to_numeric(df[value_col], errors="coerce").fillna(0.0)})
        .groupby(label_col, dropna=False)[value_col]
        .agg(agg)
        .reset_index()
        .sort_values(value_col, ascending=False)
    )
    if grouped.empty:
        return NOT_AVAILABLE
    value = str(grouped.iloc[0][label_col]).strip()
    return value or NOT_AVAILABLE


def _mode_value(df: pd.DataFrame, label_col: str, *, exclude: set[str] | None = None) -> str:
    if df.empty or label_col not in df.columns:
        return NOT_AVAILABLE
    values = df[label_col].dropna().astype(str).str.strip()
    values = values[values != ""]
    if exclude:
        values = values[~values.isin(exclude)]
    if values.empty:
        return NOT_AVAILABLE
    return str(values.value_counts().index[0])


def build_business_outcomes(outputs: Mapping[str, pd.DataFrame]) -> dict[str, str]:
    marketplace = outputs.get("marketplace_summary", pd.DataFrame())
    product = outputs.get("product_performance", pd.DataFrame())
    channel = outputs.get("marketplace_channel_performance", pd.DataFrame())
    action = outputs.get("product_action_review", pd.DataFrame())

    return {
        "Top Marketplace": _top_value(marketplace, "marketplace", "sales_index"),
        "Top Product Group": _top_value(product, "product_group", "sales_index"),
        "Highest Review Area": _mode_value(action, "recommended_action", exclude={"Monitor"}),
        "Top Revenue Quality Segment": _top_value(channel, "channel", "avg_revenue_quality_score"),
        "Most Common Action": _mode_value(action, "recommended_action"),
    }
