# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261015T053212Z-1c908a` · generated 2026-10-15T05:32:12.706834Z · trigger `kalshi_capture` · mode `reprice_only`

**Kalshi prices observed 2026-10-15T05:29:19.443945Z (CURRENT at publish; CURRENT until 2026-10-15T05:49:19.443945Z, STALE after 2026-10-15T05:59:19.443945Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-15T01:42:52.637874Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.14s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-15T23:00:00Z | Huracán vs Gimnasia La Plata (arg.primera) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-16T18:30:00Z | Eintracht Frankfurt vs 1. FC Köln (ger.bundesliga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-16T18:45:00Z | Le Mans vs Toulouse (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-16T18:45:00Z | Frosinone vs Sassuolo (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-16T19:00:00Z | Deportivo La Coruña vs Levante (esp.la_liga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-16T23:00:00Z | Mirassol vs Internacional (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-17T01:00:00Z | Necaxa vs Atlas (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (0; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|

## Counts

```
action_NO_EDGE: 173
action_NO_QUOTE: 39
contract_sides: 212
fixtures: 7
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
