# Testing Record

Run the full suite from the repository root:

```bash
python -m pytest
```

The suite covers:

- upload parsing, normalization, joining, and anonymization;
- YAML contract loading and live-path validation;
- safe quarantine records and privacy scans;
- public-output schemas, ranges, counts, and metric behavior;
- Streamlit data loading, filtering, labels, charts, and exports;
- recommendation rules and workflow transitions;
- variance calculation and activity-aware period selection;
- Azure SQL star-schema construction and loader behavior.

Additional validation commands:

```bash
python python/run_privacy_scan.py
make validate
```

The CI workflow runs Python compilation, pytest, the privacy scan, contract loading, public-output schema checks, and workflow artifact validation on Python 3.11 and 3.13.

Most recent result: **245 passed**.
