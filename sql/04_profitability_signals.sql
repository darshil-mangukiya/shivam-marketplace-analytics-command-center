-- Shivam Multi-Marketplace Analytics Command Center
-- Purpose: Estimated profitability and margin-risk signals (bands/indexes only, no raw amounts).
-- Scope: Privacy-safe public analytics query (reads public/output tables only)
-- Note: Marketplace-channel join coverage is unavailable unless mapping keys are populated.

-- Estimated profitability and margin-risk analysis.
-- No raw cost, revenue, fee, or profit amounts are selected.

select
    dataset_period,
    marketplace,
    category_group,
    brand_group,
    product_group,
    margin_band_public,
    profitability_band_public,
    sales_index,
    units_index,
    margin_index,
    estimated_profitability_index,
    margin_risk_score,
    margin_risk_band,
    revenue_quality_score,
    revenue_quality_band
from profitability_summary
order by margin_risk_score desc, sales_index desc;

