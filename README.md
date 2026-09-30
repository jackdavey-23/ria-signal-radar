# RIA Signal Radar

> **Drafts only. Nothing is ever sent.** `DEMO_MODE` is hard-coded, no module may import an email library (a test enforces it), no LinkedIn, no BrokerCheck, no vendor logos or claimed affiliation.

Ranks the SEC-registered investment advisers in the monthly Form ADV roster against an alternatives platform's ideal customer profile, explains every score with the filing fields behind it, and exports a suppressed, CRM-shaped list. The ICP is a lookalike of one vendor's four public advisory customers (trade press, 2026-09-09). Built as a portfolio piece for GTM engineering work.

Every number on this page is copied from [`outputs/run_log.json`](outputs/run_log.json) for run **`20260930T052002-96162ad`** (config `d0f4e529eb3d`, frozen before the first run). Reproduce it with `uv run radar run --sensitivity` after `uv run python scripts/fetch_sec.py`.

## Funnel

Sep 2026 roster (17,149 firms × 448 columns) joined to Sep 2025 on CRD: 15,456 matched, 1,693 new registrants.

| Gate | Rule | Remaining |
|---|---|---|
| all | rows in file | 17,149 |
| us | Main office in the United States | 14,863 |
| bd_linked | Broker-dealer linked: 6A(1) is a broker-dealer, 6A(2) is a registered representative, or 7A(1) has a broker-dealer related person | 2,523 |
| real_network | 5B(2) registered representatives of a broker-dealer >= 5 | 1,323 |
| size | 5F(2)(c) regulatory assets under management between $250M and $25B | 787 |
| staff | 5A employees >= 10 | 711 |
| wealth_clients | 5D(b)(1) high net worth clients > 0 and HNW share of RAUM (5D(b)(3) / 5F(2)(c)) >= 0.20 | 392 |
| wealth_manager | Individuals (5D(a)(3) + 5D(b)(3)) >= 50% of RAUM and pooled vehicles 5D(f)(3) < 50% | 359 |

Universe: **359 firms**. Tiers: A 36 · B 67 · C 256 (A ≥ 75, B ≥ 60).

## How it works

`ingest` (typed load driven by [`config/fields.yaml`](config/fields.yaml), which quotes the Form ADV wording for every column) → `join_years` → `signals.derive` → `gates` → `score` → `export`. The ICP is data, not code: [`config/icp_aqua.yaml`](config/icp_aqua.yaml) holds the gates, weights, hypotheses and seeds, so a different vendor is a new YAML file. Decisions and their alternatives are in [`docs/decisions/`](docs/decisions/).

## Gates

| Gate | Rule |
|---|---|
| `us` | Main office in the United States |
| `bd_linked` | Broker-dealer linked: 6A(1) is a broker-dealer, 6A(2) is a registered representative, or 7A(1) has a broker-dealer related person |
| `real_network` | 5B(2) registered representatives of a broker-dealer >= 5 |
| `size` | 5F(2)(c) regulatory assets under management between $250M and $25B |
| `staff` | 5A employees >= 10 |
| `wealth_clients` | 5D(b)(1) high net worth clients > 0 and HNW share of RAUM (5D(b)(3) / 5F(2)(c)) >= 0.20 |
| `wealth_manager` | Individuals (5D(a)(3) + 5D(b)(3)) >= 50% of RAUM and pooled vehicles 5D(f)(3) < 50% |

## Scoring (100 points)

In RevOps terms this is a **fit score** built from explicit attributes in public filings. Public data has no engagement signal; growth is the closest thing and is mostly market beta, so it is percentile-ranked rather than used raw.

| Factor | Pts | Field (Form ADV wording) and transform | Hypothesis | Base rate in the 359 |
|---|---|---|---|---|
| `growth` | 20 | 5F(2)(c) total RAUM, this roster vs last year's; winsorized p5/p95; percentile rank (new registrants get 0.5 and a flag) | Growing networks onboard advisors and assets onto platforms. Percentile rank strips the market beta that dominates the median (+18.9% in the universe, 2026-09-29). Growth is annual-amendment to annual-amendment, not 'last 12 months'. | median +18.8% (p25 +11.7%, p75 +27.7%) |
| `seats` | 20 | max(5B(1) employees who perform investment advisory functions, 5B(2) registered representatives of a broker-dealer); log ramp 10 → 300 | The vendor's revenue KPI is advisor seats; one network decision covers hundreds of reps. seats = max(5B(1), 5B(2)). The score rank-correlates with network size by design. | median 35 (p25 14, p75 108) |
| `offices` | 10 | Item 1.F total number of offices other than the principal office; log ramp 1 → 100 | Office count (Item 1.F) makes independent broker-dealer networks visible. | median 9 (p25 1, p75 38) |
| `hybrid_depth` | 10 | 5B(2) ÷ 5A employees; linear 0 → 0.8 | Share of staff who are BD reps (5B(2) / 5A) = the alternatives distribution channel. | median 70% (p25 43%, p75 91%) |
| `platform_sponsor` | 10 | 5I(2)(a) or 5I(2)(c) RAUM as sponsor of a wrap fee program > 0 | Sponsors its own wrap fee program (5I(2)(a) or (c) > 0): one centralized platform decision. 5I(1) alone is too loose (53.5% of the universe). | 46% of the universe |
| `alts_re_lp` | 5 | 7A(14) related person is a real estate broker or dealer, or 7A(15) a sponsor or syndicator of limited partnerships | HYPOTHESIS. Related person is a real estate broker/dealer (7A(14)) or an LP sponsor/syndicator (7A(15)): the DST / non-traded program channel. | 10% of the universe |
| `alts_pooled` | 5 | 7B adviser to a private fund, or 7A(16) related person sponsors pooled investment vehicles, or 5D(f)(3) > 0 | HYPOTHESIS. Advises a private fund (7B), related person sponsors pooled vehicles (7A(16)), or 5D(f)(3) > 0: already runs access vehicles by hand. Capped at 5 because two of four seeds score zero. | 28% of the universe |
| `scale` | 10 | 5F(2)(c) total RAUM; log ramp $250M → $5B, flat above | Platform minimums. A log ramp, not a bell: two seeds are $8.8B and $12.9B. | median $1.59B (p25 $0.65B, p75 $4.20B) |
| `hnw_mix` | 10 | 5D(b)(3) HNW RAUM ÷ 5F(2)(c); linear 0.20 → 0.60 | Eligible clients. Form ADV 'high net worth' is the rule 205-3 qualified-client test, a lower bar than qualified purchaser, so this never claims accredited/QP eligibility. | median 56% (p25 41%, p75 71%) |

## What the data killed

Factors from the first draft, cut because they were constants or the wrong construct (computed 2026-09-29 on that draft's 4,258-firm universe):

- **5E(1) percent-of-AUM fee**: Y for 99% of firms. Discriminates nothing.
- **"Alts gap" = 7B is N**: on for 88%, and 7B means the adviser sponsors private funds, not that clients hold alternatives.
- **Discretionary share 5F(2)(a) ÷ 5F(2)(c)**: median 0.993. A flag now (`low_discretion`).
- **5A headcount growth**: median change 0.0% year over year.
- **"Filed in 2026"**: true for 16,912 of 17,149 firms. A flag now (`stale_filing`).
- **Raw RAUM growth**: median about +17%, which is 2025 market beta; hence percentile rank.

## Sanity check, not a backtest

The vendor's four public advisory customers all pass the gates and rank Arkadios Wealth Advisors #23 (A, 77.3), Independent Financial Group #50 (B, 71.4), Concorde Asset Management #93 (B, 61.5), DAI Wealth #151 (C, 53.1) of 359. n = 4, and these firms shaped the gates and weights, so this is a sanity check, not a backtest. The smallest logo lands in C tier because the score tracks network size by design; the run log reports it as is.

## Sensitivity

Each weight moved ±5 points; how many of the baseline top 50 stay in the top 50. This replaces weight sliders.

| Factor | Δ points | Top 50 kept |
|---|---|---|
| `growth` | +5 | 48 / 50 |
| `growth` | -5 | 48 / 50 |
| `seats` | +5 | 50 / 50 |
| `seats` | -5 | 49 / 50 |
| `offices` | +5 | 50 / 50 |
| `offices` | -5 | 49 / 50 |
| `hybrid_depth` | +5 | 50 / 50 |
| `hybrid_depth` | -5 | 48 / 50 |
| `platform_sponsor` | +5 | 46 / 50 |
| `platform_sponsor` | -5 | 49 / 50 |
| `alts_re_lp` | +5 | 49 / 50 |
| `alts_re_lp` | -5 | 47 / 50 |
| `alts_pooled` | +5 | 47 / 50 |
| `alts_pooled` | -5 | 45 / 50 |
| `scale` | +5 | 50 / 50 |
| `scale` | -5 | 49 / 50 |
| `hnw_mix` | +5 | 48 / 50 |
| `hnw_mix` | -5 | 47 / 50 |

## Flags and suppression

Flags appear in the why string and the exports. They are never scored, never gated, and never used in an opener. Share of the universe: `item11` 31%, `new_registrant` 1%, `stale_filing` 3%, `crossed_500m` 6%, `crossed_1b` 6%, `crossed_5b` 4%, `fund_launched` 1%, `bank_affiliate` 13%, `seat_growth` 12%, `low_discretion` 13%, `commissions` 12%, `manager_selection` 76%.

- **`item11`** covers the affiliated broker-dealer's regulatory history as well as the adviser's, which is why it is common in a BD-linked universe. Two of the four seed customers carry it. A flag for a human, never a hook.
- **`bank_affiliate`** (7A(8)) marks captive bank and insurer arms that surface in the top 50; those are enterprise procurement, not a founder-to-founder sale, and are removed by hand from any list a vendor sees.
- **Suppression** ([`config/suppression.yaml`](config/suppression.yaml)) removes the vendor's public customers and their affiliates by CRD only, never by name substring, before `top25_aqua.csv` is written. Every export row carries the `run_id`.

## Limitations

- **Timing.** Items 5, 6 and 7 of Form ADV change only in the annual updating amendment, due within 90 days of fiscal year end. The Sep 2026 roster mostly carries fiscal-year-end 2025 data, so "growth" is annual amendment to annual amendment, about nine months stale by the time this ran.
- **Growth is not purchase intent.** Nothing here measures whether anyone bought anything.
- **Brokerage-side alternatives are invisible.** Non-traded programs sold through the affiliated broker-dealer never appear in the adviser's ADV.
- **No custodian field** in the roster.
- **"High net worth"** on Form ADV is the rule 205-3 qualified-client test, a lower bar than qualified purchaser; this never claims accredited or QP eligibility.
- **No clean historical holdout exists.** The one candidate (7B flipping N → Y year over year) reverses direction depending on whether the alts factor is in the score, so it is not reported as validation.

## What I would do with budget

Contact waterfall (Clay or similar) for named decision-makers, reply-rate testing on two openers, the IAPD individual-adviser feed for real advisor movement, Form D for actual fund launches, and a monthly diff honestly named "new registrants and rebrands" rather than "movers".

## Compliance

Public SEC data only, at the firm level. Requests to sec.gov declare a User-Agent and stay under 10 per second. No IAPD brochure crawling, no BrokerCheck, no LinkedIn. Contacts in any export are placeholders. Keys live in `.env`; `data/` and the full scored universe are gitignored.

## Roadmap

v2: Claude-drafted openers for the top 50 with a validator that rejects any number not in the firm's row (drafts are exported, never sent); a HubSpot company-import CSV; a static report page.

## Author note

Claude Code writes most of the syntax. I set the gates and weights, tested the rankings against firms I know on IAPD, and fixed what broke.
