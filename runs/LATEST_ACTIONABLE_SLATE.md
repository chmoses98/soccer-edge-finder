# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261015T120823Z-ddcbbf` · generated 2026-10-15T12:08:23.170819Z · trigger `kalshi_capture` · mode `reprice_only`

**Kalshi prices observed 2026-10-15T12:05:30.506708Z (CURRENT at publish; CURRENT until 2026-10-15T12:25:30.506708Z, STALE after 2026-10-15T12:35:30.506708Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-15T11:42:28.739380Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.15s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-15T23:00:00Z | Huracán vs Gimnasia La Plata (arg.primera) | VALID (AGING) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-16T18:30:00Z | Eintracht Frankfurt vs 1. FC Köln (ger.bundesliga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-16T18:45:00Z | Le Mans vs Toulouse (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-16T18:45:00Z | Frosinone vs Sassuolo (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-16T19:00:00Z | Deportivo La Coruña vs Levante (esp.la_liga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-16T23:00:00Z | Mirassol vs Internacional (bra.serie_a) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-17T01:00:00Z | Necaxa vs Atlas (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-17T03:00:00Z | Atlante vs Pumas UNAM (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-17T03:05:00Z | Tijuana vs Puebla (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 32 | 0 |
| 2026-10-17T11:30:00Z | Everton vs Chelsea (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |

## Candidates on CURRENT prices (8; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Everton vs Chelsea | Result: away | no | 0.5600 | 0.732 [0.582, 0.867] | +0.154 | +0.064 | 0.62 | - | * | RESEARCH_CANDIDATE |
| Everton vs Chelsea | Result: home | yes | 0.3000 | 0.494 [0.314, 0.676] | +0.179 | +0.063 | 0.36 | - |  | RESEARCH_CANDIDATE |
| Tijuana vs Puebla | btts | no | 0.4500 | 0.596 [0.481, 0.710] | +0.129 | +0.056 | 0.5 | - | * | RESEARCH_CANDIDATE |
| Tijuana vs Puebla | Total goals over 3.5 | no | 0.6900 | 0.796 [0.662, 0.910] | +0.091 | +0.018 | 0.7 | - | * | RESEARCH_CANDIDATE |
| Tijuana vs Puebla | Total goals over 2.5 | no | 0.4700 | 0.605 [0.438, 0.762] | +0.117 | +0.016 | 0.48 | - |  | RESEARCH_CANDIDATE |
| Tijuana vs Puebla | Total goals over 1.5 | no | 0.2300 | 0.346 [0.202, 0.493] | +0.103 | +0.011 | 0.24 | - |  | RESEARCH_CANDIDATE |
| Tijuana vs Puebla | Total goals over 4.5 | no | 0.8500 | 0.908 [0.826, 0.972] | +0.049 | +0.010 | 0.86 | - |  | RESEARCH_CANDIDATE |
| Tijuana vs Puebla | away team total over 1.5 | no | 0.7400 | 0.818 [0.710, 0.906] | +0.064 | +0.004 | 0.74 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 359
action_NO_QUOTE: 69
action_RESEARCH_CANDIDATE: 8
contract_sides: 436
fixtures: 10
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
