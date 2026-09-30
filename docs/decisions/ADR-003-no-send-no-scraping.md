# ADR-003: No send path, no LinkedIn or BrokerCheck, firm-level data only

## Status
Accepted

## Date
2026-09-29

## Context
This is a prospecting pipeline built by a student as a portfolio piece. CAN-SPAM applies to B2B email. LinkedIn's User Agreement (section 8.2) and FINRA BrokerCheck's terms prohibit scraping.

## Decision
`DEMO_MODE = True` is a module constant. No module imports an email library; a test enforces it. Contacts are placeholders. Only public SEC data at the firm level is stored. SEC requests declare a User-Agent and stay under 10 per second. No vendor logos or claimed affiliation.

## Consequences
- Drafts are exported, never sent.
- Contact enrichment is described in the README as "what I'd do with budget," not implemented.
