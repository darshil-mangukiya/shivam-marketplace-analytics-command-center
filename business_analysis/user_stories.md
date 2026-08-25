# User Stories & Acceptance Criteria

Each story maps to an existing business requirement, and — wherever one
already exists — to a real automated test and/or UAT case, instead of
inventing new coverage. Personas are modeled (see
[`business_requirements_document.md`](business_requirements_document.md)).

## Marketplace performance

**US-01.** As a Marketplace Operations Manager, I want marketplaces ranked
by deteriorating Sales Index and Revenue Quality Score, so that I know
where to focus attention first.
- *Given* ≥2 distinct transaction months in the dataset, *when* I open
  Performance Drivers & Root Cause, *then* I see marketplaces ranked by
  absolute variance, largest deterioration first. (AC-BR01-1;
  `tests/test_variance_engine.py`; UAT-27)

**US-02.** As a Marketplace Operations Manager, I want to compare fee,
refund, and promotion percentage of gross across marketplaces, so that I
can spot channels with disproportionate cost burden.
- *Given* a loaded dataset, *when* I open Marketplace Performance, *then*
  I see fee/refund/promotion % of gross per marketplace from
  `marketplace_summary.csv`. (AC-BR02-1)

**US-03.** As a BI Manager, I want the marketplace-channel mapping status
to always read "Unavailable" unless real mapping keys exist, so that the
dashboard never overstates join coverage.
- *Given* incomplete `Marketplace_Channel_Master` keys, *when* any output
  is generated, *then* `channel_mapping_status` is `"Unavailable"` and
  `marketplace_join_coverage_pct` is `0.0`. (AC-BR05-1; `tests/test_public_outputs.py`)

## Product, brand & category intelligence

**US-04.** As an E-Commerce Manager, I want products ranked by Sales Index
within brand/category groupings, so that I can identify top and
underperforming listings.
- *Given* a loaded dataset, *when* I open Product, Brand & Category
  Intelligence, *then* products are ranked descending by `sales_index`,
  grouped by `brand_group`/`category_group`. (AC-BR06-1)

**US-05.** As an E-Commerce Manager, I want to filter product performance
by marketplace and by a specific public product ID, so that I can
investigate a single channel or listing without scanning the full table.
- *Given* the Product, Brand & Category Intelligence page, *when* I select
  a marketplace and/or a product ID filter, *then* the table and charts
  update to only that subset. (UAT-09, UAT-11; `tests/test_dashboard_filters.py`)

## Fees, refunds & profitability

**US-06.** As a Finance Analyst, I want products with elevated fee or
refund percentage flagged for review, so that I can investigate margin
erosion before it compounds.
- *Given* `fee_pct_of_gross ≥ 25` or `refund_pct_of_gross ≥ 10` with
  sufficient sales index, *when* fee_refund_summary is generated, *then*
  the row is flagged `"Review"`. (AC-BR07-1)

**US-07.** As a Finance Analyst, I want an estimated profitability signal
per product, clearly labeled as an estimate, so that I can prioritize
margin conversations without mistaking it for audited profit.
- *Given* the profitability output, *when* I view it, *then* every label
  and doc reference calls it an "estimated" signal, never "profit." (BR-10)

## Inventory & action review

**US-08.** As an Inventory Planner, I want restock-priority products
identified from low inventory band + high units index, so that I can
prevent stockouts.
- *Given* `units_index ≥ 50` and (low inventory OR high restock
  priority), *when* inventory_action_review is generated, *then* the
  product is flagged `Restock Review`, `High` priority. (BR-11;
  `tests/test_kpi_registry.py` alignment check)

**US-09.** As an Operations Director, I want a high-priority
recommendation to become a trackable exception with a status, so that I
can track it through review and closure.
- *Given* a `product_action_review`/`inventory_action_review` row with
  `action_priority = "High"`, *when* the workflow build runs, *then* an
  exception with status `New` appears in `artifacts/workflow/exception_queue.json`.
  (BR-23; `tests/test_workflow.py`)

**US-10.** As an Operations Director, I want every status change on an
exception recorded with who changed it and why, so that I have an audit
trail of decision activity.
- *Given* an exception in status `New`, *when* a reviewer persona
  transitions it to `Under Review` with a reason, *then* a row is appended
  to `artifacts/workflow/action_log.csv` with `previous_status`,
  `new_status`, `reviewer_persona`, `reason`, `timestamp`. (BR-24;
  `tests/test_workflow.py`)

**US-11.** As an Operations Director, I want an invalid status transition
(e.g. `Closed` → `New` directly) rejected, so that the audit trail can't be
corrupted by a bad update.
- *Given* an exception in status `Closed`, *when* a caller attempts to set
  it to `New` directly, *then* the workflow module raises a controlled
  error and no log row is written. (BR-25; `tests/test_workflow.py`)

## Root-cause / variance analysis

**US-12.** As a Data Analyst, I want period-over-period variance explained
without fabricated causal language, so that stakeholders don't
over-interpret a correlation as a cause.
- *Given* a variance mart, *when* the narrative sentence is generated,
  *then* it is template-filled from the top contributor row only — no
  free-text generation. (BR-15; `tests/test_variance_engine.py`)

**US-13.** As a Data Analyst, I want trailing zero-activity months
excluded from comparison rather than compared against, so that a
not-yet-populated month doesn't produce a fabricated "-100%" result.
- *Given* a trailing month with `order_count = 0`, *when* the default
  comparison period is selected, *then* that month is excluded and
  reported via `excluded_trailing_periods`, not silently deleted or
  compared. (BR-16; `tests/test_variance_engine.py`; UAT-27, UAT-28)

## Data quality, contracts & privacy

**US-14.** As a BI Manager, I want uploaded files validated against a
formal contract, so that bad files fail gracefully instead of corrupting
downstream KPIs.
- *Given* a file missing a required field, *when* it is uploaded, *then*
  the row is rejected with a specific, actionable error, and rejected rows
  never reach the accepted dataset. (BR-18; `tests/test_contract_integration.py`)

**US-15.** As a BI Manager, I want rows that fail validation quarantined
with safe metadata, not silently dropped, so that I know what happened to
missing rows without exposing private values.
- *Given* a rejected row, *when* it is quarantined, *then* the ledger
  contains only `source_name, row_number, error_code, error_category,
  validation_rule, reason, severity, timestamp` — never the raw cell
  value. (BR-19; `tests/test_quarantine.py`)

**US-16.** As a BI Manager, I want every declared public-output contract
to actually execute on every generation, so that a schema-drift bug is
caught before publication, not after.
- *Given* a generated public output with a declared contract, *when* the
  pipeline runs, *then* it is validated and, on any reject-level
  violation, the export stops. (BR-18, BR-20; `tests/test_contract_integration.py`)

**US-17.** As a user uploading a structurally valid file with zero data
rows, I want a specific "no transaction rows" message, not a misleading
date-parse error, so that I know exactly what to fix.
- *Given* a valid header with zero data rows, *when* uploaded, *then* the
  error names the actual problem. (UAT-03)

**US-18.** As a user accidentally uploading a non-CSV file renamed
`.csv`, I want a clear rejection message, not a traceback.
- *Given* a binary file renamed `.csv`, *when* uploaded, *then* the app
  shows "does not contain recognizable marketplace transaction columns."
  (UAT-04)

## KPI governance & reporting

**US-19.** As a BI Manager, I want every governed KPI's output column
verified present in its claimed public outputs with values in its
declared range, so that documentation cannot silently drift from
behavior.
- *Given* the KPI registry, *when* it runs against real public outputs,
  *then* presence, range, and privacy classification all pass. (BR-21;
  `tests/test_kpi_registry.py`)

**US-20.** As any user, I want to export the full public-output set as a
ZIP, so that I can use the data outside the app.
- *Given* a completed analysis run, *when* I click export, *then* a ZIP
  containing all public outputs downloads. (Page 8)

**US-21.** As a first-time visitor, I want to explore the app with
pre-generated Sample Demo data with zero setup, so that I can evaluate the
project without owning marketplace data myself.
- *Given* no uploaded files, *when* I open the app, *then* Sample Demo
  mode loads 17 public outputs from `data/public/`. (`build_demo_result`)

## Release / governance

**US-22.** As a BI Manager, I want a documented release gate (tests,
contracts, privacy, UAT) before I consider the project ready for a public
repository audit, so that nothing regresses silently.
- *Given* a candidate release, *when* the gate checklist runs, *then*
  every item (pytest, contracts, privacy scan, public schema, critical
  UAT) is explicitly PASS/FAIL. (`docs/bi/release_governance.md`)

**US-23.** As a new team member, I want a concise SOP for triaging a
failed refresh, so that I don't have to read the entire codebase to
respond to a broken run.
- *Given* a pipeline error, *when* I follow
  `docs/sop/failed_refresh_triage.md`, *then* I can identify whether it's
  an upload-contract failure, a public-output contract failure, or a
  privacy-scan failure, and what to check next.
