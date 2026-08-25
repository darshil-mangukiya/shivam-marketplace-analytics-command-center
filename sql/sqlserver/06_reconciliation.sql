-- 06_reconciliation.sql — reconciliation queries between marts (BR-04).
-- STATUS: NOT EXECUTED — see 00_create_database.sql header.

USE ShivamMarketplaceAnalytics;
GO

-- Reconciliation 1: every dim_product member (other than the synthetic
-- Unknown row, key 0) should be used by at least one fact_product_performance
-- row -- dim_product is built directly from product_performance.csv, so an
-- unused dimension member indicates a reshape bug, not a real gap.
-- (fact_product_performance carries no month grain -- product_performance.csv
-- is aggregated across the whole dataset period, not per month -- so this
-- reconciliation is at the product x marketplace grain, not month x
-- marketplace; see 03_create_facts.sql header for why.)
SELECT p.product_key, p.public_product_id
FROM analytics.dim_product p
LEFT JOIN analytics.fact_product_performance f ON f.product_key = p.product_key
WHERE p.product_key <> 0
  AND f.fact_key IS NULL;
-- Empty result set = every real dim_product member is used by at least one fact row.

-- Reconciliation 2: every product_key in fact_inventory_action must also
-- appear in fact_product_performance for at least one month (no orphans).
SELECT ia.product_key, ia.marketplace_key
FROM analytics.fact_inventory_action ia
LEFT JOIN analytics.fact_product_performance pp
    ON pp.product_key = ia.product_key AND pp.marketplace_key = ia.marketplace_key
WHERE pp.fact_key IS NULL;
-- Empty result set = no orphaned inventory-action rows.

-- Reconciliation 3: every fact_performance_variance row's marketplace-level
-- previous/current values should reconcile to fact_marketplace_activity for
-- the same two months (sales_index shown as an example metric).
SELECT
    v.marketplace_key,
    v.previous_month_key,
    v.current_month_key,
    v.previous_value AS variance_previous_value,
    prev.sales_index AS fact_previous_value,
    v.current_value AS variance_current_value,
    curr.sales_index AS fact_current_value
FROM analytics.fact_performance_variance v
JOIN analytics.fact_marketplace_activity prev
    ON prev.month_key = v.previous_month_key AND prev.marketplace_key = v.marketplace_key
JOIN analytics.fact_marketplace_activity curr
    ON curr.month_key = v.current_month_key AND curr.marketplace_key = v.marketplace_key
WHERE v.metric = 'sales_index'
  AND (v.previous_value <> prev.sales_index OR v.current_value <> curr.sales_index);
-- Empty result set = the variance mart reconciles to the activity fact for
-- the sales_index metric.
