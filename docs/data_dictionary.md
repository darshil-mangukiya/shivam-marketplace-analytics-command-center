# Data Dictionary — Public Outputs

Covers every column of the two most structurally important public datasets
(`anonymized_master.csv` and `mart_marketplace_variance_drivers.csv`) plus a
summary table of all 17 public outputs. Full per-field detail for the two
upload types and 6 representative public outputs is also captured formally
in [`contracts/`](../contracts) (machine-readable YAML — the source of
truth for required/optional/type/range/allowed-values; this document is the
human-readable companion).

## Dataset summary (all 17 public outputs)

| Dataset | Grain | Public/Private | Contract |
|---|---|---|---|
| `anonymized_master.csv` | one row per transaction | Public | `contracts/public_outputs/anonymized_master.yml` |
| `marketplace_summary.csv` | (transaction_month, marketplace) | Public | `contracts/public_outputs/marketplace_summary.yml` |
| `marketplace_channel_performance.csv` | (marketplace, channel) | Public | — |
| `product_performance.csv` | (public_product_id, marketplace, ...) | Public | `contracts/public_outputs/product_performance.yml` |
| `category_performance.csv` | (marketplace, category_group, subcategory_group) | Public | — |
| `brand_performance.csv` | (marketplace, brand_group, category_group) | Public | — |
| `profitability_summary.csv` | (marketplace, category, brand, product group, bands) | Public | — |
| `margin_risk_review.csv` | (public_product_id, marketplace) | Public | — |
| `inventory_action_review.csv` | (public_product_id, marketplace) | Public | `contracts/public_outputs/inventory_action_review.yml` |
| `fee_refund_summary.csv` | (public_product_id, marketplace) | Public | — |
| `fulfillment_comparison.csv` | fulfillment_type | Public | — |
| `product_action_review.csv` | (public_product_id, marketplace) | Public | — |
| `mart_marketplace_variance_drivers.csv` | (marketplace, metric) | Public | — |
| `mart_product_variance_contributors.csv` | (public_product_id, marketplace, brand_group, category_group, metric) | Public | — |
| `mart_performance_driver_summary.csv` | metric | Public | — |
| `dataset_profile.csv` | public_output_name | Public | `contracts/public_outputs/dataset_profile.yml` |
| `validation_summary.csv` | check_name | Public | `contracts/public_outputs/validation_summary.yml` |

## `anonymized_master.csv` — column reference

| Column | Type | Public/Private | Nullable | Derivation | Validation |
|---|---|---|---|---|---|
| transaction_month | string | Public | No | Parsed from transaction date | non-empty |
| dataset_period | string | Public | No | Set at pipeline run (e.g. "12m") | non-empty |
| marketplace | string | Public | No | Cleaned/grouped marketplace name | allowed set (5 marketplaces) |
| channel | string | Public | No | Marketplace sub-channel (mapping status Unavailable — see BR-05) | non-empty |
| public_product_id | string | Public | No | Anonymized ID (never real SKU/ASIN) | `shared/privacy.py` content scan |
| brand_group | string | Public | No | Grouped brand | non-empty |
| category_group | string | Public | No | Grouped category | non-empty |
| subcategory_group | string | Public | No | Grouped subcategory | non-empty |
| product_group | string | Public | No | Grouped product family | non-empty |
| fulfillment_type | string | Public | No | Cleaned fulfillment channel | non-empty |
| state_group | string | Public | No | Grouped delivery state (never a postal code) | privacy scan |
| origin_country_group | string | Public | No | India / Imported-Other | allowed set |
| listing_price_band | string | Public | No | Price banded, never raw price | non-empty |
| inventory_band | string | Public | No | Banded inventory level | allowed set |
| margin_band_public | string | Public | No | Derived from `band_from_pct` | allowed set |
| profitability_band_public | string | Public | No | Derived from `band_from_pct` | allowed set |
| sales_index | number | Public | No | `index_from_values(gross_sales)` | 0–100 |
| units_index | number | Public | No | `index_from_values(units)` | 0–100 |
| fee_pct_of_gross | number | Public | No | `pct_of_gross(fee, gross)` | 0–300 |
| refund_pct_of_gross | number | Public | No | `pct_of_gross(refund, gross)` | 0–300 |
| promotion_pct_of_gross | number | Public | No | `pct_of_gross(promo, gross)` | 0–300 |
| net_to_gross_pct | number | Public | No | `pct_of_gross(net, gross, signed=True)` | -300–300 |
| margin_index | number | Public | Yes (null for non-product rows) | `index_from_values(profit.clip(lower=0))` | 0–100 |
| estimated_profitability_index | number | Public | Yes | Blended signal, see KPI catalog | 0–100 |
| margin_risk_score | number | Public | Yes | See KPI catalog | 0–100 |
| margin_risk_band | string | Public | No | See profitability.py | allowed set |
| revenue_quality_score | number | Public | Yes | See KPI catalog | 0–100 |
| revenue_quality_band | string | Public | No | See profitability.py | allowed set |
| recommended_action | string | Public | No | `add_actions()` rule engine | allowed set (9 values) |
| action_priority | string | Public | No | `add_actions()` rule engine | High/Medium/Low |
| action_reason | string | Public | No | `add_actions()` rule engine | non-empty when action ≠ Monitor |
| mapping_status | string | Public | No | Join/mapping status flag | non-empty |

## `mart_marketplace_variance_drivers.csv` — column reference

| Column | Type | Derivation |
|---|---|---|
| marketplace | string | Dimension value |
| metric | string | One of the 9 headline metric keys (see KPI catalog) |
| metric_label | string | Human-readable metric name |
| previous_value | number | Aggregated metric value for the previous transaction_month |
| current_value | number | Aggregated metric value for the current transaction_month |
| abs_variance | number | `current_value - previous_value` |
| pct_variance | number or null | `(current-previous)/abs(previous)*100`; null when previous is 0 |
| contribution_share_pct | number | Share of total absolute variance for this metric attributable to this marketplace |
| movement | string | Deterioration / Improvement / Increase / Decrease / No Change |

`mart_product_variance_contributors.csv` follows the identical schema with
`public_product_id`, `marketplace`, `brand_group`, `category_group` as the
dimension columns. `mart_performance_driver_summary.csv` is metric-grain
only, adding `previous_period`, `current_period`, `total_abs_variance`,
`total_pct_variance`, and a deterministic `narrative` string.

## Generation

Column lists above were cross-checked against
`shared/public_output_builder.py:PUBLIC_DASHBOARD_COLUMNS` and
`shared/variance_engine.py:VARIANCE_COLUMNS` at authoring time to keep this
document aligned with code. Re-check both when either module's column list
changes.
