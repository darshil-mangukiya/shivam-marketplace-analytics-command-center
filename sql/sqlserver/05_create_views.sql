-- 05_create_views.sql — business-facing reporting views for Power BI / SQL.
-- STATUS: NOT EXECUTED — see 00_create_database.sql header.

USE ShivamMarketplaceAnalytics;
GO

CREATE OR ALTER VIEW analytics.vw_marketplace_performance AS
SELECT
    m.transaction_month,
    mp.marketplace,
    mp.channel,
    f.total_orders,
    f.product_count,
    f.sales_index,
    f.units_index,
    f.avg_fee_pct_of_gross,
    f.avg_refund_pct_of_gross,
    f.avg_promotion_pct_of_gross,
    f.avg_net_to_gross_pct,
    f.margin_risk_score,
    f.revenue_quality_score
FROM analytics.fact_marketplace_activity f
JOIN analytics.dim_month m ON m.month_key = f.month_key
JOIN analytics.dim_marketplace mp ON mp.marketplace_key = f.marketplace_key;
GO

CREATE OR ALTER VIEW analytics.vw_product_performance AS
-- fact_product_performance is grain (product, marketplace) only — the
-- source public CSV (product_performance.csv) is not month-grained, so no
-- dim_month join is fabricated here. `dataset_period` is carried as a
-- plain attribute instead.
SELECT
    f.dataset_period,
    p.public_product_id,
    p.brand_group,
    p.category_group,
    p.subcategory_group,
    p.product_group,
    mp.marketplace,
    f.sales_index,
    f.units_index,
    f.fee_pct_of_gross,
    f.refund_pct_of_gross,
    f.promotion_pct_of_gross,
    f.net_to_gross_pct,
    f.margin_index,
    f.estimated_profitability_index,
    f.margin_risk_score,
    f.revenue_quality_score,
    f.recommended_action,
    f.action_priority
FROM analytics.fact_product_performance f
JOIN analytics.dim_product p ON p.product_key = f.product_key
JOIN analytics.dim_marketplace mp ON mp.marketplace_key = f.marketplace_key;
GO

CREATE OR ALTER VIEW analytics.vw_inventory_action AS
SELECT
    p.public_product_id,
    p.brand_group,
    p.category_group,
    p.inventory_band,
    mp.marketplace,
    f.units_index,
    f.sales_index,
    f.restock_priority,
    f.recommended_action,
    f.action_priority
FROM analytics.fact_inventory_action f
JOIN analytics.dim_product p ON p.product_key = f.product_key
JOIN analytics.dim_marketplace mp ON mp.marketplace_key = f.marketplace_key;
GO

CREATE OR ALTER VIEW analytics.vw_revenue_quality AS
SELECT
    f.dataset_period,
    mp.marketplace,
    p.public_product_id,
    p.brand_group,
    p.category_group,
    f.revenue_quality_score,
    f.fee_pct_of_gross,
    f.refund_pct_of_gross,
    f.promotion_pct_of_gross,
    f.net_to_gross_pct
FROM analytics.fact_product_performance f
JOIN analytics.dim_product p ON p.product_key = f.product_key
JOIN analytics.dim_marketplace mp ON mp.marketplace_key = f.marketplace_key;
GO

CREATE OR ALTER VIEW analytics.vw_margin_risk AS
SELECT
    f.dataset_period,
    mp.marketplace,
    p.public_product_id,
    p.brand_group,
    p.category_group,
    f.margin_risk_score,
    f.recommended_action,
    f.action_priority
FROM analytics.fact_product_performance f
JOIN analytics.dim_product p ON p.product_key = f.product_key
JOIN analytics.dim_marketplace mp ON mp.marketplace_key = f.marketplace_key
WHERE f.margin_risk_score IS NOT NULL;
GO

CREATE OR ALTER VIEW analytics.vw_performance_drivers AS
SELECT
    pm.transaction_month AS previous_month,
    cm.transaction_month AS current_month,
    mp.marketplace,
    f.metric,
    f.previous_value,
    f.current_value,
    f.abs_variance,
    f.pct_variance,
    f.contribution_share_pct,
    f.movement
FROM analytics.fact_performance_variance f
JOIN analytics.dim_month pm ON pm.month_key = f.previous_month_key
JOIN analytics.dim_month cm ON cm.month_key = f.current_month_key
JOIN analytics.dim_marketplace mp ON mp.marketplace_key = f.marketplace_key;
GO

CREATE OR ALTER VIEW analytics.vw_validation_summary AS
SELECT check_name, check_status, check_value, expected_value, notes
FROM audit.audit_validation;
GO
