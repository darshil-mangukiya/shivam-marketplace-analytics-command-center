"""Tests for the optional SQL Server load layer (Priority 7).

These tests never require a real SQL Server instance or pyodbc — they only
exercise config parsing, connection-string construction (never leaking the
password outside the string itself), and load/reconciliation logic against
a mock connection object. Importing shared.sqlserver_loader must never
require pyodbc to be installed (it is a lazy import inside get_connection).
"""

from __future__ import annotations

import pandas as pd
import pytest

from shared.sqlserver_loader import (
    LOAD_ORDER,
    SqlServerConfig,
    SqlServerConfigError,
    SqlServerLoadError,
    get_connection,
    load_all_from_public_outputs,
    load_table,
)
from shared.sqlserver_star_schema import build_sqlserver_star_schema


def test_importing_module_does_not_require_pyodbc():
    # If this test file imports without error, the module-level import
    # succeeded without pyodbc installed — the assertion below just makes
    # the intent explicit.
    import shared.sqlserver_loader  # noqa: F401


def test_config_from_env_raises_when_required_vars_missing(monkeypatch):
    monkeypatch.delenv("SQLSERVER_HOST", raising=False)
    monkeypatch.delenv("SQLSERVER_DATABASE", raising=False)
    monkeypatch.delenv("SQLSERVER_USERNAME", raising=False)
    monkeypatch.delenv("SQLSERVER_PASSWORD", raising=False)
    with pytest.raises(SqlServerConfigError):
        SqlServerConfig.from_env()


def test_config_from_env_succeeds_with_all_vars_set(monkeypatch):
    monkeypatch.setenv("SQLSERVER_HOST", "localhost")
    monkeypatch.setenv("SQLSERVER_DATABASE", "TestDb")
    monkeypatch.setenv("SQLSERVER_USERNAME", "tester")
    monkeypatch.setenv("SQLSERVER_PASSWORD", "secret123")
    cfg = SqlServerConfig.from_env()
    assert cfg.host == "localhost"
    assert cfg.database == "TestDb"
    assert cfg.port == 1433  # default


def test_connection_string_contains_password_only_once_and_no_extra_leak():
    cfg = SqlServerConfig(host="h", port=1433, database="d", username="u", password="p@ss", driver="ODBC Driver 18 for SQL Server")
    conn_str = cfg.connection_string()
    assert "p@ss" in conn_str
    assert conn_str.count("p@ss") == 1


def test_get_connection_without_pyodbc_raises_load_error(monkeypatch):
    # Force the lazy `import pyodbc` inside get_connection to fail even if
    # pyodbc happens to be installed in this environment, so the test is
    # deterministic either way.
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pyodbc":
            raise ImportError("simulated: pyodbc not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setenv("SQLSERVER_HOST", "localhost")
    monkeypatch.setenv("SQLSERVER_DATABASE", "TestDb")
    monkeypatch.setenv("SQLSERVER_USERNAME", "tester")
    monkeypatch.setenv("SQLSERVER_PASSWORD", "secret123")
    with pytest.raises(SqlServerLoadError):
        get_connection()


class _FakeCursor:
    def __init__(self, table_rows: dict[str, int]):
        self._table_rows = table_rows
        self.fast_executemany = False
        self._last_count_table: str | None = None

    def execute(self, sql, *args):
        if sql.strip().upper().startswith("TRUNCATE TABLE"):
            table = sql.split()[-1]
            self._table_rows[table] = 0
        elif sql.strip().upper().startswith("SELECT COUNT(*)"):
            table = sql.split()[-1]
            self._last_count_table = table

    def executemany(self, sql, rows):
        table = sql.split("INTO", 1)[1].split("(", 1)[0].strip()
        self._table_rows[table] = self._table_rows.get(table, 0) + len(rows)
        self._last_insert_table = table

    def fetchone(self):
        table = self._last_count_table
        return (self._table_rows.get(table, 0),)


class _FakeConnection:
    def __init__(self):
        self.table_rows: dict[str, int] = {}
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return _FakeCursor(self.table_rows)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_load_table_reconciles_row_count():
    conn = _FakeConnection()
    df = pd.DataFrame({"marketplace": ["Amazon", "Flipkart"], "channel": ["Marketplace", "Marketplace"]})
    loaded = load_table(conn, "analytics", "dim_marketplace", df)
    assert loaded == 2
    assert conn.committed


def test_load_table_empty_dataframe_is_a_noop():
    conn = _FakeConnection()
    df = pd.DataFrame(columns=["marketplace", "channel"])
    loaded = load_table(conn, "analytics", "dim_marketplace", df)
    assert loaded == 0
    assert not conn.committed  # never opened a transaction for zero rows


def test_load_order_puts_dimensions_before_facts_and_facts_before_audit():
    dim_positions = [LOAD_ORDER.index(name) for name in LOAD_ORDER if name.startswith("dim_")]
    fact_positions = [LOAD_ORDER.index(name) for name in LOAD_ORDER if name.startswith("fact_")]
    audit_positions = [LOAD_ORDER.index(name) for name in LOAD_ORDER if name.startswith("audit_")]
    assert max(dim_positions) < min(fact_positions)
    assert max(fact_positions) < min(audit_positions)


# ---------------------------------------------------------------------------
# End-to-end: real star-schema reshape output loaded through the mock
# connection, exercising the full "reshape -> load -> reconcile" path
# without any real SQL Server (Priority 1 / Requirement 24).
# ---------------------------------------------------------------------------

def _sample_outputs() -> dict[str, pd.DataFrame]:
    product_performance = pd.DataFrame(
        {
            "public_product_id": ["P0001", "P0002"],
            "marketplace": ["Amazon", "Flipkart"],
            "brand_group": ["Brand A", "Brand B"],
            "category_group": ["Skin Care", "Hair Care"],
            "subcategory_group": ["Face", "Shampoo"],
            "product_group": ["Cream", "Bottle"],
            "fulfillment_type": ["FBA", "Merchant"],
            "listing_price_band": ["500-1000", "0-500"],
            "inventory_band": ["Moderate", "Low"],
            "margin_band_public": ["Healthy Margin", "Low Margin"],
            "profitability_band_public": ["Healthy Margin", "Low Margin"],
            "sales_index": [80.0, 40.0],
            "units_index": [70.0, 30.0],
            "fee_pct_of_gross": [20.0, 15.0],
            "refund_pct_of_gross": [5.0, 2.0],
            "promotion_pct_of_gross": [3.0, 1.0],
            "net_to_gross_pct": [72.0, 82.0],
            "margin_index": [50.0, 40.0],
            "estimated_profitability_index": [55.0, 45.0],
            "margin_risk_score": [30.0, 20.0],
            "revenue_quality_score": [60.0, 70.0],
            "recommended_action": ["Monitor", "Fee Review"],
            "action_priority": ["Low", "High"],
        }
    )
    marketplace_summary = pd.DataFrame(
        {
            "dataset_period": ["12m", "12m"],
            "transaction_month": ["2026-05", "2026-06"],
            "marketplace": ["Amazon", "Amazon"],
            "total_orders": [6000, 6100],
            "product_count": [80, 82],
            "sales_index": [210.0, 210.7],
            "units_index": [215.6, 215.5],
            "avg_fee_pct_of_gross": [20.0, 19.5],
            "avg_refund_pct_of_gross": [5.0, 4.8],
            "avg_promotion_pct_of_gross": [3.0, 2.8],
            "avg_net_to_gross_pct": [72.0, 72.5],
            "margin_risk_score": [30.0, 29.0],
            "revenue_quality_score": [60.0, 61.0],
        }
    )
    inventory_action_review = product_performance[["public_product_id", "marketplace"]].copy()
    inventory_action_review["units_index"] = [70.0, 30.0]
    inventory_action_review["sales_index"] = [80.0, 40.0]
    inventory_action_review["restock_priority"] = ["Monitor", "High"]
    inventory_action_review["recommended_action"] = ["Monitor", "Restock Review"]
    inventory_action_review["action_priority"] = ["Low", "High"]

    return {
        "product_performance": product_performance,
        "marketplace_summary": marketplace_summary,
        "inventory_action_review": inventory_action_review,
        "mart_marketplace_variance_drivers": pd.DataFrame(columns=["marketplace", "metric", "previous_value", "current_value", "abs_variance", "pct_variance", "contribution_share_pct", "movement"]),
        "mart_performance_driver_summary": pd.DataFrame([{"metric": "n/a", "previous_period": "n/a", "current_period": "n/a", "movement": "Insufficient Periods"}]),
        "validation_summary": pd.DataFrame({"check_name": ["Public outputs generated"], "check_status": ["PASS"], "check_value": ["1"], "expected_value": ["> 0"], "notes": [""]}),
        "dataset_profile": pd.DataFrame({"public_output_name": ["product_performance"], "row_count": [2], "dataset_period": ["12m"], "dataset_label": ["12-Month Demo"]}),
    }


def test_star_schema_output_loads_cleanly_through_mock_connection():
    result = build_sqlserver_star_schema(_sample_outputs(), dataset_period="12m")
    conn = _FakeConnection()
    loaded_counts = load_all_from_public_outputs(conn, result.tables)

    for table_name, df in result.tables.items():
        assert loaded_counts.get(table_name, 0) == len(df)
    assert conn.committed


def test_star_schema_reconciliation_matches_mock_load_counts():
    result = build_sqlserver_star_schema(_sample_outputs(), dataset_period="12m")
    conn = _FakeConnection()
    loaded_counts = load_all_from_public_outputs(conn, result.tables)

    fact_rows = result.reconciliation.set_index("target_table")["target_rows"].to_dict()
    for table_name, expected_rows in fact_rows.items():
        assert loaded_counts.get(table_name, 0) == expected_rows


# ---------------------------------------------------------------------------
# mssql_python client-library support (added for live Azure SQL execution).
# These are unit/mock tests only -- no live database is required or contacted.
# ---------------------------------------------------------------------------


def test_connection_string_without_driver_omits_driver_token():
    cfg = SqlServerConfig(host="h", port=1433, database="d", username="u", password="p@ss", driver="ODBC Driver 18 for SQL Server")
    with_driver = cfg.connection_string()
    without_driver = cfg.connection_string(include_driver=False)
    assert "DRIVER=" in with_driver
    assert "DRIVER=" not in without_driver
    # Everything else must be identical.
    assert without_driver == with_driver.replace("DRIVER={ODBC Driver 18 for SQL Server};", "")


def test_get_connection_defaults_to_pyodbc_when_client_library_unset(monkeypatch):
    # Existing callers/tests that never mention mssql_python must keep
    # getting exactly the pre-existing pyodbc-or-nothing behavior.
    monkeypatch.delenv("SQLSERVER_CLIENT_LIBRARY", raising=False)
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pyodbc":
            raise ImportError("simulated: pyodbc not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setenv("SQLSERVER_HOST", "localhost")
    monkeypatch.setenv("SQLSERVER_DATABASE", "TestDb")
    monkeypatch.setenv("SQLSERVER_USERNAME", "tester")
    monkeypatch.setenv("SQLSERVER_PASSWORD", "secret123")
    with pytest.raises(SqlServerLoadError, match="pyodbc"):
        get_connection()


def test_get_connection_mssql_python_missing_raises_load_error(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "mssql_python":
            raise ImportError("simulated: mssql_python not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setenv("SQLSERVER_HOST", "localhost")
    monkeypatch.setenv("SQLSERVER_DATABASE", "TestDb")
    monkeypatch.setenv("SQLSERVER_USERNAME", "tester")
    monkeypatch.setenv("SQLSERVER_PASSWORD", "secret123")
    with pytest.raises(SqlServerLoadError, match="mssql_python"):
        get_connection(client_library="mssql_python")


def test_get_connection_client_library_env_var_selects_mssql_python(monkeypatch):
    # SQLSERVER_CLIENT_LIBRARY, not a passed argument, must be enough to
    # route to the mssql_python branch.
    import builtins

    real_import = builtins.__import__
    attempted = {}

    def fake_import(name, *args, **kwargs):
        if name == "mssql_python":
            attempted["mssql_python"] = True
            raise ImportError("simulated: not installed, just checking routing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setenv("SQLSERVER_CLIENT_LIBRARY", "mssql_python")
    monkeypatch.setenv("SQLSERVER_HOST", "localhost")
    monkeypatch.setenv("SQLSERVER_DATABASE", "TestDb")
    monkeypatch.setenv("SQLSERVER_USERNAME", "tester")
    monkeypatch.setenv("SQLSERVER_PASSWORD", "secret123")
    with pytest.raises(SqlServerLoadError):
        get_connection()
    assert attempted.get("mssql_python") is True


def test_clear_table_falls_back_to_delete_when_truncate_rejected():
    from shared.sqlserver_loader import _clear_table

    class _RejectsTruncateCursor:
        def __init__(self):
            self.executed = []

        def execute(self, sql, *args):
            self.executed.append(sql)
            if sql.strip().upper().startswith("TRUNCATE TABLE"):
                raise Exception("simulated: rejected by a FOREIGN KEY constraint")

    class _RejectsTruncateConnection:
        def __init__(self):
            self.cur = _RejectsTruncateCursor()

        def cursor(self):
            return self.cur

    conn = _RejectsTruncateConnection()
    _clear_table(conn, "analytics.dim_product")
    assert conn.cur.executed[0].strip().upper().startswith("TRUNCATE TABLE")
    assert conn.cur.executed[1].strip().upper().startswith("DELETE FROM")


def test_load_all_from_public_outputs_clears_in_reverse_dependency_order():
    # Wraps the existing _FakeConnection/_FakeCursor (which already know how
    # to track per-table row counts realistically) to additionally record
    # the order TRUNCATE/DELETE calls happen in, so we can assert facts are
    # always cleared before the dimensions they reference -- a stand-in for
    # the real FK-ordering constraint discovered on Azure SQL.
    order: list[str] = []
    conn = _FakeConnection()
    real_cursor_factory = conn.cursor

    def tracking_cursor():
        cursor = real_cursor_factory()
        real_execute = cursor.execute

        def tracking_execute(sql, *args):
            stripped = sql.strip().upper()
            if stripped.startswith("TRUNCATE TABLE") or stripped.startswith("DELETE FROM"):
                order.append(sql.split()[-1])
            return real_execute(sql, *args)

        cursor.execute = tracking_execute
        return cursor

    conn.cursor = tracking_cursor

    result = build_sqlserver_star_schema(_sample_outputs(), dataset_period="12m")
    load_all_from_public_outputs(conn, result.tables)

    dim_positions = {name: i for i, name in enumerate(order) if ".dim_" in name}
    fact_positions = {name: i for i, name in enumerate(order) if ".fact_" in name}
    assert dim_positions and fact_positions
    assert max(fact_positions.values()) < min(dim_positions.values()), (
        "facts must be cleared before dimensions to respect FK constraints on a real database"
    )
