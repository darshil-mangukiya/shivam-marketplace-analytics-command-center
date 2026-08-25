-- 08_root_cause_analysis.sql — SQL equivalent of shared/variance_engine.py.
-- The queries use descriptive variance decomposition to rank the
-- marketplaces and products associated with a metric change.
-- Latest-period selection excludes the Unknown dimension member.

USE ShivamMarketplaceAnalytics;
GO

-- Q1: Headline metric movement by marketplace for the most recent
-- comparison period, ranked by absolute variance magnitude.
SELECT
    v.marketplace,
    v.metric,
    v.previous_value,
    v.current_value,
    v.abs_variance,
    v.pct_variance,
    v.contribution_share_pct,
    v.movement
FROM analytics.vw_performance_drivers v
WHERE v.current_month = (SELECT MAX(current_month) FROM analytics.vw_performance_drivers)
ORDER BY v.metric, ABS(v.abs_variance) DESC;

-- Q2: Top-3 marketplace contributors to Sales Index movement, most recent period.
SELECT TOP 3
    v.marketplace, v.abs_variance, v.contribution_share_pct, v.movement
FROM analytics.vw_performance_drivers v
WHERE v.metric = 'sales_index'
  AND v.current_month = (SELECT MAX(current_month) FROM analytics.vw_performance_drivers)
ORDER BY ABS(v.abs_variance) DESC;

-- Q3: Total (net) variance per headline metric, most recent period — a
-- quick "did this metric net-improve or net-deteriorate" summary.
SELECT
    v.metric,
    SUM(v.previous_value) AS total_previous_value,
    SUM(v.current_value)  AS total_current_value,
    SUM(v.current_value) - SUM(v.previous_value) AS net_abs_variance
FROM analytics.vw_performance_drivers v
WHERE v.current_month = (SELECT MAX(current_month) FROM analytics.vw_performance_drivers)
GROUP BY v.metric
ORDER BY v.metric;

-- Q4: Marketplaces where a metric moved into "Deterioration" this period.
SELECT v.marketplace, v.metric, v.abs_variance, v.contribution_share_pct
FROM analytics.vw_performance_drivers v
WHERE v.movement = 'Deterioration'
  AND v.current_month = (SELECT MAX(current_month) FROM analytics.vw_performance_drivers)
ORDER BY v.metric, ABS(v.abs_variance) DESC;
