# INC-003 — One of Six Declared Public-Output Contracts Never Executed

This defect was found during contract-path review and is covered by integration tests.

## Impact

Of 6 declared public-output data contracts, only 5 ever actually ran on
any live upload — `validation_summary`'s contract was silently skipped
every single run, even though it was correctly declared and its YAML file
was well-formed. Documentation describing "5 applicable contracts" would
have permanently understated the intended scope had this not been caught.

## Detection

Caught during a read-only clarification review that asked, specifically,
why the final report said "5 applicable" contracts when 6 were declared.
Verified empirically by instrumenting a real pipeline run and printing the
actual set of contract-result keys returned — confirmed exactly 5, never
6, every time.

## Root Cause

`app/utils/data_loader.py` called `validate_public_outputs(outputs)`
**before** `outputs["validation_summary"]` was assigned. Since
`validate_public_outputs` correctly skips any output that is `None` or
empty (by design, for outputs without data yet), `validation_summary` was
always `None` at the moment of validation and was silently skipped — a
call-ordering bug, not an intentional scope limit.

## Fix

Resolved the underlying **build-order dependency cycle**:
`validation_summary`'s own content reports the other 5 outputs' contract
results as a row, so it cannot be built before they run — but it is
itself one of the 6 declared-contract outputs, so it must be checked once
it exists. `validate_public_outputs()` (the same function, not a
duplicate implementation) is now called twice, against two disjoint
slices of the outputs dict: the 5 pre-existing outputs, then just
`validation_summary` after it's built. Each of the 6 contracts is loaded
and evaluated exactly once.

## Regression Test

`tests/test_contract_integration.py::test_public_output_contracts_are_checked_on_a_real_upload_run`
was **strengthened** from asserting 2 keys are present to asserting the
result set is **exactly** the 6 expected keys — the guard that would have
caught this bug had it existed before the fix. Three additional tests
confirm `validation_summary` is passed through
`validate_dataframe()` (not just contract-loadable), fails closed on a
forced violation, and that the 17/6/11 output-vs-contract split holds.

## Prevention

Any future test asserting "a set of things were checked" should assert
the exact expected set, not a subset — a weak assertion (checking 2 of 6
keys) is exactly what let this bug ship undetected in the first place.

## Evidence

- `app/utils/data_loader.py` (the two-call resolution, documented inline)
- `tests/test_contract_integration.py`
- `tests/test_contract_integration.py`
- `business_analysis/defect_log.csv` DEF-04
