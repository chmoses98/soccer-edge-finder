# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261022T124016Z-3c5e2c` · generated 2026-10-22T12:40:16.544493Z · trigger `kalshi_capture` · mode `reprice_only`

**Kalshi prices observed 2026-10-22T12:37:22.470225Z (CURRENT at publish; CURRENT until 2026-10-22T12:57:22.470225Z, STALE after 2026-10-22T13:07:22.470225Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-22T01:17:44.678113Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.16s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-23T18:30:00Z | VfB Stuttgart vs Borussia Mönchengladbach (ger.bundesliga) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T18:45:00Z | Brest vs Nice (fra.ligue_1) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T18:45:00Z | Torino vs Monza (ita.serie_a) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T19:00:00Z | Ipswich Town vs Nottingham Forest (eng.premier_league) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T23:00:00Z | Cruzeiro vs Remo (bra.serie_a) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 11 | 3 |
| 2026-10-24T01:00:00Z | Necaxa vs FC Juárez (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (1; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Torino vs Monza | Result: draw | no | 0.7200 | 0.783 [0.712, 0.854] | +0.049 | +0.005 | 0.72 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 173
action_NO_QUOTE: 26
action_RESEARCH_CANDIDATE: 1
contract_sides: 200
fixtures: 6
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
