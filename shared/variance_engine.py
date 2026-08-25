"""Marketplace Performance Driver / Root-Cause engine.

This module implements deterministic, descriptive period-over-period
variance decomposition — NOT causal inference. Every public-facing string
this module produces uses "associated with" / "contributed to" language
rather than "caused by" (see docs/business_rules.md, rule set
"Variance / root-cause rules" and acceptance criteria AC-BR17-1).

The engine operates on already-aggregated "matrices" (one row per
period x dimension, with metric columns) rather than raw transaction rows,
so it has no dependency on private columns and is independently testable.
`shared/public_output_builder.py` is the only caller that feeds it
pipeline-derived matrices; tests feed it small hand-built DataFrames.
"""

from __future__ import annotations

import pandas as pd

# Headline metrics surfaced on the Performance Drivers & Root Cause page.
# Keys are the public column names as they appear in the aggregated marts
# built by shared/public_output_builder.aggregate_public().
METRIC_LABELS: dict[str, str] = {
    "sales_index": "Sales Index",
    "units_index": "Units Index",
    "fee_pct_of_gross": "Fee % of Gross",
    "refund_pct_of_gross": "Refund % of Gross",
    "promotion_pct_of_gross": "Promotion % of Gross",
    "net_to_gross_pct": "Net-to-Gross %",
    "margin_risk_score": "Margin Risk Score",
    "revenue_quality_score": "Revenue Quality Score",
    "estimated_profitability_index": "Estimated Profitability Index",
}

# Metrics where a numeric *increase* is a deterioration in business terms.
DETERIORATES_ON_INCREASE = {
    "fee_pct_of_gross",
    "refund_pct_of_gross",
    "promotion_pct_of_gross",
    "margin_risk_score",
}
# Metrics where a numeric *decrease* is a deterioration in business terms.
DETERIORATES_ON_DECREASE = {
    "sales_index",
    "units_index",
    "net_to_gross_pct",
    "revenue_quality_score",
    "estimated_profitability_index",
}

VARIANCE_COLUMNS = [
    "metric",
    "metric_label",
    "previous_value",
    "current_value",
    "abs_variance",
    "pct_variance",
    "contribution_share_pct",
    "movement",
]

UNKNOWN_PERIOD_VALUES = {"", "unknown", "nan", "none", "custom"}

# The column used to decide whether a calendar month has any recorded
# activity at all. This is checked at the OVERALL month level (summed
# across every dimension value present in the matrix passed in — e.g. every
# marketplace) — a period is never excluded merely because one marketplace
# or product within it happens to have zero activity (Requirement 4).
DEFAULT_ACTIVITY_COLUMN = "order_count"


def available_periods(matrix: pd.DataFrame, period_col: str = "transaction_month") -> list[str]:
    """Distinct, orderable period labels present in a matrix, excluding placeholders."""
    if matrix.empty or period_col not in matrix.columns:
        return []
    values = matrix[period_col].dropna().astype(str).unique().tolist()
    cleaned = [v for v in values if v.strip().lower() not in UNKNOWN_PERIOD_VALUES]
    return sorted(cleaned)


def period_activity_totals(
    matrix: pd.DataFrame,
    period_col: str = "transaction_month",
    activity_col: str = DEFAULT_ACTIVITY_COLUMN,
) -> dict[str, float]:
    """Aggregated activity_col total per period, summed across every
    dimension value present in `matrix` (e.g. every marketplace). Returns an
    empty dict when `activity_col` is not present in `matrix` at all — this
    is the signal callers use to fall back to "activity unknown" behavior
    rather than treating every period as inactive."""
    periods = available_periods(matrix, period_col)
    if activity_col not in matrix.columns:
        return {}
    totals: dict[str, float] = {}
    for period in periods:
        subset = matrix[matrix[period_col].astype(str) == str(period)]
        totals[period] = float(pd.to_numeric(subset[activity_col], errors="coerce").fillna(0.0).sum())
    return totals


def valid_activity_periods(
    matrix: pd.DataFrame,
    period_col: str = "transaction_month",
    activity_col: str = DEFAULT_ACTIVITY_COLUMN,
) -> list[str]:
    """Periods whose aggregated `activity_col` (default: order_count) sums
    to > 0 at the overall month level (Requirement 3).

    When `activity_col` is not present in `matrix` (e.g. a matrix built
    without an activity column), activity cannot be determined here, so
    every period is treated as valid — this preserves the prior "compare
    the two most recent distinct periods" behavior for callers/tests that
    do not carry activity information, while the real pipeline path always
    passes a marketplace-level matrix that does carry `order_count`.
    """
    periods = available_periods(matrix, period_col)
    if activity_col not in matrix.columns:
        return periods
    totals = period_activity_totals(matrix, period_col, activity_col)
    return [p for p in periods if totals.get(p, 0.0) > 0]


def excluded_trailing_periods(
    matrix: pd.DataFrame,
    period_col: str = "transaction_month",
    activity_col: str = DEFAULT_ACTIVITY_COLUMN,
) -> list[str]:
    """Periods that are chronologically AFTER the most recent valid period
    but were excluded from comparison because they have zero aggregated
    activity (Requirement 6/7) — e.g. an in-progress or not-yet-populated
    trailing month. This is informational, not an error condition
    (Requirement 8): the zero-activity month is never described as bad or
    invalid, only as unavailable for comparative analysis.

    A period earlier than the most recent valid period is never reported
    here even if it happens to have zero activity — only *trailing* gaps
    are surfaced, since those are the ones a viewer would otherwise wonder
    why the comparison "stopped short" of.
    """
    periods = available_periods(matrix, period_col)
    if not periods:
        return []
    valid = valid_activity_periods(matrix, period_col, activity_col)
    if not valid:
        return []
    newest_valid = max(valid)
    return sorted(p for p in periods if p not in valid and p > newest_valid)


def format_excluded_trailing_message(periods: list[str]) -> str:
    """Human-readable, non-judgmental info message for the periods returned
    by `excluded_trailing_periods` (Requirement 7). Returns "" when the
    list is empty so callers can use it directly as a falsy check."""
    if not periods:
        return ""
    if len(periods) == 1:
        return f"{periods[0]} was excluded from period comparison because it contains no transaction activity."
    joined = ", ".join(periods[:-1]) + f" and {periods[-1]}"
    return f"{joined} were excluded from period comparison because they contain no transaction activity."


def select_default_periods(
    matrix: pd.DataFrame,
    period_col: str = "transaction_month",
    activity_col: str = DEFAULT_ACTIVITY_COLUMN,
) -> tuple[str, str] | None:
    """Pick (previous, current) as the two most recent VALID ACTIVITY
    periods (Requirement 2/5) — i.e. the two most recent periods whose
    aggregated `activity_col` is > 0 at the overall month level. A trailing
    period with zero aggregated activity (e.g. 2026-07 in the demo dataset)
    is safely ignored rather than compared against (Requirement 6); it is
    never deleted or modified (Requirement 1) and never treated as an error
    (Requirement 8) — see `excluded_trailing_periods` for the informational
    list of skipped periods.

    Returns None when fewer than two valid periods exist — callers must not
    fabricate a comparison in that case (BR-16).
    """
    valid = valid_activity_periods(matrix, period_col, activity_col)
    if len(valid) < 2:
        return None
    return valid[-2], valid[-1]


def _safe_pct_variance(previous: float, current: float) -> float | None:
    if previous == 0 or pd.isna(previous):
        return None
    return (current - previous) / abs(previous) * 100.0


def _movement_label(metric: str, abs_variance: float) -> str:
    if abs(abs_variance) < 1e-9:
        return "No Change"
    increased = abs_variance > 0
    if metric in DETERIORATES_ON_INCREASE:
        return "Deterioration" if increased else "Improvement"
    if metric in DETERIORATES_ON_DECREASE:
        return "Improvement" if increased else "Deterioration"
    return "Increase" if increased else "Decrease"


def compare_periods(
    matrix: pd.DataFrame,
    dimension_cols: list[str],
    metric_cols: list[str],
    previous_period: str,
    current_period: str,
    period_col: str = "transaction_month",
) -> pd.DataFrame:
    """Long-format variance table: one row per (dimension combination, metric).

    Deterministic and side-effect free: calling this twice on identical
    inputs produces identical output (AC-BR15-1).
    """
    empty_columns = dimension_cols + VARIANCE_COLUMNS
    if matrix.empty or previous_period is None or current_period is None:
        return pd.DataFrame(columns=empty_columns)

    prev = matrix[matrix[period_col].astype(str) == str(previous_period)]
    curr = matrix[matrix[period_col].astype(str) == str(current_period)]
    if prev.empty and curr.empty:
        return pd.DataFrame(columns=empty_columns)

    records: list[pd.DataFrame] = []
    for metric in metric_cols:
        if metric not in matrix.columns:
            continue
        prev_slice = prev[dimension_cols + [metric]].rename(columns={metric: "previous_value"})
        curr_slice = curr[dimension_cols + [metric]].rename(columns={metric: "current_value"})
        merged = prev_slice.merge(curr_slice, on=dimension_cols, how="outer")
        merged["previous_value"] = pd.to_numeric(merged["previous_value"], errors="coerce").fillna(0.0)
        merged["current_value"] = pd.to_numeric(merged["current_value"], errors="coerce").fillna(0.0)
        merged["abs_variance"] = (merged["current_value"] - merged["previous_value"]).round(2)
        merged["pct_variance"] = merged.apply(
            lambda row: _safe_pct_variance(row["previous_value"], row["current_value"]), axis=1
        )
        merged["pct_variance"] = pd.to_numeric(merged["pct_variance"], errors="coerce").round(2)
        total_abs = float(merged["abs_variance"].abs().sum())
        merged["contribution_share_pct"] = (
            (merged["abs_variance"].abs() / total_abs * 100.0).round(1) if total_abs > 0 else 0.0
        )
        merged["movement"] = merged["abs_variance"].map(lambda v: _movement_label(metric, v))
        merged["metric"] = metric
        merged["metric_label"] = METRIC_LABELS.get(metric, metric)
        records.append(merged[dimension_cols + VARIANCE_COLUMNS])

    if not records:
        return pd.DataFrame(columns=empty_columns)
    return pd.concat(records, ignore_index=True)


def rank_contributors(variance_df: pd.DataFrame, metric: str, top_n: int = 5) -> pd.DataFrame:
    """Top-N dimension rows for one metric, ranked by absolute variance."""
    if variance_df.empty or "metric" not in variance_df.columns:
        return variance_df
    subset = variance_df[variance_df["metric"] == metric].copy()
    if subset.empty:
        return subset
    order = subset["abs_variance"].abs().sort_values(ascending=False).index
    return subset.loc[order].head(top_n).reset_index(drop=True)


def total_variance(variance_df: pd.DataFrame, metric: str) -> tuple[float, float | None]:
    """Overall (abs, pct) variance for a metric, summed/derived across all dimension rows."""
    if variance_df.empty or "metric" not in variance_df.columns:
        return 0.0, None
    subset = variance_df[variance_df["metric"] == metric]
    if subset.empty:
        return 0.0, None
    previous_total = float(subset["previous_value"].sum())
    current_total = float(subset["current_value"].sum())
    abs_total = round(current_total - previous_total, 2)
    pct_total = _safe_pct_variance(previous_total, current_total)
    return abs_total, (round(pct_total, 2) if pct_total is not None else None)


def generate_narrative(
    metric: str,
    total_abs_variance: float,
    total_pct_variance: float | None,
    top_contributors: pd.DataFrame,
    dimension_label_col: str,
    *,
    negligible_threshold: float = 0.05,
) -> str:
    """Deterministic, template-filled narrative sentence for one metric.

    Uses "associated with" / "the largest contributor" language, never
    causal language (AC-BR17-1). Returns an explicit no-driver sentence when
    movement is negligible or no contributors are available (AC-BR16-1).
    """
    metric_label = METRIC_LABELS.get(metric, metric)
    if top_contributors.empty or abs(total_abs_variance) < negligible_threshold:
        return (
            f"No meaningful driver identified for {metric_label}; period-over-period "
            f"movement was negligible."
        )

    movement = _movement_label(metric, total_abs_variance)
    direction_word = "increased" if total_abs_variance > 0 else "decreased"
    if total_pct_variance is None:
        pct_text = "an unquantified percentage change (previous period value was zero)"
    else:
        pct_text = f"{abs(total_pct_variance):.1f}%"

    top = top_contributors.iloc[0]
    contributor_name = top.get(dimension_label_col, "an unmapped segment")
    contributor_share = float(top.get("contribution_share_pct", 0.0))

    lead = (
        f"{metric_label} {direction_word} by {abs(total_abs_variance):.1f} points "
        f"({pct_text}) period-over-period, a {movement.lower()}."
    )
    detail = (
        f" {contributor_name} was associated with the largest share of this movement, "
        f"contributing {contributor_share:.1f}% of the total variance."
    )
    if len(top_contributors) > 1:
        second = top_contributors.iloc[1]
        second_name = second.get(dimension_label_col, "an unmapped segment")
        second_share = float(second.get("contribution_share_pct", 0.0))
        detail += f" {second_name} contributed a further {second_share:.1f}%."
    return lead + detail


def build_driver_summary(
    marketplace_matrix: pd.DataFrame,
    previous_period: str | None,
    current_period: str | None,
    headline_metrics: list[str] | None = None,
    *,
    dimension_label_col: str = "marketplace",
    excluded_trailing_periods_list: list[str] | None = None,
    activity_col: str = DEFAULT_ACTIVITY_COLUMN,
) -> pd.DataFrame:
    """One row per headline metric: overall variance + deterministic narrative.

    This is the `mart_performance_driver_summary` output. When periods are
    insufficient, returns a single explanatory row rather than an empty
    frame with no context (BR-16 applied at the summary level too).

    Every row also carries an `excluded_trailing_periods` column (a
    comma-joined string, "" when none) so the Streamlit page can surface
    the Requirement 7 informational message without recomputing period
    validity itself — `previous_period`/`current_period` here are always
    the same values `shared/public_output_builder.py` passed to
    `compare_periods` for the other two variance marts, so all three
    outputs stay consistent (Requirement 9/10).
    """
    headline_metrics = headline_metrics or [
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
    excluded_trailing_periods_list = excluded_trailing_periods_list or []
    excluded_joined = ", ".join(excluded_trailing_periods_list)
    excluded_note = format_excluded_trailing_message(excluded_trailing_periods_list)

    if previous_period is None or current_period is None:
        valid = valid_activity_periods(marketplace_matrix, "transaction_month", activity_col)
        if len(valid) == 1:
            narrative = (
                f"Only one transaction month with recorded activity is available ({valid[0]}); "
                "at least two are required for a period-over-period comparison."
            )
        elif len(valid) == 0:
            narrative = (
                "No transaction months with recorded activity are present in this dataset, "
                "so no period-over-period comparison is available."
            )
        else:
            narrative = (
                "Fewer than two distinct transaction months are present in this "
                "dataset, so no period-over-period comparison is available."
            )
        if excluded_note:
            narrative = f"{narrative} {excluded_note}"
        return pd.DataFrame(
            [
                {
                    "metric": "n/a",
                    "metric_label": "n/a",
                    "previous_period": "n/a",
                    "current_period": "n/a",
                    "total_abs_variance": None,
                    "total_pct_variance": None,
                    "movement": "Insufficient Periods",
                    "narrative": narrative,
                    "excluded_trailing_periods": excluded_joined,
                }
            ]
        )

    variance_df = compare_periods(
        marketplace_matrix,
        [dimension_label_col],
        headline_metrics,
        previous_period,
        current_period,
    )
    rows = []
    for metric in headline_metrics:
        abs_total, pct_total = total_variance(variance_df, metric)
        contributors = rank_contributors(variance_df, metric, top_n=3)
        narrative = generate_narrative(metric, abs_total, pct_total, contributors, dimension_label_col)
        rows.append(
            {
                "metric": metric,
                "metric_label": METRIC_LABELS.get(metric, metric),
                "previous_period": previous_period,
                "current_period": current_period,
                "total_abs_variance": abs_total,
                "total_pct_variance": pct_total,
                "movement": _movement_label(metric, abs_total),
                "narrative": narrative,
                "excluded_trailing_periods": excluded_joined,
            }
        )
    return pd.DataFrame(rows)
