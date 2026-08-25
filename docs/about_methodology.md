# Methodology

## Processing path

```text
Upload → Validate → Clean → Join → Anonymize → Analyze → Validate → Export
```

The application accepts a product/cost/channel workbook and a marketplace transaction CSV. YAML contracts validate file structure. Cleaning normalizes headers, marketplace names, dates, fulfillment types, and numeric fields. SKU reconciliation retains non-product settlement activity and records unmatched counts.

## Public analytical layer

Public outputs use `public_product_id`, grouped attributes, bands, indexes, ratios, and scores. The privacy layer checks column names and every cell before frames reach the application or export code.

Metric formulas are centralized in [kpi_catalog.md](kpi_catalog.md) and [business_rules.md](business_rules.md). Eight ordered recommendation rules assign an action and priority using the public analytical fields.

## Variance analysis

The variance engine compares the two latest active periods, calculates marketplace and product contributions, and creates deterministic descriptive narratives. It reports insufficient-period and zero-contribution conditions explicitly.

## Reporting and storage

- Streamlit: 9-page local application.
- Power BI Desktop: 8-page report over six public CSVs.
- Azure SQL Database: dimensional warehouse over the public marts.
- Microsoft Fabric: Data Factory ingestion into Bronze, Silver, and Gold Delta tables.

## Metric interpretation

Indexes are relative to the selected dataset. Profitability measures are directional estimates. Marketplace-channel enrichment remains unavailable while mapping keys are incomplete.
