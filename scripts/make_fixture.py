"""Cut a 20-firm fixture from the real roster files, in raw format, for the test suite.

Usage: uv run python scripts/make_fixture.py   (needs data/raw/ from scripts/fetch_sec.py)
Selection is deterministic: the four seed CRDs, the first 8 CRDs (sorted) that look like the ICP,
the first 8 that fail the size gate, plus the first 2 CRDs absent from the prior-year file.
"""

from __future__ import annotations

from pathlib import Path

from radar.ingest import load_fields, parse_money, read_raw

ROOT = Path(__file__).resolve().parents[1]
CUR = ROOT / "data" / "raw" / "ia09012026-registered.csv"
PRIOR = ROOT / "data" / "raw" / "ia09022025.xlsx"
OUT = ROOT / "tests" / "fixtures"
SEEDS = [288863, 7717, 140367, 138938]


def main() -> None:
    fields = load_fields(ROOT / "config" / "fields.yaml")
    cols = [f.column for f in fields]
    cur, prior = read_raw(CUR)[cols], read_raw(PRIOR)[cols]
    crd = cur["Organization CRD#"].astype(int)
    raum = cur["5F(2)(c)"].map(parse_money)
    reps = cur["5B(2)"].map(parse_money)
    us = cur["Main Office Country"].eq("United States")
    looks_icp = us & raum.between(250e6, 25e9) & (reps >= 5)
    too_small = raum < 250e6
    prior_crds = set(prior["Organization CRD#"].astype(int))
    absent = ~crd.isin(prior_crds)
    picks = (
        SEEDS
        + sorted(crd[looks_icp])[:8]
        + sorted(crd[too_small])[:8]
        + sorted(crd[absent & looks_icp])[:2]
    )
    picks = list(dict.fromkeys(picks))
    OUT.mkdir(parents=True, exist_ok=True)
    cur[crd.isin(picks)].to_csv(OUT / "registered_2026.csv", index=False)
    prior[prior["Organization CRD#"].astype(int).isin(picks)].to_csv(
        OUT / "registered_2025.csv", index=False
    )
    print(f"wrote {crd.isin(picks).sum()} firms (2026) to {OUT}")


if __name__ == "__main__":
    main()
