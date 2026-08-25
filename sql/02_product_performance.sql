-- Shivam Multi-Marketplace Analytics Command Center
-- Purpose: Product / brand / category indexed performance and revenue-quality signals.
-- Scope: Privacy-safe public analytics query (reads public/output tables only)
-- Note: Marketplace-channel join coverage is unavailable unless mapping keys are populated.

-- Public-safe product, brand, and category intelligence.
-- Source table shape: data/public/product_performance.csv

select
    marketplace,
    brand_group,
    category_group,
    subcategory_group,
    product_group,
    listing_price_band,
    inventory_band,
    sales_index,
    units_index,
    net_to_gross_pct,
    revenue_quality_score,
    recommended_action,
    action_priority
from product_performance
order by sales_index desc, units_index desc;

