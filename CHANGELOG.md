# Changelog

## v2 — 2026-09-30
- Vendor-neutral config name (`icp_alts_platform.yaml`), second preset `icp_am_distribution.yaml` (run `20260930T053209-645da65`: 17,149 → 14,863 → 8,248 → 6,887 → 3,409 → 3,377 → 1,740).
- `radar draft`: Claude Haiku 4.5 openers with a claims validator; drafts exported, never sent; cost from real usage.
- `radar report`: static page in `docs/` for GitHub Pages. HubSpot company-import CSV with social-host domain guard.

## v1 — 2026-09-30
- First scoring run `20260930T052002-96162ad` (config `d0f4e529eb3d`): funnel 17,149 → 14,863 → 2,523 → 1,323 → 787 → 711 → 392 → 359; tiers A 36 / B 67 / C 256; seeds Arkadios Wealth Advisors #23 (A, 77.3), Independent Financial Group #50 (B, 71.4), Concorde Asset Management #93 (B, 61.5), DAI Wealth #151 (C, 53.1).
- Modules: ingest, signals, gates, score (+ sensitivity, seed ranks), export (suppression by CRD), run log, CLI.  in CI.

## v0 — 2026-09-29
- Scaffold: config-as-data (`config/`), field dictionary, suppression list, ADRs, CI, fetch script.
- No scoring has been run. Weights in `config/icp_alts_platform.yaml` are frozen before the first run.
