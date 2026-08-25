# DAX Measures

All measures live in the dedicated `Measures` table and use public fields only. Do
not create raw sales, raw fee, raw refund, or raw net amount measures.

Table references below match the built model: `FactProductMarketplace`
(`product_performance.csv`), `FactMarketplaceMonth` (`marketplace_summary.csv`),
`FactPublicActivity` (`anonymized_master.csv`), `FactInventoryAction`
(`inventory_action_review.csv`), `AuditValidation` (`validation_summary.csv`), and
`AuditDatasetProfile` (`dataset_profile.csv`).

## Core KPIs

```DAX
Total Orders = SUM ( FactMarketplaceMonth[total_orders] )
```

```DAX
Count of Products = DISTINCTCOUNT ( FactProductMarketplace[public_product_id] )
```

```DAX
Count of Marketplaces = DISTINCTCOUNT ( FactProductMarketplace[marketplace] )
```

```DAX
Average Sales Index = AVERAGE ( FactProductMarketplace[sales_index] )
```

```DAX
Average Units Index = AVERAGE ( FactProductMarketplace[units_index] )
```

## Quality Ratios

```DAX
Fee % = AVERAGE ( FactProductMarketplace[fee_pct_of_gross] )
```

```DAX
Refund % = AVERAGE ( FactProductMarketplace[refund_pct_of_gross] )
```

```DAX
Promotion % = AVERAGE ( FactProductMarketplace[promotion_pct_of_gross] )
```

```DAX
Net-to-Gross % = AVERAGE ( FactProductMarketplace[net_to_gross_pct] )
```

## Profitability & Risk (estimated signals only)

```DAX
Margin Index = AVERAGE ( FactProductMarketplace[margin_index] )
```

```DAX
Estimated Profitability Index = AVERAGE ( FactProductMarketplace[estimated_profitability_index] )
```

```DAX
Margin Risk Score = AVERAGE ( FactProductMarketplace[margin_risk_score] )
```

```DAX
Revenue Quality Score = AVERAGE ( FactProductMarketplace[revenue_quality_score] )
```

## Action Measures

```DAX
Recommended Action Count = COUNTROWS ( FactProductMarketplace )
```

```DAX
High Priority Action Count =
CALCULATE (
    DISTINCTCOUNT ( FactProductMarketplace[public_product_id] ),
    FactProductMarketplace[action_priority] = "High"
)
```

```DAX
Fee Review Count =
CALCULATE ( COUNTROWS ( FactProductMarketplace ), FactProductMarketplace[recommended_action] = "Fee Review" )
```

```DAX
Refund Review Count =
CALCULATE ( COUNTROWS ( FactProductMarketplace ), FactProductMarketplace[recommended_action] = "Refund Review" )
```

```DAX
Restock Review Count =
CALCULATE ( COUNTROWS ( FactProductMarketplace ), FactProductMarketplace[recommended_action] = "Restock Review" )
```

```DAX
Revenue Quality Review Count =
CALCULATE ( COUNTROWS ( FactProductMarketplace ), FactProductMarketplace[recommended_action] = "Revenue Quality Review" )
```

```DAX
Monitor Count =
CALCULATE ( COUNTROWS ( FactProductMarketplace ), FactProductMarketplace[recommended_action] = "Monitor" )
```

## Row-Count / Audit Measures

```DAX
Activity Row Count = COUNTROWS ( FactPublicActivity )
```

```DAX
Inventory Action Row Count = COUNTROWS ( FactInventoryAction )
```

```DAX
Validation Pass Count =
CALCULATE ( COUNTROWS ( AuditValidation ), AuditValidation[check_status] = "PASS" )
```

```DAX
Validation Warning Count =
CALCULATE ( COUNTROWS ( AuditValidation ), AuditValidation[check_status] = "WARN" )
```

```DAX
Validation Failure Count =
CALCULATE ( COUNTROWS ( AuditValidation ), AuditValidation[check_status] = "FAIL" )
```

```DAX
Public Output Count = DISTINCTCOUNT ( AuditDatasetProfile[public_output_name] )
```

> Note: "Revenue Quality Score" may appear as "Revenue Quality Index" in some visual
> titles. Both refer to the same public 0-100 score.
