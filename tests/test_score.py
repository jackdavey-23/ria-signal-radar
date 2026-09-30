from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from radar.score import flag, linear, log_ramp, percentile, score

CFG = yaml.safe_load(Path("config/icp_alts_platform.yaml").read_text())


def test_points_sum_to_100():
    assert sum(f["points"] for f in CFG["factors"]) == 100


def test_transforms_are_bounded():
    s = pd.Series([0.0, 1.0, 10.0, 300.0, 5000.0, np.nan])
    assert log_ramp(s, 10, 300).tolist()[:5] == [0.0, 0.0, 0.0, 1.0, 1.0]
    assert linear(pd.Series([0.1, 0.4, 0.9]), 0.2, 0.6).round(2).tolist() == [0.0, 0.5, 1.0]
    assert flag(pd.Series([True, False, None])).tolist() == [1.0, 0.0, 0.0]
    p = percentile(pd.Series([-5.0, 0.1, 0.2, 0.3, 50.0, np.nan]), winsor=[0.05, 0.95], missing=0.5)
    assert p.between(0, 1).all() and p.iloc[-1] == 0.5


def _scored():
    rng = np.random.default_rng(0)
    n = 40
    df = pd.DataFrame(
        {
            "crd": range(n),
            "name": [f"Firm {i}" for i in range(n)],
            "growth": rng.normal(0.15, 0.2, n),
            "seats": rng.integers(5, 400, n).astype(float),
            "offices": rng.integers(0, 150, n).astype(float),
            "hybrid_depth": rng.uniform(0, 1, n),
            "platform_sponsor": rng.random(n) > 0.5,
            "alts_re_lp": rng.random(n) > 0.8,
            "alts_pooled": rng.random(n) > 0.7,
            "raum": rng.uniform(2.5e8, 2.5e10, n),
            "hnw_share": rng.uniform(0.2, 0.9, n),
            "item11": rng.random(n) > 0.7,
            "fund_launched": rng.random(n) > 0.9,
        }
    )
    for flag_name in CFG["flags"]:
        if flag_name not in df:
            df[flag_name] = False
    return score(df, CFG)


def test_score_bounds_and_sum():
    s = _scored()
    pts = s[[c for c in s.columns if c.startswith("pts_")]]
    assert s["score"].between(0, 100).all()
    assert np.allclose(s["score"], pts.sum(axis=1).round(1), atol=0.11)
    assert s["score"].is_monotonic_decreasing and set(s["tier"]) <= {"A", "B", "C"}


def test_why_string_names_top_factor_and_flags():
    s = _scored()
    assert s["why"].str.len().gt(10).all()
    hit = s[s["fund_launched"]]
    assert hit.empty or hit["why"].str.contains("fund_launched").all()


def test_alts_direction_gap_flips_alts_points():
    active = _scored()
    cfg_gap = dict(CFG, alts_direction="gap")
    gap = score(active.drop(columns=[c for c in active.columns if c.startswith("pts_")]), cfg_gap)
    a = active.set_index("crd")["pts_alts_pooled"]
    g = gap.set_index("crd")["pts_alts_pooled"].reindex(a.index)
    assert ((a > 0) == (g == 0)).all()
