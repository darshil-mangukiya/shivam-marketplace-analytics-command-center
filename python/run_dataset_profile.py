from __future__ import annotations

import pandas as pd

from pipeline_utils import PUBLIC_DIR, PUBLIC_OUTPUTS


def main() -> None:
    rows = []
    for name, path in PUBLIC_OUTPUTS.items():
        if path.exists():
            rows.append({"public_output_name": name, "row_count": int(len(pd.read_csv(path))), "path": str(path)})
    profile = pd.DataFrame(rows)
    output = PUBLIC_DIR / "dataset_profile.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    profile.to_csv(output, index=False)
    print(profile.to_string(index=False))


if __name__ == "__main__":
    main()

