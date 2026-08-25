import numpy as np
import pandas as pd

from shared.recommendations import add_actions, recommended_action


def _fixture(n: int = 1500) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "fee_pct_of_gross": rng.uniform(0, 40, n),
            "refund_pct_of_gross": rng.uniform(0, 20, n),
            "promotion_pct_of_gross": rng.uniform(0, 20, n),
            "net_to_gross_pct": rng.uniform(40, 110, n),
            "sales_index": rng.uniform(0, 100, n),
            "units_index": rng.uniform(0, 100, n),
            "margin_risk_score": rng.uniform(0, 100, n),
            "revenue_quality_score": rng.uniform(0, 100, n),
            "listing_price_band": rng.choice(["500-999", "3000-3999", "4000+", "premium", "Unknown"], n),
            "inventory_band": rng.choice(
                ["Out of Stock / 0", "Very Low / 1-5", "Low / 6-20", "High / 51-100", "Very High / 100+", "Unknown"], n
            ),
            "restock_priority": rng.choice(["High", "Monitor", "Low", ""], n),
        }
    )


def test_vectorized_add_actions_matches_rowwise_reference():
    df = _fixture()
    vectorized = add_actions(df)
    reference = df.apply(recommended_action, axis=1, result_type="expand")
    reference.columns = ["recommended_action", "action_priority", "action_reason"]
    for col in ["recommended_action", "action_priority", "action_reason"]:
        assert (vectorized[col].values == reference[col].values).all(), f"mismatch in {col}"


def test_add_actions_handles_empty_frame():
    out = add_actions(pd.DataFrame())
    assert list(out.columns) == ["recommended_action", "action_priority", "action_reason"]
    assert out.empty


def test_action_priorities_are_valid():
    out = add_actions(_fixture(200))
    assert out["action_priority"].isin({"High", "Medium", "Low"}).all()
