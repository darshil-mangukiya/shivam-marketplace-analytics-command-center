# Non-Functional Requirements

| Category | Requirement | Verification |
|---|---|---|
| Determinism | Identical inputs produce identical analytical tables and workflow identifiers | Repeated-run tests and reconciliation |
| Privacy | Public frames exclude private identifiers and raw financial fields | Column and full-frame content scans |
| Reliability | Validation failures stop affected processing with a specific error | Contract and application tests |
| Traceability | Requirements link to source fields, rules, outputs, interfaces, and tests | `docs/requirements_traceability_matrix.csv` |
| Maintainability | KPI formulas and recommendation rules have centralized implementation references | `shared/kpi_registry.py`, `shared/recommendations.py` |
| Portability | The local app runs on Python 3.11+ with pinned dependencies | CI matrix and `requirements.txt` |
| Recoverability | Workflow refresh preserves existing state; failed database loads roll back | Workflow and SQL loader tests |
| Observability | Validation, reconciliation, queue, and action-log artifacts expose run results | `data/public/validation_summary.csv`, `artifacts/` |
| Usability | Users can upload two files or load the checked-in public outputs | Streamlit tests and UAT |
| Performance | The current 141,000-row transaction dataset completes within a practical local batch window | Local pipeline execution |

Current scale observations describe the checked-in dataset. Capacity and latency should be remeasured for materially larger inputs or concurrent use.
