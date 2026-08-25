from pipeline_utils import build_public_outputs


if __name__ == "__main__":
    outputs = build_public_outputs()
    for name, df in outputs.items():
        print(f"{name}: {len(df):,} rows")
