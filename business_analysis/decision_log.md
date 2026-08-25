# Decision Log

| ID | Decision | Rationale |
|---|---|---|
| D-01 | Publish indexes, ratios, bands, and public product IDs | Preserves analytical comparisons while excluding raw identifiers and financial amounts |
| D-02 | Label profitability measures as estimates | Available costs and fees support prioritization rather than audited profit reporting |
| D-03 | Keep Streamlit and Power BI on the public CSV layer | Both reporting surfaces remain reproducible without cloud credentials |
| D-04 | Use deterministic variance narratives | Template-based descriptions are repeatable and testable |
| D-05 | Maintain 8 YAML contracts: 2 upload and 6 public-output | The selected outputs sit on upload, dashboard, or export boundaries; other outputs retain schema, regression, and privacy coverage |
| D-06 | Skip trailing zero-activity months for default variance comparisons | Prevents an empty trailing period from appearing as a full decline while preserving the period in source data |
| D-07 | Mark marketplace-channel enrichment `Unavailable` | The source mapping keys are incomplete |
| D-08 | Use deterministic surrogate keys with an `Unknown` member | Repeated loads produce stable keys and unresolved facts remain visible |
| D-09 | Use full-table overwrite for the current batch sizes | Repeat runs are easy to reconcile and produce stable row counts |
| D-10 | Store workflow state locally in JSON and CSV | The queue needs a small, inspectable persistence layer and no additional service |
