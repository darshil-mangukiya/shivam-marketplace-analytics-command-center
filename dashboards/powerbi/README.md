# Power BI Report

`Shivam_Multi_Marketplace_Analytics_Command_Center.pbix` is an 8-page Power BI Desktop report over six public CSV outputs.

## Pages

1. Executive Overview
2. Marketplace Performance
3. Product & Category Intelligence
4. Fees, Refunds & Promotions
5. Estimated Profitability
6. Inventory Health
7. Action Center & Recommendations
8. Data Validation & Privacy

The report contains 26 documented DAX measures. Page definitions are in [dashboard_spec.md](dashboard_spec.md); model details are in [data_model.md](data_model.md); formulas are in [dax_measures.md](dax_measures.md).

## Imported data

| CSV | Use |
|---|---|
| `anonymized_master.csv` | monthly marketplace activity and grouped attributes |
| `product_performance.csv` | product, brand, category, fee, refund, and score metrics |
| `marketplace_summary.csv` | monthly marketplace KPIs |
| `inventory_action_review.csv` | inventory actions and priority |
| `validation_summary.csv` | validation status |
| `dataset_profile.csv` | selected dataset label and row counts |

The model uses public product IDs, grouped attributes, indexes, ratios, scores, and bands. Marketplace-channel enrichment is unavailable while the source mapping keys are incomplete.

Estimated profitability is a directional signal derived from the available cost, fee, refund, promotion, and revenue-quality fields.

## Refresh

1. Place the six public CSVs under `data/public/`.
2. Open the PBIX in Power BI Desktop.
3. Update the source folder if the repository path changed.
4. Refresh all queries.
5. Confirm the validation page and headline totals.

The current PBIX reads the CSV layer. The Azure SQL and Fabric implementations are separate data-platform paths.

## Screenshots

| Page | File |
|---|---|
| Executive Overview | [01_executive_overview.png](screenshots/01_executive_overview.png) |
| Marketplace Performance | [02_marketplace_performance.png](screenshots/02_marketplace_performance.png) |
| Product & Category Intelligence | [03_product_category_intelligence.png](screenshots/03_product_category_intelligence.png) |
| Fees, Refunds & Promotions | [04_fees_refunds_promotions.png](screenshots/04_fees_refunds_promotions.png) |
| Estimated Profitability | [05_estimated_profitability.png](screenshots/05_estimated_profitability.png) |
| Inventory Health | [06_inventory_health.png](screenshots/06_inventory_health.png) |
| Action Center | [07_action_center_recommendations.png](screenshots/07_action_center_recommendations.png) |
