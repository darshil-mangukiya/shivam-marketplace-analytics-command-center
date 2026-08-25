# Azure SQL Runtime Record

## Environment

| Component | Value |
|---|---|
| Database engine | Azure SQL Database |
| Engine version | Microsoft SQL Azure 12.0.2000.8 |
| Client | Microsoft `mssql-python` |
| Loader | `shared/sqlserver_loader.py` |
| Schema scripts | `sql/sqlserver/` |

Credentials were supplied through local environment variables and are absent from tracked files and artifacts.

## Deployed objects

| Object type | Count |
|---|---:|
| Dimensions | 4 |
| Facts | 4 |
| Audit tables | 2 |
| Reporting views | 7 |
| Primary keys | 10 |
| Foreign keys | 9 |
| Nonclustered indexes | 8 |

The object counts were queried from Azure SQL system catalogs after deployment.

## Loaded rows

| Table | Rows |
|---|---:|
| `dim_product` | 153 |
| `dim_marketplace` | 6 |
| `dim_month` | 14 |
| `dim_fulfillment` | 3 |
| `fact_marketplace_activity` | 65 |
| `fact_product_performance` | 760 |
| `fact_inventory_action` | 760 |
| `fact_performance_variance` | 45 |
| `audit_validation` | 34 |
| `audit_dataset_profile` | 15 |
| **Total** | **1,855** |

Each source DataFrame reconciled to its target table with difference 0. The checked-in [reconciliation CSV](../../artifacts/sql/azure_sql_reconciliation.csv) contains the per-table results.

## Integrity checks

- Foreign-key validation returned 0 orphaned fact rows.
- A duplicate primary-key insert was rejected.
- An invalid foreign-key insert was rejected.
- Two complete loads returned identical row counts.
- Query totals matched 120,000 orders, 760 product-performance rows, and 145 high-priority inventory actions.

## Loader corrections from runtime execution

Azure SQL rejects `TRUNCATE TABLE` for dimensions referenced by foreign keys. The loader now clears all tables in reverse dependency order and falls back to `DELETE` when truncation is unavailable.

Database parameter binding also exposed missing-value handling that required conversion from pandas `NaN` values to SQL `NULL`. Both behaviors have regression coverage in `tests/test_sqlserver_loader.py`.

Analytical query timing was measured on tables of at most 760 rows. The results describe this dataset size.
