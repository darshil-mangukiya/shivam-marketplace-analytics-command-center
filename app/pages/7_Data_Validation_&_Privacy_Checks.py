from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.components.kpi_cards import render_kpi_card  # noqa: E402
from app.components.style import (  # noqa: E402
    inject_global_css,
    render_footer,
    render_insight_box,
    render_mode_badge,
    render_page_header,
    render_sidebar_status,
)
from app.components.tables import render_table_section  # noqa: E402
from app.utils.export_utils import dataframe_to_csv_bytes  # noqa: E402
from app.utils.validation import scan_public_outputs  # noqa: E402


st.set_page_config(page_title="Data Validation & Privacy Checks", layout="wide")
inject_global_css()
render_page_header(
    "Data Validation & Privacy Checks",
    "Validation results for output completeness, masking, content scans, and downloads.",
)

result = st.session_state.get("analysis_result")
render_sidebar_status(result=result)
if not result:
    st.info("Load demo public outputs or upload files on the main page first.")
    st.stop()
render_mode_badge(result)

outputs = result["outputs"]
validation = result["validation_summary"]
join_metrics = result["join_metrics"]

status_counts = validation["check_status"].value_counts().to_dict() if not validation.empty else {}
scan = scan_public_outputs(outputs)
content_hits = int(scan.get("content_hit_count", 0) or 0)

cols = st.columns(3)
with cols[0]:
    render_kpi_card(
        "Public Output Privacy Scan",
        "PASSED" if scan["is_safe"] else "FAILED",
        "Column and content scans across public outputs",
        "Passed" if scan["is_safe"] else "Failed",
    )
with cols[1]:
    render_kpi_card("Join Coverage %", join_metrics.get("join_coverage_pct", 0), "Rows with SKUs matched to product master", "Passed")
with cols[2]:
    render_kpi_card(
        "Channel Mapping Status",
        join_metrics.get("channel_mapping_status", "Unavailable"),
        "Marketplace-channel enrichment is unavailable because the mapping keys are incomplete",
        "Warning",
    )

content_totals = {
    "ASIN-Like Hits": 0,
    "SKU/Private ID Hits": 0,
    "Order-ID-Like Hits": 0,
    "Postal-Like Hits": 0,
    "Currency Leakage Hits": 0,
}
for output_scan in scan.get("content_scan_by_output", {}).values():
    content_totals["ASIN-Like Hits"] += int(output_scan.get("asin_like_values", 0) or 0)
    content_totals["SKU/Private ID Hits"] += int(output_scan.get("known_private_identifier_values", 0) or 0)
    content_totals["Order-ID-Like Hits"] += int(output_scan.get("order_id_like_values", 0) or 0)
    content_totals["Postal-Like Hits"] += int(output_scan.get("postal_code_like_values", 0) or 0)
    content_totals["Currency Leakage Hits"] += int(output_scan.get("currency_marker_values", 0) or 0)

leak_cols = st.columns(5)
for col, (label, value) in zip(leak_cols, content_totals.items()):
    with col:
        render_kpi_card(label, value, "Content-level privacy scan count", "Passed" if value == 0 else "Failed")

render_insight_box(
    "Validation reports private SKU, ASIN, order, and postal risks as counts only. Real identifier values are never displayed in the public dashboard."
)

render_table_section(
    "Validation Summary",
    "PASS/WARN/FAIL checks for loading, joining, marketplace mapping, anonymization, metric generation, and privacy scanning.",
    validation,
    height=560,
    download_name="validation_summary",
)

safe_metrics = {
    "Transaction Rows": join_metrics.get("transaction_row_count", 0),
    "Order Rows": join_metrics.get("order_row_count", 0),
    "Product Master Rows": join_metrics.get("product_master_row_count", 0),
    "Marketplace Master Rows": join_metrics.get("marketplace_channel_row_count", 0),
    "Transaction Rows With SKU": join_metrics.get("transaction_rows_with_sku", 0),
    "Matched Transaction Rows": join_metrics.get("matched_transaction_rows", 0),
    "Unmatched Transaction Rows": join_metrics.get("unmatched_transaction_rows", 0),
    "Unmatched Transaction SKU Count": join_metrics.get("unmatched_transaction_skus", 0),
    "Unmatched Listing SKU Count": join_metrics.get("unmatched_listing_skus", 0),
    "Unmatched Marketplace Master Rows": join_metrics.get("unmatched_marketplace_channel_rows_count", 0),
    "Duplicate SKU Count": join_metrics.get("duplicate_sku_count", 0),
    "Products in All 5 Marketplaces": join_metrics.get("products_with_all_5_channels_count", 0),
    "Products Missing a Marketplace": join_metrics.get("products_missing_channel_count", 0),
    "Join Coverage %": join_metrics.get("join_coverage_pct", 0),
    "Channel Mapping Status": join_metrics.get("channel_mapping_status", "Unavailable"),
    "Privacy Content Hit Count": content_hits,
}
safe_metrics_df = pd.DataFrame([{"metric": metric, "value": value} for metric, value in safe_metrics.items()])
render_table_section(
    "Join Coverage & Privacy Count Checks",
    "Only safe counts are shown. Real SKU, ASIN, order ID, and postal values remain private.",
    safe_metrics_df,
    height=460,
    download_name="join_privacy_count_summary",
)

content_summary = []
for output_name, output_scan in scan.get("content_scan_by_output", {}).items():
    content_summary.append(
        {
            "public_output_name": output_name,
            "total_content_hits": output_scan.get("total_content_hits", 0),
            "asin_like_values": output_scan.get("asin_like_values", 0),
            "known_private_identifier_values": output_scan.get("known_private_identifier_values", 0),
            "order_id_like_values": output_scan.get("order_id_like_values", 0),
            "postal_code_like_values": output_scan.get("postal_code_like_values", 0),
            "currency_marker_values": output_scan.get("currency_marker_values", 0),
        }
    )
render_table_section(
    "Content-Level Privacy Scan",
    "Counts of sensitive-looking content in public outputs. Leaked values are not printed.",
    pd.DataFrame(content_summary),
    height=420,
    download_name="content_privacy_scan_counts",
)

schema_source = outputs.get("anonymized_master", pd.DataFrame())
schema = schema_source.dtypes.astype(str).reset_index()
schema.columns = ["column_name", "dtype"]
render_table_section(
    "Public Output Schema",
    "Schema for the anonymized public dashboard dataframe.",
    schema,
    height=420,
    download_name="public_output_schema",
)

st.subheader("Download Public Outputs")
for name, df in outputs.items():
    st.download_button(
        label=f"Download {name}.csv",
        data=dataframe_to_csv_bytes(df),
        file_name=f"{name}.csv",
        mime="text/csv",
        use_container_width=True,
        key=f"validation_page_download_{name}",
    )
render_footer()
