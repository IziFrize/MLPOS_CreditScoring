from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def metrics_at_threshold(y_true, y_proba, threshold: float = 0.5) -> dict[str, float]:
    y_pred = (np.asarray(y_proba) >= threshold).astype(int)
    metrics = {
        "threshold": threshold,
        "accuracy": accuracy_score(y_true, y_pred),
        "precision_bad": precision_score(y_true, y_pred, zero_division=0),
        "recall_bad": recall_score(y_true, y_pred, zero_division=0),
        "f1_bad": f1_score(y_true, y_pred, zero_division=0),
        "f1_macro": f1_score(y_true, y_pred, average="macro", zero_division=0),
    }
    try:
        metrics["roc_auc"] = roc_auc_score(y_true, y_proba)
    except ValueError:
        metrics["roc_auc"] = float("nan")
    try:
        metrics["pr_auc"] = average_precision_score(y_true, y_proba)
    except ValueError:
        metrics["pr_auc"] = float("nan")
    return metrics


def threshold_table(y_true, y_proba, thresholds=(0.3, 0.4, 0.5, 0.6)) -> pd.DataFrame:
    return pd.DataFrame([metrics_at_threshold(y_true, y_proba, t) for t in thresholds])


def full_report(y_true, y_proba, threshold: float = 0.5) -> dict:
    y_pred = (np.asarray(y_proba) >= threshold).astype(int)
    return {
        "metrics": metrics_at_threshold(y_true, y_proba, threshold),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
        "classification_report": classification_report(y_true, y_pred, target_names=["Good", "Bad"], zero_division=0),
    }
