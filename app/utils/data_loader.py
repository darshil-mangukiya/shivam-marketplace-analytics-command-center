from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from app.utils.anonymizer import assert_public_frame_is_safe
from app.utils.data_cleaner import AppDataError
from app.utils.export_utils import outputs_to_zip_bytes
from app.utils.joiner import join_transactions_to_product_master
from app.utils.metrics import build_public_outputs_from_private, compute_kpis
from app.utils.product_master_loader import load_product_and_channel_context
from app.utils.recommendations import executive_summary_text
from app.utils.transaction_cleaner import clean_transaction_file
from app.utils.validation import build_validation_summary
from shared.contracts import validate_public_outputs
from shared.dataset_labels import dataset_label, dataset_mode_badge, dataset_period_from_profile
from shared.quarantine import combine_quarantine, quarantine_totals, summarize_quarantine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DIR = PROJECT_ROOT / "data" / "public"


def _safe_filename(name: str, fallback: str) -> str:
    cleaned = Path(name or fallback).name.replace(" ", "_")
    return cleaned or fallback


def save_uploaded_file(uploaded_file: BinaryIO, destination: Path, fallback_name: str) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(getattr(uploaded_file, "name", fallback_name), fallback_name)
    path = destination / filename
    data = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
    path.write_bytes(data)
    return path


def run_analysis_from_uploads(product_upload: BinaryIO, transaction_upload: BinaryIO) -> dict[str, object]:
    return run_analysis_from_uploads_with_options(product_upload, transaction_upload, dataset_period="custom")


GENERIC_PRIVATE_VALUE_EXCLUSIONS = {
    "adjustment",
    "order",
    "refund",
    "service fee",
    "transfer",
}


def _looks_like_private_identifier(value: object, column: str) -> bool:
    text = str(value).strip()
    if not text:
        return False
    lowered = text.lower()
    if lowered in GENERIC_PRIVATE_VALUE_EXCLUSIONS:
        return False
    if lowered in {"nan", "none", "null", "n/a"}:
        return False

    if column in {"order_postal"}:
        return bool(re.fullmatch(r"[1-9][0-9]{5}", text))
    if column in {"asin1"}:
        return bool(re.fullmatch(r"B0[A-Z0-9]{8}", text, re.IGNORECASE))
    if column in {"seller_sku", "sku", "order_id", "listing_id", "product_id"}:
        has_identifier_shape = any(char.isdigit() for char in text) or any(char in text for char in "-_/")
        return len(text) >= 5 and has_identifier_shape
    if column in {"item_name", "item_description", "description"}:
        word_count = len(re.findall(r"\w+", text))
        return len(text) >= 20 and word_count >= 3
    return False


def _known_private_values(products: pd.DataFrame, transactions: pd.DataFrame) -> list[object]:
    values: list[object] = []
    for df, columns in [
        (products, ["seller_sku", "asin1", "item_name", "item_description", "listing_id", "product_id"]),
        (transactions, ["sku", "order_id", "description", "order_postal"]),
    ]:
        for col in columns:
            if col in df.columns:
                values.extend(
                    value
                    for value in df[col].dropna().astype(str).unique().tolist()
                    if _looks_like_private_identifier(value, col)
                )
    return values


def run_analysis_from_uploads_with_options(
    product_upload: BinaryIO,
    transaction_upload: BinaryIO,
    *,
    dataset_period: str = "custom",
) -> dict[str, object]:
    if product_upload is None:
        raise AppDataError("Please upload the Product / Cost / Channel Master Excel file.")
    if transaction_upload is None:
        raise AppDataError("Please upload the Marketplace Transaction CSV file.")

    with tempfile.TemporaryDirectory(prefix="shivam_streamlit_") as temp_dir:
        session_dir = Path(temp_dir)
        product_path = save_uploaded_file(product_upload, session_dir, "product_master.xlsx")
        transaction_path = save_uploaded_file(transaction_upload, session_dir, "monthly_transaction.csv")

        product_master, marketplace_channels, product_metrics = load_product_and_channel_context(product_path)
        transactions, transaction_metrics = clean_transaction_file(transaction_path)
        transaction_metrics["dataset_period"] = dataset_period

        # Combine the two upload-side quarantine ledgers (product master +
        # transactions) into one safe summary. Both ledgers already contain
        # only the documented safe metadata columns (source_name, row_number,
        # error_code, error_category, validation_rule, reason, severity,
        # timestamp) — never a raw cell value — enforced structurally by
        # shared.quarantine.assert_quarantine_is_safe() inside combine_quarantine().
        combined_quarantine_ledger = combine_quarantine(
            product_metrics.get("quarantine_ledger"),
            transaction_metrics.get("quarantine_ledger"),
        )
        quarantine_category_summary = summarize_quarantine(combined_quarantine_ledger)
        rejected_ledger_rows = (
            combined_quarantine_ledger[combined_quarantine_ledger["severity"] == "reject"]
            if not combined_quarantine_ledger.empty
            else combined_quarantine_ledger
        )
        warning_ledger_rows = (
            combined_quarantine_ledger[combined_quarantine_ledger["severity"] == "warn"]
            if not combined_quarantine_ledger.empty
            else combined_quarantine_ledger
        )
        combined_quarantine_totals = quarantine_totals(
            rejected_ledger_rows,
            warning_ledger_rows,
            total_input_rows=int(product_metrics.get("contract_total_rows", 0) or 0)
            + int(transaction_metrics.get("contract_total_rows", 0) or 0),
            accepted_rows=int(product_metrics.get("contract_accepted_rows", 0) or 0)
            + int(transaction_metrics.get("contract_accepted_rows", 0) or 0),
        )

        private_master, join_metrics = join_transactions_to_product_master(
            transactions,
            product_master,
            product_metrics,
            marketplace_channels,
        )
        private_master["dataset_period"] = dataset_period
        known_values = _known_private_values(product_master, transactions)
        outputs = build_public_outputs_from_private(private_master, dataset_period=dataset_period)

        # Public-output contract validation — BEFORE the privacy scan, per
        # the "Build -> Contract validation -> Privacy validation -> Publish"
        # policy. Raises PublicOutputContractError (a schema-drift bug, not a
        # user data problem) and stops the export outright on any
        # reject-level violation; never silently drops or ships rows.
        #
        # There are 6 declared public-output contracts (see
        # shared.contracts.PUBLIC_OUTPUT_CONTRACT_FILES), one of which is
        # `validation_summary` itself. This creates a genuine one-way
        # dependency cycle, not an oversight to "fix around":
        # `validation_summary` is BUILT FROM the contract-check results of
        # the other 5 declared-contract outputs (it reports them as a row,
        # see build_validation_summary's `public_output_contract_results`
        # argument below), so it cannot exist before that first check runs —
        # but `validation_summary` is also one of the 6 declared-contract
        # outputs, so it must itself be checked once it exists. We resolve
        # this with two calls to the SAME validate_public_outputs() entry
        # point against two disjoint sets of outputs (the 5 that exist
        # already, then the 1 that exists only after being built), so
        # together every declared contract is checked exactly once — this
        # is not a duplicate check of the same output, and no contract is
        # loaded or evaluated twice.
        public_output_contract_results = validate_public_outputs(outputs)  # Five outputs exist at this point.

        validation_summary = build_validation_summary(
            outputs,
            product_metrics,
            transaction_metrics,
            join_metrics,
            known_private_values=known_values,
            quarantine_totals_summary=combined_quarantine_totals,
            public_output_contract_results=public_output_contract_results,
        )
        outputs["validation_summary"] = validation_summary

        # 6th of 6: validate_summary now exists — check it against its own
        # contract (contracts/public_outputs/validation_summary.yml) and
        # fold the result into the same results dict, still fail-closed on
        # any reject-level violation, still before the privacy scan below.
        public_output_contract_results.update(
            validate_public_outputs({"validation_summary": outputs["validation_summary"]})
        )

        for name, df in outputs.items():
            if name != "validation_summary":
                assert_public_frame_is_safe(df, known_private_values=known_values)

        kpis = compute_kpis(outputs, join_metrics)
        summary_text = executive_summary_text(outputs, join_metrics)

        # Do not return private source frames; Streamlit keeps only safe outputs and count metrics.
        # quarantine_category_summary/combined_quarantine_totals are already
        # safe aggregates (counts by category/code/severity) — never a raw
        # rejected value.
        return {
            "outputs": outputs,
            "kpis": kpis,
            "product_metrics": product_metrics,
            "transaction_metrics": transaction_metrics,
            "join_metrics": join_metrics,
            "validation_summary": validation_summary,
            "summary_text": summary_text,
            "zip_bytes": outputs_to_zip_bytes(outputs),
            "mode": "Upload Analysis",
            "dataset_period": dataset_period,
            "dataset_label": dataset_label(dataset_period),
            "mode_badge": dataset_mode_badge("Upload Analysis", dataset_period),
            "quarantine_totals": combined_quarantine_totals,
            "quarantine_category_summary": quarantine_category_summary,
            "public_output_contract_results": public_output_contract_results,
        }


def _read_public_outputs(public_dir_str: str) -> dict[str, pd.DataFrame]:
    outputs: dict[str, pd.DataFrame] = {}
    for path in sorted(Path(public_dir_str).glob("*.csv")):
        outputs[path.stem] = pd.read_csv(path)
    return outputs


try:  # pragma: no cover - caching is a Streamlit-runtime optimization only
    import streamlit as st

    @st.cache_data(show_spinner=False)
    def _read_public_outputs_cached(public_dir_str: str, signature: tuple) -> dict[str, pd.DataFrame]:
        # `signature` (filename + mtime per file) is part of the cache key so the
        # cache invalidates automatically whenever the public CSVs are regenerated.
        # st.cache_data returns a fresh copy per call, so callers may safely mutate.
        return _read_public_outputs(public_dir_str)

    def load_public_output_sample(public_dir: Path) -> dict[str, pd.DataFrame]:
        paths = sorted(public_dir.glob("*.csv"))
        signature = tuple((p.name, p.stat().st_mtime_ns) for p in paths)
        return _read_public_outputs_cached(str(public_dir), signature)

except Exception:  # pragma: no cover - tests / non-Streamlit contexts
    def load_public_output_sample(public_dir: Path) -> dict[str, pd.DataFrame]:
        return _read_public_outputs(str(public_dir))


def _validation_value(validation_summary: pd.DataFrame, check_names: list[str], default: int = 0) -> int:
    if validation_summary.empty or "check_name" not in validation_summary.columns:
        return default
    lookup = validation_summary.copy()
    lookup["_check_key"] = lookup["check_name"].astype(str).str.strip().str.lower()
    for check_name in check_names:
        matches = lookup[lookup["_check_key"] == check_name.strip().lower()]
        if matches.empty or "check_value" not in matches.columns:
            continue
        value = matches.iloc[0]["check_value"]
        try:
            return int(float(str(value).replace(",", "")))
        except (TypeError, ValueError):
            continue
    return default


def build_demo_result(public_dir: Path = PUBLIC_DIR, dataset_period: str = "latest") -> dict[str, object]:
    outputs = load_public_output_sample(public_dir)
    if not outputs:
        raise AppDataError(
            "No public demo outputs were found. Run the pipeline or upload files once to generate public CSVs."
        )
    validation_summary = outputs.get("validation_summary", pd.DataFrame())
    product = outputs.get("product_performance", pd.DataFrame())
    anonymized = outputs.get("anonymized_master", pd.DataFrame())
    order_row_count = int((anonymized.get("transaction_type_group", pd.Series(dtype=str)) == "Order").sum())
    actual_dataset_period = dataset_period_from_profile(
        outputs.get("dataset_profile", pd.DataFrame()),
        fallback=dataset_period,
        transaction_rows=len(anonymized),
        order_rows=order_row_count,
    )
    if "dataset_profile" in outputs and not outputs["dataset_profile"].empty:
        profile = outputs["dataset_profile"].copy()
        profile["dataset_period"] = actual_dataset_period
        if "dataset_label" not in profile.columns:
            profile["dataset_label"] = dataset_label(
                actual_dataset_period,
                transaction_rows=len(anonymized),
                order_rows=order_row_count,
            )
        outputs["dataset_profile"] = profile
    product_master_rows = _validation_value(
        validation_summary,
        ["Raw product master loaded", "product master row count > 0"],
        default=int(product.get("public_product_id", pd.Series(dtype=str)).nunique()),
    )
    join_metrics = {
        "transaction_row_count": int(len(anonymized)),
        "order_row_count": order_row_count,
        "product_master_row_count": product_master_rows,
        "transaction_rows_with_sku": int(len(anonymized)),
        "matched_transaction_rows": int(len(anonymized)),
        "unmatched_transaction_rows": 0,
        "unique_transaction_skus": "masked",
        "unique_product_master_skus": "masked",
        "matched_skus": "masked",
        "unmatched_transaction_skus": 0,
        "unmatched_listing_skus": 0,
        "join_coverage_pct": 100.0 if len(anonymized) else 0.0,
        # Marketplace-channel enrichment remains unavailable while the
        # Marketplace_Channel_Master mapping keys are incomplete.
        "marketplace_join_coverage_pct": 0.0,
        "channel_mapping_status": "Unavailable",
        "duplicate_sku_count": 0,
    }
    product_metrics = {
        "product_master_row_count": join_metrics["product_master_row_count"],
        "marketplace_channel_row_count": len(outputs.get("marketplace_channel_performance", pd.DataFrame())),
        "marketplace_count": int(anonymized.get("marketplace", pd.Series(dtype=str)).nunique()) if not anonymized.empty else 0,
    }
    transaction_metrics = {
        "transaction_row_count": join_metrics["transaction_row_count"],
        "order_row_count": join_metrics["order_row_count"],
        "dataset_period": actual_dataset_period,
        "marketplace_count": product_metrics["marketplace_count"],
    }
    validation_summary = build_validation_summary(outputs, product_metrics, transaction_metrics, join_metrics)
    outputs["validation_summary"] = validation_summary
    kpis = compute_kpis(outputs, join_metrics)
    summary_text = executive_summary_text(outputs, join_metrics)
    return {
        "outputs": outputs,
        "kpis": kpis,
        "product_metrics": product_metrics,
        "transaction_metrics": transaction_metrics,
        "join_metrics": join_metrics,
        "validation_summary": validation_summary,
        "summary_text": summary_text,
        "zip_bytes": outputs_to_zip_bytes(outputs),
        "mode": "Sample Demo",
        "dataset_period": actual_dataset_period,
        "dataset_label": dataset_label(
            actual_dataset_period,
            transaction_rows=join_metrics["transaction_row_count"],
            order_rows=join_metrics["order_row_count"],
        ),
        "mode_badge": dataset_mode_badge(
            "Sample Demo",
            actual_dataset_period,
            transaction_rows=join_metrics["transaction_row_count"],
            order_rows=join_metrics["order_row_count"],
        ),
    }
