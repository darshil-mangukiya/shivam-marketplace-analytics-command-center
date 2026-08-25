# INC-001 — Zero-Activity Trailing Period Selected for Comparison

This defect was found during a dashboard walkthrough and is covered by regression tests.

## Impact

The Performance Drivers & Root Cause page compared the most recent two
calendar months by default. When the most recent month had
`total_orders = 0` (a not-yet-populated trailing period), the comparison
produced a fabricated "-100%" deterioration for every metric — a
misleading result that would erode trust in the whole root-cause feature.

## Detection

Caught by the project owner during a manual verification pass: they
inspected `marketplace_summary.csv` directly and noticed 2026-07 had
`total_orders = 0`, then compared that against what the Performance
Drivers page was showing.

## Root Cause

The default period-selection logic picked "the two most recent distinct
`transaction_month` values" without checking whether the most recent one
had any real activity.

## Fix

`shared/variance_engine.py:select_default_periods` now selects the two
most recent months with `order_count > 0`, explicitly excluding trailing
zero-activity periods rather than deleting the row or silently comparing
against it. Any excluded period is reported via
`excluded_trailing_periods` on `mart_performance_driver_summary.csv`, so
the exclusion is visible, not hidden.

## Regression Test

`tests/test_variance_engine.py` — covers period selection with a trailing
zero-activity month present, asserting it is excluded and reported.

## Prevention

- Business rule BR-16 was added, explicitly requiring "no fabricated
  comparison against an inactive period," transcribed in
  `docs/business_rules.md`.
- The fix pattern (exclude + report, never silently delete or compare) is
  now the documented standard for any future period-selection logic in
  this project.

## Evidence

- `shared/variance_engine.py` (`select_default_periods`,
  `variance_excluded_trailing_periods`)
- `tests/test_variance_engine.py`
- `docs/business_rules.md` BR-16
- `business_analysis/defect_log.csv` DEF-01
