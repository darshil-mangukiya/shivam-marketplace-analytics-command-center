from pipeline_utils import build_private_master


if __name__ == "__main__":
    df = build_private_master()
    print(f"Built private master: {len(df):,} rows")
