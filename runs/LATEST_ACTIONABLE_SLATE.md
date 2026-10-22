# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261022T020243Z-88d3de` · generated 2026-10-22T02:02:43.612495Z · trigger `kalshi_capture:slate_refresh` · mode `reprice_only`

**Kalshi prices observed 2026-10-22T02:00:05.326684Z (CURRENT at publish; CURRENT until 2026-10-22T02:20:05.326684Z, STALE after 2026-10-22T02:30:05.326684Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-22T01:17:44.678113Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.13s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-22T03:10:00Z | Pachuca vs Cruz Azul (mex.liga_mx) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-22T03:10:00Z | Santos Laguna vs Pumas UNAM (mex.liga_mx) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-23T18:30:00Z | VfB Stuttgart vs Borussia Mönchengladbach (ger.bundesliga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T18:45:00Z | Brest vs Nice (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T18:45:00Z | Torino vs Monza (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T19:00:00Z | Ipswich Town vs Nottingham Forest (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T23:00:00Z | Cruzeiro vs Remo (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 11 | 3 |
| 2026-10-24T01:00:00Z | Necaxa vs FC Juárez (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (3; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Pachuca vs Cruz Azul | First half: away wins by more than 1.5 | no | 0.8900 | 0.932 [0.869, 0.981] | +0.035 | +0.003 | 0.89 | - | * | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | Result: away | no | 0.5800 | 0.687 [0.531, 0.819] | +0.089 | +0.002 | 0.58 | - | * | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | away team total over 1.5 | no | 0.5000 | 0.621 [0.447, 0.765] | +0.104 | +0.001 | 0.5 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 433
action_NO_QUOTE: 72
action_RESEARCH_CANDIDATE: 3
contract_sides: 508
fixtures: 8
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
