# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261111T181435Z-c959d0` · generated 2026-11-11T18:14:35.939800Z · trigger `kalshi_capture` · mode `reprice_only`

**Kalshi prices observed 2026-11-11T18:11:24.375916Z (CURRENT at publish; CURRENT until 2026-11-11T18:31:24.375916Z, STALE after 2026-11-11T18:41:24.375916Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-11T15:23:49.831951Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.50s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-12T17:00:00Z | Lithuania vs Suriname (fifa.friendly) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-12T17:00:00Z | Armenia vs Cyprus (uefa.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-12T17:00:00Z | Türkiye vs Belgium (uefa.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-12T19:00:00Z | Barbados vs Guadeloupe (concacaf.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-12T19:00:00Z | Cayman Islands vs Guyana (concacaf.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-12T19:45:00Z | Albania vs Finland (uefa.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-12T19:45:00Z | Czechia vs Spain (uefa.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-12T19:45:00Z | England vs Croatia (uefa.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-12T19:45:00Z | Italy vs France (uefa.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-12T19:45:00Z | Montenegro vs Latvia (uefa.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-12T19:45:00Z | San Marino vs Belarus (uefa.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-12T20:00:00Z | Bonaire vs Cuba (concacaf.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-12T22:00:00Z | Aruba vs Martinique (concacaf.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-12T23:00:00Z | Antigua and Barbuda vs Trinidad and Tobago (concacaf.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-13T00:30:00Z | Curaçao vs Panama (concacaf.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-13T14:45:00Z | Qatar vs Australia (fifa.friendly) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |

## Candidates on CURRENT prices (0; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|

## Counts

```
action_EXCLUDED_BY_GATE: 76
action_NO_EDGE: 977
action_NO_QUOTE: 147
contract_sides: 1200
fixtures: 16
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
