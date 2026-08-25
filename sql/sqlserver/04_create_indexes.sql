-- 04_create_indexes.sql
-- STATUS: NOT EXECUTED — see 00_create_database.sql header.
--
-- Indexing rationale: every fact table is queried primarily by month and by
-- marketplace (dashboard filters) and secondarily by product (drill-down),
-- so nonclustered indexes are added on those foreign keys in addition to the
-- unique constraints (which SQL Server already backs with a unique index).

USE ShivamMarketplaceAnalytics;
GO

CREATE INDEX IX_fact_marketplace_activity_month ON analytics.fact_marketplace_activity (month_key);
CREATE INDEX IX_fact_marketplace_activity_marketplace ON analytics.fact_marketplace_activity (marketplace_key);

CREATE INDEX IX_fact_product_performance_product ON analytics.fact_product_performance (product_key);
CREATE INDEX IX_fact_product_performance_marketplace ON analytics.fact_product_performance (marketplace_key);
CREATE INDEX IX_fact_product_performance_action_priority ON analytics.fact_product_performance (action_priority);

CREATE INDEX IX_fact_inventory_action_priority ON analytics.fact_inventory_action (action_priority);

CREATE INDEX IX_fact_performance_variance_metric ON analytics.fact_performance_variance (metric);
CREATE INDEX IX_fact_performance_variance_marketplace ON analytics.fact_performance_variance (marketplace_key);
GO
