# Streamlit Deployment Guide

The app entry point is `app/streamlit_app.py`. Sample Demo mode reads the checked-in public outputs and requires no secrets.

## Streamlit Community Cloud

1. Connect the GitHub repository in Streamlit Community Cloud.
2. Select branch `main` and entry point `app/streamlit_app.py`.
3. Use Python 3.11 or later.
4. Leave the secrets section empty for the CSV-backed app.
5. Deploy and run the health checks below.

`requirements.txt` contains the pinned application dependencies. The optional Azure SQL driver manifest is separate and is unnecessary for Streamlit deployment.

## Health checks

- The landing page opens without an exception.
- Sample Demo loads all 9 pages.
- Data Validation & Privacy Checks shows a passing public-output scan.
- CSV and ZIP exports contain only public fields.
- A malformed upload returns a specific validation error.

## Troubleshooting

| Symptom | Check |
|---|---|
| Demo outputs missing | Confirm `data/public/*.csv` is present in the deployed revision |
| Import error | Confirm the entry point is relative to the repository root |
| Upload rejected | Review the named field and rule in the contract error |
| Upload too large | Review `server.maxUploadSize` in `.streamlit/config.toml` |

Streamlit Community Cloud redeploys when the watched branch changes. Use a normal Git revert to restore a prior revision.
