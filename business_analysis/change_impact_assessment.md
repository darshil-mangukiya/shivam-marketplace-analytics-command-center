# Change Impact Assessment: Workflow Layer

The workflow layer converts high- and medium-priority product and inventory recommendations into trackable exceptions.

| Area | Impact | Control |
|---|---|---|
| Public outputs | Read-only consumption of product and inventory action CSVs | Source files remain unchanged |
| Runtime | Separate CLI path in `python/run_workflow.py` | Streamlit and the main pipeline have no dependency on the workflow CLI |
| Storage | JSON exception queue and CSV action log | Files contain public fields and workflow metadata |
| Privacy | New artifacts reuse privacy-scanned product IDs and grouped values | Tests assert the allowed field set |
| State changes | Status transitions follow `VALID_TRANSITIONS` | Invalid transitions raise `WorkflowError` |
| Recovery | Existing queue statuses are preserved during refresh | Stable exception IDs support deterministic refresh |

The implementation is additive to the analytical pipeline. Changes to its status model require updates to `shared/workflow.py`, workflow tests, the artifact README, and any consuming interface.
