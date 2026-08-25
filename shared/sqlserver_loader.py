"""SQL Server and Azure SQL reporting-warehouse load layer.

The Streamlit startup path does not import this module. Both `pyodbc` and `mssql_python` are
imported lazily inside `get_connection()` so importing this module never
requires either database driver to be installed.

The Azure SQL runtime used Microsoft's `mssql-python` driver. The `pyodbc`
path remains available for compatible SQL Server connections. See
`docs/evidence/azure_sql_runtime_evidence.md` for deployment and reconciliation results.

Configuration is environment-variable driven; see `.env.example`.

`load_all_from_public_outputs()` expects the dimension/fact DataFrames
already produced by `shared/sqlserver_star_schema.py:build_sqlserver_star_schema()`
— that module does the flat-mart -> star-schema reshape; this module only
handles the load mechanics (connection, transaction, row-count
reconciliation, load ordering).
"""

from __future__ import annotations

import dataclasses
import os
from typing import Any

import pandas as pd


class SqlServerConfigError(Exception):
    pass


class SqlServerLoadError(Exception):
    """Raised on a connection/transaction failure. Never includes the
    connection string or credentials in its message (only host/db name)."""


@dataclasses.dataclass(frozen=True)
class SqlServerConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    driver: str

    @classmethod
    def from_env(cls) -> "SqlServerConfig":
        required = {
            "SQLSERVER_HOST": os.environ.get("SQLSERVER_HOST"),
            "SQLSERVER_DATABASE": os.environ.get("SQLSERVER_DATABASE"),
            "SQLSERVER_USERNAME": os.environ.get("SQLSERVER_USERNAME"),
            "SQLSERVER_PASSWORD": os.environ.get("SQLSERVER_PASSWORD"),
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise SqlServerConfigError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                "Copy .env.example to .env and fill in real values, or export "
                "these variables directly. SQL Server is optional — the public "
                "Streamlit demo does not require any of this."
            )
        return cls(
            host=required["SQLSERVER_HOST"],
            port=int(os.environ.get("SQLSERVER_PORT", "1433")),
            database=required["SQLSERVER_DATABASE"],
            username=required["SQLSERVER_USERNAME"],
            password=required["SQLSERVER_PASSWORD"],
            driver=os.environ.get("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server"),
        )

    def connection_string(self, *, include_driver: bool = True) -> str:
        """Build the ODBC-style connection string.

        `include_driver=False` omits the `DRIVER={...}` token: Microsoft's
        `mssql_python` driver bundles its own ODBC runtime and treats
        `driver` as a reserved keyword it controls itself, rejecting a
        connection string that specifies one (unlike `pyodbc`, which
        requires it to select a system-installed driver). Both variants
        otherwise carry the identical server/database/credential/encryption
        settings — Azure SQL requires `Encrypt=yes` regardless of driver."""
        driver_clause = f"DRIVER={{{self.driver}}};" if include_driver else ""
        return (
            f"{driver_clause}SERVER={self.host},{self.port};"
            f"DATABASE={self.database};UID={self.username};PWD={self.password};"
            "Encrypt=yes;TrustServerCertificate=no;"
        )


def get_connection(config: SqlServerConfig | None = None, *, client_library: str | None = None):
    """Open a DB-API 2.0 connection to SQL Server / Azure SQL.

    `client_library` selects the Python driver: `"pyodbc"` (default, unchanged
    behavior for every pre-existing caller/test) or `"mssql_python"` (Microsoft's
    pure-Python driver with a bundled ODBC runtime — the supported path for live
    Azure SQL execution on macOS, where installing `msodbcsql18`/`unixODBC`
    system packages is unnecessary). Defaults to the `SQLSERVER_CLIENT_LIBRARY`
    environment variable when not passed explicitly, so existing code and tests
    that never set that variable keep using `pyodbc` exactly as before — this is
    an additive connection-boundary change, not a replacement of the existing
    design. Both drivers implement the same DB-API surface
    (`cursor()`/`execute()`/`executemany()`/`commit()`/`rollback()`/`fetchone()`)
    that `load_table()` and `load_all_from_public_outputs()` already use, and
    both accept the identical ODBC-style connection string produced by
    `SqlServerConfig.connection_string()` — qmark (`?`) parameter placeholders
    are supported by mssql_python as well as pyodbc, so no query-building code
    needed to change.

    Raises SqlServerLoadError with a message that never contains the password
    if the driver is missing or the connection fails."""
    library = (client_library or os.environ.get("SQLSERVER_CLIENT_LIBRARY") or "pyodbc").strip().lower()
    cfg = config or SqlServerConfig.from_env()

    if library == "mssql_python":
        try:
            import mssql_python  # local import: never a hard dependency of the app
        except ImportError as exc:
            raise SqlServerLoadError(
                "mssql_python is not installed. Install it only if you intend to "
                "use the optional SQL Server / Azure SQL reporting warehouse via "
                "Microsoft's mssql-python driver — it is not required to run the "
                "public Streamlit demo."
            ) from exc
        try:
            return mssql_python.connect(cfg.connection_string(include_driver=False), timeout=10)
        except Exception as exc:  # pragma: no cover - requires a real server
            raise SqlServerLoadError(
                f"Could not connect to SQL Server at {cfg.host}:{cfg.port}/{cfg.database} "
                f"via mssql_python. Underlying driver error: {type(exc).__name__}."
            ) from exc

    try:
        import pyodbc  # local import: never a hard dependency of the app
    except ImportError as exc:
        raise SqlServerLoadError(
            "pyodbc is not installed. Install it (and a platform ODBC driver "
            "for SQL Server) only if you intend to use the optional SQL "
            "Server reporting warehouse — it is not required to run the "
            "public Streamlit demo."
        ) from exc

    try:
        return pyodbc.connect(cfg.connection_string(), timeout=10)
    except Exception as exc:  # pragma: no cover - requires a real server
        raise SqlServerLoadError(
            f"Could not connect to SQL Server at {cfg.host}:{cfg.port}/{cfg.database}. "
            f"Underlying driver error: {type(exc).__name__}."
        ) from exc


# Deterministic load order: dimensions before facts, and within facts, the
# order that respects foreign-key dependencies declared in
# sql/sqlserver/03_create_facts.sql.
LOAD_ORDER: list[str] = [
    "dim_product",
    "dim_marketplace",
    "dim_month",
    "dim_fulfillment",
    "fact_marketplace_activity",
    "fact_product_performance",
    "fact_inventory_action",
    "fact_performance_variance",
    "audit_validation",
    "audit_dataset_profile",
]


def _clear_table(connection: Any, qualified_name: str) -> None:
    """Empty one table for a full reload.

    TRUNCATE resets identity values when SQL Server permits it. Dimension
    tables referenced by foreign keys fall back to DELETE.
    """
    cursor = connection.cursor()
    try:
        cursor.execute(f"TRUNCATE TABLE {qualified_name}")
    except Exception:
        cursor.execute(f"DELETE FROM {qualified_name}")


def load_table(connection: Any, table_schema: str, table_name: str, df: pd.DataFrame, *, truncate_first: bool = True) -> int:
    """Load a DataFrame into one warehouse table with row-count reconciliation.

    Empties the target table first by default (full-reload semantics,
    appropriate for this warehouse refreshed from a batch pipeline
    run — see `_clear_table` for why this is TRUNCATE-with-a-DELETE-fallback,
    not a plain TRUNCATE) then inserts every row inside one transaction,
    rolling back and raising SqlServerLoadError on any failure so a partial
    load never silently succeeds.

    Callers loading a full warehouse with foreign-key relationships (e.g.
    `load_all_from_public_outputs`) must clear every table in reverse
    dependency order (facts/audit before dimensions) *before* calling this
    function to insert in forward dependency order — pass
    `truncate_first=False` in that case, since the tables are already
    empty; see `load_all_from_public_outputs`.
    """
    if df.empty:
        return 0
    cursor = connection.cursor()
    qualified_name = f"{table_schema}.{table_name}"
    try:
        if truncate_first:
            _clear_table(connection, qualified_name)
        columns = list(df.columns)
        placeholders = ", ".join("?" for _ in columns)
        column_list = ", ".join(columns)
        insert_sql = f"INSERT INTO {qualified_name} ({column_list}) VALUES ({placeholders})"
        cursor.fast_executemany = True
        # Pandas represents a missing value in a numeric column as NaN
        # (float64), never as Python's None -- a real behavior discovered
        # loading dim_month's Unknown-member row (key 0) into Azure SQL: a
        # bare NaN sent as a parameter is not the same thing as a SQL NULL
        # and the driver rejects it for a typed numeric column. Convert
        # every NaN to None before binding so nullable columns receive a
        # true SQL NULL, exactly as the target schema's `NULL` constraints
        # (see sql/sqlserver/02_create_dimensions.sql) expect.
        clean = df[columns].astype(object).where(df[columns].notna(), None)
        cursor.executemany(insert_sql, clean.values.tolist())
        connection.commit()
    except Exception as exc:
        connection.rollback()
        raise SqlServerLoadError(f"Load failed for {qualified_name}: {type(exc).__name__}") from exc

    cursor.execute(f"SELECT COUNT(*) FROM {qualified_name}")
    (loaded_row_count,) = cursor.fetchone()
    if int(loaded_row_count) != len(df):
        raise SqlServerLoadError(
            f"Row-count reconciliation failed for {qualified_name}: "
            f"expected {len(df)}, found {loaded_row_count}."
        )
    return int(loaded_row_count)


def _qualify(table_name: str) -> tuple[str, str]:
    schema = "audit" if table_name.startswith("audit_") else "analytics"
    return schema, f"{schema}.{table_name}"


def load_all_from_public_outputs(connection: Any, outputs: dict[str, pd.DataFrame]) -> dict[str, int]:
    """Load the star-schema tables for a full warehouse refresh. `outputs`
    is expected to already be the `.tables` dict returned by
    `shared.sqlserver_star_schema.build_sqlserver_star_schema()` — this
    function only handles load mechanics (order, transaction, row-count
    reconciliation), not the flat-mart -> dimension/fact reshape itself.

    Two-phase reload, required for FK-constrained tables (see
    `_clear_table`'s docstring): first empty every present table in
    *reverse* LOAD_ORDER (facts/audit before the dimensions they reference),
    then insert every present table in *forward* LOAD_ORDER (dimensions
    before facts, satisfying each fact row's FK at insert time). A
    single-phase "truncate-then-insert per table in forward order" would
    fail the very first dimension table on a real SQL Server/Azure SQL
    database, because TRUNCATE is rejected whenever *any* FK references the
    table being truncated — independent of insert order.
    """
    tables_present = [name for name in LOAD_ORDER if name in outputs]

    for table_name in reversed(tables_present):
        _, qualified_name = _qualify(table_name)
        _clear_table(connection, qualified_name)
        # Commit after EVERY table's clear, not once at the end of the loop.
        # Real behavior discovered on live Azure SQL: a later table's DELETE
        # (e.g. dim_month, once its TRUNCATE is rejected per _clear_table's
        # docstring) can fail an FK-conflict check against an EARLIER table
        # in this same loop (e.g. fact_performance_variance) even though
        # that earlier table was already emptied moments before in the same
        # uncommitted transaction -- the constraint check did not reliably
        # observe the session's own uncommitted DELETE. Committing after
        # each table removes the ambiguity: every subsequent constraint
        # check sees fully durable state. This was reproduced deterministically
        # against the Azure SQL Database targeted by this warehouse.
        connection.commit()

    results: dict[str, int] = {}
    for table_name in tables_present:
        schema, _ = _qualify(table_name)
        results[table_name] = load_table(connection, schema, table_name, outputs[table_name], truncate_first=False)
    return results
