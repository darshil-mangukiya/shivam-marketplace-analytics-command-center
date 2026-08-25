from __future__ import annotations

import pandas as pd


def action_counts(product_action_review: pd.DataFrame) -> pd.DataFrame:
    if product_action_review.empty or "recommended_action" not in product_action_review.columns:
        return pd.DataFrame(columns=["recommended_action", "count"])
    return (
        product_action_review["recommended_action"]
        .value_counts()
        .rename_axis("recommended_action")
        .reset_index(name="count")
    )


def priority_counts(product_action_review: pd.DataFrame) -> pd.DataFrame:
    if product_action_review.empty or "action_priority" not in product_action_review.columns:
        return pd.DataFrame(columns=["action_priority", "count"])
    order = pd.CategoricalDtype(["High", "Medium", "Low"], ordered=True)
    counts = product_action_review.copy()
    counts["action_priority"] = counts["action_priority"].astype(order)
    return (
        counts["action_priority"]
        .value_counts(sort=False)
        .rename_axis("action_priority")
        .reset_index(name="count")
        .dropna()
    )


def executive_summary_text(outputs: dict[str, pd.DataFrame], join_metrics: dict[str, object]) -> str:
    product_actions = outputs.get("product_action_review", pd.DataFrame())
    marketplace = outputs.get("marketplace_channel_performance", pd.DataFrame())
    coverage = float(join_metrics.get("join_coverage_pct", 0) or 0)
    refund_count = int((product_actions.get("recommended_action", pd.Series(dtype=str)) == "Refund Review").sum())
    promo_count = int((product_actions.get("recommended_action", pd.Series(dtype=str)) == "Promotion Review").sum())
    slow_count = int((product_actions.get("recommended_action", pd.Series(dtype=str)) == "Slow Mover Review").sum())
    margin_count = int((product_actions.get("recommended_action", pd.Series(dtype=str)) == "Margin Risk Review").sum())
    high_count = int((product_actions.get("action_priority", pd.Series(dtype=str)) == "High").sum())
    marketplace_count = int(marketplace.get("marketplace", pd.Series(dtype=str)).nunique())

    return (
        f"The uploaded transaction file joined successfully with the product master at {coverage:.1f}% "
        "coverage on rows with SKUs. "
        f"Reporting spans {marketplace_count} public marketplace group(s); marketplace-channel enrichment is "
        "unavailable until seller-SKU/public-product mappings are populated. "
        f"The privacy-safe action logic identified {high_count} high-priority item(s), "
        f"{refund_count} Refund Review candidate(s), {promo_count} Promotion Review candidate(s), "
        f"{slow_count} Slow Mover Review candidate(s), and {margin_count} Margin Risk Review candidate(s). "
        "All dashboard metrics use indexed activity, ratios, scores, percentages, and bands instead of raw money values."
    )
