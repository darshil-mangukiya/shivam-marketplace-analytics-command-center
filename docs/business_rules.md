# Business Rules

Each rule cites its implementation. See [kpi_catalog.md](kpi_catalog.md) for
the metric-level reference.

## Ratio and index rules — `shared/metrics.py`

- **`pct_of_gross(numerator, gross, signed=False)`**: `numerator / gross * 100`,
  clipped to `[0, 300]` (or `[-300, 300]` when `signed=True`); returns `0` when
  gross ≤ 0. Used for fee/refund/promotion/net % of gross.
- **`index_from_values(values)`**: `value / max(values) * 100`, clipped to
  `[0, 100]`; returns all-zero when the max is ≤ 0. Used for Sales Index,
  Units Index, Order Count Index, Margin Index, Estimated Profitability Index.
- **`band_from_pct(value)`**: margin band — `< 0` → "Loss / Negative"; `< 10`
  → "Low Margin"; `< 20` → "Moderate Margin"; `< 35` → "Healthy Margin";
  else → "High Margin".

## Score rules — `shared/profitability.py`

- **Margin Risk Score** (`margin_risk_score`):
  `fee_pct*0.35 + refund_pct*0.25 + promotion_pct*0.15 + max(0, 70-net_pct)*0.15 + max(0, 30-margin_pct)*0.10`,
  clipped to `[0, 100]`, rounded to 1 decimal.
  - Band: `≥70` Critical Review, `≥45` High Risk, `≥25` Medium Risk, else Low Risk.
- **Revenue Quality Score** (`revenue_quality_score`):
  `net_pct - fee_pct*0.30 - refund_pct*0.25 - promotion_pct*0.15`, clipped to
  `[0, 100]`, rounded to 1 decimal.
  - Band: `≥80` Strong, `≥65` Healthy, `≥45` Watch, `≥25` At Risk, else Critical.

## Recommendation rules — `shared/recommendations.py`

Rules are evaluated **in order**; the first matching rule wins
(`ACTION_RULES` / `add_actions`):

| # | Action | Priority | Condition | Reason |
|---|---|---|---|---|
| 1 | Margin Risk Review | High | `margin_risk_score ≥ 70` | Critical margin-risk score from fee, refund, promotion, net, and margin signals. |
| 2 | Refund Review | High | `refund_pct_of_gross ≥ 10 AND sales_index ≥ 10` | Meaningful sales-index product with elevated refund percentage. |
| 3 | Fee Review | High | `fee_pct_of_gross ≥ 25 AND sales_index ≥ 20` | High sales-index product with elevated fee percentage. |
| 4 | Restock Review | High | `units_index ≥ 50 AND (low inventory OR high restock priority)` | High indexed unit movement with low inventory or restock priority. |
| 5 | Promotion Review | Medium | `promotion_pct_of_gross ≥ 10 AND net_to_gross_pct < 70` | Promotion percentage elevated while net-to-gross is below target. |
| 6 | Revenue Quality Review | Medium | `revenue_quality_score < 45 AND sales_index ≥ 15` | Weak revenue quality for a product with measurable indexed demand. |
| 7 | Pricing Review | Medium | `sales_index < 10 AND units_index < 10 AND high price band` | Low indexed demand for a higher-price-band listing. |
| 8 | Slow Mover Review | Low | `units_index < 10 AND high inventory band` | Low indexed unit movement with high inventory band. |
| — | Monitor | Low | none of the above | No action threshold triggered; continue monitoring. |

"Low inventory" = inventory band contains "out of stock", "very low", or
"low". "High inventory" = contains "high" or "100+". "High price band" =
listing price band contains "premium", starts with "3000"/"4000", or ends
with "+".

## Variance rules — `shared/variance_engine.py`

- A comparison requires **at least two distinct `transaction_month` values**
  in the dataset; with fewer than two, the engine returns an explicit
  "insufficient periods" result rather than fabricating a comparison
  (BR-16).
- **Absolute variance** = `current − previous`. **Percentage variance** =
  `(current − previous) / abs(previous) * 100`, undefined (`None`/`NaN`) when
  `previous == 0`, never divided-by-zero silently.
- **Contribution share** for a dimension value = its absolute variance
  divided by the sum of absolute variances of all dimension values in the
  same direction as the total change, expressed as a percentage. This is a
  descriptive decomposition (BR-17).
- Narrative sentences are template-filled from the top-ranked contributor row
  only — no free-text generation, so output is deterministic and reproducible
  from the same input marts (BR-15).

## Join / reconciliation rules — `app/utils/joiner.py`

- `join_coverage_pct` = matched transaction rows with a resolvable SKU ÷ all
  transaction rows with a non-null SKU, × 100.
- `channel_mapping_status` is hard-coded to `"Unavailable"` and
  `marketplace_join_coverage_pct` to `0.0` while the
  `Marketplace_Channel_Master` mapping keys remain incomplete (BR-05). This
  rule stays in effect until the mapping keys are populated.

## Privacy rules — `shared/privacy.py`

- A public output is "safe" only if: (a) no disallowed column name is
  present, and (b) `scan_public_outputs` finds zero ASIN-shaped,
  known-private-identifier, order-ID-shaped, postal-code-shaped, or
  currency-marker content hits across every cell of every output frame.
- `app/utils/anonymizer.assert_public_frame_is_safe` raises before any frame
  reaches the UI or export layer if either check fails — this is enforced
  code, not a convention.

## Contract / quarantine rules (`contracts/`, `shared/contracts.py`, `shared/quarantine.py`)

**Live-wired**: called by `app/utils/transaction_cleaner.py` and
`app/utils/product_master_cleaner.py` as the last step of upload cleaning,
and by `app/utils/data_loader.py` on every generated public output that has
a contract, before the privacy scan. Not a standalone/unused framework.

- A row is **rejected** if a required field is missing, fails its declared
  type, or fails a declared range/allowed-value check with reject severity.
  Rejected rows are excluded from the accepted DataFrame; if every row is
  rejected, `AppDataError` is raised with a safe, aggregate message.
- A row is **warned** (accepted but flagged) if a field fails a soft rule
  (e.g., an unrecognized-but-plausible marketplace name, or an
  out-of-range numeric value) with warn severity.
- Rejected-row records store only: `source_name`, `row_number`, `error_code`,
  `error_category`, `validation_rule`, `reason`, `severity`, and `timestamp`.
- Public-output contracts are fail-closed: a reject-level violation on a
  generated public mart raises `PublicOutputContractError` and stops the
  export outright — it never silently drops rows or silently ships a
  non-compliant output, since a reject here signals a pipeline bug, not a
  user data problem.
- **Contract coverage is 6 of 17 public outputs** —
  `anonymized_master`, `marketplace_summary`, `product_performance`,
  `inventory_action_review`, `dataset_profile`, and `validation_summary`
  each have a declared YAML contract and are live-checked on every
  generation. The remaining 11 public marts remain covered by schema,
  privacy, and regression controls. `validation_summary`'s
  check depends on a resolved build-order cycle (it reports the other 5
  outputs' contract results as a row, so it must be built after them, but
  is itself a declared-contract output, so it is checked once it exists)
  once the frame exists.
- The `sku` field on the transaction contract is `required` (the column
  must exist — enforced doubly, since the app already checks this
  procedurally) but `nullable: true` — a blank SKU is a legitimate,
  intentional case (non-product settlement lines: fees, refunds,
  adjustments — see `app/utils/joiner.py`'s `NON_PRODUCT_ID` handling), not
  a data-quality defect.
