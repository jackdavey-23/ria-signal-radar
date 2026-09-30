"""Suppression by CRD and CSV exports. Nothing in this package can send anything."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

SOCIAL_HOSTS = (
    "linkedin.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "youtube.com",
    "tiktok.com",
)
EXPORT_COLUMNS = [
    "rank",
    "crd",
    "name",
    "city",
    "state",
    "raum",
    "growth",
    "seats",
    "offices",
    "hnw_share",
    "score",
    "tier",
    "why",
    "iapd_url",
]


def iapd_url(crd: int) -> str:
    return f"https://adviserinfo.sec.gov/firm/summary/{int(crd)}"


def domain_from_website(url: str | None) -> str | None:
    """Company domain for CRM import; social-media hosts never count (34.6% of ADV websites)."""
    if url is None or not str(url).strip():
        return None
    raw = str(url).strip()
    if "://" not in raw:
        raw = "http://" + raw
    host = (urlparse(raw).hostname or "").lower()
    host = host.removeprefix("www.")
    if not host or any(host == s or host.endswith("." + s) for s in SOCIAL_HOSTS):
        return None
    return host


def apply_suppression(df: pd.DataFrame, entries: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split by CRD membership only. Never by name substring (see config/suppression.yaml)."""
    crds = {int(e["crd"]) for e in entries}
    mask = df["crd"].isin(crds)
    return df[~mask].reset_index(drop=True), df[mask].reset_index(drop=True)


def write_outputs(
    scored: pd.DataFrame,
    suppressed: pd.DataFrame,
    flags: list[str],
    out_dir: Path,
    run_id: str,
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    d = scored.copy()
    d.insert(0, "rank", range(1, len(d) + 1))
    d["iapd_url"] = d["crd"].map(iapd_url)
    d["run_id"] = run_id
    cols = EXPORT_COLUMNS + [f for f in flags if f in d.columns] + ["run_id"]
    paths = {
        "scored_universe": out_dir / "scored_universe.csv",
        "top50": out_dir / "top50.csv",
        "top25": out_dir / "top25.csv",
        "suppression": out_dir / "suppression.csv",
    }
    d.to_csv(paths["scored_universe"], index=False)
    d[cols].head(50).to_csv(paths["top50"], index=False)
    top25 = d[cols].head(25).copy()
    top25["your_verdict"] = ""  # Yes / No / Already talking, filled in by the reader
    top25.to_csv(paths["top25"], index=False)
    s = suppressed.copy()
    s["iapd_url"] = s["crd"].map(iapd_url) if len(s) else []
    s["run_id"] = run_id
    keep = [c for c in ["crd", "name", "score", "tier", "iapd_url", "run_id"] if c in s.columns]
    s[keep].to_csv(paths["suppression"], index=False)
    return paths
