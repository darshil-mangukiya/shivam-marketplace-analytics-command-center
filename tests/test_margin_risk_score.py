import pandas as pd

from shared.profitability import margin_risk_band, margin_risk_score, revenue_quality_band, revenue_quality_score


def test_margin_risk_score_is_normalized():
    score = margin_risk_score(
        pd.Series([40.0]),
        pd.Series([15.0]),
        pd.Series([10.0]),
        pd.Series([50.0]),
        pd.Series([5.0]),
    )
    assert score.iloc[0] > 0
    assert score.iloc[0] <= 100
    assert margin_risk_band(score.iloc[0]) in {"Low Risk", "Medium Risk", "High Risk", "Critical Review"}


def test_revenue_quality_score_is_normalized():
    score = revenue_quality_score(pd.Series([80.0]), pd.Series([10.0]), pd.Series([5.0]), pd.Series([3.0]))
    assert score.iloc[0] <= 100
    assert revenue_quality_band(score.iloc[0]) in {"Strong", "Healthy", "Watch", "At Risk", "Critical"}

