"""Derived ratios, growth and flags. A pure function of the joined frame."""

from __future__ import annotations

import pandas as pd


def derive(df: pd.DataFrame, today_year: int) -> pd.DataFrame:
    d = df.copy()
    raum = d["raum"].where(d["raum"] > 0)
    d["hnw_share"] = d["hnw_amt"] / raum
    d["individuals_share"] = (d["ind_amt"].fillna(0) + d["hnw_amt"].fillna(0)) / raum
    d["pooled_share"] = d["pooled_amt"].fillna(0) / raum
    d["discretion_share"] = d["disc_amt"] / raum
    d["seats"] = d[["adv_staff", "bd_reps"]].max(axis=1)
    d["hybrid_depth"] = (d["bd_reps"] / d["staff"].where(d["staff"] > 0)).clip(upper=1.0)
    # Annual-amendment to annual-amendment, not "last 12 months" (see README timing paragraph).
    d["growth"] = d["raum"] / d["raum_prior"].where(d["raum_prior"] > 0) - 1
    d["bd_linked"] = d["is_bd"] | d["is_rep"] | d["bd_affiliate"]
    d["alts_re_lp"] = d["re_broker"] | d["lp_sponsor"]
    d["alts_pooled"] = d["private_fund"] | d["pooled_sponsor"] | (d["pooled_amt"].fillna(0) > 0)
    d["platform_sponsor"] = (d["wrap_sponsor_amt"].fillna(0) > 0) | (
        d["wrap_both_amt"].fillna(0) > 0
    )
    d["stale_filing"] = d["latest_filing_date"].dt.year < today_year
    for label, level in (("500m", 5e8), ("1b", 1e9), ("5b", 5e9)):
        d[f"crossed_{label}"] = (d["raum_prior"] < level) & (d["raum"] >= level)
    prior_pf = d["private_fund_prior"].fillna(False).astype(bool)
    d["fund_launched"] = ~prior_pf & d["private_fund"] & ~d["new_registrant"]
    seats_prior = d[["adv_staff_prior", "bd_reps_prior"]].max(axis=1)
    d["seat_growth"] = (d["seats"] / seats_prior.where(seats_prior > 0) - 1) >= 0.20
    d["low_discretion"] = d["discretion_share"] < 0.5
    return d
