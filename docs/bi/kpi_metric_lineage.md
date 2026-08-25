# KPI / Metric Lineage

This table links each metric from source to calculation, output, report, and test.

| Metric | Source | Normalized Field | Calculation | Business Rule | Public Output | Dashboard | Validation/Test |
|---|---|---|---|---|---|---|---|
| Sales Index | Transaction `product_sales` etc. | `gross_sales_private` (private) | `shared/metrics.py:index_from_values` | Ratio/index rules (`docs/business_rules.md`) | `marketplace_summary.csv`, `product_performance.csv` | Streamlit Pages 1–3, 9; Power BI Pages 1–3 | `tests/test_metrics.py`, `tests/test_kpi_registry.py` |
| Units Index | Transaction `quantity` | `units_private` (private) | `shared/metrics.py:index_from_values` | Ratio/index rules | `marketplace_summary.csv`, `product_performance.csv`, `inventory_action_review.csv` | Streamlit Pages 2, 3, 6, 9 | `tests/test_metrics.py`, `tests/test_kpi_registry.py` |
| Fee % of Gross | Transaction `selling_fees`/`fba_fees`/`other_transaction_fees` | fee amount (private) | `shared/metrics.py:pct_of_gross` | Ratio/index rules; Fee Review rule (`shared/recommendations.py`) | `marketplace_summary.csv`, `fee_refund_summary.csv`, `product_performance.csv` | Streamlit Page 4, 9 | `tests/test_metrics.py`, `tests/test_public_outputs.py` |
| Refund % of Gross | Transaction refund-type rows | refund amount (private) | `shared/metrics.py:pct_of_gross` | Ratio/index rules; Refund Review rule | `fee_refund_summary.csv`, `product_performance.csv` | Streamlit Page 4, 9 | `tests/test_metrics.py` |
| Promotion % of Gross | Transaction `promotional_rebates` | promotion amount (private) | `shared/metrics.py:pct_of_gross` | Ratio/index rules; Promotion Review rule | `fee_refund_summary.csv`, `product_performance.csv` | Streamlit Page 4 | `tests/test_metrics.py` |
| Net-to-Gross % | All revenue/fee/refund/promotion fields | net amount (private) | `shared/metrics.py:pct_of_gross (signed=True)` | Ratio/index rules | `product_performance.csv` | Streamlit Page 4, 5 | `tests/test_metrics.py` |
| Revenue Quality Score | Fee/refund/promotion/net % | n/a (computed from public ratios) | `shared/profitability.py:revenue_quality_score` | Score rules | `product_performance.csv`, `marketplace_channel_performance.csv` | Streamlit Page 4, 5; `app/utils/business_outcomes.py` executive summary | `tests/test_profitability.py` |
| Margin Risk Score | Fee/refund/promotion/net/margin % | n/a (computed from public ratios) | `shared/profitability.py:margin_risk_score` | Score rules; Margin Risk Review rule | `product_performance.csv`, `margin_risk_review.csv` | Streamlit Page 5, 6 | `tests/test_profitability.py` |
| Restock Review (action) | `units_index`, `inventory_band` | n/a (categorical) | `shared/recommendations.py:ACTION_RULES` rule #4 | Recommendation rules | `product_action_review.csv`, `inventory_action_review.csv` | Streamlit Page 6 | `tests/test_recommendations.py` |
| High Priority Action | `action_priority` on any recommendation | n/a (categorical) | `shared/recommendations.py:add_actions` | Recommendation rules | `product_action_review.csv`, `inventory_action_review.csv` | Streamlit Page 6; `artifacts/workflow/exception_queue.json` | `tests/test_recommendations.py`, `tests/test_workflow.py` |
| Marketplace variance (Sales Index, etc.) | `marketplace_summary` matrix, two periods | n/a (computed) | `shared/variance_engine.py:compare_periods` | Variance/root-cause rules (BR-14–17) | `mart_marketplace_variance_drivers.csv`, `mart_performance_driver_summary.csv` | Streamlit Page 9 | `tests/test_variance_engine.py` |
| Product variance (contribution share) | Product-level matrix, two periods | n/a (computed) | `shared/variance_engine.py:compare_periods` | Variance/root-cause rules | `mart_product_variance_contributors.csv` | Streamlit Page 9 | `tests/test_variance_engine.py` |

## Governance note

`shared/kpi_registry.py` automates the presence/range/privacy-classification
checks for the rows above that are KPIs (not the workflow-status row, which
is categorical and not range-bound). This lineage document is the
BI-governance-facing companion — it exists to answer "where does this
number come from, all the way back to source" in one place, without
duplicating the formula source of truth.
