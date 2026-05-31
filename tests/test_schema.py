from src.config import RAW_DIR
from src.features import align_train_test_columns, build_test_dataset, build_training_dataset
from src.preprocessing import load_data


def test_no_target_in_features():
    data = load_data(RAW_DIR)
    X, y, _ = build_training_dataset(data["trainperf"], data["traindemographics"], data["trainprevloans"])
    assert "good_bad_flag" not in X.columns
    assert "target_bad" not in X.columns
    assert y.notna().all()


def test_train_and_test_have_same_feature_columns():
    data = load_data(RAW_DIR)
    X_train, _, _ = build_training_dataset(data["trainperf"], data["traindemographics"], data["trainprevloans"])
    X_test, _ = build_test_dataset(data["testperf"], data["testdemographics"], data["testprevloans"])
    X_train, X_test = align_train_test_columns(X_train, X_test)
    assert list(X_train.columns) == list(X_test.columns)


def test_submission_expected_shape_after_sample_load():
    data = load_data(RAW_DIR)
    sample = data["sample_submission"]
    assert list(sample.columns) == ["customerid", "Good_Bad_flag"]
    assert len(sample) == len(data["testperf"])
