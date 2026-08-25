# Microsoft Fabric Runtime Record

## Environment

| Component | Name |
|---|---|
| Capacity | Fabric Trial |
| Workspace | `P8-Marketplace-Analytics` |
| Lakehouse | `P8_Marketplace_Lakehouse` |
| Copy Job | `CopyJob_1` |
| Pipeline | `PL_AzureSQL_to_OneLake` |
| Notebook | `NB_Silver_Gold_Transform` |

Fabric Data Factory connects to the Azure SQL dimensional warehouse and writes to OneLake.

## Bronze ingestion

The Copy Job loads all 10 physical Azure SQL tables using overwrite semantics.

| Result | Count |
|---|---:|
| Sources selected | 10 |
| Sources succeeded | 10 |
| Azure SQL rows read | 1,855 |
| Bronze rows written | 1,855 |
| Row difference | 0 |

Two Copy Job runs produced identical per-table counts. Details are stored in [fabric_reconciliation.csv](../../artifacts/fabric/fabric_reconciliation.csv) and [fabric_run_summary.csv](../../artifacts/fabric/fabric_run_summary.csv).

## Silver conformance

The PySpark notebook reads the 10 Bronze tables, trims string fields, validates table keys, removes duplicate keys if encountered, adds lineage columns, and writes 10 Silver Delta tables. The validated run found 0 null keys and 0 duplicate-key drops.

## Gold tables

| Table | Rows | Purpose |
|---|---:|---|
| `gold_marketplace_performance` | 65 | marketplace and month performance |
| `gold_product_performance` | 760 | product-level metrics and actions |
| `gold_inventory_actions` | 760 | inventory review priorities |
| `gold_variance_drivers` | 45 | marketplace variance contributions |
| `gold_validation_summary` | 34 | data-quality results |

Gold selects existing metric, score, and recommendation fields from the conformed data. Metric formulas remain centralized in the Python analytical layer.

## Delta validation

All 25 Bronze, Silver, and Gold tables passed `DeltaTable.isDeltaTable()` validation. The notebook also inspected a multi-version Delta transaction history for `bronze_dim_product`.

## Reconciliation

Notebook checks returned:

- 120,000 total orders;
- 6 stored marketplace dimension values: five marketplaces plus `Unknown`;
- 145 high-priority product actions;
- 760 Gold product-performance rows.

## Retry and recovery

A controlled run referenced the nonexistent table `audit.audit_validation_NONEXISTENT_TEST`. The activity returned SQL error 208, and the configured retry repeated the failure. After restoring the source to `audit.audit_validation`, the next run succeeded with 34 rows, matching the baseline.

| Pipeline run | Status | Rows |
|---|---|---:|
| Baseline | Succeeded | 34 |
| Invalid source | Failed | — |
| Configured retry | Failed | — |
| Corrected source | Succeeded | 34 |

Bronze, the corrected pipeline run, and the Silver/Gold notebook each produced the same counts on repetition.

## Screenshots

| File | Content |
|---|---|
| [Workspace overview](screenshots/fabric/10_fabric_workspace_overview.png) | Fabric items in the workspace |
| [Bronze ingestion](screenshots/fabric/11_fabric_bronze_ingestion_success.png) | 10 successful copies and row counts |
| [Silver conformance](screenshots/fabric/12_fabric_silver_conformance.png) | key and duplicate checks |
| [Gold tables](screenshots/fabric/13_fabric_gold_curated_tables.png) | Gold row counts |
| [Delta validation](screenshots/fabric/14_fabric_delta_validation.png) | 25 Delta tables and transaction history |
| [Business reconciliation](screenshots/fabric/15_fabric_business_reconciliation.png) | order, marketplace, action, and product totals |
| [Retry and recovery](screenshots/fabric/16_fabric_failure_retry_recovery.png) | baseline, failure, and corrected run history |
