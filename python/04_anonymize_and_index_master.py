from pipeline_utils import anonymize_and_index_master


if __name__ == "__main__":
    df = anonymize_and_index_master()
    print(f"Built anonymized master: {len(df):,} rows")
