from pipeline_utils import load_and_clean_product_master


if __name__ == "__main__":
    df = load_and_clean_product_master()
    print(f"Cleaned product master: {len(df):,} rows")
