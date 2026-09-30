# ADR-002: Freeze weights before the first run; sensitivity table instead of sliders

## Status
Accepted

## Date
2026-09-29

## Context
Weight sliders in a demo invite the question "so the weights are arbitrary?" and let the author tune weights after seeing the ranking.

## Decision
`config/icp_aqua.yaml` is committed before any scoring run and the README cites the commit hash. The report shows a sensitivity table: each weight moved +/-5 points, how many of the top 50 remain. Every factor row carries the Form ADV wording, the transform, a hypothesis, and its base rate in the universe.

## Alternatives Considered
- Interactive sliders (Streamlit): rejected; sleeps on the free tier and answers the wrong question.
- Fitting weights to an outcome: rejected; no clean outcome exists in the data (see README limitations).

## Consequences
- Factors that turn out to be constants are cut and listed under "What the data killed" rather than silently reweighted.
- Changing a weight is a new commit and a new run_id.
