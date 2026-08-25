"""Formal data-contract validation layer.

Contracts are declarative YAML files under `contracts/` describing required
fields, types, nullability, ranges, allowed values, and privacy
classification for the two upload types and a representative set of public
outputs. This module is the single, reusable validation layer around those
contracts — it does not duplicate the existing procedural cleaning logic in
`app/utils/*_cleaner.py`.

Upload-side: `app/utils/transaction_cleaner.py` and
`app/utils/product_master_cleaner.py` call `validate_dataframe()` as the
last step of cleaning, after existing header/schema detection and
normalization. Output-side: `app/utils/data_loader.py` calls
`validate_public_outputs()` (below) on every generated public mart that has
a contract, before the privacy scan, on every live upload analysis run.

Row-level failures are turned into quarantine records
(`shared/quarantine.py`) that never carry the offending private cell value —
only safe metadata (source name, row number, error code/category, the rule
that fired, severity, timestamp).
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

CONTRACTS_DIR = Path(__file__).resolve().parents[1] / "contracts"

REJECTED_ROW_COLUMNS = [
    "source_name",
    "row_number",
    "error_code",
    "error_category",
    "validation_rule",
    "reason",
    "severity",
    "timestamp",
]


class ContractError(Exception):
    """Raised for a contract-level problem that prevents row-level validation
    (e.g. the contract file itself is missing a required field entirely)."""


def load_contract(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_absolute():
        path = CONTRACTS_DIR / path
    if not path.exists():
        raise ContractError(f"Contract file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        contract = yaml.safe_load(handle)
    if not isinstance(contract, dict) or "fields" not in contract:
        raise ContractError(f"Contract file is malformed (missing 'fields'): {path}")
    return contract


def _now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat(timespec="seconds")


def _reject_record(
    source_name: str,
    row_number: int | None,
    error_code: str,
    error_category: str,
    validation_rule: str,
    reason: str,
    severity: str,
) -> dict[str, Any]:
    return {
        "source_name": source_name,
        "row_number": row_number,
        "error_code": error_code,
        "error_category": error_category,
        "validation_rule": validation_rule,
        "reason": reason,
        "severity": severity,
        "timestamp": _now_iso(),
    }


def _is_type_ok(value: Any, field_type: str) -> bool:
    if pd.isna(value):
        return True  # nullability is checked separately
    if field_type == "number":
        try:
            float(value)
        except (TypeError, ValueError):
            return False
        return True
    if field_type == "string":
        return True  # anything can be coerced to string; we only reject on emptiness elsewhere
    return True


def validate_dataframe(
    df: pd.DataFrame,
    contract: dict[str, Any],
    source_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Validate a DataFrame against a contract.

    Returns (accepted_df, rejected_records_df, warning_records_df).

    - A row is REJECTED (excluded from accepted_df) when a required field is
      missing/null, fails its declared type, or a forbidden field is present
      with `forbidden_field_present: reject` severity.
    - A row is WARNED (included in accepted_df, but logged) for soft
      violations: out-of-range numeric values or unrecognized-but-plausible
      categorical values, when the contract's severity for that violation is
      `warn`.
    - Rejected/warning records never contain the offending cell value —
      only field names, codes, and rule descriptions.
    """
    severity_map = contract.get("validation_severity", {})
    fields: dict[str, dict[str, Any]] = contract.get("fields", {})
    forbidden = set(contract.get("forbidden_fields", []) or [])

    reject_records: list[dict[str, Any]] = []
    warn_records: list[dict[str, Any]] = []

    present_forbidden = forbidden & set(df.columns)
    if present_forbidden:
        severity = severity_map.get("forbidden_field_present", "reject")
        for column in present_forbidden:
            reject_records.append(
                _reject_record(
                    source_name,
                    None,
                    "FORBIDDEN_FIELD_PRESENT",
                    "PRIVACY_ERROR",
                    f"forbidden_fields:{column}",
                    f"Column '{column}' is on the contract's forbidden list and must never appear in this dataset.",
                    severity,
                )
            )
        if severity == "reject":
            return df.iloc[0:0].copy(), pd.DataFrame(reject_records, columns=REJECTED_ROW_COLUMNS), pd.DataFrame(warn_records, columns=REJECTED_ROW_COLUMNS)

    if df.empty:
        empty = pd.DataFrame(columns=REJECTED_ROW_COLUMNS)
        return df.copy(), empty, empty

    reject_mask = pd.Series(False, index=df.index)

    for field_name, spec in fields.items():
        if field_name not in df.columns:
            if spec.get("required"):
                severity = severity_map.get("missing_required_field", "reject")
                reject_records.append(
                    _reject_record(
                        source_name,
                        None,
                        "MISSING_REQUIRED_COLUMN",
                        "SCHEMA_ERROR",
                        f"fields.{field_name}.required",
                        f"Required column '{field_name}' is absent from the uploaded file.",
                        severity,
                    )
                )
                if severity == "reject":
                    reject_mask[:] = True
            continue

        series = df[field_name]
        field_type = spec.get("type", "string")
        required = bool(spec.get("required"))
        nullable = spec.get("nullable", not required)

        is_null = series.isna() | series.astype("string").fillna("").str.strip().eq("")
        if required and not nullable:
            missing_rows = df.index[is_null]
            if len(missing_rows) > 0:
                severity = severity_map.get("missing_required_field", "reject")
                for row_number in missing_rows:
                    reject_records.append(
                        _reject_record(
                            source_name,
                            int(row_number),
                            "MISSING_REQUIRED_VALUE",
                            "VALIDATION_ERROR",
                            f"fields.{field_name}.nullable=false",
                            f"Required field '{field_name}' is missing on this row.",
                            severity,
                        )
                    )
                if severity == "reject":
                    reject_mask.loc[missing_rows] = True

        if field_type == "number":
            non_null = df.index[~is_null]
            bad_type_rows = [i for i in non_null if not _is_type_ok(series.loc[i], "number")]
            if bad_type_rows:
                severity = severity_map.get("type_mismatch", "reject")
                for row_number in bad_type_rows:
                    reject_records.append(
                        _reject_record(
                            source_name,
                            int(row_number),
                            "TYPE_MISMATCH",
                            "VALIDATION_ERROR",
                            f"fields.{field_name}.type=number",
                            f"Field '{field_name}' could not be interpreted as a number on this row.",
                            severity,
                        )
                    )
                if severity == "reject":
                    reject_mask.loc[bad_type_rows] = True

            numeric = pd.to_numeric(series, errors="coerce")
            lower = spec.get("min")
            upper = spec.get("max")
            if lower is not None or upper is not None:
                out_of_range = pd.Series(False, index=df.index)
                if lower is not None:
                    out_of_range |= numeric < lower
                if upper is not None:
                    out_of_range |= numeric > upper
                out_of_range &= numeric.notna()
                if out_of_range.any():
                    severity = severity_map.get("out_of_range", "warn")
                    for row_number in df.index[out_of_range]:
                        record = _reject_record(
                            source_name,
                            int(row_number),
                            "OUT_OF_RANGE",
                            "VALIDATION_ERROR",
                            f"fields.{field_name}.range=[{lower},{upper}]",
                            f"Field '{field_name}' is outside the expected range on this row.",
                            severity,
                        )
                        (reject_records if severity == "reject" else warn_records).append(record)
                    if severity == "reject":
                        reject_mask.loc[df.index[out_of_range]] = True

        allowed_values = spec.get("allowed_values")
        if allowed_values:
            non_null = df.index[~is_null]
            unknown_rows = [i for i in non_null if str(series.loc[i]).strip() not in set(allowed_values)]
            if unknown_rows:
                severity = severity_map.get("unknown_value", "warn")
                for row_number in unknown_rows:
                    record = _reject_record(
                        source_name,
                        int(row_number),
                        "UNKNOWN_VALUE",
                        "VALIDATION_ERROR",
                        f"fields.{field_name}.allowed_values",
                        f"Field '{field_name}' has a value outside the documented allowed set on this row.",
                        severity,
                    )
                    (reject_records if severity == "reject" else warn_records).append(record)
                if severity == "reject":
                    reject_mask.loc[unknown_rows] = True

        if spec.get("unique"):
            duplicated = series.duplicated(keep="first") & ~is_null
            if duplicated.any():
                severity = severity_map.get("duplicate_primary_key", "warn")
                for row_number in df.index[duplicated]:
                    record = _reject_record(
                        source_name,
                        int(row_number),
                        "DUPLICATE_KEY",
                        "VALIDATION_ERROR",
                        f"fields.{field_name}.unique",
                        f"Field '{field_name}' repeats a value already seen earlier in the file.",
                        severity,
                    )
                    (reject_records if severity == "reject" else warn_records).append(record)
                if severity == "reject":
                    reject_mask.loc[df.index[duplicated]] = True

    accepted = df.loc[~reject_mask].copy()
    rejected_df = pd.DataFrame(reject_records, columns=REJECTED_ROW_COLUMNS) if reject_records else pd.DataFrame(columns=REJECTED_ROW_COLUMNS)
    warning_df = pd.DataFrame(warn_records, columns=REJECTED_ROW_COLUMNS) if warn_records else pd.DataFrame(columns=REJECTED_ROW_COLUMNS)
    return accepted, rejected_df, warning_df


# ---------------------------------------------------------------------------
# Public-output contract validation.
#
# These 6 contracts describe already-public, already-privacy-scanned marts.
# Unlike upload validation, a reject-level violation here means the PIPELINE
# produced a non-compliant public output — a schema-drift bug, not a user
# data-quality problem. Per the fail-closed policy: a reject-level violation
# on a public output must STOP the export, never silently drop rows or
# silently continue. out_of_range/unknown_value stay warn-severity exactly
# as declared in each contract, so harmless drift
# doesn't block a legitimate export.
# ---------------------------------------------------------------------------

PUBLIC_OUTPUT_CONTRACT_FILES: dict[str, str] = {
    "anonymized_master": "public_outputs/anonymized_master.yml",
    "marketplace_summary": "public_outputs/marketplace_summary.yml",
    "product_performance": "public_outputs/product_performance.yml",
    "inventory_action_review": "public_outputs/inventory_action_review.yml",
    "validation_summary": "public_outputs/validation_summary.yml",
    "dataset_profile": "public_outputs/dataset_profile.yml",
}


class PublicOutputContractError(Exception):
    """Raised when a generated public output fails its declared contract at
    reject severity. This indicates a pipeline schema-drift bug, not a user
    upload problem — reject-level failures here are never silently
    swallowed or used to narrow an exported frame."""


def validate_public_outputs(outputs: dict[str, "pd.DataFrame"]) -> dict[str, dict[str, int]]:
    """Validate every public output that has a declared contract in
    `PUBLIC_OUTPUT_CONTRACT_FILES`. Outputs without a contract, or that are
    empty, are skipped (not every mart has a contract yet — see
    `contracts/public_outputs/`). Returns a per-output row-count summary.

    Raises `PublicOutputContractError` immediately on the first output with
    any reject-level violation — never continues past a reject-level
    failure and never silently narrows the exported frame.
    """
    results: dict[str, dict[str, int]] = {}
    for name, contract_relpath in PUBLIC_OUTPUT_CONTRACT_FILES.items():
        frame = outputs.get(name)
        if frame is None or frame.empty:
            continue
        contract = load_contract(contract_relpath)
        accepted, rejected, warnings = validate_dataframe(frame, contract, f"{name}.csv")
        results[name] = {
            "total_rows": int(len(frame)),
            "accepted_rows": int(len(accepted)),
            "rejected_rows": int(len(rejected)),
            "warning_rows": int(len(warnings)),
        }
        if not rejected.empty:
            error_codes = sorted(rejected["error_code"].astype(str).unique().tolist())
            raise PublicOutputContractError(
                f"Public output '{name}' failed contract validation with {len(rejected)} "
                f"reject-level violation(s) ({', '.join(error_codes)}). Export stopped — "
                "this indicates a pipeline schema-drift bug, not a user upload problem."
            )
    return results
