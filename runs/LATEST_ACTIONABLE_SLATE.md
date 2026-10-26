# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261026T011305Z-693491` · generated 2026-10-26T01:13:05.157315Z · trigger `kalshi_capture` · mode `reprice_only`

**Kalshi prices observed 2026-10-26T01:10:01.654557Z (CURRENT at publish; CURRENT until 2026-10-26T01:30:01.654557Z, STALE after 2026-10-26T01:40:01.654557Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-26T00:30:41.830067Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.16s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-26T03:10:00Z | Tijuana vs Santos Laguna (mex.liga_mx) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 32 | 0 |
| 2026-10-26T22:00:00Z | Unión vs Estudiantes de La Plata (arg.primera) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-26T22:30:00Z | Coritiba vs Grêmio (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-26T23:00:00Z | Flamengo vs Atlético Mineiro (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-27T00:15:00Z | Instituto vs Deportivo Riestra (arg.primera) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-27T17:30:00Z | Sassuolo vs Lazio (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 32 | 0 |
| 2026-10-27T19:45:00Z | AS Roma vs Cagliari (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-27T19:45:00Z | Torino vs Como (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |

## Candidates on CURRENT prices (14; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Tijuana vs Santos Laguna | btts | no | 0.3900 | 0.534 [0.409, 0.653] | +0.128 | +0.048 | 0.43 | - | * | RESEARCH_CANDIDATE |
| Tijuana vs Santos Laguna | Total goals over 2.5 | no | 0.4200 | 0.567 [0.403, 0.723] | +0.130 | +0.025 | 0.44 | - | * | RESEARCH_CANDIDATE |
| Tijuana vs Santos Laguna | Total goals over 4.5 | no | 0.8100 | 0.891 [0.799, 0.961] | +0.070 | +0.022 | 0.83 | - |  | RESEARCH_CANDIDATE |
| Tijuana vs Santos Laguna | Total goals over 3.5 | no | 0.6500 | 0.767 [0.626, 0.887] | +0.101 | +0.020 | 0.66 | - |  | RESEARCH_CANDIDATE |
| Tijuana vs Santos Laguna | Total goals over 1.5 | no | 0.1900 | 0.311 [0.180, 0.447] | +0.110 | +0.019 | 0.2 | - |  | RESEARCH_CANDIDATE |
| Tijuana vs Santos Laguna | away team total over 0.5 | no | 0.2700 | 0.380 [0.257, 0.502] | +0.096 | +0.013 | 0.28 | - | * | RESEARCH_CANDIDATE |
| Tijuana vs Santos Laguna | away team total over 1.5 | no | 0.6300 | 0.735 [0.606, 0.848] | +0.089 | +0.011 | 0.64 | - |  | RESEARCH_CANDIDATE |
| Tijuana vs Santos Laguna | Total goals over 5.5 | no | 0.9200 | 0.954 [0.906, 0.989] | +0.029 | +0.007 | 0.92 | - |  | RESEARCH_CANDIDATE |
| Tijuana vs Santos Laguna | First half: both teams to score | no | 0.7700 | 0.834 [0.748, 0.912] | +0.052 | +0.006 | 0.77 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | Result: draw | yes | 0.1650 | 0.228 [0.149, 0.304] | +0.053 | +0.005 | 0.16 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | Result: home | no | 0.2550 | 0.370 [0.220, 0.519] | +0.102 | +0.002 | 0.25 | - |  | RESEARCH_CANDIDATE |
| Tijuana vs Santos Laguna | First-half total goals over 1.5 | no | 0.6200 | 0.706 [0.588, 0.822] | +0.070 | +0.002 | 0.62 | - | * | RESEARCH_CANDIDATE |
| AS Roma vs Cagliari | Result: home | no | 0.2800 | 0.399 [0.228, 0.582] | +0.105 | +0.001 | 0.28 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | Total goals over 3.5 | no | 0.6200 | 0.725 [0.561, 0.868] | +0.088 | +0.000 | 0.62 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 123
action_NO_QUOTE: 131
action_RESEARCH_CANDIDATE: 14
contract_sides: 268
fixtures: 8
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 4

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
