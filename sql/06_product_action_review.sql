-- Shivam Multi-Marketplace Analytics Command Center
-- Purpose: Prioritized product action review from public sales/fee/refund/inventory signals.
-- Scope: Privacy-safe public analytics query (reads public/output tables only)
-- Note: Marketplace-channel join coverage is unavailable unless mapping keys are populated.

/*
Business question:
Which products should be reviewed first, and why?

Expected insight:
Action priority combines public sales, unit, fee, refund, promotion, price-band, and inventory-band signals.
*/

SELECT
    public_product_id,
    brand_group,
    category_group,
    product_group,
    sales_index,
    units_index,
    fee_pct_of_gross,
    refund_pct_of_gross,
    promotion_pct_of_gross,
    net_to_gross_pct,
    recommended_action,
    action_priority,
    action_reason
FROM product_action_review
WHERE recommended_action <> 'Monitor'
ORDER BY
    CASE action_priority
        WHEN 'High' THEN 1
        WHEN 'Medium' THEN 2
        ELSE 3
    END,
    sales_index DESC,
    units_index DESC;
