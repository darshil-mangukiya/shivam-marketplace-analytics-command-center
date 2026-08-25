from __future__ import annotations

import pandas as pd

from shared.dataset_labels import dataset_label
from shared.privacy import scan_public_outputs


def validation_row(check_name: str, status: str, value: object, expected: object, notes: str = "") -> dict[str, str]:
    return {
        "check_name": check_name,
        "check_status": status,
        "check_value": str(value),
        "expected_value": str(expected),
        "notes": notes,
    }


def pass_warn_fail(condition: bool, warn_condition: bool = False) -> str:
    if condition:
        return "PASS"
    if warn_condition:
        return "WARN"
    return "FAIL"


def build_validation_summary(
    outputs: dict[str, pd.DataFrame],
    product_metrics: dict[str, object],
    transaction_metrics: dict[str, object],
    join_metrics: dict[str, object],
    *,
    known_private_values: list[object] | None = None,
    quarantine_totals_summary: dict[str, int] | None = None,
    public_output_contract_results: dict[str, dict[str, int]] | None = None,
) -> pd.DataFrame:
    public = outputs.get("anonymized_master", pd.DataFrame())
    action = outputs.get("product_action_review", pd.DataFrame())
    product = outputs.get("product_performance", pd.DataFrame())
    profile = outputs.get("dataset_profile", pd.DataFrame())
    scan = scan_public_outputs(outputs, known_private_values=known_private_values)
    content_hit_count = int(scan.get("content_hit_count", 0) or 0)
    dataset_period = transaction_metrics.get("dataset_period", "custom")
    generated_sales_activity = bool(pd.to_numeric(public.get("sales_index", pd.Series(dtype=float)), errors="coerce").fillna(0).gt(0).any())
    aggregated_sales_activity = bool(pd.to_numeric(product.get("sales_index", pd.Series(dtype=float)), errors="coerce").fillna(0).gt(0).any())
    rows = [
        validation_row("Raw product master loaded", "PASS" if product_metrics.get("product_master_row_count", 0) else "FAIL", product_metrics.get("product_master_row_count", 0), "> 0"),
        validation_row("Marketplace master loaded", pass_warn_fail(bool(product_metrics.get("marketplace_channel_row_count", 0)), warn_condition=True), product_metrics.get("marketplace_channel_row_count", 0), "> 0 for 5-marketplace mode"),
        validation_row("All 5 marketplaces present", pass_warn_fail(int(product_metrics.get("marketplace_count", 0) or 0) >= 5, warn_condition=bool(product_metrics.get("marketplace_count", 0))), product_metrics.get("marketplace_count", 0), "5"),
        validation_row("Each product has 5 marketplace rows", pass_warn_fail(product_metrics.get("products_missing_channel_count", 0) == 0 and bool(product_metrics.get("marketplace_channel_row_count", 0)), warn_condition=True), product_metrics.get("products_missing_channel_count", "not available"), "0 missing"),
        validation_row("Raw transaction report loaded", "PASS" if transaction_metrics.get("transaction_row_count", 0) else "FAIL", transaction_metrics.get("transaction_row_count", 0), "> 0"),
        validation_row("Dataset period detected", "PASS" if transaction_metrics.get("dataset_period") else "WARN", dataset_label(dataset_period, transaction_rows=transaction_metrics.get("transaction_row_count", 0), order_rows=transaction_metrics.get("order_row_count", 0)), "known or custom"),
        validation_row("Transaction row count valid", "PASS" if transaction_metrics.get("transaction_row_count", 0) else "FAIL", transaction_metrics.get("transaction_row_count", 0), "> 0"),
        validation_row("Order row count valid", "PASS" if transaction_metrics.get("order_row_count", 0) else "WARN", transaction_metrics.get("order_row_count", 0), "> 0 order rows"),
        validation_row("SKU column detected", "PASS" if join_metrics.get("transaction_rows_with_sku", 0) else "FAIL", join_metrics.get("transaction_rows_with_sku", 0), "> 0 rows with SKU"),
        validation_row("Marketplace column detected", "PASS" if transaction_metrics.get("marketplace_count", 0) else "WARN", transaction_metrics.get("marketplace_count", 0), "> 0 marketplaces"),
        validation_row("SKU join coverage calculated", "PASS", join_metrics.get("join_coverage_pct", 0), "calculated"),
        validation_row("Marketplace-channel mapping status", "WARN", join_metrics.get("channel_mapping_status", "Unavailable"), "available mapping keys", "Marketplace-channel enrichment is unavailable because Marketplace_Channel_Master mapping keys are incomplete."),
        validation_row("Unmatched SKUs counted", "PASS", join_metrics.get("unmatched_transaction_skus", 0), "calculated", "Only counts are shown; SKU values are private."),
        validation_row("Duplicate SKUs counted", "PASS", join_metrics.get("duplicate_sku_count", 0), "calculated"),
        validation_row("Public outputs generated", "PASS" if not public.empty else "FAIL", len(public), "> 0 rows"),
        validation_row("No sensitive columns in public outputs", "PASS" if not scan["unsafe_columns_by_output"] else "FAIL", scan["unsafe_columns_by_output"] or "safe", "safe"),
        validation_row("No ASIN-like values in public outputs", "PASS" if content_hit_count == 0 else "FAIL", content_hit_count, "0 content hits"),
        validation_row("No known SKU values in public outputs", "PASS" if content_hit_count == 0 else "FAIL", content_hit_count, "0 content hits"),
        validation_row("No order-ID-like values in public outputs", "PASS" if content_hit_count == 0 else "FAIL", content_hit_count, "0 content hits"),
        validation_row("No postal-code-like values in public outputs", "PASS" if content_hit_count == 0 else "FAIL", content_hit_count, "0 content hits"),
        validation_row("No raw rupee amount leakage in public outputs", "PASS" if content_hit_count == 0 else "FAIL", content_hit_count, "0 content hits"),
        validation_row("Indexes generated", "PASS" if {"sales_index", "units_index"} <= set(public.columns) else "FAIL", "sales_index, units_index", "present"),
        validation_row("Public sales indexes contain activity", "PASS" if generated_sales_activity else "WARN", generated_sales_activity, "nonzero when transactions contain sales activity"),
        validation_row("Aggregated sales indexes contain activity", "PASS" if aggregated_sales_activity else "WARN", aggregated_sales_activity, "nonzero when transactions contain sales activity"),
        validation_row(
            "Ratios generated",
            "PASS" if {"fee_pct_of_gross", "refund_pct_of_gross", "promotion_pct_of_gross", "net_to_gross_pct"} <= set(public.columns) else "FAIL",
            "fee/refund/promotion/net ratios",
            "present",
        ),
        validation_row("Profitability bands generated", "PASS" if "profitability_band_public" in public.columns else "FAIL", "profitability_band_public", "present"),
        validation_row("Margin risk scores generated", "PASS" if "margin_risk_score" in public.columns else "FAIL", "margin_risk_score", "present"),
        validation_row("Revenue quality scores generated", "PASS" if "revenue_quality_score" in public.columns else "FAIL", "revenue_quality_score", "present"),
        validation_row("Recommended actions generated", "PASS" if not action.empty and "recommended_action" in action.columns else "FAIL", len(action), "> 0 rows"),
        validation_row("Dataset profile includes display label", "PASS" if "dataset_label" in profile.columns else "WARN", "dataset_label" if "dataset_label" in profile.columns else "missing", "present"),
    ]

    # Contract validation / quarantine rows — only added when the live
    # upload path actually ran contract validation (quarantine_totals_summary
    # is populated by app/utils/data_loader.py; Sample Demo mode never
    # passes this, since it has no live upload to validate). Safe aggregate
    # counts only — never a raw rejected value.
    if quarantine_totals_summary is not None:
        rejected_rows = int(quarantine_totals_summary.get("rejected_rows", 0) or 0)
        warning_rows = int(quarantine_totals_summary.get("warning_rows", 0) or 0)
        rows.append(
            validation_row(
                "Upload contract validation — rejected rows",
                pass_warn_fail(rejected_rows == 0, warn_condition=True),
                rejected_rows,
                "0 rejected",
                "Rows failing required-field/type contract checks are excluded from analysis and quarantined (safe metadata only — no private values stored).",
            )
        )
        rows.append(
            validation_row(
                "Upload contract validation — warning rows",
                pass_warn_fail(warning_rows == 0, warn_condition=True),
                warning_rows,
                "0 warnings",
                "Rows with out-of-range values or unrecognized-but-plausible categories are kept and logged as warnings.",
            )
        )

    if public_output_contract_results is not None:
        checked_outputs = sorted(public_output_contract_results.keys())
        rows.append(
            validation_row(
                "Public output contract validation",
                "PASS" if checked_outputs else "WARN",
                f"{len(checked_outputs)} output(s) checked" if checked_outputs else "no contracted outputs present",
                "0 reject-level violations",
                f"Checked: {', '.join(checked_outputs)}" if checked_outputs else "",
            )
        )

    return pd.DataFrame(rows)
