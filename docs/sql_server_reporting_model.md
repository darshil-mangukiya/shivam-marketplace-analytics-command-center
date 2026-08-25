# Azure SQL Reporting Model

The reporting warehouse runs on Azure SQL Database. Python reshapes privacy-safe public marts into dimensions and facts, then loads the tables transactionally.

```text
data/public/*.csv
        ↓
shared/sqlserver_star_schema.py
        ↓
4 dimensions + 4 facts + 2 audit tables
        ↓
shared/sqlserver_loader.py
        ↓
Azure SQL Database
        ↓
7 reporting views
```

## Tables

| Table | Grain | Source |
|---|---|---|
| `analytics.dim_product` | one row per `public_product_id` plus `Unknown` | `product_performance.csv` |
| `analytics.dim_marketplace` | one row per marketplace plus `Unknown` | marketplace marts |
| `analytics.dim_month` | one row per transaction month plus `Unknown` | `marketplace_summary.csv` |
| `analytics.dim_fulfillment` | one row per fulfillment type plus `Unknown` | `product_performance.csv` |
| `analytics.fact_marketplace_activity` | month × marketplace | `marketplace_summary.csv` |
| `analytics.fact_product_performance` | product × marketplace | `product_performance.csv` |
| `analytics.fact_inventory_action` | product × marketplace | `inventory_action_review.csv` |
| `analytics.fact_performance_variance` | previous month × current month × marketplace × metric | variance marts |
| `audit.audit_validation` | validation check | `validation_summary.csv` |
| `audit.audit_dataset_profile` | output profile row | `dataset_profile.csv` |

Product performance is aggregated across the selected dataset period, so its fact table carries `dataset_period` as an attribute and has no month foreign key.

## Keys and constraints

Distinct natural keys are sorted and assigned stable integer surrogate keys starting at 1. Key 0 is reserved for an `Unknown` dimension member. Unresolved fact keys map to that member so the row remains visible for reconciliation.

The deployed schema contains 10 primary keys, 9 foreign keys, 8 nonclustered indexes, and uniqueness constraints at each fact grain.

Marketplace-channel enrichment is unavailable while its source mapping keys are incomplete. `dim_marketplace.channel` therefore carries the constant value `Marketplace` and the warehouse remains at marketplace grain.

## Load process

1. `build_sqlserver_star_schema()` creates the 10 DataFrames and checks dimension uniqueness and fact foreign keys.
2. The loader clears tables in reverse dependency order, then loads dimensions, facts, and audit tables in dependency order.
3. Each table load runs in a transaction and reconciles the target row count to its source DataFrame.
4. Load errors roll back the active transaction and omit credentials from exception messages.

The loader supports Microsoft `mssql-python` and optional `pyodbc`. Connection settings come from environment variables listed in `.env.example`.

## Reporting views

`sql/sqlserver/05_create_views.sql` defines:

- `vw_marketplace_performance`
- `vw_product_performance`
- `vw_inventory_action`
- `vw_revenue_quality`
- `vw_margin_risk`
- `vw_performance_drivers`
- `vw_validation_summary`

## Validation result

The Azure SQL run loaded all 10 tables with zero row-count discrepancies and zero orphaned foreign keys. Duplicate-primary-key and invalid-foreign-key inserts were rejected by the database. Business totals reconciled to 120,000 orders, 760 product-performance rows, and 145 high-priority inventory actions.

See [Azure SQL runtime evidence](evidence/azure_sql_runtime_evidence.md), [reconciliation output](../artifacts/sql/azure_sql_reconciliation.csv), and [T-SQL scripts](../sql/sqlserver/).
