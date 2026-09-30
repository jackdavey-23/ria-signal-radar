# ADR-001: Build the ICP as a lookalike of the vendor's public customers

## Status
Accepted

## Date
2026-09-29

## Context
The first draft targeted fee-only, HNW-heavy RIAs with $250M–$5B in regulatory AUM. The modeled vendor's four public advisory customers (named in trade press, 2026-09-09) are broker-dealer-linked hybrid wealth networks. Two of the four are above $5B; a third has a 25% HNW share, which the draft's curve scored at zero.

## Decision
Define the ICP so that all four public customers pass every gate: broker-dealer link, >= 5 BD reps, $250M–$25B RAUM, >= 10 staff, HNW share >= 20%, individuals >= 50% of the book, US only. Score on network size and channel signals, not on RAUM alone.

## Alternatives Considered
- Fee-only HNW boutiques (the draft): rejected because the vendor's own logos would not make the list.
- Breakaway advisors: rejected because Form ADV has no prior-employer field and yields only 74–339 candidate firms a year; kept as a possible second preset.

## Consequences
- The universe is a few hundred firms, not several thousand; a top 50 is a large share of it.
- The seed check is circular by construction and is labeled a sanity check, never a backtest.
