from __future__ import annotations

import joblib
import pandas as pd

try:
    from .config import MODELS_DIR, PROCESSED_DIR, RAW_DIR, ensure_directories
    from .features import build_test_dataset
    from .preprocessing import load_data
except ImportError:
    from config import MODELS_DIR, PROCESSED_DIR, RAW_DIR, ensure_directories
    from features import build_test_dataset
    from preprocessing import load_data


def main() -> None:
    ensure_directories()
    bundle = joblib.load(MODELS_DIR / "best_model.pkl")
    pipeline = bundle["pipeline"]
    threshold = float(bundle.get("threshold", 0.5))
    features = bundle["features"]

    data = load_data(RAW_DIR)
    X_test, _ = build_test_dataset(data["testperf"], data["testdemographics"], data["testprevloans"])
    X_test = X_test.reindex(columns=features)
    proba_bad = pipeline.predict_proba(X_test)[:, 1]
    labels = pd.Series((proba_bad >= threshold).astype(int)).map({0: "Good", 1: "Bad"})

    submission = pd.DataFrame(
        {
            "customerid": data["testperf"]["customerid"],
            "Good_Bad_flag": labels,
        }
    )
    submission.to_csv(PROCESSED_DIR / "submission.csv", index=False)
    print(f"Saved {PROCESSED_DIR / 'submission.csv'} with {len(submission)} rows.")


if __name__ == "__main__":
    main()
