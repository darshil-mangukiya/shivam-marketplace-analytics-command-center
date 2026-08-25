from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


FILTER_FIELDS: tuple[tuple[str, str], ...] = (
    ("Marketplace", "marketplace"),
    ("Category", "category_group"),
    ("Brand", "brand_group"),
    ("Product Group", "product_group"),
    ("Action Priority", "action_priority"),
    ("Recommended Action", "recommended_action"),
)
PUBLIC_FILTER_COLUMNS = tuple(col for _, col in FILTER_FIELDS)
NO_RECORDS_MESSAGE = "No records match the selected filters."


def _clean_options(series: pd.Series) -> list[str]:
    values = series.dropna().astype(str).str.strip()
    values = values[(values != "") & (values.str.lower() != "nan")]
    return sorted(values.unique().tolist())


def combine_filter_sources(*frames: pd.DataFrame) -> pd.DataFrame:
    public_frames: list[pd.DataFrame] = []
    for frame in frames:
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            cols = [col for col in PUBLIC_FILTER_COLUMNS if col in frame.columns]
            if cols:
                public_frames.append(frame[cols].copy())
    if not public_frames:
        return pd.DataFrame(columns=PUBLIC_FILTER_COLUMNS)
    return pd.concat(public_frames, ignore_index=True, sort=False).drop_duplicates()


def filter_source_from_outputs(outputs: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    return combine_filter_sources(
        outputs.get("product_action_review", pd.DataFrame()),
        outputs.get("product_performance", pd.DataFrame()),
        outputs.get("inventory_action_review", pd.DataFrame()),
        outputs.get("margin_risk_review", pd.DataFrame()),
        outputs.get("profitability_summary", pd.DataFrame()),
        outputs.get("category_performance", pd.DataFrame()),
        outputs.get("brand_performance", pd.DataFrame()),
        outputs.get("marketplace_channel_performance", pd.DataFrame()),
    )


def get_available_filter_values(df: pd.DataFrame) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for _, column in FILTER_FIELDS:
        values[column] = _clean_options(df[column]) if column in df.columns else []
    return values


def render_sidebar_filters(df: pd.DataFrame, *, key_prefix: str = "dashboard") -> dict[str, list[str]]:
    import streamlit as st

    available = get_available_filter_values(df)
    filters: dict[str, list[str]] = {}
    st.sidebar.markdown("### Dashboard Filters")
    st.sidebar.caption("Default: All")
    for label, column in FILTER_FIELDS:
        options = available.get(column, [])
        if not options:
            filters[column] = ["All"]
            continue
        filters[column] = st.sidebar.multiselect(
            label,
            ["All", *options],
            default=["All"],
            key=f"{key_prefix}_{column}",
        )
    return filters


def apply_dashboard_filters(df: pd.DataFrame, filters: Mapping[str, list[str]]) -> pd.DataFrame:
    filtered = df.copy()
    for column, selected in filters.items():
        if column not in filtered.columns:
            continue
        selected_values = [str(value) for value in selected if str(value).strip()]
        if not selected_values or "All" in selected_values:
            continue
        filtered = filtered[filtered[column].astype(str).isin(selected_values)]
    return filtered


def has_active_filters(filters: Mapping[str, list[str]]) -> bool:
    return any(values and "All" not in [str(value) for value in values] for values in filters.values())


# ---------------------------------------------------------------------------
# Marketplace + Product (public_product_id) filters — dedicated, page-level
# selectboxes for the Product, Brand & Category Intelligence page (and any
# other page that wants a single-marketplace / single-product drill-down in
# addition to the generic multiselect sidebar filters above).
#
# The product filter reads the privacy-safe `public_product_id` field.
# ---------------------------------------------------------------------------

ALL_OPTION = "All"


def public_marketplace_options(df: pd.DataFrame) -> list[str]:
    """Distinct marketplace values from the public `marketplace` column."""
    if "marketplace" not in df.columns:
        return []
    return _clean_options(df["marketplace"])


def public_product_options(df: pd.DataFrame, marketplace: str | None = None) -> list[str]:
    """Distinct public_product_id values, optionally scoped to one
    marketplace (Requirement 3: "if a marketplace is selected, limit the
    available public product IDs to those valid for that marketplace").

    Only ever reads the `public_product_id` column — never a real SKU,
    ASIN, seller SKU, listing ID, or title column, even if one is present
    elsewhere on `df`.
    """
    if "public_product_id" not in df.columns:
        return []
    scoped = df
    if marketplace and marketplace != ALL_OPTION and "marketplace" in df.columns:
        scoped = scoped[scoped["marketplace"].astype(str) == str(marketplace)]
    return _clean_options(scoped["public_product_id"])


def apply_marketplace_product_filter(
    df: pd.DataFrame,
    marketplace: str | None,
    public_product_id: str | None,
) -> pd.DataFrame:
    """Apply the marketplace and product (public_product_id) filters
    together (Requirement 4). Either one left as None/"All" is a no-op, so
    the two filters combine with AND semantics without requiring both to be
    set."""
    filtered = df.copy()
    if marketplace and marketplace != ALL_OPTION and "marketplace" in filtered.columns:
        filtered = filtered[filtered["marketplace"].astype(str) == str(marketplace)]
    if public_product_id and public_product_id != ALL_OPTION and "public_product_id" in filtered.columns:
        filtered = filtered[filtered["public_product_id"].astype(str) == str(public_product_id)]
    return filtered


def render_marketplace_product_filters(
    df: pd.DataFrame, *, key_prefix: str = "marketplace_product"
) -> tuple[str, str]:
    """Render the two page-level selectboxes and return the selected
    (marketplace, public_product_id) — each defaulting to "All". The
    product dropdown's options are recomputed from whatever marketplace is
    currently selected, so choosing a marketplace narrows the product list
    to only public product IDs that actually appear in that marketplace."""
    import streamlit as st

    marketplace_options = public_marketplace_options(df)
    selected_marketplace = st.selectbox(
        "Marketplace",
        [ALL_OPTION, *marketplace_options],
        index=0,
        key=f"{key_prefix}_marketplace",
    )
    product_options = public_product_options(df, selected_marketplace)
    selected_product_id = st.selectbox(
        "Product (public product ID)",
        [ALL_OPTION, *product_options],
        index=0,
        key=f"{key_prefix}_product_id",
    )
    return selected_marketplace, selected_product_id
