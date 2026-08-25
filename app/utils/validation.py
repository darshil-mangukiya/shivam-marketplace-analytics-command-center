from __future__ import annotations

import pandas as pd

from shared.privacy import scan_public_outputs as _scan_public_outputs
from shared.validation import build_validation_summary as _build_validation_summary


def scan_public_outputs(
    outputs: dict[str, pd.DataFrame],
    known_private_values: list[object] | None = None,
) -> dict[str, object]:
    return _scan_public_outputs(outputs, known_private_values=known_private_values)


def build_validation_summary(
    outputs: dict[str, pd.DataFrame],
    product_metrics: dict[str, object],
    transaction_metrics: dict[str, object],
    join_metrics: dict[str, object],
    known_private_values: list[object] | None = None,
    quarantine_totals_summary: dict[str, int] | None = None,
    public_output_contract_results: dict[str, dict[str, int]] | None = None,
) -> pd.DataFrame:
    return _build_validation_summary(
        outputs,
        product_metrics,
        transaction_metrics,
        join_metrics,
        known_private_values=known_private_values,
        quarantine_totals_summary=quarantine_totals_summary,
        public_output_contract_results=public_output_contract_results,
    )
