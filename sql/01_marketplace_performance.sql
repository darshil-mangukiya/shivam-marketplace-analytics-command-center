-- Shivam Multi-Marketplace Analytics Command Center
-- Purpose: Marketplace-level indexed performance, fee/refund/promotion ratios, and quality scores.
-- Scope: Privacy-safe public analytics query (reads public/output tables only)
-- Note: Marketplace-channel join coverage is unavailable unless mapping keys are populated.

-- Public-safe marketplace/channel performance view.
-- Source table shape: data/public/marketplace_channel_performance.csv

select
    dataset_period,
    marketplace,
    channel,
    product_count,
    order_count_index,
    sales_index,
    units_index,
    avg_fee_pct_of_gross,
    avg_refund_pct_of_gross,
    avg_promotion_pct_of_gross,
    avg_net_to_gross_pct,
    avg_margin_risk_score,
    avg_revenue_quality_score,
    high_priority_action_count
from marketplace_channel_performance
order by sales_index desc, units_index desc;

