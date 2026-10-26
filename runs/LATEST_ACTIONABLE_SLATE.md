# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261026T144028Z-37255d` · generated 2026-10-26T14:40:28.444960Z · trigger `kalshi_capture:slate_refresh` · mode `reprice_only`

**Kalshi prices observed 2026-10-26T14:37:49.277039Z (CURRENT at publish; CURRENT until 2026-10-26T14:57:49.277039Z, STALE after 2026-10-26T15:07:49.277039Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-26T11:55:04.811687Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.06s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-26T22:00:00Z | Unión vs Estudiantes de La Plata (arg.primera) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-26T22:30:00Z | Coritiba vs Grêmio (bra.serie_a) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-26T23:00:00Z | Flamengo vs Atlético Mineiro (bra.serie_a) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-27T00:15:00Z | Instituto vs Deportivo Riestra (arg.primera) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-27T17:30:00Z | Sassuolo vs Lazio (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-27T19:45:00Z | AS Roma vs Cagliari (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-27T19:45:00Z | Torino vs Como (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |

## Candidates on CURRENT prices (8; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Flamengo vs Atlético Mineiro | home wins by more than 1.5 | no | 0.4600 | 0.612 [0.435, 0.774] | +0.135 | +0.032 | 0.49 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | Result: home | no | 0.2300 | 0.370 [0.220, 0.519] | +0.128 | +0.028 | 0.25 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | home wins by more than 2.5 | no | 0.6900 | 0.801 [0.658, 0.920] | +0.096 | +0.022 | 0.71 | - |  | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | Result: draw | yes | 0.1550 | 0.228 [0.149, 0.304] | +0.063 | +0.015 | 0.16 | - |  | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | Total goals over 2.5 | no | 0.3900 | 0.519 [0.342, 0.694] | +0.113 | +0.006 | 0.39 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | Total goals over 4.5 | no | 0.7900 | 0.862 [0.746, 0.953] | +0.060 | +0.006 | 0.79 | - |  | RESEARCH_CANDIDATE |
| AS Roma vs Cagliari | Result: home | no | 0.2800 | 0.400 [0.228, 0.583] | +0.106 | +0.001 | 0.28 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | Total goals over 3.5 | no | 0.6200 | 0.725 [0.561, 0.868] | +0.088 | +0.000 | 0.62 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 65
action_NO_QUOTE: 73
action_RESEARCH_CANDIDATE: 8
contract_sides: 146
fixtures: 7
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
