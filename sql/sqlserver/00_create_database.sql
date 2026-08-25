-- Shivam Multi-Marketplace Analytics — SQL Server Reporting Warehouse
-- 00_create_database.sql
--
-- STATUS: Implemented as portable T-SQL. NOT EXECUTED — SQL Server runtime
-- unavailable in some local environments. Static
-- syntax review only (see docs/sql_server_reporting_model.md for details
-- and docs/sql_server_reporting_model.md for setup details).
--
-- This script is idempotent: safe to re-run against an existing server.

IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = N'ShivamMarketplaceAnalytics')
BEGIN
    CREATE DATABASE ShivamMarketplaceAnalytics;
END
GO
