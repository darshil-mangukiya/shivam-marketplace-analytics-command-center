# SQL Reference

The seven top-level queries mirror analytics from the public CSV layer using portable SQL. They select public IDs, grouped dimensions, indexes, ratios, scores, and bands.

| File | Analysis |
|---|---|
| `01_marketplace_performance.sql` | marketplace performance |
| `02_product_performance.sql` | product performance |
| `03_fee_refund_promotion_analysis.sql` | revenue-quality ratios |
| `04_profitability_signals.sql` | profitability and margin-risk signals |
| `05_inventory_action_review.sql` | inventory actions |
| `06_product_action_review.sql` | product actions |
| `07_validation_summary.sql` | validation results |

Marketplace-channel enrichment is unavailable while mapping keys are incomplete, so these queries operate at marketplace grain.

`sql/sqlserver/` contains the Azure SQL dimensional schema, views, indexes, reconciliation, performance, and validation scripts. See [Azure SQL Reporting Model](../docs/sql_server_reporting_model.md).
