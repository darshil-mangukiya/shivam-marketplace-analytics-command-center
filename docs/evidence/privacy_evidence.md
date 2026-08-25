# Privacy Evidence

| Item | Status |
|---|---|
| Column-name allowlist scan | Implemented and runtime-validated — `shared/privacy.py:unsafe_columns` |
| Full-frame content scan (ASIN/SKU/order-ID/postal/currency/long-title patterns) | Implemented and runtime-validated — `shared/privacy.py:content_privacy_scan`; `python python/run_privacy_scan.py` → `content_hit_count: 0`, `is_safe: true` on the full 17-output public dataset |
| Enforcement point before any frame reaches the UI or export layer | Implemented and runtime-validated — `app/utils/anonymizer.py:assert_public_frame_is_safe`, called on every output including the 3 new variance marts |
| New-mart privacy review | Implemented and runtime-validated — adding `mart_marketplace_variance_drivers`, `mart_product_variance_contributors`, and `mart_performance_driver_summary` required two narrow, documented allowlist additions (the `narrative` column, for the same reason `action_reason` was already allowlisted; and `narrative` added to the order-pattern exemption list for the same reason `marketplace`/`channel` already were) — no existing protection was weakened, and the same scan continues to check every column, including `narrative`, for ASIN/known-identifier/order-ID/postal/currency patterns |
| Data contracts as a second, declarative privacy layer | Implemented — `contracts/public_outputs/*.yml` each declare a `forbidden_fields` list independently of `shared/privacy.py`, checked by `shared/contracts.py:validate_dataframe` |
| Quarantine records never carry raw cell values | Implemented and tested — `shared/quarantine.py:assert_quarantine_is_safe` (schema allowlist guard) + `tests/test_contracts.py::test_rejected_records_never_contain_raw_cell_values` |
| Session-only upload processing (no persistent storage of uploaded files) | Pre-existing, re-verified — `app/utils/data_loader.py` uses `tempfile.TemporaryDirectory`, auto-cleaned; only the already-privacy-scanned `outputs` dict and count metrics are kept in `st.session_state` |

## Full-frame privacy scan output

```
content_hit_count: 0
is_safe: true
```

## Test coverage

`tests/test_content_privacy_scan.py`, `tests/test_full_frame_privacy_scan.py`,
`tests/test_financial_masking.py`, `tests/test_marketplace_channel_coverage_honesty.py`,
the 19 `tests/test_contracts.py` / `tests/test_quarantine.py` tests, and the
new `tests/test_dashboard_filters.py` private-identifier-exposure tests
(confirming the Product filter added to Product, Brand & Category
Intelligence only ever reads `public_product_id`, never a real SKU/ASIN)
all passed in the current 245-test suite run.
