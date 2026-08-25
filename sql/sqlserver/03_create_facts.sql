-- 03_create_facts.sql
-- STATUS: NOT EXECUTED — see 00_create_database.sql header.
--
-- Grain documentation (verified against the actual public CSV columns in
-- data/public/ — see docs/sql_server_reporting_model.md):
--   fact_marketplace_activity : one row per (month_key, marketplace_key) —
--                                loaded from marketplace_summary.csv, which
--                                carries a transaction_month column.
--   fact_product_performance  : one row per (product_key, marketplace_key) —
--                                loaded from product_performance.csv, which
--                                does NOT carry a transaction_month column
--                                (it is aggregated across the whole dataset
--                                period, not per month). `dataset_period` is
--                                carried as a plain attribute instead of a
--                                dim_month foreign key — no month grain is
--                                fabricated that the source data doesn't
--                                actually have.
--   fact_inventory_action      : one row per (product_key, marketplace_key) —
--                                loaded from inventory_action_review.csv.
--   fact_performance_variance  : one row per (previous_month_key,
--                                current_month_key, marketplace_key, metric)
--                                — loaded from mart_marketplace_variance_drivers.csv
--                                (the previous/current period labels come from
--                                the single comparison pair in
--                                mart_performance_driver_summary.csv). Empty
--                                when the dataset has fewer than two valid
--                                activity periods — no comparison is
--                                fabricated (BR-16).
--
-- Surrogate keys are plain INT/BIGINT PRIMARY KEY (not IDENTITY) supplied
-- deterministically by shared/sqlserver_star_schema.py — see
-- 02_create_dimensions.sql header for the key-generation strategy.
--
-- All fact columns are already public/anonymized indexes, ratios, scores,
-- and bands; raw currency, SKUs, ASINs, and order IDs stay outside the warehouse.

USE ShivamMarketplaceAnalytics;
GO

IF OBJECT_ID('analytics.fact_marketplace_activity', 'U') IS NULL
CREATE TABLE analytics.fact_marketplace_activity (
    fact_key                 BIGINT NOT NULL PRIMARY KEY,
    month_key                 INT NOT NULL REFERENCES analytics.dim_month(month_key),
    marketplace_key             INT NOT NULL REFERENCES analytics.dim_marketplace(marketplace_key),
    total_orders                  INT NOT NULL,
    product_count                  INT NOT NULL,
    sales_index                     DECIMAL(6,2) NOT NULL,
    units_index                     DECIMAL(6,2) NOT NULL,
    avg_fee_pct_of_gross              DECIMAL(6,2) NOT NULL,
    avg_refund_pct_of_gross            DECIMAL(6,2) NOT NULL,
    avg_promotion_pct_of_gross          DECIMAL(6,2) NOT NULL,
    avg_net_to_gross_pct                 DECIMAL(6,2) NOT NULL,
    margin_risk_score                     DECIMAL(6,2) NULL,
    revenue_quality_score                  DECIMAL(6,2) NULL,
    CONSTRAINT UQ_fact_marketplace_activity UNIQUE (month_key, marketplace_key)
);
GO

IF OBJECT_ID('analytics.fact_product_performance', 'U') IS NULL
CREATE TABLE analytics.fact_product_performance (
    fact_key           BIGINT NOT NULL PRIMARY KEY,
    product_key            INT NOT NULL REFERENCES analytics.dim_product(product_key),
    marketplace_key           INT NOT NULL REFERENCES analytics.dim_marketplace(marketplace_key),
    dataset_period               NVARCHAR(50) NULL,
    sales_index                     DECIMAL(6,2) NOT NULL,
    units_index                       DECIMAL(6,2) NOT NULL,
    fee_pct_of_gross                     DECIMAL(6,2) NOT NULL,
    refund_pct_of_gross                     DECIMAL(6,2) NOT NULL,
    promotion_pct_of_gross                     DECIMAL(6,2) NOT NULL,
    net_to_gross_pct                              DECIMAL(6,2) NOT NULL,
    margin_index                                    DECIMAL(6,2) NULL,
    estimated_profitability_index                     DECIMAL(6,2) NULL,
    margin_risk_score                                   DECIMAL(6,2) NULL,
    revenue_quality_score                                 DECIMAL(6,2) NULL,
    recommended_action                                      NVARCHAR(50) NOT NULL,
    action_priority                                           NVARCHAR(10) NOT NULL,
    CONSTRAINT UQ_fact_product_performance UNIQUE (product_key, marketplace_key)
);
GO

IF OBJECT_ID('analytics.fact_inventory_action', 'U') IS NULL
CREATE TABLE analytics.fact_inventory_action (
    fact_key       BIGINT NOT NULL PRIMARY KEY,
    product_key       INT NOT NULL REFERENCES analytics.dim_product(product_key),
    marketplace_key       INT NOT NULL REFERENCES analytics.dim_marketplace(marketplace_key),
    units_index               DECIMAL(6,2) NOT NULL,
    sales_index                 DECIMAL(6,2) NOT NULL,
    restock_priority               NVARCHAR(50) NULL,
    recommended_action               NVARCHAR(50) NOT NULL,
    action_priority                    NVARCHAR(10) NOT NULL,
    CONSTRAINT UQ_fact_inventory_action UNIQUE (product_key, marketplace_key)
);
GO

IF OBJECT_ID('analytics.fact_performance_variance', 'U') IS NULL
CREATE TABLE analytics.fact_performance_variance (
    fact_key             BIGINT NOT NULL PRIMARY KEY,
    previous_month_key      INT NOT NULL REFERENCES analytics.dim_month(month_key),
    current_month_key          INT NOT NULL REFERENCES analytics.dim_month(month_key),
    marketplace_key                INT NOT NULL REFERENCES analytics.dim_marketplace(marketplace_key),
    metric                           NVARCHAR(50) NOT NULL,
    previous_value                     DECIMAL(10,2) NOT NULL,
    current_value                        DECIMAL(10,2) NOT NULL,
    abs_variance                           DECIMAL(10,2) NOT NULL,
    pct_variance                              DECIMAL(10,2) NULL,
    contribution_share_pct                       DECIMAL(6,2) NOT NULL,
    movement                                       NVARCHAR(20) NOT NULL,
    CONSTRAINT UQ_fact_performance_variance UNIQUE (previous_month_key, current_month_key, marketplace_key, metric)
);
GO

-- Audit tables (loaded from validation_summary.csv and dataset_profile.csv).
-- These are intentionally NOT foreign-keyed to the analytical dimensions —
-- they are pipeline run-level observability records (what did validation
-- say, what did the row-count profile look like), not facts about a
-- marketplace/product/month, so a relational tie to the star schema would
-- be artificial. This is a deliberate design decision, not an omission.

IF OBJECT_ID('audit.audit_validation', 'U') IS NULL
CREATE TABLE audit.audit_validation (
    audit_key       BIGINT NOT NULL PRIMARY KEY,
    load_timestamp     DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    check_name             NVARCHAR(200) NOT NULL,
    check_status              NVARCHAR(10) NOT NULL,
    check_value                 NVARCHAR(4000) NULL,
    expected_value                 NVARCHAR(4000) NULL,
    notes                              NVARCHAR(4000) NULL
);
GO

IF OBJECT_ID('audit.audit_dataset_profile', 'U') IS NULL
CREATE TABLE audit.audit_dataset_profile (
    audit_key       BIGINT NOT NULL PRIMARY KEY,
    load_timestamp     DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    public_output_name     NVARCHAR(200) NOT NULL,
    row_count                 INT NOT NULL,
    dataset_period                NVARCHAR(50) NOT NULL,
    dataset_label                    NVARCHAR(200) NOT NULL
);
GO
