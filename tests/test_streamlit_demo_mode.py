from pathlib import Path

import pandas as pd

from app.utils.data_loader import build_demo_result


def test_demo_mode_loads_public_outputs(tmp_path: Path):
    pd.DataFrame(
        {
            "transaction_month": ["2026-05"],
            "dataset_period": ["demo"],
            "marketplace": ["Amazon"],
            "public_product_id": ["P0001"],
            "product_group": ["Product"],
            "sales_index": [100.0],
            "units_index": [100.0],
            "fee_pct_of_gross": [10.0],
            "refund_pct_of_gross": [0.0],
            "promotion_pct_of_gross": [5.0],
            "net_to_gross_pct": [85.0],
            "recommended_action": ["Monitor"],
            "action_priority": ["Low"],
        }
    ).to_csv(tmp_path / "anonymized_master.csv", index=False)
    pd.DataFrame(
        {
            "public_product_id": ["P0001"],
            "marketplace": ["Amazon"],
            "brand_group": ["Brand"],
            "category_group": ["Category"],
            "product_group": ["Product"],
            "sales_index": [100.0],
            "units_index": [100.0],
            "fee_pct_of_gross": [10.0],
            "refund_pct_of_gross": [0.0],
            "promotion_pct_of_gross": [5.0],
            "net_to_gross_pct": [85.0],
            "revenue_quality_score": [80.0],
            "recommended_action": ["Monitor"],
            "action_priority": ["Low"],
        }
    ).to_csv(tmp_path / "product_performance.csv", index=False)
    result = build_demo_result(tmp_path, dataset_period="demo")
    assert result["mode"] == "Sample Demo"
    assert result["kpis"]["Transaction Rows"] == 1
