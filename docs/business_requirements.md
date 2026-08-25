# Business Requirements

Requirements are grouped by the reporting role that uses each output. Every requirement ID maps to source fields, transformations, interfaces, and tests in `requirements_traceability_matrix.csv`.

## Marketplace performance

- **BR-01:** Rank marketplace performance changes between active periods.
- **BR-02:** Compare fee, refund, and promotion percentages by marketplace.
- **BR-03:** Show order and indexed sales trends without exposing raw financial values.
- **BR-04:** Reconcile dashboard metrics to named public-output columns.
- **BR-05:** Show marketplace-channel enrichment as `Unavailable` while mapping keys are incomplete.

## Product, brand, and category analysis

- **BR-06:** Rank public products within brand and category groupings.
- **BR-07:** Flag products with elevated fee or refund ratios.
- **BR-08:** Rank product contributions to revenue-quality movement.
- **BR-09:** Identify products with elevated Margin Risk Score.
- **BR-10:** Label profitability metrics as estimates.

## Inventory

- **BR-11:** Identify restock-review candidates from unit velocity and inventory bands.
- **BR-12:** Identify slow movers with low indexed demand and high inventory.
- **BR-13:** Show the rule and supporting metrics for each recommendation.

## Variance analysis

- **BR-14:** Decompose period-over-period changes by marketplace and product contribution.
- **BR-15:** Produce deterministic output and narrative text.
- **BR-16:** Return an explicit no-driver result when movement has no meaningful contributor.
- **BR-17:** Use descriptive contribution language.

## Data quality

- **BR-18:** Validate uploads against YAML contracts and return specific errors.
- **BR-19:** Record rejected rows with safe reason metadata.
- **BR-20:** Run column and content privacy scans before UI display or export.
- **BR-21:** Maintain KPI metadata aligned with implementation fields and ranges.
- **BR-22:** Maintain UAT for upload, demo, filter, export, and validation workflows.

## Action workflow

- **BR-23:** Convert high- and medium-priority recommendations into stable exception records.
- **BR-24:** Append every accepted status change to an action log.
- **BR-25:** Reject status changes outside the declared transition table.
