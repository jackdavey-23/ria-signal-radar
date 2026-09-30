from pathlib import Path

import yaml

from radar.gates import apply_gates
from radar.ingest import join_years, load_fields, load_registered
from radar.signals import derive

CFG = yaml.safe_load(Path("config/icp_alts_platform.yaml").read_text())


def _universe(fixture_2026, fixture_2025):
    f = load_fields(Path("config/fields.yaml"))
    cur, _ = load_registered(fixture_2026, f)
    prior, _ = load_registered(fixture_2025, f)
    return derive(join_years(cur, prior), today_year=2026)


def test_funnel_is_monotonic_and_labeled(fixture_2026, fixture_2025):
    kept, funnel = apply_gates(_universe(fixture_2026, fixture_2025), CFG["gates"])
    counts = [row["remaining"] for row in funnel]
    assert counts == sorted(counts, reverse=True) and funnel[0]["gate"] == "all"
    assert [row["gate"] for row in funnel[1:]] == [g["id"] for g in CFG["gates"]]
    assert len(kept) == counts[-1]


def test_all_four_seeds_pass_every_gate(fixture_2026, fixture_2025):
    kept, _ = apply_gates(_universe(fixture_2026, fixture_2025), CFG["gates"])
    assert {s["crd"] for s in CFG["seeds"]} <= set(kept["crd"])
