# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261115T142829Z-ed09e4` · generated 2026-11-15T14:28:29.610909Z · trigger `kalshi_capture:slate_refresh` · mode `reprice_only`

**Kalshi prices observed 2026-11-15T14:25:02.311463Z (CURRENT at publish; CURRENT until 2026-11-15T14:45:02.311463Z, STALE after 2026-11-15T14:55:02.311463Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-15T13:32:02.057613Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.84s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-15T17:00:00Z | Belarus vs Albania (uefa.nations_league) | VALID (AGING) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-15T17:00:00Z | Finland vs San Marino (uefa.nations_league) | VALID (AGING) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-15T19:45:00Z | Belgium vs Italy (uefa.nations_league) | VALID (AGING) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-15T19:45:00Z | Croatia vs Czechia (uefa.nations_league) | VALID (AGING) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-15T19:45:00Z | Spain vs England (uefa.nations_league) | VALID (AGING) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-15T19:45:00Z | France vs Türkiye (uefa.nations_league) | VALID (AGING) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-15T23:00:00Z | Panama vs Curaçao (concacaf.nations_league) | VALID (AGING) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 16 | 0 |
| 2026-11-16T15:00:00Z | Faroe Islands vs Moldova (uefa.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-16T15:00:00Z | Kazakhstan vs Slovakia (uefa.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-16T17:00:00Z | Estonia vs Bulgaria (uefa.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-16T17:00:00Z | Iceland vs Luxembourg (uefa.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-16T17:00:00Z | Lithuania vs Liechtenstein (uefa.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-16T18:00:00Z | Andorra vs Azerbaijan (fifa.friendly) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-16T19:00:00Z | Cuba vs Grenada (concacaf.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-16T19:00:00Z | Guadeloupe vs Bermuda (concacaf.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-16T19:00:00Z | Guyana vs Puerto Rico (concacaf.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-16T19:45:00Z | Germany vs Netherlands (uefa.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-16T19:45:00Z | Gibraltar vs Malta (uefa.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-16T19:45:00Z | Greece vs Serbia (uefa.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-16T19:45:00Z | North Macedonia vs Slovenia (uefa.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-16T19:45:00Z | Switzerland vs Scotland (uefa.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-17T00:00:00Z | Martinique vs Aruba (concacaf.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 16 | 0 |
| 2026-11-17T00:00:00Z | Trinidad and Tobago vs Antigua and Barbuda (concacaf.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 16 | 0 |
| 2026-11-17T01:00:00Z | Canada vs Guatemala (concacaf.nations_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 16 | 0 |
| 2026-11-17T13:10:00Z | Japan vs Paraguay (fifa.friendly) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |

## Candidates on CURRENT prices (0; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|

## Counts

```
action_EXCLUDED_BY_GATE: 104
action_NO_EDGE: 1802
action_NO_QUOTE: 314
contract_sides: 2220
fixtures: 25
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 2

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
