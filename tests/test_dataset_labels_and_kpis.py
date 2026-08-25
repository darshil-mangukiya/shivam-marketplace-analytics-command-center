from pathlib import Path

import pandas as pd

from app.utils.data_loader import build_demo_result
from shared.dataset_labels import dataset_label, infer_dataset_period_from_counts


def test_dataset_label_infers_12m_from_row_and_order_counts():
    assert infer_dataset_period_from_counts(transaction_rows=141_000, order_rows=120_000) == "12m"
    assert dataset_label("", transaction_rows=141_000, order_rows=120_000) == "12M / 120K Orders"


def test_demo_result_uses_dataset_profile_label_and_master_row_count(tmp_path: Path):
    pd.DataFrame(
        {
            "transaction_month": ["2026-05", "2026-05"],
            "dataset_period": ["12m", "12m"],
            "marketplace": ["Amazon", "Flipkart"],
            "public_product_id": ["PUBLIC_PRODUCT_001", "PUBLIC_PRODUCT_002"],
            "product_group": ["Group A", "Group B"],
            "transaction_type_group": ["Order", "Order"],
            "sales_index": [100.0, 50.0],
            "units_index": [100.0, 50.0],
            "fee_pct_of_gross": [10.0, 12.0],
            "refund_pct_of_gross": [0.0, 0.0],
            "promotion_pct_of_gross": [5.0, 4.0],
            "net_to_gross_pct": [85.0, 84.0],
            "recommended_action": ["Monitor", "Monitor"],
            "action_priority": ["Low", "Low"],
        }
    ).to_csv(tmp_path / "anonymized_master.csv", index=False)
    pd.DataFrame(
        {
            "public_product_id": ["PUBLIC_PRODUCT_001", "PUBLIC_PRODUCT_002"],
            "marketplace": ["Amazon", "Flipkart"],
            "brand_group": ["Brand A", "Brand B"],
            "category_group": ["Category A", "Category B"],
            "product_group": ["Group A", "Group B"],
            "sales_index": [100.0, 50.0],
            "units_index": [100.0, 50.0],
            "fee_pct_of_gross": [10.0, 12.0],
            "refund_pct_of_gross": [0.0, 0.0],
            "promotion_pct_of_gross": [5.0, 4.0],
            "net_to_gross_pct": [85.0, 84.0],
            "revenue_quality_score": [80.0, 75.0],
            "recommended_action": ["Monitor", "Monitor"],
            "action_priority": ["Low", "Low"],
        }
    ).to_csv(tmp_path / "product_performance.csv", index=False)
    pd.DataFrame(
        {
            "public_output_name": ["anonymized_master", "product_performance"],
            "row_count": [2, 2],
            "dataset_period": ["12m", "12m"],
        }
    ).to_csv(tmp_path / "dataset_profile.csv", index=False)
    pd.DataFrame(
        {
            "check_name": ["product master row count > 0"],
            "check_status": ["PASS"],
            "check_value": ["1264"],
            "expected_value": ["> 0"],
            "notes": [""],
        }
    ).to_csv(tmp_path / "validation_summary.csv", index=False)

    result = build_demo_result(tmp_path, dataset_period="1m")

    assert result["dataset_label"] == "12M / 120K Orders"
    assert result["mode_badge"] == "SAMPLE DEMO: 12M / 120K Orders"
    assert result["kpis"]["Product Master Rows"] == 1264
    assert result["kpis"]["Products With Transactions"] == 2
