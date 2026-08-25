from shared.public_output_builder import PUBLIC_DASHBOARD_COLUMNS
from shared.privacy import SENSITIVE_COLUMNS


def test_public_dashboard_schema_excludes_sensitive_columns():
    assert not (set(PUBLIC_DASHBOARD_COLUMNS) & SENSITIVE_COLUMNS)
    assert "public_product_id" in PUBLIC_DASHBOARD_COLUMNS
    assert "margin_risk_score" in PUBLIC_DASHBOARD_COLUMNS
    assert "revenue_quality_score" in PUBLIC_DASHBOARD_COLUMNS

