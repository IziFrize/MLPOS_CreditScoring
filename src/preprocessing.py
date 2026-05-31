from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from .config import RAW_FILES, TARGET_BINARY_COLUMN, TARGET_COLUMN, TARGET_MAPPING
except ImportError:
    from config import RAW_FILES, TARGET_BINARY_COLUMN, TARGET_COLUMN, TARGET_MAPPING


DATE_COLUMNS_PERF = ["approveddate", "creationdate"]
DATE_COLUMNS_PREV = ["approveddate", "creationdate", "closeddate", "firstduedate", "firstrepaiddate"]
DEMO_CATEGORICAL_COLUMNS = [
    "bank_account_type",
    "bank_name_clients",
    "employment_status_clients",
    "level_of_education_clients",
]


def load_data(raw_dir) -> dict[str, pd.DataFrame]:
    raw_dir = pd.io.common.stringify_path(raw_dir)
    return {name: pd.read_csv(f"{raw_dir}/{filename}") for name, filename in RAW_FILES.items()}


def _safe_rate(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = pd.to_numeric(denominator, errors="coerce")
    numerator = pd.to_numeric(numerator, errors="coerce")
    return np.where(denominator.ne(0), numerator / denominator, np.nan)


def clean_demographics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.drop_duplicates()
    df = df.sort_values("customerid").drop_duplicates("customerid", keep="first")

    df["birthdate"] = pd.to_datetime(df["birthdate"], errors="coerce")
    reference_date = pd.Timestamp("2017-12-31")
    df["age"] = ((reference_date - df["birthdate"]).dt.days / 365.25).clip(lower=18, upper=100)

    df["has_bank_branch"] = df["bank_branch_clients"].notna().astype(int)
    df["has_education_info"] = df["level_of_education_clients"].notna().astype(int)
    df["has_employment_info"] = df["employment_status_clients"].notna().astype(int)

    for col in DEMO_CATEGORICAL_COLUMNS:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str)

    if "bank_branch_clients" in df.columns:
        df = df.drop(columns=["bank_branch_clients"])
    if "birthdate" in df.columns:
        df = df.drop(columns=["birthdate"])

    return df


def clean_perf(df: pd.DataFrame, is_train: bool = True) -> pd.DataFrame:
    df = df.copy()
    for col in DATE_COLUMNS_PERF:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df["has_referrer"] = df["referredby"].notna().astype(int)
    df["loan_interest"] = pd.to_numeric(df["totaldue"], errors="coerce") - pd.to_numeric(
        df["loanamount"], errors="coerce"
    )
    df["loan_interest_rate"] = _safe_rate(df["loan_interest"], df["loanamount"])

    if is_train:
        df[TARGET_BINARY_COLUMN] = df[TARGET_COLUMN].map(TARGET_MAPPING)

    drop_cols = [c for c in ["referredby", "approveddate", "creationdate", TARGET_COLUMN] if c in df.columns]
    return df.drop(columns=drop_cols)


def clean_prevloans(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in DATE_COLUMNS_PREV:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df["previous_days_late"] = (df["firstrepaiddate"] - df["firstduedate"]).dt.days
    df["previous_is_late"] = (df["previous_days_late"] > 0).astype(int)
    df["previous_is_early"] = (df["previous_days_late"] < 0).astype(int)
    df["previous_repayment_duration"] = (df["firstrepaiddate"] - df["approveddate"]).dt.days
    df["previous_loan_interest"] = pd.to_numeric(df["totaldue"], errors="coerce") - pd.to_numeric(
        df["loanamount"], errors="coerce"
    )
    df["previous_loan_interest_rate"] = _safe_rate(df["previous_loan_interest"], df["loanamount"])
    df["has_prev_referrer"] = df["referredby"].notna().astype(int)
    return df


def build_preprocessor(categorical_cols: list[str], numerical_cols: list[str]) -> ColumnTransformer:
    try:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse=False)

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", encoder),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numerical_cols),
            ("cat", categorical_pipeline, categorical_cols),
        ],
        remainder="drop",
    )
