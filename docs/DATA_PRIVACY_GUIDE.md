# Data Privacy Guide

The public app and CSV outputs must never expose ASINs, real SKUs, seller SKUs, order IDs, listing IDs, exact product titles, item descriptions, postal codes, private cost fields, or raw rupee amounts.

Allowed public values are grouped attributes, anonymized `public_product_id`, marketplace/channel names, bands, indexes, ratios, and scores.

The project includes two privacy layers:

1. Column scan: blocks sensitive column names and private/raw financial columns.
2. Content scan: counts ASIN-like, known-private-identifier, order-ID-like, postal-code-like, and currency-marker values without printing the leaked values.

The content scan is **full-frame by default**: it inspects every row of every public
output (including the ~141K-row `anonymized_master.csv`), not just a sample. It uses
vectorized string matching so the full scan stays fast. A `max_rows` parameter exists
purely as a developer performance toggle; it defaults to `None` (full scan), and the
full-frame guarantee only holds while no cap is set.

Private raw files stay in `data/private_raw/` and private mapping files stay in `data/private_mapping/`. Both folders are ignored by Git.

