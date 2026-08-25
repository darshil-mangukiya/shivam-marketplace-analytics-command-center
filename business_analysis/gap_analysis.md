# Gap Analysis

| Area | As-Is process | Target process | Implemented capability |
|---|---|---|---|
| Intake | Variable spreadsheet and export formats | Controlled two-file intake | Header normalization and YAML contracts |
| Rejected data | Manual deletion or failed workbook | Traceable rejection | Safe quarantine metadata |
| SKU matching | Spreadsheet lookups | Reconciled product mapping | Centralized join with unmatched counts |
| Metrics | Formulas repeated across files | Shared calculation logic | Metrics, profitability, KPI registry, and recommendation modules |
| Reporting | Separate marketplace files | Comparable analytical layer | 17 public outputs, Streamlit, and Power BI |
| Variance review | Manual comparisons | Repeatable contribution analysis | Marketplace and product variance marts |
| Actions | Static flags | Trackable status lifecycle | Local exception queue and action log |
| Data storage | Flat analytical files | Dimensional warehouse | Azure SQL dimensions, facts, views, keys, and indexes |
| Cloud processing | Single local batch path | Layered lake processing | Fabric Data Factory, OneLake, PySpark, and Delta tables |
| Quality | Manual spot checks | Repeatable release controls | pytest, contracts, privacy scan, UAT, CI, and reconciliation |

## Remaining gaps

- Marketplace-channel enrichment requires completed mapping keys.
- Eleven public outputs rely on schema, regression, and privacy tests without individual YAML contracts.
- The application has a single-user local execution model.
- Fabric and Azure SQL are separate from the CSV-backed reporting surfaces.
