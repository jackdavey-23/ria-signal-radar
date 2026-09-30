"""Score = sum over factors of points x transform(column). The YAML config drives everything."""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd

PERCENT_COLUMNS = {"hybrid_depth", "hnw_share", "individuals_share", "pooled_share"}
COUNT_COLUMNS = {"seats", "offices", "staff", "bd_reps", "adv_staff"}


def linear(s: pd.Series, lo: float, hi: float) -> pd.Series:
    lo, hi = float(lo), float(hi)  # PyYAML reads 250e6 as a string
    return ((s - lo) / (hi - lo)).clip(0, 1).fillna(0.0)


def log_ramp(s: pd.Series, lo: float, hi: float) -> pd.Series:
    lo, hi = float(lo), float(hi)
    x = s.where(s > 0)
    return ((np.log(x) - np.log(lo)) / (np.log(hi) - np.log(lo))).clip(0, 1).fillna(0.0)


def percentile(s: pd.Series, winsor=(0.05, 0.95), missing: float = 0.5) -> pd.Series:
    lo, hi = s.quantile(winsor[0]), s.quantile(winsor[1])
    return s.clip(lo, hi).rank(pct=True).fillna(missing)


def flag(s: pd.Series) -> pd.Series:
    return s.fillna(False).astype(bool).astype(float)


TRANSFORMS = {"linear": linear, "log_ramp": log_ramp, "percentile": percentile, "flag": flag}


def _fmt(col: str, v: object) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    if col == "growth":
        return f"{v:+.0%}"
    if col == "raum":
        return f"${v / 1e9:.1f}B" if v >= 1e9 else f"${v / 1e6:.0f}M"
    if isinstance(v, (bool, np.bool_)):
        return "yes" if v else "no"
    if col in PERCENT_COLUMNS:
        return f"{v:.0%}"
    return f"{v:,.0f}"


def why_string(row: pd.Series, cfg: dict) -> str:
    """Top three contributing factors with their raw values, then any flags that fired."""
    parts = []
    for f in sorted(cfg["factors"], key=lambda f: -row[f"pts_{f['id']}"])[:3]:
        pts = row[f"pts_{f['id']}"]
        parts.append(f"{f['id']} {_fmt(f['column'], row[f['column']])} (+{pts:.0f})")
    fired = [name for name in cfg["flags"] if bool(row.get(name, False))]
    if fired:
        parts.append("flags: " + ", ".join(fired))
    return " · ".join(parts)


def score(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    d = df.copy()
    gap = cfg.get("alts_direction", "active") == "gap"
    total = pd.Series(0.0, index=d.index)
    for f in cfg["factors"]:
        col = d[f["column"]]
        if gap and f["id"].startswith("alts_"):
            col = ~col.fillna(False).astype(bool)
        unit = TRANSFORMS[f["transform"]](col, **f.get("params", {}))
        d[f"pts_{f['id']}"] = (unit * f["points"]).round(2)
        total = total + d[f"pts_{f['id']}"]
    d["score"] = total.round(1)
    a, b = cfg["tiers"]["A"], cfg["tiers"]["B"]
    d["tier"] = np.select([d["score"] >= a, d["score"] >= b], ["A", "B"], default="C")
    d["why"] = [why_string(r, cfg) for _, r in d.iterrows()]
    return d.sort_values(["score", "raum"], ascending=[False, False]).reset_index(drop=True)


def sensitivity(df: pd.DataFrame, cfg: dict, delta: int = 5, top_n: int = 50) -> list[dict]:
    """Move each weight +/- delta and count how many of the baseline top_n survive."""
    base = set(score(df, cfg).head(top_n)["crd"])
    rows = []
    for f in cfg["factors"]:
        for sign in (1, -1):
            c2 = copy.deepcopy(cfg)
            for g in c2["factors"]:
                if g["id"] == f["id"]:
                    g["points"] = max(0, g["points"] + sign * delta)
            kept = len(base & set(score(df, c2).head(top_n)["crd"]))
            rows.append({"factor": f["id"], "delta": sign * delta, "top_n_kept": kept})
    return rows


def seed_ranks(scored: pd.DataFrame, seeds: list[dict]) -> list[dict]:
    """Where the sanity-check firms land. n is tiny and they shaped the config: not a backtest."""
    pos = {int(crd): i + 1 for i, crd in enumerate(scored["crd"])}
    out = []
    for s in seeds:
        r = pos.get(int(s["crd"]))
        row = scored.iloc[r - 1] if r else None
        out.append(
            {
                "crd": int(s["crd"]),
                "name": s["name"],
                "rank": r,
                "tier": None if row is None else str(row["tier"]),
                "score": None if row is None else float(row["score"]),
            }
        )
    return out


NETWORK_FACTORS = ("seats", "offices", "scale", "hybrid_depth")
NETWORK_COLUMNS = {
    "seats": "seats",
    "offices": "offices",
    "scale": "raum",
    "hybrid_depth": "hybrid_depth",
}


def collapse_network(scored: pd.DataFrame, cfg: dict, top_n: int = 50) -> dict:
    """Robustness check for correlated size inputs.

    seats, offices, scale and hybrid depth are related measures of network size. Merge them into
    one factor worth their combined points (the mean of their unit scores) and count how many of
    the baseline top_n survive. Also report the Spearman correlations between the raw inputs.
    """
    pts = {f["id"]: f["points"] for f in cfg["factors"]}
    net = [f for f in NETWORK_FACTORS if f in pts]
    total_net = sum(pts[f] for f in net)
    unit = sum(scored[f"pts_{f}"] / pts[f] for f in net) / len(net)
    other = sum(scored[f"pts_{f}"] for f in pts if f not in net)
    collapsed = other + unit * total_net
    base = set(scored.head(top_n)["crd"])
    new_top = scored.assign(_collapsed=collapsed).sort_values("_collapsed", ascending=False)
    kept = len(base & set(new_top.head(top_n)["crd"]))
    cols = [NETWORK_COLUMNS[f] for f in net]
    corr = scored[cols].corr(method="spearman")
    spearman = {
        f"{a}~{b}": round(float(corr.loc[NETWORK_COLUMNS[a], NETWORK_COLUMNS[b]]), 2)
        for i, a in enumerate(net)
        for b in net[i + 1 :]
    }
    return {
        "network_factors": net,
        "network_points": total_net,
        "top_n": top_n,
        "top_n_kept_when_collapsed": kept,
        "spearman": spearman,
    }
