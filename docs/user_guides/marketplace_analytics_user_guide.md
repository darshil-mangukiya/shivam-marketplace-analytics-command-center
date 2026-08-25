# Marketplace Analytics User Guide

## Getting started

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

The app opens with **Sample Demo** mode active — no files required. To
analyze your own data, use the **Upload Analysis** option in the sidebar
and provide:

1. A product/cost/channel master Excel workbook.
2. A marketplace transaction export CSV.

## What each page shows

1. **Executive Overview** — headline KPIs and a business-facing summary.
2. **Marketplace Performance** — per-marketplace Sales Index, Units Index,
   fee/refund/promotion % of gross.
3. **Product, Brand & Category Intelligence** — product ranking with
   Marketplace and Product filters.
4. **Fees, Refunds & Revenue Quality** — cost-burden and revenue-quality
   flags.
5. **Profitability & Margin Intelligence** — estimated profitability
   signal and margin-risk scoring (estimated, not audited).
6. **Inventory, Restock & Action Review** — recommended actions ranked by
   priority.
7. **Data Validation & Privacy Checks** — the validation summary and
   privacy-scan status for the current run.
8. **Demo & Export Center** — download the full public-output set as a
   ZIP.
9. **Performance Drivers & Root Cause** — deterministic period-over-period
   variance and contributor ranking.

## Understanding an "Unavailable" mapping status

`channel_mapping_status = "Unavailable"` means the current dataset has
incomplete marketplace-channel mapping keys.

## Understanding "estimated" profitability

Every profitability-related number in this app is explicitly labeled
**estimated** — a directional signal built from fee/refund/promotion-
adjusted ratios, not audited accounting profit. Do not use it as a
substitute for real financial reporting.

## Tracking a flagged exception

High/Medium-priority recommendations on Page 6 can be tracked through a
status lifecycle using the local workflow layer:

```bash
python python/run_workflow.py
```

This builds/refreshes `artifacts/workflow/exception_queue.json`. See
[`docs/sop/inventory_action_review.md`](../sop/inventory_action_review.md)
for the full procedure, and
[`artifacts/workflow/README.md`](../../artifacts/workflow/README.md) for
the honesty statement about what this workflow does and does not
represent.

## If something goes wrong

See [`docs/sop/failed_refresh_triage.md`](../sop/failed_refresh_triage.md).

## Where the numbers come from

Every KPI traces back to a named source field and business rule — see
[`docs/kpi_catalog.md`](../kpi_catalog.md) and
[`docs/bi/kpi_metric_lineage.md`](../bi/kpi_metric_lineage.md).
