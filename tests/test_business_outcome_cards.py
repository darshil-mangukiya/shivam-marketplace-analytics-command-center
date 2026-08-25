from __future__ import annotations

import pandas as pd

from app.utils.business_outcomes import NOT_AVAILABLE, OUTCOME_LABELS, build_business_outcomes


def test_business_outcomes_use_public_safe_index_and_score_fields():
    outputs = {
        "marketplace_summary": pd.DataFrame({"marketplace": ["Amazon", "Website"], "sales_index": [70.0, 100.0]}),
        "product_performance": pd.DataFrame({"product_group": ["Hair Care", "Skin Care"], "sales_index": [40.0, 100.0]}),
        "marketplace_channel_performance": pd.DataFrame(
            {"channel": ["Marketplace", "Website"], "avg_revenue_quality_score": [72.0, 91.0]}
        ),
        "product_action_review": pd.DataFrame(
            {"recommended_action": ["Monitor", "Fee Review", "Fee Review", "Refund Review"]}
        ),
    }

    outcomes = build_business_outcomes(outputs)

    assert set(outcomes) == set(OUTCOME_LABELS)
    assert outcomes["Top Marketplace"] == "Website"
    assert outcomes["Top Product Group"] == "Skin Care"
    assert outcomes["Highest Review Area"] == "Fee Review"
    assert outcomes["Top Revenue Quality Segment"] == "Website"
    assert outcomes["Most Common Action"] == "Fee Review"


def test_business_outcomes_fall_back_when_data_is_missing():
    outcomes = build_business_outcomes({})

    assert all(value == NOT_AVAILABLE for value in outcomes.values())


def test_business_outcome_labels_do_not_reference_private_identifiers():
    private_terms = {"asin", "sku", "order", "postal", "title", "raw"}

    assert not any(term in label.lower() for label in OUTCOME_LABELS for term in private_terms)
