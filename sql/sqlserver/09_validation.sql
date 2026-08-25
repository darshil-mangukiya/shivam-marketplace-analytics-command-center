-- 09_validation.sql — warehouse-side validation checks.
-- STATUS: NOT EXECUTED — see 00_create_database.sql header.

USE ShivamMarketplaceAnalytics;
GO

-- V1: Every check in the latest audit_validation load must be PASS or WARN,
-- never FAIL.
SELECT check_name, check_status, check_value, expected_value, notes
FROM audit.audit_validation
WHERE load_timestamp = (SELECT MAX(load_timestamp) FROM audit.audit_validation)
  AND check_status = 'FAIL';
-- Empty result set = no failing checks in the most recent load.

-- V2: Row counts loaded into each fact table must be > 0 for a completed load.
SELECT 'fact_marketplace_activity' AS fact_table, COUNT(*) AS row_count FROM analytics.fact_marketplace_activity
UNION ALL
SELECT 'fact_product_performance', COUNT(*) FROM analytics.fact_product_performance
UNION ALL
SELECT 'fact_inventory_action', COUNT(*) FROM analytics.fact_inventory_action
UNION ALL
SELECT 'fact_performance_variance', COUNT(*) FROM analytics.fact_performance_variance;

-- V3: dataset_profile row counts loaded into the warehouse should match the
-- row counts of the public CSVs they were sourced from (spot-check pattern
-- for a BI manager reconciling the warehouse against the CSV mode).
SELECT public_output_name, row_count, dataset_period, dataset_label
FROM audit.audit_dataset_profile
WHERE load_timestamp = (SELECT MAX(load_timestamp) FROM audit.audit_dataset_profile);

-- V4: No dimension table should contain a value from the forbidden-field
-- list (defense-in-depth; the real enforcement point is
-- shared/privacy.py + contracts/*.yml before data ever reaches this
-- warehouse). This is a shape check, not a content scan.
SELECT COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'analytics'
  AND COLUMN_NAME IN ('asin', 'asin1', 'seller_sku', 'sku', 'order_id', 'listing_id', 'item_name', 'item_description', 'order_postal');
-- Empty result set = no forbidden column names exist anywhere in the schema.
