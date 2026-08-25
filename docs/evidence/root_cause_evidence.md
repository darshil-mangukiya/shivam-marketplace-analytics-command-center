# Variance Analysis Record

`shared/variance_engine.py` calculates period-over-period metric changes and ranks marketplace and product contributions by absolute variance. The pipeline writes:

- `mart_marketplace_variance_drivers.csv`
- `mart_product_variance_contributors.csv`
- `mart_performance_driver_summary.csv`

Default comparison periods are the two latest months with recorded order activity. Trailing zero-activity periods remain in the source data and are listed in `excluded_trailing_periods`, but are skipped for the comparison.

Narratives use descriptive contribution language. When contributions are zero or fewer than two active periods exist, the engine returns an explicit no-driver or insufficient-period result.

Tests in `tests/test_variance_engine.py` cover period selection, variance calculation, ranking, deterministic output, narrative wording, zero-variance handling, and privacy-safe identifiers. UAT-27 and UAT-28 record the Streamlit page and product-contributor table walkthrough.
