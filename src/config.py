from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
FEATURES_DIR = DATA_DIR / "features"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

RANDOM_STATE = 42
TEST_SIZE = 0.20
TARGET_COLUMN = "good_bad_flag"
TARGET_BINARY_COLUMN = "target_bad"
TARGET_MAPPING = {"Good": 0, "Bad": 1}
ID_COLUMNS = ["customerid", "systemloanid"]


RAW_FILES = {
    "trainperf": "trainperf.csv",
    "traindemographics": "traindemographics.csv",
    "trainprevloans": "trainprevloans.csv",
    "testperf": "testperf.csv",
    "testdemographics": "testdemographics.csv",
    "testprevloans": "testprevloans.csv",
    "sample_submission": "SampleSubmission.csv",
}


def ensure_directories() -> None:
    for path in [RAW_DIR, PROCESSED_DIR, FEATURES_DIR, MODELS_DIR, FIGURES_DIR]:
        path.mkdir(parents=True, exist_ok=True)
