# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261103T153440Z-96bfdd` · generated 2026-11-03T15:34:40.788653Z · trigger `kalshi_capture:slate_refresh` · mode `reprice_only`

**Kalshi prices observed 2026-11-03T15:32:04.085445Z (CURRENT at publish; CURRENT until 2026-11-03T15:52:04.085445Z, STALE after 2026-11-03T16:02:04.085445Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-03T15:18:17.770287Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.12s

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

## Candidates on CURRENT prices (4; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Botafogo vs Atlético Mineiro | Total goals over 3.5 | no | 0.6700 | 0.772 [0.639, 0.884] | +0.086 | +0.013 | 0.68 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Total goals over 2.5 | no | 0.4500 | 0.572 [0.415, 0.719] | +0.105 | +0.009 | 0.45 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | btts | no | 0.4300 | 0.526 [0.405, 0.639] | +0.079 | +0.004 | 0.43 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Total goals over 4.5 | no | 0.8400 | 0.894 [0.809, 0.960] | +0.045 | +0.003 | 0.84 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 163
action_NO_QUOTE: 181
action_RESEARCH_CANDIDATE: 4
contract_sides: 348
fixtures: 6
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
