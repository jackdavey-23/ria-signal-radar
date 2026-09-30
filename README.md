# RIA Signal Radar

> **Drafts only. Nothing is ever sent.** `DEMO_MODE` is hard-coded. No LinkedIn, no BrokerCheck, no vendor affiliation.

Ranks SEC-registered investment advisers from public Form ADV filings against a vendor's ideal customer profile, explains every score, and exports CRM-ready lists. Status: **v0 scaffold, no scoring run yet.** The ICP and weights in `config/icp_aqua.yaml` were committed before the first run.

## Layout
- `config/` — the ICP as data: gates, weights, hypotheses, field dictionary, suppression list
- `src/radar/` — ingest → join → derive → gates → score → export
- `docs/decisions/` — architecture decision records
- `scripts/fetch_sec.py` — downloads the two SEC roster files (declared User-Agent)

## Run
```bash
uv sync --all-groups
uv run python scripts/fetch_sec.py
uv run pytest
```
