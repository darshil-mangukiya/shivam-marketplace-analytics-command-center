from __future__ import annotations

import streamlit as st


def render_upload_panel() -> tuple[object, object, bool]:
    st.subheader("Upload 2 Files")
    st.caption("Upload both marketplace files, then run the local privacy-safe analysis.")

    product_upload = st.file_uploader(
        "Upload Product Master Excel",
        type=["xlsx", "xls"],
        help="Excel workbook with Product_Master, Marketplace_Channel_Master, and Assumptions sheets.",
    )
    transaction_upload = st.file_uploader(
        "Upload Transaction CSV",
        type=["csv"],
        help="CSV export with orders, refunds, fees, fulfillment, promotions, and settlement activity.",
    )
    run_clicked = st.button(
        "Run Full Analysis",
        type="primary",
        use_container_width=True,
        disabled=not (product_upload and transaction_upload),
    )
    return product_upload, transaction_upload, run_clicked
