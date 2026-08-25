# Functional Requirements

Each functional requirement maps to implemented code and to a business
requirement in [`docs/business_requirements.md`](../docs/business_requirements.md).
FR-23–FR-27 map to workflow requirements BR-23–BR-25 in
[`business_requirements_document.md`](business_requirements_document.md).

| ID | Functional requirement | Implementation | Related BR |
|---|---|---|---|
| FR-01 | Accept a product/cost/channel master Excel upload and a marketplace transaction CSV upload | `app/utils/product_master_loader.py`, `app/streamlit_app.py` upload widgets | BR-18 |
| FR-02 | Detect the real header row/schema in a transaction export with a variable-length preamble | `app/utils/transaction_cleaner.py` (header/alias detection) | BR-18 |
| FR-03 | Normalize marketplace names, fulfillment types, and numeric financial fields | `app/utils/transaction_cleaner.py`, `python/pipeline_utils.py` | BR-02 |
| FR-04 | Reconcile transaction SKUs against the product master, mapping unmatched/blank SKUs to a `NON_PRODUCT_ACTIVITY` sentinel rather than dropping them | `app/utils/joiner.py` | BR-04 |
| FR-05 | Validate uploaded files against a declarative YAML contract as an additional gate after cleaning | `shared/contracts.py`, `contracts/*.yml` | BR-18 |
| FR-06 | Quarantine rejected/warned rows with safe metadata only, never raw cell values | `shared/quarantine.py` | BR-19 |
| FR-07 | Mask/anonymize all public output content (public product IDs, indexed metrics, no raw identifiers) | `app/utils/anonymizer.py`, `shared/privacy.py` | BR-20 |
| FR-08 | Compute marketplace-level and product-level KPIs (Sales/Units Index, fee/refund/promotion %, Revenue Quality Score, Margin Risk Score) | `shared/metrics.py`, `shared/profitability.py` | BR-01, BR-09, BR-10 |
| FR-09 | Generate 17 privacy-safe public analytical outputs | `shared/public_output_builder.py` | BR-04, BR-20 |
| FR-10 | Filter the Product, Brand & Category Intelligence page by marketplace and by product (public ID only) | `app/utils/filters.py`, Page 3 | BR-06 |
| FR-11 | Compute deterministic period-over-period variance and contribution share by marketplace and by product | `shared/variance_engine.py` | BR-14, BR-17 |
| FR-12 | Select active periods for comparison, excluding trailing zero-activity months, and report exclusions explicitly | `shared/variance_engine.py` (`select_default_periods`, `variance_excluded_trailing_periods`) | BR-16 |
| FR-13 | Generate an ordered set of recommended actions (Margin Risk Review, Refund Review, Fee Review, Restock Review, Promotion Review, Revenue Quality Review, Pricing Review, Slow Mover Review, Monitor) | `shared/recommendations.py` | BR-11, BR-12 |
| FR-14 | Surface a data-validation and privacy-check summary with pass/warn/fail rows | `shared/validation.py`, Page 7 | BR-04, BR-22 |
| FR-15 | Export the full public-output set as a downloadable ZIP | `app/utils/export_utils.py`, Page 8 | — |
| FR-16 | Run in Sample Demo mode against pre-generated public CSVs with no upload required | `app/utils/data_loader.py:build_demo_result` | — |
| FR-17 | Fail with a specific, non-misleading message on a structurally valid but zero-row transaction file | `app/utils/transaction_cleaner.py` (UAT-03) | BR-18 |
| FR-18 | Fail with a specific, non-traceback message on a non-CSV file renamed `.csv` | `app/utils/transaction_cleaner.py` (UAT-04) | BR-18 |
| FR-19 | Validate 6 declared public outputs against their contracts on every generation, failing closed on a reject-level violation | `shared/contracts.py:validate_public_outputs`, `app/utils/data_loader.py` | BR-18, BR-20 |
| FR-20 | Govern KPI alignment (presence, range, privacy classification, doc-reference) against `docs/kpi_catalog.md` | `shared/kpi_registry.py` | BR-21 |
| FR-21 | Reshape the flat public marts into a SQL-Server-compatible star schema with deterministic surrogate keys | `shared/sqlserver_star_schema.py` | — |
| FR-22 | Optionally load the star schema into SQL Server through an environment-configured loader | `shared/sqlserver_loader.py` | — |
| FR-23 | Represent a high-priority recommendation as a trackable exception with a lifecycle status | `shared/workflow.py`, `artifacts/workflow/exception_queue.json` | BR-23 |
| FR-24 | Record every status transition on an exception with reviewer persona, reason, and timestamp | `shared/workflow.py`, `artifacts/workflow/action_log.csv` | BR-24 |
| FR-25 | Reject an invalid or out-of-sequence status transition rather than silently applying it | `shared/workflow.py` | BR-25 |
| FR-26 | Regenerate the exception queue deterministically from the current `product_action_review`/`inventory_action_review` outputs | `shared/workflow.py:build_exception_queue` | BR-23 |
| FR-27 | Provide a local CLI entry point for the workflow build | `python/run_workflow.py` | BR-23 |
