import pandas as pd

from radar.signals import derive


def _frame(**over):
    base = {
        "crd": [1],
        "raum": [1.0e9],
        "raum_prior": [4.0e8],
        "hnw_amt": [6.0e8],
        "ind_amt": [3.0e8],
        "pooled_amt": [0.0],
        "disc_amt": [9.5e8],
        "staff": [100.0],
        "adv_staff": [60.0],
        "bd_reps": [80.0],
        "adv_staff_prior": [50.0],
        "bd_reps_prior": [50.0],
        "is_bd": [False],
        "is_rep": [False],
        "bd_affiliate": [True],
        "re_broker": [False],
        "lp_sponsor": [True],
        "private_fund": [True],
        "private_fund_prior": [False],
        "pooled_sponsor": [False],
        "wrap_sponsor_amt": [0.0],
        "wrap_both_amt": [1.0],
        "new_registrant": [False],
        "latest_filing_date": [pd.Timestamp("2026-03-15")],
    }
    base.update(over)
    return pd.DataFrame(base)


def test_ratios_and_growth():
    d = derive(_frame(), today_year=2026).iloc[0]
    assert d["hnw_share"] == 0.6 and d["individuals_share"] == 0.9 and d["pooled_share"] == 0.0
    assert abs(d["growth"] - 1.5) < 1e-9 and d["seats"] == 80 and d["hybrid_depth"] == 0.8


def test_flags():
    d = derive(_frame(), today_year=2026).iloc[0]
    assert d["bd_linked"] and d["alts_re_lp"] and d["alts_pooled"] and d["platform_sponsor"]
    assert d["crossed_500m"] and d["crossed_1b"] and not d["crossed_5b"]
    assert d["fund_launched"] and d["seat_growth"]
    assert not d["low_discretion"] and not d["stale_filing"]


def test_zero_raum_gives_nan_not_error():
    d = derive(_frame(raum=[0.0]), today_year=2026).iloc[0]
    assert pd.isna(d["hnw_share"])
