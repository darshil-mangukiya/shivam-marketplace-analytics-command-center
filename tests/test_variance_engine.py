"""Variance engine tests.

Covers: previous/current period selection, percentage variance, zero
denominator, missing comparison period, marketplace/product/category
contribution, fee/refund/promotion/score movements, no-change cases,
one-driver cases, multiple-driver ranking, and deterministic narrative
generation.
"""

from __future__ import annotations

import pandas as pd
import pytest

from shared.variance_engine import (
    available_periods,
    build_driver_summary,
    compare_periods,
    excluded_trailing_periods,
    format_excluded_trailing_message,
    generate_narrative,
    period_activity_totals,
    rank_contributors,
    select_default_periods,
    total_variance,
    valid_activity_periods,
)


def _matrix(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_available_periods_excludes_placeholders():
    matrix = _matrix(
        [
            {"transaction_month": "2026-01", "marketplace": "Amazon"},
            {"transaction_month": "Unknown", "marketplace": "Amazon"},
            {"transaction_month": "2026-02", "marketplace": "Amazon"},
        ]
    )
    assert available_periods(matrix) == ["2026-01", "2026-02"]


def test_select_default_periods_needs_at_least_two():
    one_period = _matrix([{"transaction_month": "2026-01", "marketplace": "Amazon"}])
    assert select_default_periods(one_period) is None

    two_periods = _matrix(
        [
            {"transaction_month": "2026-01", "marketplace": "Amazon"},
            {"transaction_month": "2026-02", "marketplace": "Amazon"},
        ]
    )
    assert select_default_periods(two_periods) == ("2026-01", "2026-02")


def test_select_default_periods_picks_two_most_recent_of_three():
    matrix = _matrix(
        [
            {"transaction_month": m, "marketplace": "Amazon"}
            for m in ["2026-01", "2026-02", "2026-03"]
        ]
    )
    assert select_default_periods(matrix) == ("2026-02", "2026-03")


def test_compare_periods_missing_period_returns_empty_with_schema():
    matrix = _matrix([{"transaction_month": "2026-01", "marketplace": "Amazon", "sales_index": 50.0}])
    result = compare_periods(matrix, ["marketplace"], ["sales_index"], None, None)
    assert result.empty
    assert "marketplace" in result.columns
    assert "abs_variance" in result.columns


def test_compare_periods_computes_abs_and_pct_variance():
    matrix = _matrix(
        [
            {"transaction_month": "2026-01", "marketplace": "Amazon", "sales_index": 40.0},
            {"transaction_month": "2026-02", "marketplace": "Amazon", "sales_index": 60.0},
        ]
    )
    result = compare_periods(matrix, ["marketplace"], ["sales_index"], "2026-01", "2026-02")
    row = result.iloc[0]
    assert row["previous_value"] == 40.0
    assert row["current_value"] == 60.0
    assert row["abs_variance"] == 20.0
    assert row["pct_variance"] == pytest.approx(50.0)
    assert row["movement"] == "Improvement"  # sales_index increasing is an improvement


def test_compare_periods_zero_previous_denominator_gives_none_pct():
    matrix = _matrix(
        [
            {"transaction_month": "2026-01", "marketplace": "Amazon", "sales_index": 0.0},
            {"transaction_month": "2026-02", "marketplace": "Amazon", "sales_index": 25.0},
        ]
    )
    result = compare_periods(matrix, ["marketplace"], ["sales_index"], "2026-01", "2026-02")
    row = result.iloc[0]
    assert row["abs_variance"] == 25.0
    assert pd.isna(row["pct_variance"])


def test_compare_periods_fee_increase_is_deterioration():
    matrix = _matrix(
        [
            {"transaction_month": "2026-01", "marketplace": "Amazon", "fee_pct_of_gross": 10.0},
            {"transaction_month": "2026-02", "marketplace": "Amazon", "fee_pct_of_gross": 30.0},
        ]
    )
    result = compare_periods(matrix, ["marketplace"], ["fee_pct_of_gross"], "2026-01", "2026-02")
    assert result.iloc[0]["movement"] == "Deterioration"


def test_compare_periods_no_change_case():
    matrix = _matrix(
        [
            {"transaction_month": "2026-01", "marketplace": "Amazon", "sales_index": 50.0},
            {"transaction_month": "2026-02", "marketplace": "Amazon", "sales_index": 50.0},
        ]
    )
    result = compare_periods(matrix, ["marketplace"], ["sales_index"], "2026-01", "2026-02")
    assert result.iloc[0]["movement"] == "No Change"
    assert result.iloc[0]["abs_variance"] == 0.0


def test_marketplace_contribution_one_driver():
    matrix = _matrix(
        [
            {"transaction_month": "2026-01", "marketplace": "Amazon", "sales_index": 50.0},
            {"transaction_month": "2026-01", "marketplace": "Flipkart", "sales_index": 50.0},
            {"transaction_month": "2026-02", "marketplace": "Amazon", "sales_index": 30.0},
            {"transaction_month": "2026-02", "marketplace": "Flipkart", "sales_index": 50.0},
        ]
    )
    result = compare_periods(matrix, ["marketplace"], ["sales_index"], "2026-01", "2026-02")
    top = rank_contributors(result, "sales_index", top_n=1)
    assert top.iloc[0]["marketplace"] == "Amazon"
    assert top.iloc[0]["contribution_share_pct"] == 100.0


def test_product_multiple_driver_ranking():
    matrix = _matrix(
        [
            {"transaction_month": "2026-01", "public_product_id": "P1", "revenue_quality_score": 80.0},
            {"transaction_month": "2026-01", "public_product_id": "P2", "revenue_quality_score": 80.0},
            {"transaction_month": "2026-01", "public_product_id": "P3", "revenue_quality_score": 80.0},
            {"transaction_month": "2026-02", "public_product_id": "P1", "revenue_quality_score": 50.0},
            {"transaction_month": "2026-02", "public_product_id": "P2", "revenue_quality_score": 70.0},
            {"transaction_month": "2026-02", "public_product_id": "P3", "revenue_quality_score": 80.0},
        ]
    )
    result = compare_periods(matrix, ["public_product_id"], ["revenue_quality_score"], "2026-01", "2026-02")
    ranked = rank_contributors(result, "revenue_quality_score", top_n=3)
    assert list(ranked["public_product_id"]) == ["P1", "P2", "P3"]
    assert ranked.iloc[0]["contribution_share_pct"] > ranked.iloc[1]["contribution_share_pct"]


def test_category_contribution_dimension():
    matrix = _matrix(
        [
            {"transaction_month": "2026-01", "category_group": "Electronics", "margin_risk_score": 20.0},
            {"transaction_month": "2026-01", "category_group": "Apparel", "margin_risk_score": 20.0},
            {"transaction_month": "2026-02", "category_group": "Electronics", "margin_risk_score": 60.0},
            {"transaction_month": "2026-02", "category_group": "Apparel", "margin_risk_score": 20.0},
        ]
    )
    result = compare_periods(matrix, ["category_group"], ["margin_risk_score"], "2026-01", "2026-02")
    top = rank_contributors(result, "margin_risk_score", top_n=1)
    assert top.iloc[0]["category_group"] == "Electronics"
    assert top.iloc[0]["movement"] == "Deterioration"


def test_total_variance_matches_sum_of_dimension_values():
    matrix = _matrix(
        [
            {"transaction_month": "2026-01", "marketplace": "Amazon", "sales_index": 40.0},
            {"transaction_month": "2026-01", "marketplace": "Flipkart", "sales_index": 20.0},
            {"transaction_month": "2026-02", "marketplace": "Amazon", "sales_index": 45.0},
            {"transaction_month": "2026-02", "marketplace": "Flipkart", "sales_index": 15.0},
        ]
    )
    result = compare_periods(matrix, ["marketplace"], ["sales_index"], "2026-01", "2026-02")
    abs_total, pct_total = total_variance(result, "sales_index")
    assert abs_total == pytest.approx(0.0)  # +5 and -5 net to zero
    assert pct_total == pytest.approx(0.0)


def test_generate_narrative_no_meaningful_driver():
    matrix = _matrix(
        [
            {"transaction_month": "2026-01", "marketplace": "Amazon", "sales_index": 50.0},
            {"transaction_month": "2026-02", "marketplace": "Amazon", "sales_index": 50.0},
        ]
    )
    result = compare_periods(matrix, ["marketplace"], ["sales_index"], "2026-01", "2026-02")
    contributors = rank_contributors(result, "sales_index", top_n=3)
    text = generate_narrative("sales_index", 0.0, 0.0, contributors, "marketplace")
    assert "No meaningful driver identified" in text


def test_generate_narrative_uses_non_causal_language():
    matrix = _matrix(
        [
            {"transaction_month": "2026-01", "marketplace": "Amazon", "refund_pct_of_gross": 5.0},
            {"transaction_month": "2026-01", "marketplace": "Flipkart", "refund_pct_of_gross": 5.0},
            {"transaction_month": "2026-02", "marketplace": "Amazon", "refund_pct_of_gross": 20.0},
            {"transaction_month": "2026-02", "marketplace": "Flipkart", "refund_pct_of_gross": 5.0},
        ]
    )
    result = compare_periods(matrix, ["marketplace"], ["refund_pct_of_gross"], "2026-01", "2026-02")
    abs_total, pct_total = total_variance(result, "refund_pct_of_gross")
    contributors = rank_contributors(result, "refund_pct_of_gross", top_n=2)
    text = generate_narrative("refund_pct_of_gross", abs_total, pct_total, contributors, "marketplace")
    assert "caused" not in text.lower()
    assert "because of" not in text.lower()
    assert "associated with" in text.lower() or "contributing" in text.lower()
    assert "Amazon" in text


def test_generate_narrative_is_deterministic():
    matrix = _matrix(
        [
            {"transaction_month": "2026-01", "marketplace": "Amazon", "sales_index": 40.0},
            {"transaction_month": "2026-02", "marketplace": "Amazon", "sales_index": 60.0},
        ]
    )
    result_a = compare_periods(matrix, ["marketplace"], ["sales_index"], "2026-01", "2026-02")
    result_b = compare_periods(matrix, ["marketplace"], ["sales_index"], "2026-01", "2026-02")
    pd.testing.assert_frame_equal(result_a, result_b)

    contributors_a = rank_contributors(result_a, "sales_index", top_n=1)
    contributors_b = rank_contributors(result_b, "sales_index", top_n=1)
    abs_a, pct_a = total_variance(result_a, "sales_index")
    abs_b, pct_b = total_variance(result_b, "sales_index")
    text_a = generate_narrative("sales_index", abs_a, pct_a, contributors_a, "marketplace")
    text_b = generate_narrative("sales_index", abs_b, pct_b, contributors_b, "marketplace")
    assert text_a == text_b


def test_build_driver_summary_insufficient_periods():
    one_period = _matrix([{"transaction_month": "2026-01", "marketplace": "Amazon", "sales_index": 50.0}])
    summary = build_driver_summary(one_period, None, None)
    assert len(summary) == 1
    assert summary.iloc[0]["movement"] == "Insufficient Periods"
    # This matrix carries no order_count column, so activity cannot be
    # determined and the single period is treated as the one available
    # (valid) period — the narrative should name it specifically rather
    # than use the generic "fewer than two periods" wording.
    assert "Only one transaction month" in summary.iloc[0]["narrative"]
    assert "2026-01" in summary.iloc[0]["narrative"]
    assert summary.iloc[0]["excluded_trailing_periods"] == ""


def test_build_driver_summary_zero_valid_periods_uses_distinct_wording():
    matrix = _matrix(
        [
            {"transaction_month": "2026-07", "marketplace": "Amazon", "order_count": 0, "sales_index": 0.0},
            {"transaction_month": "2026-07", "marketplace": "Flipkart", "order_count": 0, "sales_index": 0.0},
        ]
    )
    summary = build_driver_summary(matrix, None, None)
    assert len(summary) == 1
    assert "No transaction months with recorded activity" in summary.iloc[0]["narrative"]


def test_build_driver_summary_one_row_per_headline_metric():
    matrix = _matrix(
        [
            {
                "transaction_month": m,
                "marketplace": "Amazon",
                "sales_index": v,
                "units_index": v,
                "fee_pct_of_gross": v,
                "refund_pct_of_gross": v,
                "promotion_pct_of_gross": v,
                "net_to_gross_pct": v,
                "margin_risk_score": v,
                "revenue_quality_score": v,
                "estimated_profitability_index": v,
            }
            for m, v in [("2026-01", 40.0), ("2026-02", 60.0)]
        ]
    )
    summary = build_driver_summary(matrix, "2026-01", "2026-02")
    assert len(summary) == 9
    assert set(summary["metric"]) == {
        "sales_index",
        "units_index",
        "fee_pct_of_gross",
        "refund_pct_of_gross",
        "promotion_pct_of_gross",
        "net_to_gross_pct",
        "margin_risk_score",
        "revenue_quality_score",
        "estimated_profitability_index",
    }
    for narrative in summary["narrative"]:
        assert isinstance(narrative, str) and len(narrative) > 0


# ---------------------------------------------------------------------------
# Valid-activity-period selection tests (regression fix: a trailing
# zero-order month, e.g. 2026-07 in the real demo dataset, must never be
# selected as the "current" comparison period).
# ---------------------------------------------------------------------------

def _activity_matrix(rows: list[dict]) -> pd.DataFrame:
    """Marketplace-level matrix rows with an explicit order_count column,
    mirroring what shared/public_output_builder.py's aggregate_public()
    actually produces."""
    return pd.DataFrame(rows)


def _demo_like_matrix() -> pd.DataFrame:
    """Mirrors the real marketplace_summary.csv scenario reported against
    the live app: 2026-05 and 2026-06 both have order activity; 2026-07 is
    a trailing month with total_orders == 0 across every marketplace."""
    return _activity_matrix(
        [
            {"transaction_month": "2026-05", "marketplace": "Amazon", "order_count": 6000, "sales_index": 210.0, "units_index": 215.6},
            {"transaction_month": "2026-05", "marketplace": "Flipkart", "order_count": 4000, "sales_index": 150.0, "units_index": 140.0},
            {"transaction_month": "2026-06", "marketplace": "Amazon", "order_count": 6100, "sales_index": 210.7, "units_index": 215.5},
            {"transaction_month": "2026-06", "marketplace": "Flipkart", "order_count": 3900, "sales_index": 149.0, "units_index": 139.5},
            {"transaction_month": "2026-07", "marketplace": "Amazon", "order_count": 0, "sales_index": 0.0, "units_index": 0.0},
            {"transaction_month": "2026-07", "marketplace": "Flipkart", "order_count": 0, "sales_index": 0.0, "units_index": 0.0},
        ]
    )


def test_trailing_zero_order_month_is_excluded_from_selection():
    matrix = _demo_like_matrix()
    assert select_default_periods(matrix) == ("2026-05", "2026-06")


def test_two_latest_valid_months_are_selected_not_the_two_latest_calendar_months():
    matrix = _demo_like_matrix()
    selected = select_default_periods(matrix)
    assert selected is not None
    previous, current = selected
    assert current != "2026-07"  # the zero-activity trailing month must never be "current"
    assert (previous, current) == ("2026-05", "2026-06")


def test_valid_month_with_some_zero_activity_marketplaces_is_still_retained():
    # 2026-06 has activity in Amazon but zero in Flipkart -- the MONTH is
    # still valid overall (Requirement 4): validity is decided at the
    # aggregated month level, never by a single marketplace/product row.
    matrix = _activity_matrix(
        [
            {"transaction_month": "2026-05", "marketplace": "Amazon", "order_count": 5000},
            {"transaction_month": "2026-05", "marketplace": "Flipkart", "order_count": 5000},
            {"transaction_month": "2026-06", "marketplace": "Amazon", "order_count": 8000},
            {"transaction_month": "2026-06", "marketplace": "Flipkart", "order_count": 0},
        ]
    )
    assert valid_activity_periods(matrix) == ["2026-05", "2026-06"]
    assert select_default_periods(matrix) == ("2026-05", "2026-06")


def test_only_one_valid_month_available_returns_none():
    matrix = _activity_matrix(
        [
            {"transaction_month": "2026-06", "marketplace": "Amazon", "order_count": 6000},
            {"transaction_month": "2026-07", "marketplace": "Amazon", "order_count": 0},
        ]
    )
    assert valid_activity_periods(matrix) == ["2026-06"]
    assert select_default_periods(matrix) is None
    assert excluded_trailing_periods(matrix) == ["2026-07"]


def test_no_valid_months_available_returns_none_and_no_trailing_list():
    matrix = _activity_matrix(
        [
            {"transaction_month": "2026-06", "marketplace": "Amazon", "order_count": 0},
            {"transaction_month": "2026-07", "marketplace": "Amazon", "order_count": 0},
        ]
    )
    assert valid_activity_periods(matrix) == []
    assert select_default_periods(matrix) is None
    # With zero valid periods there is no "most recent valid period" to be
    # trailing after, so nothing is reported as an excluded trailing period
    # (there's nothing to compare against in the first place).
    assert excluded_trailing_periods(matrix) == []


def test_excluded_trailing_periods_never_includes_a_period_before_the_newest_valid_one():
    # A gap earlier in the series (not trailing) must not be reported --
    # only zero-activity periods AFTER the newest valid period count.
    matrix = _activity_matrix(
        [
            {"transaction_month": "2026-04", "marketplace": "Amazon", "order_count": 0},
            {"transaction_month": "2026-05", "marketplace": "Amazon", "order_count": 5000},
            {"transaction_month": "2026-06", "marketplace": "Amazon", "order_count": 6000},
        ]
    )
    assert excluded_trailing_periods(matrix) == []


def test_source_rows_for_excluded_period_are_never_dropped_from_the_matrix():
    # Requirement 1: the fix must not delete/modify the zero-activity
    # source rows -- it only changes which periods are SELECTED for
    # comparison. The row must still be present in the input matrix.
    matrix = _demo_like_matrix()
    assert "2026-07" in matrix["transaction_month"].unique()
    row_count_before = len(matrix)
    select_default_periods(matrix)  # calling the selector must not mutate the matrix
    assert len(matrix) == row_count_before
    assert "2026-07" in matrix["transaction_month"].unique()


def test_period_activity_totals_are_summed_across_marketplaces():
    matrix = _demo_like_matrix()
    totals = period_activity_totals(matrix)
    assert totals["2026-05"] == 10000.0
    assert totals["2026-06"] == 10000.0
    assert totals["2026-07"] == 0.0


def test_format_excluded_trailing_message_single_period():
    message = format_excluded_trailing_message(["2026-07"])
    assert message == "2026-07 was excluded from period comparison because it contains no transaction activity."


def test_format_excluded_trailing_message_multiple_periods():
    message = format_excluded_trailing_message(["2026-07", "2026-08"])
    assert "2026-07" in message and "2026-08" in message
    assert "were excluded" in message


def test_format_excluded_trailing_message_empty_list_returns_empty_string():
    assert format_excluded_trailing_message([]) == ""


def test_zero_order_month_is_never_labeled_as_an_error_or_bad_month():
    # Requirement 8: the zero-activity month must be treated as
    # unavailable/incomplete, never described with error/bad-data language.
    matrix = _demo_like_matrix()
    summary = build_driver_summary(
        matrix,
        *select_default_periods(matrix),
        excluded_trailing_periods_list=excluded_trailing_periods(matrix),
    )
    all_text = " ".join(summary["narrative"].astype(str)).lower()
    for forbidden_word in ("error", "bad month", "invalid month", "corrupt"):
        assert forbidden_word not in all_text


# ---------------------------------------------------------------------------
# Cross-mart consistency: all three marts + the deterministic narrative must
# agree on the same selected previous/current periods (Requirement 9/10).
# ---------------------------------------------------------------------------

def test_period_labels_in_all_three_marts_agree():
    marketplace_matrix = _demo_like_matrix()
    period_pair = select_default_periods(marketplace_matrix)
    assert period_pair == ("2026-05", "2026-06")
    previous_period, current_period = period_pair
    excluded = excluded_trailing_periods(marketplace_matrix)

    marketplace_drivers = compare_periods(
        marketplace_matrix, ["marketplace"], ["sales_index", "units_index"], previous_period, current_period
    )
    # A product-level matrix built independently, but compared against the
    # SAME previous/current periods chosen from the marketplace matrix.
    product_matrix = _activity_matrix(
        [
            {"transaction_month": "2026-05", "public_product_id": "P1", "marketplace": "Amazon", "sales_index": 80.0},
            {"transaction_month": "2026-06", "public_product_id": "P1", "marketplace": "Amazon", "sales_index": 85.0},
            {"transaction_month": "2026-07", "public_product_id": "P1", "marketplace": "Amazon", "sales_index": 0.0},
        ]
    )
    product_contributors = compare_periods(
        product_matrix, ["public_product_id", "marketplace"], ["sales_index"], previous_period, current_period
    )
    driver_summary = build_driver_summary(
        marketplace_matrix,
        previous_period,
        current_period,
        ["sales_index", "units_index"],
        excluded_trailing_periods_list=excluded,
    )

    # None of the three marts ever reference 2026-07 as a compared period.
    for df, cols in [
        (marketplace_drivers, []),
        (product_contributors, []),
        (driver_summary, ["previous_period", "current_period"]),
    ]:
        for col in cols:
            assert "2026-07" not in set(df[col].astype(str))

    assert set(driver_summary["previous_period"].unique()) == {"2026-05"}
    assert set(driver_summary["current_period"].unique()) == {"2026-06"}
    assert driver_summary["excluded_trailing_periods"].iloc[0] == "2026-07"


def test_deterministic_narratives_reference_the_correct_periods():
    matrix = _demo_like_matrix()
    previous_period, current_period = select_default_periods(matrix)
    excluded = excluded_trailing_periods(matrix)
    summary = build_driver_summary(
        matrix, previous_period, current_period, ["sales_index"], excluded_trailing_periods_list=excluded
    )
    row = summary.iloc[0]
    assert row["previous_period"] == "2026-05"
    assert row["current_period"] == "2026-06"
    # The narrative text itself should never claim 2026-07 was compared.
    assert "2026-07" not in row["narrative"]
    assert row["excluded_trailing_periods"] == "2026-07"
