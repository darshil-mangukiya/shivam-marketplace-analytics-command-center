from pipeline_utils import load_and_clean_transactions


if __name__ == "__main__":
    df = load_and_clean_transactions()
    print(f"Cleaned transactions: {len(df):,} rows")
