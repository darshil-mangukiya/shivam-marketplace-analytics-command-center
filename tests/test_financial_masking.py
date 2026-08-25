from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "data" / "public"


def test_public_outputs_use_ratios_and_indexes_not_raw_amounts():
    raw_amount_terms = {
        "gross_sales",
        "net_amount",
        "refund_amount",
        "amazon_fee",
        "product_sales",
        "selling_fees",
        "fba_fees",
        "total",
        "price",
    }
    for path in PUBLIC.glob("*.csv"):
        if path.name in {"validation_summary.csv", "dataset_profile.csv"}:
            continue
        columns = set(pd.read_csv(path, nrows=1).columns)
        assert not columns & raw_amount_terms, f"{path.name} contains raw amount columns"
        assert any(
            col.endswith("_index") or "pct" in col for col in columns
        ), f"{path.name} does not expose ratio/index metrics"


def test_ratio_columns_are_reasonable_ranges():
    # Period-over-period *variance* percentages (e.g. "sales_index rose 400%",
    # or fell -100% to zero) are a distinct metric type from a percent-of-gross
    # ratio and are not bounded to [-300, 300] the way those are; see
    # shared/variance_engine.py and docs/business_rules.md.
    variance_pct_columns = {"pct_variance", "total_pct_variance"}
    for path in PUBLIC.glob("*.csv"):
        df = pd.read_csv(path)
        for col in [column for column in df.columns if "pct" in column and column not in variance_pct_columns]:
            values = pd.to_numeric(df[col], errors="coerce").dropna()
            if values.empty:
                continue
            lower = -300 if "net_to_gross" in col else 0
            assert (values >= lower).all(), f"{path.name}:{col} below expected range"
            assert (values <= 300).all(), f"{path.name}:{col} above expected range"
