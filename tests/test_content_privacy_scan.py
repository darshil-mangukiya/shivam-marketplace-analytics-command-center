import pandas as pd

from shared.privacy import content_privacy_scan, scan_public_outputs


def test_content_privacy_scan_counts_sensitive_patterns():
    df = pd.DataFrame(
        {
            "public_product_id": ["P0001"],
            "brand_group": ["Safe Brand"],
            "action_reason": ["Review without private values"],
            "notes": ["ORDER-12345 should be counted only in tests"],
        }
    )
    scan = content_privacy_scan(df)
    assert scan["order_id_like_values"] == 1
    assert not scan["is_safe"]


def test_public_output_scan_passes_safe_frame():
    outputs = {
        "product_performance": pd.DataFrame(
            {
                "public_product_id": ["P0001"],
                "brand_group": ["Brand Group"],
                "sales_index": [100.0],
                "fee_pct_of_gross": [10.0],
            }
        )
    }
    scan = scan_public_outputs(outputs, known_private_values=["SKU-PRIVATE"])
    assert scan["is_safe"]


def test_public_marketplace_labels_and_row_counts_are_not_privacy_hits():
    outputs = {
        "marketplace_summary": pd.DataFrame(
            {
                "marketplace": ["JioMart", "Website"],
                "channel": ["Website", "JioMart"],
                "sales_index": [100.0, 80.0],
            }
        ),
        "dataset_profile": pd.DataFrame(
            {
                "public_output_name": ["anonymized_master"],
                "row_count": [141000],
                "dataset_period": ["12m"],
            }
        ),
    }
    scan = scan_public_outputs(outputs, known_private_values=["141000"])
    assert scan["is_safe"]
