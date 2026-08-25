-- Shivam Multi-Marketplace Analytics Command Center
-- Purpose: Inventory and restock action review using public inventory bands and indexes.
-- Scope: Privacy-safe public analytics query (reads public/output tables only)
-- Note: Marketplace-channel join coverage is unavailable unless mapping keys are populated.

-- Inventory and restock action review using bands and indexes.

select
    public_product_id,
    marketplace,
    brand_group,
    category_group,
    product_group,
    inventory_band,
    units_index,
    sales_index,
    margin_risk_band,
    revenue_quality_band,
    restock_priority,
    recommended_action,
    action_priority,
    action_reason
from inventory_action_review
order by action_priority, units_index desc;

