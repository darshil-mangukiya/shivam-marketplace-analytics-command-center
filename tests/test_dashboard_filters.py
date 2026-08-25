from __future__ import annotations

import pandas as pd

from app.utils.filters import (
    ALL_OPTION,
    PUBLIC_FILTER_COLUMNS,
    apply_dashboard_filters,
    apply_marketplace_product_filter,
    combine_filter_sources,
    filter_source_from_outputs,
    get_available_filter_values,
    public_marketplace_options,
    public_product_options,
)


def test_filter_values_use_public_safe_columns_only():
    df = pd.DataFrame(
        {
            "marketplace": ["Amazon", "Flipkart", "Amazon"],
            "category_group": ["Skin Care", "Hair Care", "Skin Care"],
            "seller_sku": ["PRIVATE-1", "PRIVATE-2", "PRIVATE-3"],
            "order_id": ["ORDER-1", "ORDER-2", "ORDER-3"],
        }
    )

    values = get_available_filter_values(df)

    assert values["marketplace"] == ["Amazon", "Flipkart"]
    assert values["category_group"] == ["Hair Care", "Skin Care"]
    assert "seller_sku" not in values
    assert "order_id" not in values


def test_apply_dashboard_filters_treats_all_as_default():
    df = pd.DataFrame({"marketplace": ["Amazon", "Flipkart"], "action_priority": ["High", "Low"]})

    filtered = apply_dashboard_filters(df, {"marketplace": ["All"], "action_priority": ["All"]})

    assert filtered.equals(df)


def test_apply_dashboard_filters_filters_matching_public_values():
    df = pd.DataFrame(
        {
            "marketplace": ["Amazon", "Flipkart", "Website"],
            "category_group": ["Skin Care", "Hair Care", "Skin Care"],
        }
    )

    filtered = apply_dashboard_filters(df, {"marketplace": ["Amazon", "Website"], "category_group": ["Skin Care"]})

    assert filtered["marketplace"].tolist() == ["Amazon", "Website"]
    assert filtered["category_group"].tolist() == ["Skin Care", "Skin Care"]


def test_filter_source_from_outputs_excludes_private_columns():
    outputs = {
        "product_performance": pd.DataFrame(
            {
                "marketplace": ["Amazon"],
                "brand_group": ["Brand A"],
                "seller_sku": ["PRIVATE-SKU"],
                "asin1": ["B000PRIVATE"],
            }
        ),
        "product_action_review": pd.DataFrame(
            {
                "recommended_action": ["Fee Review"],
                "action_priority": ["High"],
                "order_id": ["ORDER-PRIVATE"],
            }
        ),
    }

    source = filter_source_from_outputs(outputs)

    assert set(source.columns) <= set(PUBLIC_FILTER_COLUMNS)
    assert "seller_sku" not in source.columns
    assert "asin1" not in source.columns
    assert "order_id" not in source.columns


def test_combine_filter_sources_keeps_requested_public_filter_columns():
    left = pd.DataFrame({"marketplace": ["Amazon"], "category_group": ["Skin Care"]})
    right = pd.DataFrame({"recommended_action": ["Monitor"], "action_priority": ["Low"]})

    combined = combine_filter_sources(left, right)

    assert {"marketplace", "category_group", "recommended_action", "action_priority"} <= set(combined.columns)


# ---------------------------------------------------------------------------
# Marketplace + Product (public_product_id) page-level filter tests
# (Product, Brand & Category Intelligence page — UAT-09 / UAT-11).
# ---------------------------------------------------------------------------

def _product_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "marketplace": ["Amazon", "Amazon", "Flipkart", "Flipkart", "Meesho"],
            "public_product_id": ["PROD_00001", "PROD_00002", "PROD_00002", "PROD_00003", "PROD_00004"],
            "brand_group": ["Brand A", "Brand B", "Brand B", "Brand C", "Brand D"],
            "sales_index": [80.0, 60.0, 40.0, 30.0, 20.0],
        }
    )


def test_public_marketplace_options_returns_all_marketplaces_sorted():
    df = _product_frame()
    assert public_marketplace_options(df) == ["Amazon", "Flipkart", "Meesho"]


def test_all_marketplace_state_returns_every_row_unfiltered():
    df = _product_frame()
    filtered = apply_marketplace_product_filter(df, ALL_OPTION, ALL_OPTION)
    assert filtered.equals(df)

    # None is treated the same as "All" (default/unset state).
    filtered_none = apply_marketplace_product_filter(df, None, None)
    assert filtered_none.equals(df)


def test_single_marketplace_filtering_narrows_every_row():
    df = _product_frame()
    filtered = apply_marketplace_product_filter(df, "Amazon", ALL_OPTION)
    assert set(filtered["marketplace"].unique()) == {"Amazon"}
    assert len(filtered) == 2


def test_single_product_filtering_narrows_to_that_public_product_id():
    df = _product_frame()
    filtered = apply_marketplace_product_filter(df, ALL_OPTION, "PROD_00002")
    assert set(filtered["public_product_id"].unique()) == {"PROD_00002"}
    # PROD_00002 legitimately appears under two marketplaces (Amazon +
    # Flipkart) in this fixture -- filtering by product alone must return
    # both of those rows, not silently collapse to one marketplace.
    assert set(filtered["marketplace"].unique()) == {"Amazon", "Flipkart"}
    assert len(filtered) == 2


def test_combined_marketplace_and_product_filtering():
    df = _product_frame()
    filtered = apply_marketplace_product_filter(df, "Flipkart", "PROD_00002")
    assert len(filtered) == 1
    assert filtered.iloc[0]["marketplace"] == "Flipkart"
    assert filtered.iloc[0]["public_product_id"] == "PROD_00002"


def test_combined_filter_with_no_matching_rows_returns_empty_not_an_exception():
    df = _product_frame()
    # Amazon never sold PROD_00003 in this fixture.
    filtered = apply_marketplace_product_filter(df, "Amazon", "PROD_00003")
    assert filtered.empty
    # Must not raise; caller (the Streamlit page) is responsible for showing
    # the "No records match the selected filters." message on an empty frame.


def test_product_options_scoped_to_selected_marketplace():
    df = _product_frame()
    assert public_product_options(df, "Amazon") == ["PROD_00001", "PROD_00002"]
    assert public_product_options(df, "Flipkart") == ["PROD_00002", "PROD_00003"]
    assert public_product_options(df, "Meesho") == ["PROD_00004"]
    # Unscoped (All) returns every distinct product across all marketplaces.
    assert public_product_options(df, ALL_OPTION) == ["PROD_00001", "PROD_00002", "PROD_00003", "PROD_00004"]
    assert public_product_options(df, None) == ["PROD_00001", "PROD_00002", "PROD_00003", "PROD_00004"]


def test_product_options_never_include_private_identifier_columns():
    df = pd.DataFrame(
        {
            "marketplace": ["Amazon"],
            "public_product_id": ["PROD_00001"],
            "seller_sku": ["REAL-PRIVATE-SKU-999"],
            "asin1": ["B0PRIVATEASIN"],
            "item_name": ["Some Real Private Product Title"],
        }
    )
    options = public_product_options(df)
    assert options == ["PROD_00001"]
    for option in options:
        assert "REAL-PRIVATE-SKU-999" not in option
        assert "B0PRIVATEASIN" not in option
        assert "Some Real Private Product Title" not in option


def test_apply_marketplace_product_filter_never_exposes_private_columns():
    # Even if a private column happens to be present on the frame, the
    # filter must never read it, and it must remain untouched/unexposed by
    # this function (it does not drop or rename columns; it only narrows
    # rows) -- confirming the filter operates purely on the public columns.
    df = pd.DataFrame(
        {
            "marketplace": ["Amazon", "Flipkart"],
            "public_product_id": ["PROD_00001", "PROD_00002"],
            "seller_sku": ["REAL-SKU-1", "REAL-SKU-2"],
        }
    )
    filtered = apply_marketplace_product_filter(df, "Amazon", ALL_OPTION)
    assert list(filtered.columns) == list(df.columns)  # no columns added/removed
    assert filtered["public_product_id"].tolist() == ["PROD_00001"]


def test_public_product_options_missing_column_returns_empty_list():
    df = pd.DataFrame({"marketplace": ["Amazon"]})
    assert public_product_options(df) == []


def test_public_marketplace_options_missing_column_returns_empty_list():
    df = pd.DataFrame({"public_product_id": ["PROD_00001"]})
    assert public_marketplace_options(df) == []
