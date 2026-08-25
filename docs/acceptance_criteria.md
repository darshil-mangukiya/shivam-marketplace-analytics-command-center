# Acceptance Criteria

Each business requirement (`docs/business_requirements.md`) has one or more
acceptance criteria below. Criteria are written to be testable — each maps to
a `test_reference` in `docs/requirements_traceability_matrix.csv` and/or a
`uat_id` in `docs/uat/uat_test_cases.csv`.

## Marketplace performance

- **AC-BR01-1**: Given ≥2 distinct `transaction_month` values in the loaded
  dataset, the Performance Drivers page shows a ranked list of marketplaces
  by absolute Sales Index variance, largest deterioration first.
- **AC-BR01-2**: Given <2 distinct months, the page shows an explicit
  "insufficient periods" message instead of a fabricated comparison.
- **AC-BR02-1**: Marketplace Performance page shows avg fee/refund/promotion
  % of gross per marketplace, sourced from `marketplace_summary.csv`.
- **AC-BR04-1**: Every KPI card value on Marketplace Performance is
  computed directly from a named column in `marketplace_channel_performance.csv`
  or `product_performance.csv` with no additional hidden transformation.
- **AC-BR05-1**: `validation_summary.csv` always contains a
  "Marketplace-channel mapping status" row whose value is `Unavailable`
  until mapping keys are populated and validated.

## Product / brand / category intelligence

- **AC-BR06-1**: Product, Brand & Category Intelligence page ranks products
  by `sales_index` descending, grouped by `brand_group`/`category_group`.
- **AC-BR07-1**: `fee_refund_summary.csv` flags `fee_review_flag = "Review"`
  when `fee_pct_of_gross ≥ 25` and `refund_review_flag = "Review"` when
  `refund_pct_of_gross ≥ 10`.
- **AC-BR08-1**: `mart_product_variance_contributors.csv` ranks products by
  contribution to Revenue Quality Score deterioration when ≥2 periods exist.
- **AC-BR09-1**: `margin_risk_review.csv` sorts by `margin_risk_score`
  descending.
- **AC-BR10-1**: UI and documentation use "Estimated Profitability Index"
  or "profitability signal" for the derived metric.

## Inventory

- **AC-BR11-1**: `inventory_action_review.csv` sets
  `recommended_action = "Restock Review"` only when
  `units_index ≥ 50 AND (low inventory OR high restock priority)`.
- **AC-BR12-1**: `recommended_action = "Slow Mover Review"` only when
  `units_index < 10 AND high inventory band`.
- **AC-BR13-1**: Every row with a non-"Monitor" `recommended_action` has a
  non-empty `action_reason`.

## Root cause / variance

- **AC-BR14-1**: For a selected metric and marketplace/product dimension,
  the Performance Drivers page shows previous value, current value, absolute
  variance, percentage variance, and ranked contributors.
- **AC-BR15-1**: Calling the variance engine twice on identical input
  produces byte-identical output (determinism test).
- **AC-BR16-1**: When all contributors have zero variance, the narrative
  states "No meaningful driver identified" rather than naming a contributor.
- **AC-BR17-1**: Narrative templates use "associated with" or
  "contributed to" for descriptive variance output.

## Data quality / governance

- **AC-BR18-1**: Uploading a file missing a required contract field produces
  a user-facing error naming the missing field, not a stack trace.
- **AC-BR19-1**: Rows that fail contract validation appear in the quarantine
  summary with `error_code`, `error_category`, and `severity`, and are
  excluded from the accepted-row count.
- **AC-BR20-1**: `assert_public_frame_is_safe` is called on every entry of
  `outputs` (including new variance marts) before they are stored in session
  state or exported.
- **AC-BR21-1**: Every KPI in `docs/kpi_catalog.md` has a formula that
  matches its implementation in `shared/metrics.py`,
  `shared/profitability.py`, or `shared/variance_engine.py` byte-for-byte in
  meaning (verified by manual cross-check at authoring time, recorded in
  `docs/evidence/`).
- **AC-BR22-1**: At least 25 UAT cases exist covering upload, demo, filters,
  validation, and export; each executed case records `actual_result` and
  `status`.

## Operational workflow

- **AC-BR23-1**: Given `product_action_review.csv` / `inventory_action_review.csv`
  rows with `action_priority` in `{High, Medium}`, when
  `shared.workflow.build_exception_queue` runs, then one exception record
  per flagged row appears with `status = "New"` and only privacy-safe
  fields.
- **AC-BR24-1**: Given an exception transitioned via
  `shared.workflow.transition_exception`, when the log row is appended,
  then `artifacts/workflow/action_log.csv` contains
  `previous_status`/`new_status`/`reviewer_persona`/`reason`/`timestamp`
  for that change, and prior rows are unchanged (append-only).
- **AC-BR25-1**: Given an exception in a status with no outgoing edge to
  the requested status in `VALID_TRANSITIONS` (including any transition
  out of the terminal `Closed` status), when
  `shared.workflow.transition_exception` is called, then it raises
  `WorkflowError` and no log row is written.

## Cross-cutting

- **AC-XC-1 (regression)**: The full pytest suite passes with zero failures.
- **AC-XC-2 (privacy)**: `python python/run_privacy_scan.py` reports
  `content_hit_count: 0` and `is_safe: true`.
