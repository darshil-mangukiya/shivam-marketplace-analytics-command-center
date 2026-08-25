# Enterprise BI Standards

Standards used by the Streamlit and Power BI reporting surfaces.

## Naming conventions

- **Public columns**: `snake_case`, descriptive of the business concept
  (`sales_index`, `fee_pct_of_gross`, `action_priority`) — never an
  internal code abbreviation.
- **KPI names** (display): Title Case ("Sales Index", "Revenue Quality
  Score"), consistent between `docs/kpi_catalog.md`, Streamlit page
  labels, and Power BI measure names.
- **Public output files**: `snake_case.csv`, named after the business
  entity/grain they represent (`marketplace_summary.csv`,
  `product_performance.csv`), never a generic `output1.csv`.

## Metric formatting

- Indexes: 0–100, one decimal place, suffixed "Index" in display.
- Percentages (fee/refund/promotion/net-to-gross): shown as `%`, clipped
  to a documented range (`[0, 300]`, or `[-300, 300]` for signed net %) —
  never displayed unclipped, since an unclipped ratio on a near-zero
  denominator is misleading, not informative.
- Scores (Margin Risk, Revenue Quality): 0–100, one decimal, always paired
  with a categorical band (e.g. "High Risk") so a raw number is never
  shown without its business interpretation.

## Date/time handling

- All financial data is aggregated to **month grain** (`transaction_month`)
  for reporting — no exact-timestamp value is ever published (privacy and
  aggregation-integrity reasons both apply).
- Period comparisons always state both periods being compared and
  explicitly report any trailing zero-activity period excluded, rather
  than silently comparing against it.

## Dimensions / facts

- Public CSVs are wide, denormalized marts by design (matching how
  Streamlit and Power BI both consume them directly) for the CSV-mode
  reporting path.
- A separate dimensional model runs on Azure SQL Database
  (`shared/sqlserver_star_schema.py`, `sql/sqlserver/`) with deterministic
  surrogate keys and an Unknown member (key = 0).

## Report navigation

- Streamlit: 9 pages, ordered by analytical narrative (Executive Overview
  → Marketplace → Product → Fees/Refunds → Profitability → Inventory →
  Validation → Export → Root Cause), each independently navigable via the
  sidebar.
- Power BI: 8 pages over six public CSVs, documented in
  `dashboards/powerbi/dashboard_spec.md`.

## Filters

- Every filterable page exposes filters using **public-safe values only**
  (marketplace name, public product ID) — never a raw SKU/ASIN as a filter
  option.
- Filters are additive (AND, not OR) and always show the current filtered
  row count so a user knows whether a filter combination returned zero
  rows versus simply narrowed the view.

## Data freshness

- The app displays which mode produced the current view (`Sample Demo` vs
  `Upload Analysis`) and, for uploads, the detected `dataset_period` — a
  user is never left guessing whether they're looking at demo or real
  uploaded data.

## Accessibility

- All charts use Streamlit's built-in accessible chart components (no
  color-only encoding without a label); tables include column headers
  readable by screen readers via Streamlit's native table rendering.
- No information is conveyed by color alone without a text label (e.g.
  action priority is always shown as text — "High"/"Medium"/"Low" — not
  only as a colored cell).

## Testing

- Every public output has at least one automated test verifying its
  schema/columns; every KPI is checked for presence, range, and privacy
  classification by the KPI governance registry
  (`shared/kpi_registry.py`).
- No dashboard page is considered "done" without a corresponding UAT case
  (see `docs/uat/`).

## Privacy

- See [`governance/business_glossary.md`](../../governance/business_glossary.md)
  and `shared/privacy.py` — every public output passes a full-frame
  content scan (ASIN/order-ID/postal/currency-marker shaped values) before
  it can reach any BI surface.

## Release requirements

See [`release_governance.md`](release_governance.md) for the full gate
definition.

## Documentation standards

- Every business rule is transcribed from, and cites, the exact
  implementing file/function (`docs/business_rules.md`) — documentation
  is never allowed to describe behavior the code doesn't actually have.
- Every requirement traces to a test (`docs/requirements_traceability_matrix.csv`).
