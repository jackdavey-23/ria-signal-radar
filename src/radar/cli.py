"""Command line. `uv run python -m radar.cli run [--sensitivity]`. Drafts only, never sends."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml

from radar.draft import draft_openers
from radar.export import apply_suppression, write_outputs
from radar.gates import apply_gates
from radar.ingest import join_years, load_fields, load_registered
from radar.report import render_report
from radar.runlog import config_hash, run_id, write_run_log
from radar.score import collapse_network, score, seed_ranks, sensitivity
from radar.signals import derive

ROOT = Path(__file__).resolve().parents[2]


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def base_rates(universe, cfg: dict) -> dict:
    """How common each factor input and flag is in the gated universe (for the README table)."""
    out = {}
    for f in cfg["factors"]:
        s = universe[f["column"]]
        if s.dtype == bool:
            out[f["id"]] = {"share_true": round(float(s.mean()), 3)}
        else:
            q = s.quantile([0.25, 0.5, 0.75])
            out[f["id"]] = {
                "p25": float(q.iloc[0]),
                "median": float(q.iloc[1]),
                "p75": float(q.iloc[2]),
            }
    for name in cfg["flags"]:
        if name in universe:
            out[name] = {
                "share_true": round(float(universe[name].fillna(False).astype(bool).mean()), 3)
            }
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="radar")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="ingest -> join -> derive -> gates -> score -> export")
    r.add_argument("--config", type=Path, default=ROOT / "config" / "icp_alts_platform.yaml")
    r.add_argument("--fields", type=Path, default=ROOT / "config" / "fields.yaml")
    r.add_argument("--suppression", type=Path, default=ROOT / "config" / "suppression.yaml")
    r.add_argument("--current", type=Path, default=ROOT / "data/raw/ia09012026-registered.csv")
    r.add_argument("--prior", type=Path, default=ROOT / "data/raw/ia09022025.xlsx")
    r.add_argument("--out", type=Path, default=ROOT / "outputs")
    r.add_argument("--sensitivity", action="store_true", help="also run the +/-5 weight table")
    d = sub.add_parser("draft", help="draft openers for the top firms (needs ANTHROPIC_API_KEY)")
    d.add_argument("--out", type=Path, default=ROOT / "outputs")
    d.add_argument("--config", type=Path, default=ROOT / "config" / "icp_alts_platform.yaml")
    d.add_argument("--n", type=int, default=50)
    rp = sub.add_parser("report", help="render docs/index.html from outputs/")
    rp.add_argument("--out", type=Path, default=ROOT / "outputs")
    rp.add_argument("--html", type=Path, default=ROOT / "docs" / "index.html")
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
    robustness = collapse_network(scored, cfg) if args.sensitivity else None
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
        "base_rates": base_rates(kept, cfg),
        "sensitivity": sens,
        "robustness": robustness,
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


def draft(args: argparse.Namespace) -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set (put it in .env). No drafts were generated.")
    cfg = yaml.safe_load(args.config.read_text())
    top = pd.read_csv(args.out / "top50.csv")
    drafts, usage = draft_openers(top, n=args.n, flags=cfg["flags"])
    (args.out / "drafts.json").write_text(json.dumps(drafts, indent=2) + "\n")
    log_path = args.out / "run_log.json"
    log = json.loads(log_path.read_text())
    log["usage"] = usage
    write_run_log(log_path, log)
    valid = sum(d["valid"] for d in drafts)
    print(f"{valid} of {len(drafts)} drafts validated; cost ${usage['cost_usd']}")


def report(args: argparse.Namespace) -> None:
    log = json.loads((args.out / "run_log.json").read_text())
    top = pd.read_csv(args.out / "top50.csv")
    drafts_path = args.out / "drafts.json"
    drafts = json.loads(drafts_path.read_text()) if drafts_path.exists() else []
    p2_path = args.out / "am_distribution" / "run_log.json"
    preset2 = json.loads(p2_path.read_text()) if p2_path.exists() else None
    review_path = ROOT / "config" / "hand_review.yaml"
    review = None
    if review_path.exists():
        entries = (yaml.safe_load(review_path.read_text()) or {}).get("entries", [])
        review = {int(e["crd"]): e for e in entries}
    print(render_report(log, top, drafts, preset2, args.html, review))


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.cmd == "run":
        run(args)
    elif args.cmd == "draft":
        draft(args)
    elif args.cmd == "report":
        report(args)


if __name__ == "__main__":
    main()
