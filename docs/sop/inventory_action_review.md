# SOP: Inventory Action Review

**Applies to:** an Inventory Planner (or equivalent persona) reviewing
restock/slow-mover recommendations and tracking their disposition.

## Steps

1. **Open Page 6 (Inventory, Restock & Action Review)** in Sample Demo or
   Upload Analysis mode.
2. **Sort by `action_priority`.** Focus on `High` first, then `Medium`;
   `Low`/`Monitor` rows need no immediate action.
3. **Read `action_reason`** for each flagged row — it names the exact
   condition that triggered the recommendation (e.g. "High indexed unit
   movement with low inventory or restock priority").
4. **Cross-check `inventory_band`** on the same row before acting — a
   `Restock Review` flag paired with a `High` inventory band is worth a
   second look (the recommendation rule already accounts for this, but a
   manual sanity check catches edge cases).
5. **Track the decision using the workflow layer:**
   ```bash
   python python/run_workflow.py   # rebuild the exception queue from the current outputs
   ```
   Then, in Python (or a future UI surface):
   ```python
   from shared.workflow import load_exception_queue, transition_exception, append_action_log, save_exception_queue

   queue = load_exception_queue()
   queue, log_row = transition_exception(
       queue, exception_id="IAR-P0004-Meesho",
       new_status="Under Review", reviewer_persona="Inventory Planner",
       reason="Checking real inventory band before approving restock.",
   )
   append_action_log(log_row)
   save_exception_queue(queue)
   ```
6. **Close the loop.** Move the exception through `Under Review` →
   `Approved`/`Rejected` → `Actioned Externally`/`Closed` as the real-world
   decision is made, always with a `reason`.

## Reminder

This workflow tracks the *decision*, not the physical restocking itself —
`Actioned Externally` means "the restock order was placed outside this
system," recorded here for traceability, not that this system placed the
order. See `artifacts/workflow/README.md` for the full honesty statement.
