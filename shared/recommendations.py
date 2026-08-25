from __future__ import annotations

import numpy as np
import pandas as pd


# Ordered (mask, action, priority, reason). Order matters: the first matching
# rule wins, mirroring the row-wise recommended_action() reference below.
ACTION_RULES = [
    ("Margin Risk Review", "High", "Critical margin-risk score from fee, refund, promotion, net, and margin signals."),
    ("Refund Review", "High", "Meaningful sales-index product with elevated refund percentage."),
    ("Fee Review", "High", "High sales-index product with elevated fee percentage."),
    ("Restock Review", "High", "High indexed unit movement with low inventory or restock priority."),
    ("Promotion Review", "Medium", "Promotion percentage is elevated while net-to-gross is below target."),
    ("Revenue Quality Review", "Medium", "Revenue quality score is weak for a product with measurable indexed demand."),
    ("Pricing Review", "Medium", "Low indexed demand for a higher-price-band listing."),
    ("Slow Mover Review", "Low", "Low indexed unit movement with high inventory band."),
]
MONITOR_ACTION = ("Monitor", "Low", "No action threshold triggered; continue monitoring.")


def recommended_action(row: pd.Series) -> tuple[str, str, str]:
    fee = float(row.get("fee_pct_of_gross", 0) or 0)
    refund = float(row.get("refund_pct_of_gross", 0) or 0)
    promo = float(row.get("promotion_pct_of_gross", 0) or 0)
    net = float(row.get("net_to_gross_pct", 0) or 0)
    sales = float(row.get("sales_index", 0) or 0)
    units = float(row.get("units_index", 0) or 0)
    margin_risk = float(row.get("margin_risk_score", 0) or 0)
    revenue_quality = float(row.get("revenue_quality_score", 100) or 0)
    inventory_band = str(row.get("inventory_band", "")).lower()
    listing_price_band = str(row.get("listing_price_band", "")).lower()
    restock_priority = str(row.get("restock_priority", "")).lower()

    high_price_band = (
        "premium" in listing_price_band
        or listing_price_band.startswith("3000")
        or listing_price_band.startswith("4000")
        or listing_price_band.endswith("+")
    )
    low_inventory = "out of stock" in inventory_band or "very low" in inventory_band or "low" in inventory_band
    high_inventory = "high" in inventory_band or "100+" in inventory_band

    if margin_risk >= 70:
        return "Margin Risk Review", "High", "Critical margin-risk score from fee, refund, promotion, net, and margin signals."
    if refund >= 10 and sales >= 10:
        return "Refund Review", "High", "Meaningful sales-index product with elevated refund percentage."
    if fee >= 25 and sales >= 20:
        return "Fee Review", "High", "High sales-index product with elevated fee percentage."
    if units >= 50 and (low_inventory or "high" in restock_priority):
        return "Restock Review", "High", "High indexed unit movement with low inventory or restock priority."
    if promo >= 10 and net < 70:
        return "Promotion Review", "Medium", "Promotion percentage is elevated while net-to-gross is below target."
    if revenue_quality < 45 and sales >= 15:
        return "Revenue Quality Review", "Medium", "Revenue quality score is weak for a product with measurable indexed demand."
    if sales < 10 and units < 10 and high_price_band:
        return "Pricing Review", "Medium", "Low indexed demand for a higher-price-band listing."
    if units < 10 and high_inventory:
        return "Slow Mover Review", "Low", "Low indexed unit movement with high inventory band."
    return "Monitor", "Low", "No action threshold triggered; continue monitoring."


def _numeric(df: pd.DataFrame, column: str, default: float) -> pd.Series:
    if column not in df.columns:
        return pd.Series(default, index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce")


def _lower_text(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series("", index=df.index, dtype="object")
    return df[column].astype("string").fillna("").str.lower()


def add_actions(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized equivalent of row-wise recommended_action() over the whole frame.

    Produces identical recommended_action / action_priority / action_reason values
    but avoids df.apply(axis=1), which is the slowest step on 141K-row inputs.
    """
    df = df.copy()
    if df.empty:
        df["recommended_action"] = pd.Series(dtype="object")
        df["action_priority"] = pd.Series(dtype="object")
        df["action_reason"] = pd.Series(dtype="object")
        return df

    fee = _numeric(df, "fee_pct_of_gross", 0.0)
    refund = _numeric(df, "refund_pct_of_gross", 0.0)
    promo = _numeric(df, "promotion_pct_of_gross", 0.0)
    net = _numeric(df, "net_to_gross_pct", 0.0)
    sales = _numeric(df, "sales_index", 0.0)
    units = _numeric(df, "units_index", 0.0)
    margin_risk = _numeric(df, "margin_risk_score", 0.0)
    revenue_quality = _numeric(df, "revenue_quality_score", 100.0)

    price_band = _lower_text(df, "listing_price_band")
    inventory_band = _lower_text(df, "inventory_band")
    restock_priority = _lower_text(df, "restock_priority")

    higher_price_band = (
        price_band.str.contains("premium", na=False)
        | price_band.str.startswith("3000", na=False)
        | price_band.str.startswith("4000", na=False)
        | price_band.str.endswith("+", na=False)
    )
    low_inventory = (
        inventory_band.str.contains("out of stock", na=False)
        | inventory_band.str.contains("very low", na=False)
        | inventory_band.str.contains("low", na=False)
    )
    high_inventory = inventory_band.str.contains("high", na=False) | inventory_band.str.contains("100+", regex=False, na=False)

    conditions = [
        margin_risk >= 70,
        (refund >= 10) & (sales >= 10),
        (fee >= 25) & (sales >= 20),
        (units >= 50) & (low_inventory | restock_priority.str.contains("high", na=False)),
        (promo >= 10) & (net < 70),
        (revenue_quality < 45) & (sales >= 15),
        (sales < 10) & (units < 10) & higher_price_band,
        (units < 10) & high_inventory,
    ]
    conditions = [cond.fillna(False).to_numpy() for cond in conditions]

    df["recommended_action"] = np.select(conditions, [rule[0] for rule in ACTION_RULES], default=MONITOR_ACTION[0])
    df["action_priority"] = np.select(conditions, [rule[1] for rule in ACTION_RULES], default=MONITOR_ACTION[1])
    df["action_reason"] = np.select(conditions, [rule[2] for rule in ACTION_RULES], default=MONITOR_ACTION[2])
    return df

