# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261103T202511Z-9240fe` · generated 2026-11-03T20:25:11.644960Z · trigger `kickoff_chain:T-120` · mode `reprice_only`

**Kalshi prices observed 2026-11-03T20:22:31.109860Z (CURRENT at publish; CURRENT until 2026-11-03T20:42:31.109860Z, STALE after 2026-11-03T20:52:31.109860Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-03T15:18:17.770287Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.06s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-03T22:30:00Z | Chapecoense vs Mirassol (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-04T00:30:00Z | Internacional vs Coritiba (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-04T22:30:00Z | Athletico Paranaense vs Vasco da Gama (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-04T22:30:00Z | Flamengo vs Grêmio (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-05T00:30:00Z | Botafogo vs Atlético Mineiro (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-05T00:30:00Z | São Paulo vs Corinthians (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |

## Candidates on CURRENT prices (13; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Botafogo vs Atlético Mineiro | Result: home | no | 0.4600 | 0.614 [0.456, 0.749] | +0.137 | +0.038 | 0.49 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | home wins by more than 1.5 | no | 0.7100 | 0.820 [0.705, 0.913] | +0.096 | +0.026 | 0.73 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Total goals over 3.5 | no | 0.6600 | 0.772 [0.639, 0.884] | +0.096 | +0.023 | 0.68 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Total goals over 2.5 | no | 0.4400 | 0.572 [0.415, 0.719] | +0.115 | +0.019 | 0.45 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Total goals over 4.5 | no | 0.8300 | 0.894 [0.809, 0.960] | +0.054 | +0.012 | 0.84 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | home wins by more than 2.5 | no | 0.8800 | 0.932 [0.867, 0.979] | +0.045 | +0.012 | 0.89 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Total goals over 1.5 | no | 0.2100 | 0.314 [0.188, 0.443] | +0.092 | +0.009 | 0.21 | - |  | RESEARCH_CANDIDATE |
| Flamengo vs Grêmio | Result: home | no | 0.1600 | 0.265 [0.134, 0.402] | +0.095 | +0.005 | 0.16 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | btts | no | 0.4300 | 0.526 [0.405, 0.639] | +0.079 | +0.004 | 0.43 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Total goals over 0.5 | no | 0.0600 | 0.105 [0.052, 0.167] | +0.041 | +0.004 | 0.06 | - |  | RESEARCH_CANDIDATE |
| Flamengo vs Grêmio | Result: draw | yes | 0.1100 | 0.171 [0.097, 0.248] | +0.054 | +0.003 | 0.11 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Result: draw | yes | 0.2350 | 0.284 [0.232, 0.336] | +0.036 | +0.002 | 0.23 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Result: away | yes | 0.2300 | 0.330 [0.201, 0.462] | +0.088 | +0.002 | 0.23 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 154
action_NO_QUOTE: 181
action_RESEARCH_CANDIDATE: 13
contract_sides: 348
fixtures: 6
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
