-- 01_create_schema.sql
-- STATUS: NOT EXECUTED — see 00_create_database.sql header.

USE ShivamMarketplaceAnalytics;
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'analytics')
    EXEC('CREATE SCHEMA analytics');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'audit')
    EXEC('CREATE SCHEMA audit');
GO
