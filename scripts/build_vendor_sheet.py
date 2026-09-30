"""Build outputs/vendor_sheet.csv: the top 25 a vendor sees, after automatic and human review.

Order: (1) suppression already ran inside `radar run`; (2) bank_affiliate rows drop unless a
hand-review entry restores them; (3) hand-review `remove` entries drop; (4) rows beyond the reviewed
rank are admitted only if a hand-review entry keeps them. Backfills until 25 rows.
Usage: uv run python scripts/build_vendor_sheet.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]


def money(v: float) -> str:
    return f"${v / 1e9:.2f}B" if v >= 1e9 else f"${v / 1e6:.0f}M"


def load_review() -> tuple[dict[int, dict], int]:
    review = yaml.safe_load((ROOT / "config" / "hand_review.yaml").read_text()) or {}
    entries = {int(e["crd"]): e for e in review.get("entries", [])}
    return entries, int(review.get("reviewed_through_rank", 0))


def allowed(row: pd.Series, entries: dict[int, dict], reviewed_through: int) -> bool:
    e = entries.get(int(row["crd"]))
    if e and e["decision"] == "remove":
        return False
    if e and e["decision"] == "restore":
        return True
    if bool(row["bank_affiliate"]):
        return False
    if int(row["rank"]) > reviewed_through:
        return bool(e and e["decision"] == "keep")
    return True


def main() -> None:
    universe = pd.read_csv(ROOT / "outputs" / "scored_universe.csv")  # post-suppression, ranked
    entries, reviewed_through = load_review()
    keep = universe[universe.apply(lambda r: allowed(r, entries, reviewed_through), axis=1)]
    d = keep.head(25).copy()
    d["Firm"] = [
        entries.get(int(c), {}).get("display_name", n)
        for c, n in zip(d["crd"], d["name"], strict=True)
    ]
    d["Review note"] = [entries.get(int(c), {}).get("note", "") for c in d["crd"]]
    d["RAUM"] = d["raum"].map(money)
    d["Growth vs prior filing"] = d["growth"].map(lambda g: "" if pd.isna(g) else f"{g:+.0%}")
    d["HNW share"] = d["hnw_share"].map(lambda x: f"{x:.0%}")
    d["IAPD"] = d["crd"].map(lambda c: f"https://adviserinfo.sec.gov/firm/summary/{int(c)}")
    out = d.rename(
        columns={
            "rank": "Radar rank",
            "city": "City",
            "state": "State",
            "seats": "Advisor seats",
            "offices": "Other offices",
            "score": "Score",
            "tier": "Tier",
            "why": "Why",
            "fund_launched": "Launched a private fund since prior filing",
            "crd": "CRD",
        }
    )[
        [
            "Radar rank",
            "Firm",
            "City",
            "State",
            "RAUM",
            "Growth vs prior filing",
            "Advisor seats",
            "Other offices",
            "HNW share",
            "Score",
            "Tier",
            "Why",
            "Review note",
            "Launched a private fund since prior filing",
            "IAPD",
            "CRD",
        ]
    ]
    out["Your verdict (Yes / No / Already talking)"] = ""
    path = ROOT / "outputs" / "vendor_sheet.csv"
    out.to_csv(path, index=False)
    removed = sum(1 for e in entries.values() if e["decision"] == "remove")
    print(f"{len(out)} rows -> {path.name}; hand-removed {removed}")
    print("bank-affiliated rows dropped unless restored by hand review")


if __name__ == "__main__":
    main()
