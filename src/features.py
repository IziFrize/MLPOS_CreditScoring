from __future__ import annotations

import pandas as pd

try:
    from .config import ID_COLUMNS, TARGET_BINARY_COLUMN
    from .preprocessing import clean_demographics, clean_perf, clean_prevloans
except ImportError:
    from config import ID_COLUMNS, TARGET_BINARY_COLUMN
    from preprocessing import clean_demographics, clean_perf, clean_prevloans


def aggregate_prevloans(prev_df: pd.DataFrame) -> pd.DataFrame:
    prev_df = clean_prevloans(prev_df)

    agg = (
        prev_df.groupby("customerid")
        .agg(
            prev_nb_loans=("systemloanid", "count"),
            prev_total_loanamount=("loanamount", "sum"),
            prev_mean_loanamount=("loanamount", "mean"),
            prev_max_loanamount=("loanamount", "max"),
            prev_min_loanamount=("loanamount", "min"),
            prev_std_loanamount=("loanamount", "std"),
            prev_total_due=("totaldue", "sum"),
            prev_mean_totaldue=("totaldue", "mean"),
            prev_mean_termdays=("termdays", "mean"),
            prev_max_termdays=("termdays", "max"),
            prev_min_termdays=("termdays", "min"),
            prev_mean_interest=("previous_loan_interest", "mean"),
            prev_mean_interest_rate=("previous_loan_interest_rate", "mean"),
            prev_late_ratio=("previous_is_late", "mean"),
            prev_early_ratio=("previous_is_early", "mean"),
            prev_mean_days_late=("previous_days_late", "mean"),
            prev_max_days_late=("previous_days_late", "max"),
            prev_min_days_late=("previous_days_late", "min"),
            prev_mean_repayment_duration=("previous_repayment_duration", "mean"),
            prev_has_referrer_ratio=("has_prev_referrer", "mean"),
        )
        .reset_index()
    )

    sorted_prev = prev_df.sort_values(["customerid", "approveddate", "loannumber"], na_position="first")
    last = (
        sorted_prev.groupby("customerid")
        .tail(1)[["customerid", "loanamount", "previous_days_late", "totaldue", "termdays"]]
        .rename(
            columns={
                "loanamount": "prev_last_loanamount",
                "previous_days_late": "prev_last_days_late",
                "totaldue": "prev_last_totaldue",
                "termdays": "prev_last_termdays",
            }
        )
    )

    out = agg.merge(last, on="customerid", how="left")
    prev_cols = [c for c in out.columns if c.startswith("prev_")]
    out[prev_cols] = out[prev_cols].fillna(0)
    return out


def check_prevloan_leakage(perf_df: pd.DataFrame, prev_df: pd.DataFrame) -> dict[str, int]:
    merged = prev_df[["customerid", "loannumber", "approveddate"]].merge(
        perf_df[["customerid", "loannumber", "approveddate"]],
        on="customerid",
        how="inner",
        suffixes=("_prev", "_perf"),
    )
    number_leaks = int((merged["loannumber_prev"] >= merged["loannumber_perf"]).sum())
    date_leaks = int(
        (
            pd.to_datetime(merged["approveddate_prev"], errors="coerce")
            > pd.to_datetime(merged["approveddate_perf"], errors="coerce")
        ).sum()
    )
    return {"rows_checked": int(len(merged)), "loannumber_leaks": number_leaks, "approveddate_leaks": date_leaks}


def _prepare_final_dataset(perf: pd.DataFrame, demo: pd.DataFrame, prev: pd.DataFrame, is_train: bool):
    perf_clean = clean_perf(perf, is_train=is_train)
    demo_clean = clean_demographics(demo)
    prev_agg = aggregate_prevloans(prev)

    final = perf_clean.copy()
    final["has_demographics"] = final["customerid"].isin(demo_clean["customerid"]).astype(int)
    final["has_prevloans"] = final["customerid"].isin(prev_agg["customerid"]).astype(int)
    final = final.merge(demo_clean, on="customerid", how="left")
    final = final.merge(prev_agg, on="customerid", how="left")

    prev_cols = [c for c in final.columns if c.startswith("prev_")]
    final[prev_cols] = final[prev_cols].fillna(0)

    y = final[TARGET_BINARY_COLUMN] if is_train else None
    drop_cols = [c for c in ID_COLUMNS + [TARGET_BINARY_COLUMN] if c in final.columns]
    X = final.drop(columns=drop_cols)
    return X, y, final


def build_training_dataset(trainperf: pd.DataFrame, traindemo: pd.DataFrame, trainprev: pd.DataFrame):
    return _prepare_final_dataset(trainperf, traindemo, trainprev, is_train=True)


def build_test_dataset(testperf: pd.DataFrame, testdemo: pd.DataFrame, testprev: pd.DataFrame):
    X, _, final = _prepare_final_dataset(testperf, testdemo, testprev, is_train=False)
    return X, final


def align_train_test_columns(X_train: pd.DataFrame, X_test: pd.DataFrame):
    X_test = X_test.reindex(columns=X_train.columns)
    return X_train, X_test
