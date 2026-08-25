"""Minimal, stdlib-only .env loader for the OPTIONAL live Azure SQL path.

This is intentionally not `python-dotenv` — adding a new pinned dependency
to `requirements.txt` for a one-off local credential-loading convenience
would be scope creep for a feature the public Streamlit demo never needs
(see `shared/sqlserver_loader.py`'s module docstring). This helper is not
imported by the core app; only the live Azure SQL integration scripts under
`python/` import it.

Loads `KEY=VALUE` lines from a `.env` file at the repository root into
`os.environ` (never overwriting a variable already set in the real
environment). Never logs, prints, or returns the values it loads.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


def load_dotenv_if_present(path: Path = ENV_PATH) -> int:
    """Load KEY=VALUE lines from `path` into os.environ. Returns the count
    of variables set (never their names or values, to keep this safe to
    call from a script that prints its own return value casually)."""
    if not path.exists():
        return 0
    count = 0
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or key in os.environ:
            continue
        os.environ[key] = value
        count += 1
    return count
