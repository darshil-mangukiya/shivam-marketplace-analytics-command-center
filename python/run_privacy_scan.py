from __future__ import annotations

import json

import pandas as pd

from pipeline_utils import PUBLIC_DIR
from shared.privacy import scan_public_outputs


def main() -> None:
    outputs = {path.stem: pd.read_csv(path) for path in PUBLIC_DIR.glob("*.csv") if path.name != "validation_summary.csv"}
    scan = scan_public_outputs(outputs)
    print(json.dumps(scan, indent=2, default=str))
    if not scan["is_safe"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

