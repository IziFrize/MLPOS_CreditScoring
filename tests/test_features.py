import pandas as pd

from src.features import aggregate_prevloans


def test_aggregate_prevloans_returns_one_row_per_customer():
    prev = pd.DataFrame(
        {
            "customerid": ["c1", "c1", "c2"],
            "systemloanid": [1, 2, 3],
            "loannumber": [1, 2, 1],
            "approveddate": ["2017-01-01", "2017-02-01", "2017-01-15"],
            "creationdate": ["2017-01-01", "2017-02-01", "2017-01-15"],
            "loanamount": [1000, 2000, 3000],
            "totaldue": [1200, 2500, 3600],
            "termdays": [30, 30, 60],
            "closeddate": ["2017-01-20", "2017-03-01", "2017-03-15"],
            "referredby": [None, "x", None],
            "firstduedate": ["2017-01-31", "2017-03-03", "2017-03-16"],
            "firstrepaiddate": ["2017-01-25", "2017-03-05", "2017-03-10"],
        }
    )
    out = aggregate_prevloans(prev)
    assert len(out) == 2
    assert out["customerid"].is_unique
    assert "prev_nb_loans" in out.columns
