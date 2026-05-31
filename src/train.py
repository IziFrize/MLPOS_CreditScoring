from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay, PrecisionRecallDisplay, RocCurveDisplay, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

try:
    import mlflow
    import mlflow.sklearn
except ImportError:
    mlflow = None

try:
    from .config import (
        FIGURES_DIR,
        MODELS_DIR,
        PROCESSED_DIR,
        RANDOM_STATE,
        RAW_DIR,
        TARGET_MAPPING,
        TEST_SIZE,
        ensure_directories,
    )
    from .evaluate import threshold_table
    from .features import align_train_test_columns, build_test_dataset, build_training_dataset, check_prevloan_leakage
    from .preprocessing import build_preprocessor, load_data
except ImportError:
    from config import (
        FIGURES_DIR,
        MODELS_DIR,
        PROCESSED_DIR,
        RANDOM_STATE,
        RAW_DIR,
        TARGET_MAPPING,
        TEST_SIZE,
        ensure_directories,
    )
    from evaluate import threshold_table
    from features import align_train_test_columns, build_test_dataset, build_training_dataset, check_prevloan_leakage
    from preprocessing import build_preprocessor, load_data


def _split_columns(X: pd.DataFrame) -> tuple[list[str], list[str]]:
    categorical_cols = X.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    numerical_cols = [c for c in X.columns if c not in categorical_cols]
    return categorical_cols, numerical_cols


def _plot_artifacts(pipeline, X_valid, y_valid, y_proba, run_name: str) -> dict[str, Path]:
    paths = {}
    fig, ax = plt.subplots(figsize=(5, 4))
    ConfusionMatrixDisplay.from_predictions(y_valid, (y_proba >= 0.5).astype(int), display_labels=["Good", "Bad"], ax=ax)
    ax.set_title(f"Confusion matrix - {run_name}")
    path = FIGURES_DIR / f"{run_name}_confusion_matrix.png"
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths["confusion_matrix"] = path

    fig, ax = plt.subplots(figsize=(5, 4))
    RocCurveDisplay.from_predictions(y_valid, y_proba, ax=ax)
    ax.set_title(f"ROC curve - {run_name}")
    path = FIGURES_DIR / f"{run_name}_roc_curve.png"
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths["roc_curve"] = path

    fig, ax = plt.subplots(figsize=(5, 4))
    PrecisionRecallDisplay.from_predictions(y_valid, y_proba, ax=ax)
    ax.set_title(f"Precision-recall - {run_name}")
    path = FIGURES_DIR / f"{run_name}_precision_recall_curve.png"
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths["precision_recall_curve"] = path

    fitted_model = pipeline.named_steps["model"]
    if hasattr(fitted_model, "feature_importances_"):
        feature_names = pipeline.named_steps["preprocessor"].get_feature_names_out()
        importances = pd.Series(fitted_model.feature_importances_, index=feature_names).sort_values(ascending=False).head(20)
        fig, ax = plt.subplots(figsize=(7, 5))
        importances.sort_values().plot(kind="barh", ax=ax)
        ax.set_title(f"Top feature importances - {run_name}")
        ax.set_xlabel("Importance")
        path = FIGURES_DIR / f"{run_name}_feature_importance.png"
        fig.tight_layout()
        fig.savefig(path, dpi=160)
        plt.close(fig)
        paths["feature_importance"] = path

    return paths


def _train_one(run_name, model, X_train, X_valid, y_train, y_valid):
    categorical_cols, numerical_cols = _split_columns(X_train)
    pipeline = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor(categorical_cols, numerical_cols)),
            ("model", model),
        ]
    )
    pipeline.fit(X_train, y_train)
    y_train_proba = pipeline.predict_proba(X_train)[:, 1]
    y_proba = pipeline.predict_proba(X_valid)[:, 1]
    thresholds = threshold_table(y_valid, y_proba)
    best_row = thresholds.sort_values(["f1_bad", "recall_bad"], ascending=False).iloc[0]
    artifact_paths = _plot_artifacts(pipeline, X_valid, y_valid, y_proba, run_name)
    train_metrics = threshold_table(y_train, y_train_proba, thresholds=[float(best_row["threshold"])]).iloc[0].to_dict()
    valid_pred = (y_proba >= float(best_row["threshold"])).astype(int)
    report = classification_report(y_valid, valid_pred, target_names=["Good", "Bad"], zero_division=0)
    report_path = PROCESSED_DIR / f"{run_name}_classification_report.txt"
    report_path.write_text(report, encoding="utf-8")
    artifact_paths["classification_report"] = report_path
    return pipeline, thresholds, best_row.to_dict(), train_metrics, artifact_paths


def main() -> None:
    ensure_directories()
    data = load_data(RAW_DIR)

    X, y, train_final = build_training_dataset(
        data["trainperf"], data["traindemographics"], data["trainprevloans"]
    )
    X_test, test_final = build_test_dataset(data["testperf"], data["testdemographics"], data["testprevloans"])
    X, X_test = align_train_test_columns(X, X_test)

    train_final.to_csv(PROCESSED_DIR / "train_final.csv", index=False)
    test_final.to_csv(PROCESSED_DIR / "test_final.csv", index=False)
    X_test.to_csv(PROCESSED_DIR / "test_features_aligned.csv", index=False)

    leakage = check_prevloan_leakage(data["trainperf"], data["trainprevloans"])
    (PROCESSED_DIR / "leakage_check.json").write_text(json.dumps(leakage, indent=2), encoding="utf-8")
    (PROCESSED_DIR / "feature_columns.json").write_text(json.dumps(X.columns.tolist(), indent=2), encoding="utf-8")

    X_train, X_valid, y_train, y_valid = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    models = {
        "naive_always_good": DummyClassifier(strategy="constant", constant=0),
        "logistic_regression": LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
        "logistic_regression_balanced": LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE),
        "random_forest_simple": RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=2,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "random_forest_balanced": RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }

    if mlflow is not None:
        mlflow.set_experiment("credit_scoring_mlpos")

    summaries = []
    best = None
    for run_name, model in models.items():
        context = mlflow.start_run(run_name=run_name) if mlflow is not None else None
        if context is not None:
            context.__enter__()
        try:
            pipeline, thresholds, best_metrics, train_metrics, artifact_paths = _train_one(
                run_name, model, X_train, X_valid, y_train, y_valid
            )
            thresholds.to_csv(PROCESSED_DIR / f"{run_name}_thresholds.csv", index=False)
            row = {
                "run_name": run_name,
                **best_metrics,
                "train_f1_bad": train_metrics["f1_bad"],
                "train_recall_bad": train_metrics["recall_bad"],
                "train_precision_bad": train_metrics["precision_bad"],
            }
            summaries.append(row)

            if mlflow is not None:
                mlflow.log_param("model_name", model.__class__.__name__)
                mlflow.log_param("test_size", TEST_SIZE)
                mlflow.log_param("random_state", RANDOM_STATE)
                mlflow.log_param("n_train_rows", len(X_train))
                mlflow.log_param("n_valid_rows", len(X_valid))
                mlflow.log_param("n_raw_features", X_train.shape[1])
                mlflow.log_param("target_mapping", json.dumps(TARGET_MAPPING))
                for key, value in model.get_params().items():
                    if key in {"class_weight", "max_depth", "min_samples_leaf", "n_estimators", "max_iter"}:
                        mlflow.log_param(key, value)
                for key, value in best_metrics.items():
                    mlflow.log_metric(key, float(value))
                for key, value in train_metrics.items():
                    mlflow.log_metric(f"train_{key}", float(value))
                for path in artifact_paths.values():
                    mlflow.log_artifact(str(path))
                mlflow.log_artifact(str(PROCESSED_DIR / "feature_columns.json"))
                mlflow.sklearn.log_model(pipeline, "model")

            if best is None or best_metrics["f1_bad"] > best["metrics"]["f1_bad"]:
                best = {"run_name": run_name, "pipeline": pipeline, "metrics": best_metrics}
        finally:
            if context is not None:
                context.__exit__(None, None, None)

    results = pd.DataFrame(summaries).sort_values(["f1_bad", "recall_bad"], ascending=False)
    results.to_csv(PROCESSED_DIR / "model_comparison.csv", index=False)

    joblib.dump(
        {"pipeline": best["pipeline"], "threshold": float(best["metrics"]["threshold"]), "features": X.columns.tolist()},
        MODELS_DIR / "best_model.pkl",
    )
    print(results.to_string(index=False))
    print(f"Best model: {best['run_name']} at threshold {best['metrics']['threshold']}")


if __name__ == "__main__":
    main()
