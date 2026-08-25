-- 02_create_dimensions.sql
-- Deployed to Azure SQL Database; see docs/evidence/azure_sql_runtime_evidence.md.
--
-- Grain documentation:
--   dim_product        : one row per public_product_id (already anonymized;
--                         never a real SKU/ASIN — see contracts/public_outputs)
--   dim_marketplace     : one row per marketplace (channel is carried as a
--                          constant 'Marketplace' attribute — see note below)
--   dim_month           : one row per transaction_month (calendar grain used
--                          by the pipeline's dataset_period/transaction_month
--                          columns, not a full date dimension)
--   dim_fulfillment      : one row per fulfillment_type
--
-- Surrogate key strategy: keys are assigned deterministically by
-- shared/sqlserver_star_schema.py (sorted-natural-key -> consecutive
-- integer, so the same source data always produces the same keys across
-- runs — never a random UUID). Key columns are therefore plain INT/BIGINT
-- PRIMARY KEY, NOT IDENTITY: the ETL layer supplies every key value
-- explicitly on load rather than letting SQL Server generate one.
--
-- Unknown-member convention: every dimension reserves key 0 for a single
-- synthetic "Unknown" row, used by the fact-builder functions when a
-- source row's natural key cannot be resolved against the dimension
-- (Requirement 14/16) — this guarantees no fact row is ever silently
-- dropped for a missing dimension value.
--
-- Marketplace-channel note: `channel` on dim_marketplace is a
-- constant 'Marketplace' default, not a validated sub-channel breakdown.
-- The Marketplace_Channel_Master mapping keys remain incomplete
-- (channel_mapping_status = "Unavailable" throughout this project), so
-- this warehouse remains at marketplace grain.

USE ShivamMarketplaceAnalytics;
GO

IF OBJECT_ID('analytics.dim_product', 'U') IS NULL
CREATE TABLE analytics.dim_product (
    product_key                INT NOT NULL PRIMARY KEY,
    public_product_id          VARCHAR(64)   NOT NULL,
    brand_group                 NVARCHAR(200) NOT NULL,
    category_group                NVARCHAR(200) NOT NULL,
    subcategory_group               NVARCHAR(200) NULL,
    product_group                     NVARCHAR(200) NULL,
    listing_price_band                  NVARCHAR(50)  NULL,
    inventory_band                        NVARCHAR(50)  NULL,
    margin_band_public                       NVARCHAR(50) NULL,
    profitability_band_public                   NVARCHAR(50) NULL,
    CONSTRAINT UQ_dim_product_public_id UNIQUE (public_product_id)
);
GO

IF OBJECT_ID('analytics.dim_marketplace', 'U') IS NULL
CREATE TABLE analytics.dim_marketplace (
    marketplace_key INT NOT NULL PRIMARY KEY,
    marketplace      NVARCHAR(100) NOT NULL,
    channel           NVARCHAR(100) NOT NULL DEFAULT ('Marketplace'),
    CONSTRAINT UQ_dim_marketplace UNIQUE (marketplace, channel)
);
GO

IF OBJECT_ID('analytics.dim_month', 'U') IS NULL
CREATE TABLE analytics.dim_month (
    month_key         INT NOT NULL PRIMARY KEY,
    transaction_month  NVARCHAR(20) NOT NULL,
    year_month           NVARCHAR(20) NULL,
    year                    SMALLINT NULL,
    month_number              TINYINT NULL,
    month_name                  NVARCHAR(20) NULL,
    quarter                        TINYINT NULL,
    dataset_period                   NVARCHAR(50) NULL,
    CONSTRAINT UQ_dim_month UNIQUE (transaction_month)
);
GO

IF OBJECT_ID('analytics.dim_fulfillment', 'U') IS NULL
CREATE TABLE analytics.dim_fulfillment (
    fulfillment_key INT NOT NULL PRIMARY KEY,
    fulfillment_type NVARCHAR(100) NOT NULL,
    CONSTRAINT UQ_dim_fulfillment UNIQUE (fulfillment_type)
);
GO
