-- Shivam Multi-Marketplace Analytics Command Center
-- Purpose: Fee, refund, and promotion pressure on revenue quality (ratios only, no raw amounts).
-- Scope: Privacy-safe public analytics query (reads public/output tables only)
-- Note: Marketplace-channel join coverage is unavailable unless mapping keys are populated.

-- Fee, refund, promotion, and revenue quality review using ratios only.

select
    marketplace,
    brand_group,
    category_group,
    product_group,
    fee_pct_of_gross,
    refund_pct_of_gross,
    promotion_pct_of_gross,
    net_to_gross_pct,
    revenue_quality_score,
    revenue_quality_band
from fee_refund_summary
order by revenue_quality_score asc, fee_pct_of_gross desc;

