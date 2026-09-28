# Reference prices: sources, quality classes, close capture

Status: implemented (pre-launch remediation, phases 7–8; audit §G, §H, §K, §R1). Code:
`reference/quality.py`, `reference/close.py`, `reference/schemas.py` (v2 fields), `run/settle.py`
(`close_v2` on every settlement and due coverage row).

## Verdict on a free live sharp reference (2026-09-28)

**None exists.** Every source that gives Pinnacle-class quotes near kickoff requires credentials or a paid
plan (Pinnacle API, Betfair exchange API, The Odds API and other aggregators), and the sites that display
sharp prices publicly (OddsPortal, Sofascore, Oddschecker) forbid scraping in their terms. This system
therefore has **no TRUE_CLOSE-capable sharp feed**, `live_sharp_reference_available()` returns `False`,
and reference-anchored authority stays blocked until the owner provides a credentialed source (audit §R1:
the single most important owner decision). Nothing here calls Bet365 or a multi-book average "sharp".

What is implemented, honestly labelled:

| provider | quality of best bookmaker | live | near-kickoff | open/close history | cost |
|---|---|---|---|---|---|
| `football_data_couk_fixtures` (fixtures.csv) | SHARP_REFERENCE (Pinnacle column) | yes | **no** (refreshed a few times a week; quote time unknown) | no | free, keyless |
| `football_data_couk_historical` (season CSVs) | SHARP_REFERENCE | no | yes (PSCH etc. are closing) | **yes** (2019-20 →) | free, keyless |
| `kalshi_public` | KALSHI_ONLY | yes | yes | no | free |
| `the_odds_api` | SHARP_REFERENCE | yes | yes | no | key required — **not implemented** |

Because fixtures.csv quotes are stamped at *our* capture time and the upstream refresh cadence is a few
times per week, a fixtures.csv capture that lands inside the close window is a coincidence, not a close.
`is_close_candidate` is set only when the capture is ≤ 120 min before kickoff and the settlement report
counts how often that happens; expect it to be rare.

## Source quality classes

`SHARP_REFERENCE` (Pinnacle), `SECONDARY_REFERENCE` (Bet365, football-data average/max, our consensus),
`KALSHI_ONLY` (the Kalshi book; a separate axis, never an external reference), `UNAVAILABLE`.

Every reference snapshot row now carries: `source, bookmaker, market_family, side, raw_odds, decimal_odds,
devig_method, devigged_probability, captured_at, kickoff_utc, horizon_seconds, is_open,
is_close_candidate, source_quality` (plus the v1 fields). Old rows load unchanged (new fields optional).

## Close capture (phase 8)

| class | definition |
|---|---|
| TRUE_CLOSE | reference quote captured ≤ 15 min before kickoff |
| NEAR_CLOSE | reference quote captured ≤ 120 min before kickoff |
| KALSHI_CLOSE | last **valid** Kalshi book ≤ 30 min before kickoff |
| STALE | an observation exists but is older than its window |
| NONE | no pre-kickoff observation |

Valid Kalshi book: status active/open, `0 < yes_bid ≤ yes_ask < 1`, spread ≤ 10¢. Suspended markets,
sentinel `bid 0 / ask 1` and one-sided books are skipped and the search steps back to the previous valid
snapshot inside the window (counts of invalid books in the window are recorded).

For each due prediction the settlement writes `close_v2`: entry Kalshi price per side (YES ask, NO =
1 − YES bid), entry reference probability per side, the Kalshi close (bid/ask/mid, NO executable, minutes,
validity reason), the reference close (bookmaker, quality, de-vig method, p_yes and p_no, minutes) and two
completeness flags. `evaluation/settlement_coverage.v1.json` aggregates `close_completeness`: TRUE_CLOSE
share, reference-close share, Kalshi-close share, missing-close rates — the inputs to the promotion gates
(≥ 70 % TRUE_CLOSE, missing close ≤ 20 %).

The legacy `close_class` / `classify_close` (30 min / 6 h, source-agnostic) stays on the record for
continuity and is not used by the new gates.
