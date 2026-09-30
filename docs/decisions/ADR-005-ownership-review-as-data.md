# ADR-005: Ownership is invisible to Form ADV; review it as versioned data, not a gate

## Status
Accepted

## Date
2026-09-30

## Context
A name-by-name review of the first top 50 (each firm's website, Form ADV/IAPD and news, 2026-09-30) found that the shape of the list is right (20 of the 32 non-bank names are independent hybrid networks like the vendor's customers) but the roster cannot see who owns a firm. Four blind spots: insurer captives that the bank flag misses (Guardian's Park Avenue Securities, Primerica); aggregator subsidiaries scored as standalone firms (Osaic Advisory, Kestra Private Wealth); regional brokerages and an investment bank (Davenport, Stephens, A.G.P.); and duplicate or wrong-tier entities (Intrua, owned by Larson; NewEdge Wealth). One automatic removal was a false positive (Level Four: its "bank" affiliate is a trust company). Several legal names are stale brands (Visionary Square, formerly Independent Advisor Alliance).

## Decision
Keep the frozen config as is. Record every ownership judgment in `config/hand_review.yaml` (CRD, decision, category, source-dated note, display name), apply it in `scripts/build_vendor_sheet.py` after the automatic bank-affiliate removal, and show it as a column on the report page. Firms beyond the reviewed rank enter the vendor sheet only after review.

## Alternatives Considered
- Add gates now (staff ceiling near 1,000, size ceiling near $15B, a parent map by CRD): rejected for this version because changing the frozen weights reshuffles the list and admits unreviewed names; planned as config v2 with its own review.
- Ignore it and rely on the flags: rejected; a buyer who sees an insurer captive at #11 concludes the model does not understand the buyer.

## Consequences
- The vendor sheet is defensible name by name, and the judgment is auditable and diffable like the config.
- The review is a human cost per run; a config v2 with a staff ceiling and a parent map would cut it.
