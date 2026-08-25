# SOP: Data Refresh & Validation

**Applies to:** running a new analysis (Sample Demo regeneration or a real
upload) and confirming it is trustworthy before relying on it.

## Steps

1. **Choose the mode.**
   - Sample Demo: no files needed, reads `data/public/*.csv`.
   - Upload Analysis: prepare the product/cost/channel master Excel and
     the marketplace transaction CSV.
2. **Run the refresh.**
   - CLI (regenerates the public demo dataset):
     `python python/run_pipeline.py --dataset 12m` (or `1m`/`3m`/`6m`).
   - App (Upload Analysis): use the file uploaders on the Streamlit app's
     sidebar.
3. **Check the validation summary.** Open Page 7 (Data Validation &
   Privacy Checks) or read `data/public/validation_summary.csv`. Every row
   should read `PASS`; a `WARN` row (e.g. "Marketplace-channel mapping
   status") is expected and documented — it is not a failure. Any `FAIL`
   row means stop and investigate before trusting the output.
4. **Check the contract/quarantine rows** (Upload Analysis only). Look for
   "Upload contract validation — rejected rows" and "Public output
   contract validation" rows. Non-zero rejected rows means some source
   rows were excluded — check `quarantine_category_summary` for why
   (safe, aggregate reasons only, no raw values).
5. **Re-run the privacy scan.** `python python/run_privacy_scan.py` —
   confirm `content_hit_count: 0`, `is_safe: true`.
6. **Confirm the row counts make sense.** Compare
   `dataset_profile.csv`'s row counts against what you expect from the
   source file(s) — a large unexplained drop usually means a schema or
   contract issue, not a data problem.
7. **If refreshing the workflow layer too:** run
   `python python/run_workflow.py` to rebuild
   `artifacts/workflow/exception_queue.json` from the freshly generated
   action-review outputs.

## When to escalate

If step 3 or 5 shows a `FAIL`/`is_safe: false`, do not publish or export
the output — follow
[`docs/sop/failed_refresh_triage.md`](failed_refresh_triage.md) instead.
