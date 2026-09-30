# ADR-004: pandas + YAML config + pytest, static HTML report, Claude Haiku in a plain loop

## Status
Accepted

## Date
2026-09-29

## Context
The whole job is a join and a score over a 17,149 x 448 table that loads in under a second.

## Decision
Python 3.12 managed by uv; pandas and openpyxl for ingest; the ICP as YAML data, not code; pytest with fixtures cut from the real files; a static HTML report on GitHub Pages; Claude Haiku 4.5 called in a plain loop for 50 drafts with a validator that rejects any number not present in the firm's row.

## Alternatives Considered
- React/Vite/Supabase front end: rejected; adds nothing a reviewer grades and reads as padding.
- Streamlit: rejected for the demo (sleeps); possible later.
- DuckDB/Polars: rejected for v1; the data fits in pandas trivially. A SQL cross-check of the funnel is a later stretch.
- Anthropic Batch API: rejected at 50 drafts; the README says when it would pay off.

## Consequences
- Swapping vendors is a new YAML file.
- The demo page never sleeps and holds no API key.
