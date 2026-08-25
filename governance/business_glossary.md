# Business / Data Glossary

The glossary covers metrics represented in the public outputs. Formulas are
cited by reference — see
[`docs/kpi_catalog.md`](../docs/kpi_catalog.md) for the authoritative
formula table.

| Term | Definition | Purpose | Formula / Logic | Grain | Limitations | Privacy Treatment | Validation Evidence |
|---|---|---|---|---|---|---|---|
| Sales Index | Relative sales scale, 0–100, indexed against the dataset's own maximum | Compare marketplaces/products without exposing raw revenue | `shared/metrics.py:index_from_values` | Marketplace or product, per month | Relative to this dataset only — not comparable across two different datasets/time windows without re-indexing | Public — no raw currency value | `tests/test_metrics.py`, `tests/test_kpi_registry.py` |
| Units Index | Relative unit-volume scale, 0–100 | Compare volume without exposing raw unit counts at a sensitive grain | `shared/metrics.py:index_from_values` | Marketplace or product, per month | Same as Sales Index | Public | `tests/test_metrics.py` |
| Fee % of Gross | Marketplace/platform fees as a percentage of gross sales, clipped [0,300] | Identify disproportionate fee burden | `shared/metrics.py:pct_of_gross` | Marketplace or product | Clipped at 300% to avoid a misleading spike on a near-zero-gross row | Public — ratio only, no raw fee amount | `tests/test_metrics.py` |
| Refund % of Gross | Refunds as a percentage of gross sales, clipped [0,300] | Identify refund-risk products/marketplaces | `shared/metrics.py:pct_of_gross` | Marketplace or product | Same clipping caveat | Public | `tests/test_metrics.py` |
| Promotion % of Gross | Promotional rebates as a percentage of gross sales, clipped [0,300] | Identify promotion-heavy segments eroding net revenue | `shared/metrics.py:pct_of_gross` | Marketplace or product | Same clipping caveat | Public | `tests/test_metrics.py` |
| Net-to-Gross % | Net proceeds as a percentage of gross sales, signed, clipped [-300,300] | Single summary of overall revenue retention | `shared/metrics.py:pct_of_gross (signed=True)` | Marketplace or product | Signed to allow a negative result (net loss) to be visible, not floored to 0 | Public | `tests/test_metrics.py` |
| **Estimated Profitability Index** | 0–100 index built from margin-related public ratios | Directional profitability signal | `shared/public_output_builder.py:add_public_metrics` | Product | Uses available cost and fee inputs; excludes tax and overhead | Public | `tests/test_public_outputs.py` |
| Margin Risk Score | 0–100 composite score from fee/refund/promotion/net/margin percentages | Flag products needing a margin-risk review | `shared/profitability.py:margin_risk_score` | Product | A composite heuristic, not a certified risk model | Public | `tests/test_profitability.py` |
| Revenue Quality Score | 0–100 composite score rewarding high net % and penalizing fee/refund/promotion drag | Rank products/channels by revenue "cleanliness" | `shared/profitability.py:revenue_quality_score` | Product, marketplace channel | Same heuristic caveat as Margin Risk Score | Public | `tests/test_profitability.py` |
| Recommended Action / Action Priority | Categorical flag (e.g. "Restock Review", "High") from ordered business rules | Turn analysis into an actionable next step | `shared/recommendations.py:ACTION_RULES` | Product | First-matching-rule-wins ordering; not a machine-learned prioritization | Public — categorical only | `tests/test_recommendations.py` |
| Exception / Workflow Status | Trackable lifecycle state for a high/medium-priority recommendation (New, Under Review, …, Closed) | Track review progress | `shared/workflow.py` | Exception (one per flagged product×marketplace×source-output) | Local workflow state | Public-safe fields only | `tests/test_workflow.py` |
| Marketplace-Channel Mapping Status | Fixed value `"Unavailable"` | Report channel mapping availability | `app/utils/joiner.py` (hard-coded) | Dataset-level | The current `Marketplace_Channel_Master` keys are incomplete | Public | `tests/test_public_outputs.py` |
| Excluded Trailing Period | A calendar month excluded from period-over-period comparison because it has zero real activity | Prevent a fabricated "-100%" comparison against an empty period | `shared/variance_engine.py:variance_excluded_trailing_periods` | Dataset-level, per comparison | Only excludes *trailing* zero-activity periods, not mid-series gaps (which would indicate a different data-quality issue) | Public | `tests/test_variance_engine.py` |

## Privacy classification legend

- **Public** — safe for a public repository/screenshot; passes the
  content scan in `shared/privacy.py`.
- **Private** — never leaves the private processing layer; excluded from
  every public output and from every artifact in this repository's
  tracked files.

## Profitability interpretation

Profitability metrics are directional estimates derived from the available
cost, fee, refund, promotion, and revenue-quality fields.
