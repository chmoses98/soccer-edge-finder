# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261026T075022Z-b60d46` · generated 2026-10-26T07:50:22.406642Z · trigger `kalshi_capture:slate_refresh+new_fixtures` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-10-26T07:47:29.695929Z (CURRENT at publish; CURRENT until 2026-10-26T08:07:29.695929Z, STALE after 2026-10-26T08:17:29.695929Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-26T07:50:21.074469Z · simulations this update: 3 · Odds API calls this update: 0 (credits 0) · reprice 0.10s

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

## Candidates on CURRENT prices (4; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Flamengo vs Atlético Mineiro | Result: draw | yes | 0.1650 | 0.228 [0.149, 0.304] | +0.053 | +0.005 | 0.16 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | Result: home | no | 0.2550 | 0.370 [0.220, 0.519] | +0.102 | +0.002 | 0.25 | - |  | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | home wins by more than 1.5 | no | 0.4900 | 0.612 [0.435, 0.774] | +0.105 | +0.002 | 0.49 | - | * | RESEARCH_CANDIDATE |
| AS Roma vs Cagliari | Result: home | no | 0.2800 | 0.400 [0.228, 0.583] | +0.106 | +0.001 | 0.28 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 69
action_NO_QUOTE: 73
action_RESEARCH_CANDIDATE: 4
contract_sides: 146
fixtures: 7
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
