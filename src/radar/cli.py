"""Command line. `uv run python -m radar.cli run [--sensitivity]`. Drafts only, never sends."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

import yaml

from radar.export import apply_suppression, write_outputs
from radar.gates import apply_gates
from radar.ingest import join_years, load_fields, load_registered
from radar.runlog import config_hash, run_id, write_run_log
from radar.score import score, seed_ranks, sensitivity
from radar.signals import derive

ROOT = Path(__file__).resolve().parents[2]


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="radar")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="ingest -> join -> derive -> gates -> score -> export")
    r.add_argument("--config", type=Path, default=ROOT / "config" / "icp_aqua.yaml")
    r.add_argument("--fields", type=Path, default=ROOT / "config" / "fields.yaml")
    r.add_argument("--suppression", type=Path, default=ROOT / "config" / "suppression.yaml")
    r.add_argument("--current", type=Path, default=ROOT / "data/raw/ia09012026-registered.csv")
    r.add_argument("--prior", type=Path, default=ROOT / "data/raw/ia09022025.xlsx")
    r.add_argument("--out", type=Path, default=ROOT / "outputs")
    r.add_argument("--sensitivity", action="store_true", help="also run the +/-5 weight table")
    return p


def run(args: argparse.Namespace) -> dict:
    cfg = yaml.safe_load(args.config.read_text())
    fields = load_fields(args.fields)
    suppression = yaml.safe_load(args.suppression.read_text())["entries"]
    current, current_info = load_registered(args.current, fields)
    prior, prior_info = load_registered(args.prior, fields)
    now = datetime.now(UTC)
    universe = derive(join_years(current, prior), today_year=now.year)
    kept, funnel = apply_gates(universe, cfg["gates"])
    scored = score(kept, cfg)
    rid = run_id()
    seeds = seed_ranks(scored, cfg["seeds"])
    sens = sensitivity(scored, cfg) if args.sensitivity else []
    final, suppressed = apply_suppression(scored, suppression)
    paths = write_outputs(final, suppressed, cfg["flags"], args.out, rid)
    log = {
        "run_id": rid,
        "generated_at": now.isoformat(timespec="seconds"),
        "inputs": [current_info, prior_info],
        "config": {
            "path": _rel(args.config),
            "hash": config_hash(args.config),
            "alts_direction": cfg.get("alts_direction"),
        },
        "join": {
            "matched": int((~universe["new_registrant"]).sum()),
            "new_registrant": int(universe["new_registrant"].sum()),
        },
        "funnel": funnel,
        "universe_size": int(len(scored)),
        "tier_counts": {k: int(v) for k, v in scored["tier"].value_counts().items()},
        "seed_ranks": seeds,
        "sensitivity": sens,
        "suppressed": [
            {"crd": int(c), "name": n}
            for c, n in zip(suppressed["crd"], suppressed["name"], strict=True)
        ],
        "growth_fill_rule": (
            "new registrants get percentile 0.5 and the NEW_REGISTRANT flag; "
            "prior RAUM <= 0 is treated as missing"
        ),
        "outputs": {k: _rel(v) for k, v in paths.items()},
        "usage": None,
    }
    write_run_log(args.out / "run_log.json", log)
    for row in funnel:
        print(f"{row['remaining']:>7}  {row['gate']}")
    print(f"run_id {rid}  universe {len(scored)}  tiers {log['tier_counts']}")
    for s in seeds:
        print(f"seed {s['name']}: rank {s['rank']}  tier {s['tier']}  score {s['score']}")
    return log


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.cmd == "run":
        run(args)


if __name__ == "__main__":
    main()
