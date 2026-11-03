# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261103T074915Z-9811bd` · generated 2026-11-03T07:49:15.800302Z · trigger `kalshi_capture` · mode `reprice_only`

**Kalshi prices observed 2026-11-03T07:46:28.352519Z (CURRENT at publish; CURRENT until 2026-11-03T08:06:28.352519Z, STALE after 2026-11-03T08:16:28.352519Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-03T01:46:24.161896Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.06s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-03T22:30:00Z | Chapecoense vs Mirassol (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-04T00:30:00Z | Internacional vs Coritiba (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-04T22:30:00Z | Athletico Paranaense vs Vasco da Gama (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-04T22:30:00Z | Flamengo vs Grêmio (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-05T00:30:00Z | Botafogo vs Atlético Mineiro (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-05T00:30:00Z | São Paulo vs Corinthians (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |

## Candidates on CURRENT prices (5; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Botafogo vs Atlético Mineiro | Result: home | no | 0.5000 | 0.625 [0.479, 0.763] | +0.108 | +0.019 | 0.51 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | home wins by more than 1.5 | no | 0.7400 | 0.827 [0.719, 0.920] | +0.074 | +0.016 | 0.75 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | home wins by more than 2.5 | no | 0.9000 | 0.936 [0.873, 0.981] | +0.029 | +0.003 | 0.9 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Total goals over 3.5 | no | 0.6700 | 0.765 [0.629, 0.879] | +0.080 | +0.001 | 0.67 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Total goals over 0.5 | no | 0.0600 | 0.102 [0.050, 0.162] | +0.038 | +0.000 | 0.06 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 162
action_NO_QUOTE: 181
action_RESEARCH_CANDIDATE: 5
contract_sides: 348
fixtures: 6
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
