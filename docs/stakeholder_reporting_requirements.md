# Reporting Requirements by Role

These role-based requirements organize the implemented reports and review cadence.

| Role | Reporting need | Cadence | Interface or output |
|---|---|---|---|
| Marketplace operations | Marketplace ranking and period movement | Monthly | Streamlit Marketplace Performance; `marketplace_summary.csv` |
| Marketplace operations | Fee, refund, and promotion pressure | Monthly | Revenue Quality page; `fee_refund_summary.csv` |
| Product analysis | Product, brand, and category ranking | Monthly | Product Intelligence; product, brand, and category CSVs |
| Product analysis | Product variance contributors | Monthly | Performance Drivers; `mart_product_variance_contributors.csv` |
| Inventory analysis | Restock and slow-mover priorities | Weekly | Inventory page; `inventory_action_review.csv` |
| Finance analysis | Estimated profitability and margin risk | Monthly | Profitability page; profitability and margin-risk CSVs |
| BI operations | Validation and privacy status | Every run | Validation page; `validation_summary.csv` |
| BI operations | Requirements and UAT status | Per release | traceability matrix and UAT results |

Reports use public product IDs, grouped attributes, indexes, ratios, scores, and bands. Metric definitions are in [kpi_catalog.md](kpi_catalog.md), and output fields are in [data_dictionary.md](data_dictionary.md).
