-- 07_performance_analysis.sql — business-facing performance queries.
-- Latest-period queries select the maximum month with order activity.
-- This excludes the Unknown dimension member and trailing zero-activity
-- months, matching the BR-16 period-selection rule.

USE ShivamMarketplaceAnalytics;
GO

-- Q1: Marketplace ranking by Sales Index for the latest month.
SELECT TOP 10
    v.marketplace, v.sales_index, v.units_index, v.avg_fee_pct_of_gross, v.avg_net_to_gross_pct
FROM analytics.vw_marketplace_performance v
WHERE v.transaction_month = (SELECT MAX(m.transaction_month) FROM analytics.dim_month m JOIN analytics.fact_marketplace_activity f ON f.month_key = m.month_key WHERE f.total_orders > 0)
ORDER BY v.sales_index DESC;

-- Q2: Top 20 products by Sales Index across all marketplaces.
-- (vw_product_performance carries no transaction_month -- the source
-- product_performance.csv is aggregated across the full dataset_period;
-- see the 03_create_facts.sql header.)
SELECT TOP 20
    v.public_product_id, v.brand_group, v.category_group, v.marketplace, v.sales_index, v.units_index
FROM analytics.vw_product_performance v
ORDER BY v.sales_index DESC;

-- Q3: Products flagged High priority for action.
SELECT
    v.public_product_id, v.brand_group, v.category_group, v.marketplace,
    v.recommended_action, v.action_priority, v.margin_risk_score, v.revenue_quality_score
FROM analytics.vw_product_performance v
WHERE v.action_priority = 'High'
ORDER BY v.margin_risk_score DESC;

-- Q4: Fee/refund/promotion pressure by marketplace, latest month.
SELECT
    v.marketplace, v.avg_fee_pct_of_gross, v.avg_refund_pct_of_gross, v.avg_promotion_pct_of_gross
FROM analytics.vw_marketplace_performance v
WHERE v.transaction_month = (SELECT MAX(m.transaction_month) FROM analytics.dim_month m JOIN analytics.fact_marketplace_activity f ON f.month_key = m.month_key WHERE f.total_orders > 0)
ORDER BY v.avg_fee_pct_of_gross DESC;
