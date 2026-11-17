# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261117T202825Z-1f3143` · generated 2026-11-17T20:28:25.875184Z · trigger `kalshi_capture:slate_refresh` · mode `reprice_only`

**Kalshi prices observed 2026-11-17T20:25:04.563781Z (CURRENT at publish; CURRENT until 2026-11-17T20:45:04.563781Z, STALE after 2026-11-17T20:55:04.563781Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-17T19:33:32.398111Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.21s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-17T23:00:00Z | Argentina vs Costa Rica (fifa.friendly) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 23 | 0 |
| 2026-11-17T23:30:00Z | Uruguay vs Dominican Republic (fifa.friendly) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 23 | 0 |
| 2026-11-18T00:00:00Z | United States vs Haiti (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 25 | 0 |
| 2026-11-18T01:00:00Z | El Salvador vs St. Martin (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 25 | 0 |
| 2026-11-18T02:30:00Z | Mexico vs Jamaica (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 25 | 0 |
| 2026-11-18T03:00:00Z | Nicaragua vs Montserrat (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 25 | 0 |
| 2026-11-18T22:30:00Z | Coritiba vs Santos (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-18T23:00:00Z | Remo vs Chapecoense (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-18T23:30:00Z | Cruzeiro vs Palmeiras (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-18T23:30:00Z | Flamengo vs Athletico Paranaense (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-19T00:30:00Z | Corinthians vs Botafogo (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-19T00:30:00Z | Grêmio vs Bahia (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |

## Candidates on CURRENT prices (0; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|

## Counts

```
action_EXCLUDED_BY_GATE: 68
action_NO_EDGE: 371
action_NO_QUOTE: 201
contract_sides: 640
fixtures: 12
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 8

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
