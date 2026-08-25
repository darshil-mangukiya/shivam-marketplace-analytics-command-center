from __future__ import annotations

import numpy as np
import pandas as pd


def margin_risk_score(
    fee_pct_of_gross: pd.Series,
    refund_pct_of_gross: pd.Series,
    promotion_pct_of_gross: pd.Series,
    net_to_gross_pct: pd.Series,
    estimated_profit_margin_pct: pd.Series,
) -> pd.Series:
    fee = pd.to_numeric(fee_pct_of_gross, errors="coerce").fillna(0.0)
    refund = pd.to_numeric(refund_pct_of_gross, errors="coerce").fillna(0.0)
    promo = pd.to_numeric(promotion_pct_of_gross, errors="coerce").fillna(0.0)
    net = pd.to_numeric(net_to_gross_pct, errors="coerce").fillna(0.0)
    margin = pd.to_numeric(estimated_profit_margin_pct, errors="coerce").fillna(0.0)
    score = (
        fee * 0.35
        + refund * 0.25
        + promo * 0.15
        + np.maximum(0, 70 - net) * 0.15
        + np.maximum(0, 30 - margin) * 0.10
    )
    return pd.Series(score, index=fee.index).clip(lower=0, upper=100).round(1)


def revenue_quality_score(
    net_to_gross_pct: pd.Series,
    fee_pct_of_gross: pd.Series,
    refund_pct_of_gross: pd.Series,
    promotion_pct_of_gross: pd.Series,
) -> pd.Series:
    net = pd.to_numeric(net_to_gross_pct, errors="coerce").fillna(0.0)
    fee = pd.to_numeric(fee_pct_of_gross, errors="coerce").fillna(0.0)
    refund = pd.to_numeric(refund_pct_of_gross, errors="coerce").fillna(0.0)
    promo = pd.to_numeric(promotion_pct_of_gross, errors="coerce").fillna(0.0)
    score = net - fee * 0.30 - refund * 0.25 - promo * 0.15
    return pd.Series(score, index=net.index).clip(lower=0, upper=100).round(1)


def margin_risk_band(value: object) -> str:
    score = float(value or 0)
    if score >= 70:
        return "Critical Review"
    if score >= 45:
        return "High Risk"
    if score >= 25:
        return "Medium Risk"
    return "Low Risk"


def revenue_quality_band(value: object) -> str:
    score = float(value or 0)
    if score >= 80:
        return "Strong"
    if score >= 65:
        return "Healthy"
    if score >= 45:
        return "Watch"
    if score >= 25:
        return "At Risk"
    return "Critical"

