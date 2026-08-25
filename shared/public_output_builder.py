from __future__ import annotations

import numpy as np
import pandas as pd

from shared.metrics import (
    NON_PRODUCT_ID,
    band_from_pct,
    clean_text_series,
    index_from_values,
    numeric_column,
    origin_country_group,
    pct_of_gross,
    product_count,
    safe_group_value,
    text_column,
)
from shared.dataset_labels import dataset_label
from shared.profitability import (
    margin_risk_band,
    margin_risk_score,
    revenue_quality_band,
    revenue_quality_score,
)
from shared.recommendations import add_actions
from shared.variance_engine import (
    build_driver_summary,
    compare_periods,
    excluded_trailing_periods as variance_excluded_trailing_periods,
    select_default_periods,
)


# Neutral band shown for non-product activity (refunds, adjustments, fees with no
# SKU). These rows carry no product margin, so they must not be labelled with a
# real margin/profitability band and must not skew score averages.
NON_PRODUCT_BAND = "Not Applicable"


PUBLIC_DASHBOARD_COLUMNS = [
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
    "fee_pct_of_gross",
    "refund_pct_of_gross",
    "promotion_pct_of_gross",
    "net_to_gross_pct",
    "margin_index",
    "estimated_profitability_index",
    "margin_risk_score",
    "margin_risk_band",
    "revenue_quality_score",
    "revenue_quality_band",
    "recommended_action",
    "action_priority",
    "action_reason",
    "mapping_status",
]


def _ensure_public_context(df: pd.DataFrame, dataset_period: str) -> pd.DataFrame:
    public = df.copy()
    public["transaction_month"] = text_column(public, ["transaction_month"], "Unknown")
    public["dataset_period"] = text_column(public, ["dataset_period"], dataset_period)
    public["marketplace"] = text_column(public, ["marketplace"], "Unknown").map(lambda value: safe_group_value(value, "Unknown"))
    public["channel"] = text_column(public, ["channel"], "Marketplace").map(lambda value: safe_group_value(value, "Marketplace"))
    public["public_product_id"] = text_column(public, ["public_product_id"], NON_PRODUCT_ID)
    public["brand_group"] = text_column(public, ["brand_group", "brand"], "Unmapped").map(lambda value: safe_group_value(value, "Unmapped"))
    public["category_group"] = text_column(public, ["category_group", "category"], "Unmapped").map(lambda value: safe_group_value(value, "Unmapped"))
    public["subcategory_group"] = text_column(public, ["subcategory_group", "subcategory"], "Unmapped").map(lambda value: safe_group_value(value, "Unmapped"))
    public["product_group"] = text_column(public, ["product_group"], "Unmapped Product").map(lambda value: safe_group_value(value, "Unmapped Product"))
    public["fulfillment_type"] = text_column(public, ["fulfillment_type", "fulfillment_channel"], "Unknown").map(lambda value: safe_group_value(value, "Unknown"))
    public["state_group"] = text_column(public, ["state_group"], "Unknown").map(lambda value: safe_group_value(value, "Unknown"))
    public["origin_country_group"] = text_column(public, ["origin_country_group", "origin_country"], "Unknown").map(origin_country_group)
    public["imported_flag"] = text_column(public, ["imported_flag"], "Unknown").map(lambda value: safe_group_value(value, "Unknown"))
    public["listing_price_band"] = text_column(public, ["listing_price_band", "channel_price_band_public"], "Unknown")
    public["inventory_band"] = text_column(public, ["inventory_band"], "Unknown")
    public["margin_band_public"] = text_column(public, ["margin_band_public"], "Unknown")
    public["channel_margin_band_public"] = text_column(
        public,
        ["channel_margin_band_public", "margin_band_public_channel", "margin_band_public"],
        "Unknown",
    )
    public["profitability_band_public"] = text_column(
        public,
        ["profitability_band_public", "profitability_band_public_channel"],
        "Unknown",
    )
    public["transaction_type_group"] = text_column(public, ["transaction_type_group"], "Other")
    public["mapping_status"] = text_column(public, ["mapping_status"], "Unmatched")
    public["restock_priority"] = text_column(public, ["restock_priority"], "Monitor")
    return public


def add_public_metrics(df: pd.DataFrame) -> pd.DataFrame:
    public = df.copy()
    gross = numeric_column(public, ["_gross_sales_private_calc", "gross_sales_private_rs", "gross_sales_private", "product_sales"])
    units = numeric_column(public, ["_units_private_calc", "units_private", "units_private_rs", "quantity"]).clip(lower=0)
    refund = numeric_column(public, ["_refund_private_calc", "refund_amount_private_rs", "refund_amount_private"]).abs()
    promo = numeric_column(public, ["_promotion_private_calc", "promotion_amount_private_rs", "promotion_amount_private", "promotional_rebates"]).abs()
    fee = numeric_column(
        public,
        ["_fee_private_calc", "total_fee_private_rs", "amazon_fee_private"],
    ).abs()
    if fee.eq(0).all():
        fee = (
            numeric_column(public, ["selling_fee_private_rs", "selling_fees"]).abs()
            + numeric_column(public, ["fba_fee_private_rs", "fba_fees"]).abs()
            + numeric_column(public, ["other_fee_private_rs", "other_transaction_fees"]).abs()
        )
    net = numeric_column(public, ["_net_private_calc", "net_amount_private_rs", "net_amount_private", "total"])

    landed_unit_cost = numeric_column(
        public,
        ["total_channel_cost_private_rs", "landed_cost_private_rs", "total_estimated_cost_private_rs", "unit_cost_private_rs"],
    ).clip(lower=0)
    estimated_cogs = numeric_column(public, ["estimated_cogs_private_rs"])
    if estimated_cogs.eq(0).all():
        estimated_cogs = units * landed_unit_cost
    private_profit = numeric_column(
        public,
        [
            "_estimated_profit_private_calc",
            "estimated_gross_profit_private_rs",
            "estimated_channel_profit_private_rs",
            "estimated_profit_private_rs",
        ],
    )
    if private_profit.eq(0).all():
        private_profit = gross - estimated_cogs - fee - promo - refund

    public["_gross_sales_private_calc"] = gross
    public["_units_private_calc"] = units
    public["_fee_private_calc"] = fee
    public["_refund_private_calc"] = refund
    public["_promotion_private_calc"] = promo
    public["_net_private_calc"] = net
    public["_estimated_profit_private_calc"] = private_profit
    public["_estimated_profit_margin_pct_private_calc"] = np.where(gross > 0, private_profit / gross * 100.0, 0.0)

    public["sales_index"] = index_from_values(gross).round(1)
    public["units_index"] = index_from_values(units).round(1)
    public["revenue_index"] = public["sales_index"]
    public["fee_pct_of_gross"] = pct_of_gross(fee, gross).round(1)
    public["refund_pct_of_gross"] = pct_of_gross(refund, gross).round(1)
    public["promotion_pct_of_gross"] = pct_of_gross(promo, gross).round(1)
    public["net_to_gross_pct"] = pct_of_gross(net, gross, signed=True).round(1)
    public["margin_index"] = index_from_values(private_profit.clip(lower=0)).round(1)
    # estimated_profitability_index is a blended 0-100 signal computed after the
    # revenue-quality and margin-risk scores below. It is intentionally distinct
    # from margin_index (which is only the relative profit scale). Placeholder
    # here keeps the column order stable.
    public["estimated_profitability_index"] = 0.0

    margin_pct = pd.Series(public["_estimated_profit_margin_pct_private_calc"], index=public.index).round(1)
    if "margin_band_public" not in public.columns:
        public["margin_band_public"] = "Unknown"
    if "profitability_band_public" not in public.columns:
        public["profitability_band_public"] = "Unknown"
    public["margin_band_public"] = public["margin_band_public"].mask(public["margin_band_public"].eq("Unknown"), margin_pct.map(band_from_pct))
    public["profitability_band_public"] = public["profitability_band_public"].mask(
        public["profitability_band_public"].eq("Unknown"),
        margin_pct.map(band_from_pct),
    )
    public["margin_risk_score"] = margin_risk_score(
        public["fee_pct_of_gross"],
        public["refund_pct_of_gross"],
        public["promotion_pct_of_gross"],
        public["net_to_gross_pct"],
        margin_pct,
    )
    public["margin_risk_band"] = public["margin_risk_score"].map(margin_risk_band)
    public["revenue_quality_score"] = revenue_quality_score(
        public["net_to_gross_pct"],
        public["fee_pct_of_gross"],
        public["refund_pct_of_gross"],
        public["promotion_pct_of_gross"],
    )
    public["revenue_quality_band"] = public["revenue_quality_score"].map(revenue_quality_band)

    # Blend estimated_profitability_index (0-100) from four
    # signals: relative profit scale, revenue quality, inverse margin risk, and
    # net-to-gross. No raw money values are exposed; all inputs are already public.
    net_component = (
        pd.to_numeric(public["net_to_gross_pct"], errors="coerce").fillna(0.0).clip(lower=0.0, upper=100.0)
    )
    inverse_risk = (
        100.0 - pd.to_numeric(public["margin_risk_score"], errors="coerce").fillna(0.0)
    ).clip(lower=0.0, upper=100.0)
    public["estimated_profitability_index"] = (
        0.40 * pd.to_numeric(public["margin_index"], errors="coerce").fillna(0.0)
        + 0.25 * pd.to_numeric(public["revenue_quality_score"], errors="coerce").fillna(0.0)
        + 0.20 * inverse_risk
        + 0.15 * net_component
    ).clip(lower=0.0, upper=100.0).round(1)

    # Non-product activity rows (no SKU) must not carry product margin bands or
    # scores, otherwise they pollute marketplace/category averages and visuals.
    if "public_product_id" in public.columns:
        non_product = public["public_product_id"].astype("string") == NON_PRODUCT_ID
        if bool(non_product.any()):
            for band_col in ("margin_band_public", "profitability_band_public", "channel_margin_band_public"):
                if band_col in public.columns:
                    public.loc[non_product, band_col] = NON_PRODUCT_BAND
            public.loc[non_product, "margin_risk_score"] = np.nan
            public.loc[non_product, "revenue_quality_score"] = np.nan
            public.loc[non_product, "margin_index"] = np.nan
            public.loc[non_product, "estimated_profitability_index"] = np.nan
            public.loc[non_product, "margin_risk_band"] = NON_PRODUCT_BAND
            public.loc[non_product, "revenue_quality_band"] = NON_PRODUCT_BAND
    return public


def build_public_dashboard(private_master: pd.DataFrame, *, dataset_period: str = "custom") -> pd.DataFrame:
    public = _ensure_public_context(private_master, dataset_period)
    public = add_public_metrics(public)
    public = add_actions(public)
    for col in PUBLIC_DASHBOARD_COLUMNS:
        if col not in public.columns:
            public[col] = pd.NA
    return public[PUBLIC_DASHBOARD_COLUMNS].copy()


def aggregate_public(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    grouped = df.groupby(group_cols, dropna=False)
    result = grouped.agg(
        gross_sales=("_gross_sales_private_calc", "sum"),
        units=("_units_private_calc", "sum"),
        total_fee=("_fee_private_calc", "sum"),
        refund_amount=("_refund_private_calc", "sum"),
        promotion_amount=("_promotion_private_calc", "sum"),
        net_amount=("_net_private_calc", "sum"),
        estimated_profit=("_estimated_profit_private_calc", "sum"),
        product_count=("public_product_id", product_count),
        avg_margin_risk_score=("margin_risk_score", "mean"),
        avg_revenue_quality_score=("revenue_quality_score", "mean"),
    ).reset_index()
    # Round the averaged scores so public outputs never show 15-decimal floats.
    result["avg_margin_risk_score"] = result["avg_margin_risk_score"].round(1)
    result["avg_revenue_quality_score"] = result["avg_revenue_quality_score"].round(1)

    if "transaction_type_group" in df.columns:
        order_rows = df[df["transaction_type_group"].eq("Order")]
    else:
        order_rows = df
    order_id_col = "order_id" if "order_id" in df.columns else None
    if order_id_col and not order_rows.empty:
        orders = order_rows.groupby(group_cols, dropna=False)[order_id_col].nunique().reset_index(name="order_count")
        result = result.merge(orders, on=group_cols, how="left")
    else:
        order_counts = order_rows.groupby(group_cols, dropna=False).size().reset_index(name="order_count")
        result = result.merge(order_counts, on=group_cols, how="left")
    result["order_count"] = result["order_count"].fillna(0).astype(int)

    result["_gross_sales_private_calc"] = result["gross_sales"]
    result["_units_private_calc"] = result["units"]
    result["_fee_private_calc"] = result["total_fee"]
    result["_refund_private_calc"] = result["refund_amount"]
    result["_promotion_private_calc"] = result["promotion_amount"]
    result["_net_private_calc"] = result["net_amount"]
    result["_estimated_profit_private_calc"] = result["estimated_profit"]
    result = add_public_metrics(result)
    result["order_count_index"] = index_from_values(result["order_count"]).round(1)
    result["margin_risk_score"] = result["avg_margin_risk_score"].round(1)
    result["revenue_quality_score"] = result["avg_revenue_quality_score"].round(1)
    result["margin_risk_band"] = result["margin_risk_score"].map(margin_risk_band)
    result["revenue_quality_band"] = result["revenue_quality_score"].map(revenue_quality_band)
    return result.drop(
        columns=[
            "gross_sales",
            "units",
            "total_fee",
            "refund_amount",
            "promotion_amount",
            "net_amount",
            "estimated_profit",
        ],
        errors="ignore",
    )


def _sort_action(df: pd.DataFrame) -> pd.DataFrame:
    priority_rank = df["action_priority"].map({"High": 1, "Medium": 2, "Low": 3}).fillna(4)
    return df.assign(_priority_rank=priority_rank).sort_values(
        ["_priority_rank", "sales_index", "units_index"],
        ascending=[True, False, False],
    ).drop(columns=["_priority_rank"])


DRIVER_HEADLINE_METRICS = [
    "sales_index",
    "units_index",
    "fee_pct_of_gross",
    "refund_pct_of_gross",
    "promotion_pct_of_gross",
    "net_to_gross_pct",
    "margin_risk_score",
    "revenue_quality_score",
    "estimated_profitability_index",
]


def build_variance_outputs(base: pd.DataFrame, product_rows: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build marketplace and product performance-driver marts.

    Builds three privacy-safe marts from already-public-safe columns only
    (indexes, ratios, scores — no raw currency, no SKUs/ASINs/order IDs):

    - mart_marketplace_variance_drivers: period-over-period variance by
      marketplace for each headline metric.
    - mart_product_variance_contributors: period-over-period variance by
      product (+ marketplace/brand/category) for each headline metric.
    - mart_performance_driver_summary: one row per headline metric with the
      overall variance and a deterministic narrative.

    When the dataset has fewer than two VALID ACTIVITY periods (a period is
    valid when its aggregated order_count is > 0 at the overall month
    level — see shared/variance_engine.py:select_default_periods), the two
    variance marts are returned empty (defined schema, zero rows) and the
    summary mart carries one explicit "Insufficient Periods" row — no
    comparison is fabricated (BR-16). A trailing period with zero
    aggregated order activity (e.g. an in-progress or not-yet-populated
    month) is safely excluded from comparison rather than compared
    against, deleted, or treated as an error; it is reported informationally
    via the `excluded_trailing_periods` column on
    mart_performance_driver_summary.
    """
    marketplace_matrix = aggregate_public(base, ["transaction_month", "marketplace"])
    period_pair = select_default_periods(marketplace_matrix, "transaction_month")
    previous_period, current_period = period_pair if period_pair else (None, None)
    excluded_periods = variance_excluded_trailing_periods(marketplace_matrix, "transaction_month")

    marketplace_drivers = compare_periods(
        marketplace_matrix,
        ["marketplace"],
        DRIVER_HEADLINE_METRICS,
        previous_period,
        current_period,
    )

    if product_rows.empty:
        product_matrix = pd.DataFrame()
    else:
        product_matrix = aggregate_public(
            product_rows,
            ["transaction_month", "public_product_id", "marketplace", "brand_group", "category_group"],
        )
    product_contributors = compare_periods(
        product_matrix,
        ["public_product_id", "marketplace", "brand_group", "category_group"],
        DRIVER_HEADLINE_METRICS,
        previous_period,
        current_period,
    )

    driver_summary = build_driver_summary(
        marketplace_matrix,
        previous_period,
        current_period,
        DRIVER_HEADLINE_METRICS,
        dimension_label_col="marketplace",
        excluded_trailing_periods_list=excluded_periods,
    )

    return {
        "mart_marketplace_variance_drivers": marketplace_drivers,
        "mart_product_variance_contributors": product_contributors,
        "mart_performance_driver_summary": driver_summary,
    }


def build_public_outputs(private_master: pd.DataFrame, *, dataset_period: str = "custom") -> dict[str, pd.DataFrame]:
    base = _ensure_public_context(private_master, dataset_period)
    base = add_public_metrics(base)
    base = add_actions(base)
    public = base[PUBLIC_DASHBOARD_COLUMNS].copy()
    product_rows = base[base["public_product_id"] != NON_PRODUCT_ID].copy()
    outputs: dict[str, pd.DataFrame] = {"anonymized_master": public}

    marketplace = aggregate_public(base, ["dataset_period", "transaction_month", "marketplace"]).rename(
        columns={
            "order_count": "total_orders",
            "fee_pct_of_gross": "avg_fee_pct_of_gross",
            "refund_pct_of_gross": "avg_refund_pct_of_gross",
            "promotion_pct_of_gross": "avg_promotion_pct_of_gross",
            "net_to_gross_pct": "avg_net_to_gross_pct",
        }
    )
    outputs["marketplace_summary"] = marketplace[
        [
            "dataset_period",
            "transaction_month",
            "marketplace",
            "total_orders",
            "product_count",
            "sales_index",
            "units_index",
            "avg_fee_pct_of_gross",
            "avg_refund_pct_of_gross",
            "avg_promotion_pct_of_gross",
            "avg_net_to_gross_pct",
            "margin_risk_score",
            "revenue_quality_score",
        ]
    ]

    channel = aggregate_public(base, ["dataset_period", "marketplace", "channel"]).rename(
        columns={
            "fee_pct_of_gross": "avg_fee_pct_of_gross",
            "refund_pct_of_gross": "avg_refund_pct_of_gross",
            "promotion_pct_of_gross": "avg_promotion_pct_of_gross",
            "net_to_gross_pct": "avg_net_to_gross_pct",
        }
    )
    # Count DISTINCT high-priority products per channel, not transaction rows, so
    # high_priority_action_count is always <= product_count for the group.
    high_action_rows = base[
        (base["action_priority"] == "High") & (base["public_product_id"] != NON_PRODUCT_ID)
    ]
    action_counts = (
        high_action_rows.groupby(["dataset_period", "marketplace", "channel"], dropna=False)["public_product_id"]
        .nunique()
        .reset_index(name="high_priority_action_count")
    )
    channel = channel.merge(action_counts, on=["dataset_period", "marketplace", "channel"], how="left")
    channel["high_priority_action_count"] = channel["high_priority_action_count"].fillna(0).astype(int)
    channel = channel[
        [
            "dataset_period",
            "marketplace",
            "channel",
            "product_count",
            "order_count_index",
            "sales_index",
            "units_index",
            "avg_fee_pct_of_gross",
            "avg_refund_pct_of_gross",
            "avg_promotion_pct_of_gross",
            "avg_net_to_gross_pct",
            "avg_margin_risk_score",
            "avg_revenue_quality_score",
            "high_priority_action_count",
        ]
    ]
    # Drop zero-activity non-product channel rows (e.g. "Amazon, Amazon" with all
    # zeros). Keep only channels that carry products or sales activity.
    channel = channel[(channel["product_count"] > 0) | (channel["sales_index"] > 0)].reset_index(drop=True)
    outputs["marketplace_channel_performance"] = channel

    product_group_cols = [
        "public_product_id",
        "marketplace",
        "brand_group",
        "category_group",
        "subcategory_group",
        "product_group",
        "fulfillment_type",
        "listing_price_band",
        "inventory_band",
        "margin_band_public",
        "profitability_band_public",
    ]
    product = aggregate_public(product_rows, product_group_cols)
    product = add_actions(product)
    outputs["product_performance"] = product[
        product_group_cols
        + [
            "sales_index",
            "units_index",
            "fee_pct_of_gross",
            "refund_pct_of_gross",
            "promotion_pct_of_gross",
            "net_to_gross_pct",
            "margin_index",
            "estimated_profitability_index",
            "margin_risk_score",
            "margin_risk_band",
            "revenue_quality_score",
            "revenue_quality_band",
            "recommended_action",
            "action_priority",
            "action_reason",
        ]
    ].sort_values(["sales_index", "units_index"], ascending=False)

    category = aggregate_public(product_rows, ["dataset_period", "marketplace", "category_group", "subcategory_group"]).rename(
        columns={
            "fee_pct_of_gross": "avg_fee_pct_of_gross",
            "refund_pct_of_gross": "avg_refund_pct_of_gross",
            "promotion_pct_of_gross": "avg_promotion_pct_of_gross",
            "net_to_gross_pct": "avg_net_to_gross_pct",
        }
    )
    outputs["category_performance"] = category[
        [
            "dataset_period",
            "marketplace",
            "category_group",
            "subcategory_group",
            "product_count",
            "sales_index",
            "units_index",
            "avg_fee_pct_of_gross",
            "avg_refund_pct_of_gross",
            "avg_promotion_pct_of_gross",
            "avg_net_to_gross_pct",
            "margin_risk_score",
            "revenue_quality_score",
        ]
    ].sort_values(["sales_index", "units_index"], ascending=False)

    brand = aggregate_public(product_rows, ["dataset_period", "marketplace", "brand_group", "category_group"]).rename(
        columns={
            "fee_pct_of_gross": "avg_fee_pct_of_gross",
            "refund_pct_of_gross": "avg_refund_pct_of_gross",
            "promotion_pct_of_gross": "avg_promotion_pct_of_gross",
            "net_to_gross_pct": "avg_net_to_gross_pct",
        }
    )
    outputs["brand_performance"] = brand[
        [
            "dataset_period",
            "marketplace",
            "brand_group",
            "category_group",
            "product_count",
            "sales_index",
            "units_index",
            "avg_fee_pct_of_gross",
            "avg_refund_pct_of_gross",
            "avg_promotion_pct_of_gross",
            "avg_net_to_gross_pct",
            "margin_risk_score",
            "revenue_quality_score",
        ]
    ].sort_values(["sales_index", "units_index"], ascending=False)

    fee_refund = outputs["product_performance"][
        [
            "public_product_id",
            "marketplace",
            "brand_group",
            "category_group",
            "product_group",
            "fee_pct_of_gross",
            "refund_pct_of_gross",
            "promotion_pct_of_gross",
            "net_to_gross_pct",
            "revenue_quality_score",
            "revenue_quality_band",
        ]
    ].copy()
    fee_refund["fee_review_flag"] = np.where(fee_refund["fee_pct_of_gross"] >= 25, "Review", "Monitor")
    fee_refund["refund_review_flag"] = np.where(fee_refund["refund_pct_of_gross"] >= 10, "Review", "Monitor")
    fee_refund["promotion_review_flag"] = np.where(
        (fee_refund["promotion_pct_of_gross"] >= 10) & (fee_refund["net_to_gross_pct"] < 70),
        "Review",
        "Monitor",
    )
    outputs["fee_refund_summary"] = fee_refund

    fulfillment = aggregate_public(product_rows, ["dataset_period", "fulfillment_type"]).rename(
        columns={
            "fee_pct_of_gross": "avg_fee_pct_of_gross",
            "refund_pct_of_gross": "avg_refund_pct_of_gross",
            "net_to_gross_pct": "avg_net_to_gross_pct",
        }
    )
    outputs["fulfillment_comparison"] = fulfillment[
        [
            "dataset_period",
            "fulfillment_type",
            "product_count",
            "order_count",
            "sales_index",
            "units_index",
            "avg_fee_pct_of_gross",
            "avg_refund_pct_of_gross",
            "avg_net_to_gross_pct",
            "margin_risk_score",
            "revenue_quality_score",
        ]
    ].sort_values(["sales_index", "units_index"], ascending=False)

    profitability = aggregate_public(
        product_rows,
        ["dataset_period", "marketplace", "category_group", "brand_group", "product_group", "margin_band_public", "profitability_band_public"],
    )
    outputs["profitability_summary"] = profitability[
        [
            "dataset_period",
            "marketplace",
            "category_group",
            "brand_group",
            "product_group",
            "product_count",
            "sales_index",
            "units_index",
            "margin_index",
            "estimated_profitability_index",
            "margin_band_public",
            "profitability_band_public",
            "margin_risk_score",
            "margin_risk_band",
            "revenue_quality_score",
            "revenue_quality_band",
        ]
    ].sort_values(["margin_risk_score", "sales_index"], ascending=[False, False])

    margin_risk = outputs["product_performance"][
        [
            "public_product_id",
            "marketplace",
            "brand_group",
            "category_group",
            "product_group",
            "listing_price_band",
            "inventory_band",
            "sales_index",
            "units_index",
            "fee_pct_of_gross",
            "refund_pct_of_gross",
            "promotion_pct_of_gross",
            "net_to_gross_pct",
            "margin_risk_score",
            "margin_risk_band",
            "revenue_quality_score",
            "recommended_action",
            "action_priority",
            "action_reason",
        ]
    ].sort_values(["margin_risk_score", "sales_index"], ascending=[False, False])
    outputs["margin_risk_review"] = margin_risk

    inventory_context = product_rows[
        [
            "public_product_id",
            "marketplace",
            "brand_group",
            "category_group",
            "product_group",
            "inventory_band",
            "restock_priority",
        ]
    ].drop_duplicates()
    inventory = outputs["product_performance"].merge(
        inventory_context,
        on=["public_product_id", "marketplace", "brand_group", "category_group", "product_group", "inventory_band"],
        how="left",
    )
    outputs["inventory_action_review"] = inventory[
        [
            "public_product_id",
            "marketplace",
            "brand_group",
            "category_group",
            "product_group",
            "inventory_band",
            "units_index",
            "sales_index",
            "margin_risk_band",
            "revenue_quality_band",
            "restock_priority",
            "recommended_action",
            "action_priority",
            "action_reason",
        ]
    ].sort_values(["action_priority", "units_index"], ascending=[True, False])

    product_action = outputs["product_performance"].copy()
    outputs["product_action_review"] = _sort_action(product_action)

    outputs.update(build_variance_outputs(base, product_rows))

    outputs["dataset_profile"] = pd.DataFrame(
        [
            {
                "public_output_name": name,
                "row_count": int(len(df)),
                "dataset_period": dataset_period,
                "dataset_label": dataset_label(dataset_period),
            }
            for name, df in outputs.items()
        ]
    )
    return outputs
