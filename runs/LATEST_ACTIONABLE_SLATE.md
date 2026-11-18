# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261118T010052Z-5ebb6a` · generated 2026-11-18T01:00:52.026125Z · trigger `kickoff_chain:T-5` · mode `reprice_only`

**Kalshi prices observed 2026-11-18T00:57:29.958523Z (CURRENT at publish; CURRENT until 2026-11-18T01:17:29.958523Z, STALE after 2026-11-18T01:27:29.958523Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-18T00:13:27.244387Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.22s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-18T02:30:00Z | Mexico vs Jamaica (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 25 | 0 |
| 2026-11-18T03:00:00Z | Nicaragua vs Montserrat (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 25 | 0 |
| 2026-11-18T22:30:00Z | Coritiba vs Santos (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-18T23:00:00Z | Remo vs Chapecoense (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-18T23:30:00Z | Cruzeiro vs Palmeiras (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-18T23:30:00Z | Flamengo vs Athletico Paranaense (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-19T00:30:00Z | Corinthians vs Botafogo (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-19T00:30:00Z | Grêmio vs Bahia (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-19T22:30:00Z | Vasco da Gama vs Internacional (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-19T22:30:00Z | Vitória vs Red Bull Bragantino (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |

## Candidates on CURRENT prices (1; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Vitória vs Red Bull Bragantino | btts | no | 0.4200 | 0.534 [0.416, 0.646] | +0.097 | +0.024 | 0.44 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_EXCLUDED_BY_GATE: 33
action_NO_EDGE: 284
action_NO_QUOTE: 186
action_RESEARCH_CANDIDATE: 1
contract_sides: 504
fixtures: 10
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 1

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
