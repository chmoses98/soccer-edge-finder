# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261012T165734Z-706fc5` · generated 2026-10-12T16:57:34.268326Z · trigger `kickoff_chain:T-120` · mode `reprice_only`

**Kalshi prices observed 2026-10-12T16:55:01.257774Z (CURRENT at publish; CURRENT until 2026-10-12T17:15:01.257774Z, STALE after 2026-10-12T17:25:01.257774Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-12T15:43:34.194171Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.13s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-12T18:45:00Z | Torino vs Udinese (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-12T19:00:00Z | Lanús vs Vélez Sarsfield (arg.primera) | VALID (AGING) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-12T19:00:00Z | Coritiba vs Botafogo (bra.serie_a) | VALID (AGING) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-12T19:00:00Z | Coventry City vs Newcastle United (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-12T19:00:00Z | Levante vs Sevilla (esp.la_liga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-12T22:30:00Z | Chapecoense vs Athletico Paranaense (bra.serie_a) | VALID (AGING) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-13T00:00:00Z | Red Bull Bragantino vs Cruzeiro (bra.serie_a) | VALID (AGING) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |

## Candidates on CURRENT prices (6; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Red Bull Bragantino vs Cruzeiro | btts | no | 0.3900 | 0.509 [0.391, 0.631] | +0.103 | +0.026 | 0.41 | - | * | RESEARCH_CANDIDATE |
| Torino vs Udinese | Result: draw | no | 0.6900 | 0.753 [0.696, 0.805] | +0.048 | +0.013 | 0.7 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | Total goals over 3.5 | no | 0.6500 | 0.754 [0.619, 0.875] | +0.089 | +0.012 | 0.66 | - | * | RESEARCH_CANDIDATE |
| Levante vs Sevilla | Result: draw | no | 0.7000 | 0.759 [0.703, 0.814] | +0.045 | +0.007 | 0.7 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | Total goals over 2.5 | no | 0.4300 | 0.552 [0.395, 0.704] | +0.105 | +0.007 | 0.43 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | Total goals over 1.5 | no | 0.2000 | 0.297 [0.173, 0.427] | +0.086 | +0.002 | 0.2 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 96
action_NO_QUOTE: 118
action_RESEARCH_CANDIDATE: 6
contract_sides: 220
fixtures: 7
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 1

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
