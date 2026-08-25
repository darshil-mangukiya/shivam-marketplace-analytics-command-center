# SOP: Failed Refresh Triage

**Applies to:** a pipeline run or upload that produced an error, a `FAIL`
row, or an unexpected result.

## Step 1 — Identify which layer failed

| Symptom | Likely layer | Where to look |
|---|---|---|
| App shows a specific, named error (e.g. "no transaction rows", "does not contain recognizable marketplace transaction columns") | Upload-side cleaning/contract validation working as designed | This is expected, controlled behavior, not a bug — read the message, it names the actual problem |
| App shows a Python traceback | An unhandled case — a real bug | Note the traceback, check `app/utils/*_cleaner.py` and `app/utils/data_loader.py` for where it originates |
| `validation_summary.csv` has a `FAIL` row | Upstream data or join issue | Check `product_metrics`/`transaction_metrics`/`join_metrics` referenced by that row's `check_name` |
| `PublicOutputContractError` raised | A generated public output failed its contract | Inspect the named output's columns and types against `contracts/public_outputs/*.yml` |
| Privacy scan reports `is_safe: false` | A raw private value reached a public output — **stop, do not publish** | Check which output/column via the scan's per-output breakdown; trace it back through `shared/public_output_builder.py` |
| `WorkflowError` raised from `shared/workflow.py` | An invalid/out-of-sequence status transition was attempted | Check `VALID_TRANSITIONS` in `shared/workflow.py` for what's actually allowed from the current status |

## Step 2 — Reproduce with a test, not a one-off script

Prefer adding/running a targeted pytest (e.g.
`python -m pytest tests/test_contract_integration.py -k <case> -v`) over
manual clicking — the existing test suite already covers most known
failure shapes (UAT-02/03/04 and their regression tests).

## Step 3 — Never silently patch around a `FAIL`

- Do not edit `contracts/*.yml` to make a bad row pass without first
  confirming, against real data, whether the contract or the data is
  wrong (see the real example in `business_analysis/defect_log.csv`,
  DEF-05/DEF-06).
- Do not delete a failing row from a public output by hand — if the
  pipeline produced it, find and fix the root cause in code.

## Step 4 — Re-run the full gate before considering it resolved

```bash
python -m pytest
python python/run_privacy_scan.py
```

Both must be clean before the fix is considered done — see
[`docs/bi/release_governance.md`](../bi/release_governance.md).
