# User Acceptance Testing Plan

## Scope

The 33 UAT scenarios cover:

- valid, missing, empty, and malformed uploads;
- demo loading and navigation across 9 pages;
- reconciliation and validation results;
- marketplace, period, and product filters;
- recommendation, inventory, profitability, and variance views;
- privacy-safe CSV and ZIP exports;
- workflow queue construction and status transitions.

## Execution methods

Automated cases cite a pytest test in `uat_test_cases.csv`. Manual cases require a browser walkthrough for visual layout, readability, and interaction behavior.

Run automated coverage:

```bash
python -m pytest
```

Run manual cases:

```bash
streamlit run app/streamlit_app.py
```

Record the observed result and status in `uat_execution_results.csv`. A case receives PASS only after its cited automated test or manual step completes successfully.

Current summary: 24 automated and 9 manual cases, 33 PASS.
