# INC-002 — Misleading Error on a Structurally Valid, Zero-Row Transaction File

This defect was found during upload UAT and is covered by regression tests.

## Impact

Uploading a valid Amazon-style transaction CSV (correct 13-line
preamble, correct header row) with zero actual data rows produced: "The
transaction date column could not be parsed" — a message that points the
user at the wrong problem (it implies a format/date issue, when the real
issue is simply "no rows").

## Detection

Caught by the project owner during a manual UAT walkthrough (UAT-03):
they deliberately tested a valid-schema, zero-row file and observed the
misleading message.

## Root Cause

Date-column parsing ran unconditionally after header detection, before
any explicit check for "the file has zero data rows." An empty column
naturally fails to parse as a date, producing a generic parse-failure
message that didn't name the actual condition.

## Fix

`app/utils/transaction_cleaner.py` now checks for zero data rows
immediately after header/schema detection and **before** date parsing,
raising a specific `AppDataError` ("no transaction rows") when that's the
real condition — never a misleading generic date-parse error for this
case.

## Regression Test

`tests/test_transaction_cleaner_row_validation.py` — asserts the exact
message text for a zero-row, valid-header file, and separately verifies
the original date-parse error still fires correctly for the actual case it
was built for (malformed dates on a file with real rows).

## Prevention

Error-message specificity became an explicit acceptance criterion pattern
for this project: any new validation gate must be checked in the order
that produces the most specific, actionable message — not just the first
check that happens to fail.

## Evidence

- `app/utils/transaction_cleaner.py`
- `tests/test_transaction_cleaner_row_validation.py`
- `docs/uat/uat_test_cases.csv` UAT-03
- `business_analysis/defect_log.csv` DEF-02
