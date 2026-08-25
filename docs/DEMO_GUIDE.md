# Demo Guide

Run the Streamlit app:

```bash
streamlit run app/streamlit_app.py
```

To run the app on a custom port (for example, port 3000):

```bash
streamlit run app/streamlit_app.py --server.port 3000
```

Demo mode loads public CSV outputs from `data/public/`. If period-specific public outputs are not available, it uses the latest generated public output set.

Upload mode accepts:

- Product / cost / channel master Excel
- Monthly or multi-period transaction CSV

After analysis, review the dashboard pages and use the Demo & Export Center to download public-safe outputs as CSV or ZIP.

The pipeline produces **14 public CSV files**: 12 analytical outputs plus
`dataset_profile.csv` and `validation_summary.csv`.

