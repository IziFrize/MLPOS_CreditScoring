import pandas as pd

from src.preprocessing import clean_perf


def test_clean_perf_creates_binary_target():
    df = pd.DataFrame(
        {
            "customerid": ["c1", "c2"],
            "systemloanid": [1, 2],
            "loannumber": [1, 2],
            "approveddate": ["2017-01-01", "2017-01-02"],
            "creationdate": ["2017-01-01", "2017-01-02"],
            "loanamount": [1000, 2000],
            "totaldue": [1200, 2400],
            "termdays": [30, 30],
            "referredby": [None, "x"],
            "good_bad_flag": ["Good", "Bad"],
        }
    )
    cleaned = clean_perf(df, is_train=True)
    assert cleaned["target_bad"].tolist() == [0, 1]
    assert "good_bad_flag" not in cleaned.columns
    assert "has_referrer" in cleaned.columns
