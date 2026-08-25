# Streamlit Application

Run the app from the repository root:

```bash
streamlit run app/streamlit_app.py
```

The default mode accepts two files:

- Product / Cost / Channel Master Excel workbook
- Marketplace Transaction CSV

After validation, **Run Full Analysis** cleans, joins, anonymizes, analyzes, validates, and prepares downloadable public outputs. Sample Demo mode loads the checked-in `data/public/` outputs.

## Pages

1. Executive Overview
2. Marketplace Performance
3. Product, Brand & Category Intelligence
4. Fees, Refunds & Revenue Quality
5. Profitability & Margin Intelligence
6. Inventory, Restock & Action Review
7. Data Validation & Privacy Checks
8. Demo & Export Center
9. Performance Drivers & Root Cause

The application displays public product IDs, grouped fields, indexes, ratios, scores, bands, and action labels. Upload processing uses temporary storage, and public frames pass privacy checks before display or export.
