# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261022T174423Z-d151ba` · generated 2026-10-22T17:44:23.190965Z · trigger `kalshi_capture` · mode `reprice_only`

**Kalshi prices observed 2026-10-22T17:41:25.268109Z (CURRENT at publish; CURRENT until 2026-10-22T18:01:25.268109Z, STALE after 2026-10-22T18:11:25.268109Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-22T13:22:53.257379Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.33s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-23T18:30:00Z | VfB Stuttgart vs Borussia Mönchengladbach (ger.bundesliga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-23T18:45:00Z | Brest vs Nice (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-23T18:45:00Z | Torino vs Monza (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-23T19:00:00Z | Ipswich Town vs Nottingham Forest (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 81 | 0 |
| 2026-10-23T23:00:00Z | Cruzeiro vs Remo (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 21 | 3 |
| 2026-10-24T01:00:00Z | Necaxa vs FC Juárez (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-24T03:00:00Z | Atlante vs Atlético San Luis (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-24T11:30:00Z | Aston Villa vs Manchester City (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 83 | 0 |
| 2026-10-24T13:00:00Z | Cagliari vs Bologna (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-24T13:00:00Z | Como vs Sassuolo (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (3; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Atlante vs Atlético San Luis | btts | no | 0.4300 | 0.541 [0.409, 0.668] | +0.094 | +0.010 | 0.43 | - | * | RESEARCH_CANDIDATE |
| Cagliari vs Bologna | Result: home | yes | 0.3100 | 0.444 [0.282, 0.615] | +0.119 | +0.006 | 0.31 | - | * | RESEARCH_CANDIDATE |
| Cagliari vs Bologna | Result: away | no | 0.6300 | 0.736 [0.592, 0.861] | +0.090 | +0.005 | 0.63 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 321
action_NO_QUOTE: 1124
action_RESEARCH_CANDIDATE: 3
contract_sides: 1448
fixtures: 10
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
