from pathlib import Path

import pandas as pd
import pytest

from radar.ingest import join_years, load_fields, load_registered, parse_money

FIELDS = Path("config/fields.yaml")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("   434,165,916.00", 434165916.0),
        (".00", 0.0),
        ("1,000", 1000.0),
        ("434165916.0", 434165916.0),
    ],
)
def test_parse_money(raw, expected):
    assert parse_money(raw) == expected


def test_parse_money_blank_is_nan():
    assert pd.isna(parse_money("")) and pd.isna(parse_money(None))


def test_load_registered_types(fixture_2026):
    df, info = load_registered(fixture_2026, load_fields(FIELDS))
    assert info["rows"] == len(df) and info["sha256"]
    assert df["crd"].dtype == "int64" and not df["crd"].duplicated().any()
    assert df["raum"].dtype == "float64" and df["is_bd"].dtype == "bool"
    assert set(df.columns) >= {"raum", "hnw_amt", "bd_reps", "item11", "latest_filing_date"}


def test_seed_row_values(fixture_2026):
    df, _ = load_registered(fixture_2026, load_fields(FIELDS))
    row = df.set_index("crd").loc[288863]  # Arkadios Wealth Advisors, Sep 2026 file
    assert row["bd_reps"] == 112 and row["adv_staff"] == 151 and row["bd_affiliate"]
    assert 8.7e9 < row["raum"] < 8.9e9


def test_join_years_marks_new_registrants(fixture_2026, fixture_2025):
    f = load_fields(FIELDS)
    cur, _ = load_registered(fixture_2026, f)
    prior, _ = load_registered(fixture_2025, f)
    df = join_years(cur, prior)
    assert {"raum_prior", "private_fund_prior", "new_registrant"} <= set(df.columns)
    assert df["new_registrant"].sum() >= 1
    assert len(df) == len(cur)
