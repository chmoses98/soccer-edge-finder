# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261103T000213Z-169600` · generated 2026-11-03T00:02:13.920571Z · trigger `kickoff_chain:T-15` · mode `reprice_only`

**Kalshi prices observed 2026-11-02T23:59:33.606769Z (CURRENT at publish; CURRENT until 2026-11-03T00:19:33.606769Z, STALE after 2026-11-03T00:29:33.606769Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-02T23:27:44.261305Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.09s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-03T22:30:00Z | Chapecoense vs Mirassol (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-04T00:30:00Z | Internacional vs Coritiba (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-04T22:30:00Z | Athletico Paranaense vs Vasco da Gama (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-04T22:30:00Z | Flamengo vs Grêmio (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |

## Candidates on CURRENT prices (0; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|

## Counts

```
action_NO_EDGE: 111
action_NO_QUOTE: 61
contract_sides: 172
fixtures: 4
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
