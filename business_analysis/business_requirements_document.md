# Business Requirements Document

## Purpose

The system combines marketplace transactions with a product/cost master and produces privacy-safe reporting for performance, revenue quality, profitability, inventory, and action review.

## Users

The requirements use functional roles to organize reporting needs:

- marketplace operations: marketplace trends, fees, refunds, and actions;
- product analysis: product, brand, and category performance;
- inventory analysis: restock and slow-mover review;
- finance analysis: revenue quality, profitability signals, and margin risk;
- BI operations: validation, reconciliation, privacy, and traceability.

## Scope

- two-file upload with schema validation;
- normalization, SKU reconciliation, anonymization, and public-output generation;
- 17 analytical and validation CSV outputs;
- 9 Streamlit pages and an 8-page Power BI report;
- deterministic variance contribution analysis;
- rule-based product and inventory actions;
- a local exception queue and action log;
- Azure SQL dimensional storage and Microsoft Fabric medallion processing.

## Requirements summary

The catalog contains 25 requirements:

- BR-01–BR-05: marketplace performance and reconciliation;
- BR-06–BR-10: product, category, fees, profitability, and margin risk;
- BR-11–BR-13: inventory and action recommendations;
- BR-14–BR-17: variance analysis and descriptive narratives;
- BR-18–BR-22: contracts, quarantine, privacy, KPI metadata, and UAT;
- BR-23–BR-25: exception tracking, action history, and valid status transitions.

Detailed requirements are in [docs/business_requirements.md](../docs/business_requirements.md). Functional and non-functional views are in this directory.

## Data requirements

- Product/cost/channel master in Excel format.
- Marketplace transaction report in CSV format.
- Two upload contracts and six public-output contracts.
- Private identifiers and raw financial fields remain outside the public layer.
- Every public output passes schema, regression, and privacy controls appropriate to its use.

## Success criteria

- all automated tests and 33 UAT scenarios pass;
- the privacy scan returns zero content hits;
- the Azure SQL tables reconcile to their source DataFrames;
- Fabric Bronze reconciles 1,855 source rows to 1,855 target rows;
- requirements trace to code, outputs, tests, or UAT cases;
- invalid workflow transitions are rejected without changing the queue or log.

## Key constraints

Profitability metrics are directional estimates. Marketplace-channel enrichment remains unavailable while its mapping keys are incomplete. Variance analysis describes contribution and association.
