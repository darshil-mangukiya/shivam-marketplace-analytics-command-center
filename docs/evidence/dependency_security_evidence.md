# Dependency Security

Application dependencies are pinned in `requirements.txt`. Azure SQL's optional `pyodbc` driver is isolated in `requirements-sqlserver-optional.txt`.

The dependency check uses:

```bash
python -m pip check
pip-audit -r requirements.txt
```

The last clean-room scan of the pinned application set reported no broken requirements and no known vulnerabilities. The scan included resolved transitive dependencies. Security findings are point-in-time results and should be rerun before a release.

The repository keeps database drivers optional because the Streamlit application and its test suite operate on the checked-in public outputs without a database connection.
