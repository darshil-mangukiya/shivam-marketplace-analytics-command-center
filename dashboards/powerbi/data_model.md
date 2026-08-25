# Power BI Data Model

This describes the model as actually built in
`Shivam_Multi_Marketplace_Analytics_Command_Center.pbix`.

## Source Tables (6 public CSVs)

Only these privacy-safe files from `data/public/` are loaded:

| Source CSV | Power BI table | Rows |
| --- | --- | --- |
| `anonymized_master.csv` | `FactPublicActivity` | 141,000 |
| `product_performance.csv` | `FactProductMarketplace` | 760 |
| `marketplace_summary.csv` | `FactMarketplaceMonth` | 65 |
| `inventory_action_review.csv` | `FactInventoryAction` | 760 |
| `validation_summary.csv` | `AuditValidation` | 34 |
| `dataset_profile.csv` | `AuditDatasetProfile` | 15 |

The model imports these six public outputs.

## Derived Dimensions

Built inside Power BI from the public fact tables:

- `DimProduct` — one row per `public_product_id` with grouped product attributes
- `DimMarketplace` — one row per marketplace
- `DimMonth` — one row per `transaction_month`
- `DimFulfillment` — one row per `fulfillment_type`

## Measure Table

- `Measures` — a dedicated, data-less table holding all DAX measures.

## Relationship Notes

- Dimensions filter the fact tables on `public_product_id`, `marketplace`,
  `transaction_month`, and `fulfillment_type`.
- `AuditValidation` and `AuditDatasetProfile` are **disconnected** audit tables; they
  are not related to any fact table and are used on the Validation & Privacy page.
- No direct fact-to-fact relationships are used; shared filtering flows through the
  dimensions.
- Product rows can split by fulfillment type, so verify duplicate `public_product_id`
  handling before enforcing strict one-to-one relationships; visual-level filters may
  be safer than an overstrict relationship.

## Privacy Notes

The model does not include ASINs, seller SKUs, order IDs, listing IDs, item
descriptions, exact product titles, postal codes, private mapping tables, or raw
financial amounts. Only public ratios, indexes, scores, and bands are used.

## Marketplace-channel mapping

`marketplace_channel_performance.csv` is excluded because the `Marketplace_Channel_Master`
mapping columns (seller SKU and public product ID) are empty. Marketplace-channel
enrichment is therefore unavailable until the mapping is completed and validated.
