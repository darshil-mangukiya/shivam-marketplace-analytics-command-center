from __future__ import annotations

import re
from typing import Iterable

import numpy as np
import pandas as pd


NON_PRODUCT_ID = "NON_PRODUCT_ACTIVITY"


def clean_text_series(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    return cleaned.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "None": pd.NA,
            "NULL": pd.NA,
            "<NA>": pd.NA,
        }
    )


def safe_group_value(value: object, default: str = "Unmapped") -> str:
    if pd.isna(value):
        return default
    text = re.sub(r"\s+", " ", str(value).strip())
    return text if text else default


def parse_numeric_series(series: pd.Series | Iterable[object]) -> pd.Series:
    if not isinstance(series, pd.Series):
        series = pd.Series(series)
    text = series.astype("string").fillna("").str.strip()
    negative_parentheses = text.str.match(r"^\(.*\)$", na=False)
    text = text.str.replace(r"[\(\)]", "", regex=True)
    text = text.str.replace(",", "", regex=False)
    text = text.str.replace("₹", "", regex=False)
    text = text.str.replace("$", "", regex=False)
    text = text.str.replace("INR", "", case=False, regex=False)
    values = pd.to_numeric(text, errors="coerce")
    values = values.mask(negative_parentheses, -values.abs())
    return values.fillna(0.0)


def first_existing_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def numeric_column(df: pd.DataFrame, candidates: Iterable[str], default: float = 0.0) -> pd.Series:
    col = first_existing_column(df, candidates)
    if col is None:
        return pd.Series(default, index=df.index, dtype="float64")
    return parse_numeric_series(df[col])


def text_column(df: pd.DataFrame, candidates: Iterable[str], default: str) -> pd.Series:
    col = first_existing_column(df, candidates)
    if col is None:
        return pd.Series(default, index=df.index, dtype="string")
    return clean_text_series(df[col]).fillna(default)


def index_from_values(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").fillna(0.0).clip(lower=0.0)
    denominator = numeric.max()
    if denominator <= 0:
        return pd.Series(0.0, index=values.index)
    return (numeric / denominator * 100.0).clip(lower=0.0, upper=100.0)


def pct_of_gross(numerator: pd.Series, gross: pd.Series, *, signed: bool = False) -> pd.Series:
    num = pd.to_numeric(numerator, errors="coerce").fillna(0.0)
    den = pd.to_numeric(gross, errors="coerce").fillna(0.0)
    if not signed:
        num = num.abs()
    result = np.where(den > 0, num / den * 100.0, 0.0)
    lower = -300.0 if signed else 0.0
    return pd.Series(result, index=gross.index).clip(lower=lower, upper=300.0)


def product_count(series: pd.Series) -> int:
    values = clean_text_series(series).dropna()
    values = values[values != NON_PRODUCT_ID]
    return int(values.nunique())


def band_from_pct(value: float) -> str:
    if pd.isna(value):
        return "Unknown"
    if value < 0:
        return "Loss / Negative"
    if value < 10:
        return "Low Margin"
    if value < 20:
        return "Moderate Margin"
    if value < 35:
        return "Healthy Margin"
    return "High Margin"


def origin_country_group(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip().lower()
    if not text:
        return "Unknown"
    if text in {"india", "in", "bharat"}:
        return "India"
    return "Imported / Other"

