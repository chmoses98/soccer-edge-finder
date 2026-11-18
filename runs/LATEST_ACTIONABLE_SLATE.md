# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261117T235921Z-631fb6` · generated 2026-11-17T23:59:21.883318Z · trigger `kickoff_chain:T-60/T-5` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-11-17T23:55:00.080114Z (CURRENT at publish; CURRENT until 2026-11-18T00:15:00.080114Z, STALE after 2026-11-18T00:25:00.080114Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-17T23:59:14.288796Z · simulations this update: 2 · Odds API calls this update: 0 (credits 0) · reprice 0.24s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-18T00:00:00Z | United States vs Haiti (concacaf.nations_league) | VALID (CURRENT) | confirmed (CURRENT) | UNAVAILABLE | CURRENT | 25 | 0 |
| 2026-11-18T01:00:00Z | El Salvador vs St. Martin (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 25 | 0 |
| 2026-11-18T02:30:00Z | Mexico vs Jamaica (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 25 | 0 |
| 2026-11-18T03:00:00Z | Nicaragua vs Montserrat (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 25 | 0 |
| 2026-11-18T22:30:00Z | Coritiba vs Santos (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-18T23:00:00Z | Remo vs Chapecoense (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-18T23:30:00Z | Cruzeiro vs Palmeiras (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-18T23:30:00Z | Flamengo vs Athletico Paranaense (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-19T00:30:00Z | Corinthians vs Botafogo (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-19T00:30:00Z | Grêmio vs Bahia (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |

## Candidates on CURRENT prices (0; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|

## Counts

```
action_EXCLUDED_BY_GATE: 47
action_NO_EDGE: 309
action_NO_QUOTE: 192
contract_sides: 548
fixtures: 10
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 2

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
