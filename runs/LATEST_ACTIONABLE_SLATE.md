# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261124T200354Z-65f518` · generated 2026-11-24T20:03:54.855731Z · trigger `kickoff_chain:T-60` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-11-24T20:00:21.683358Z (CURRENT at publish; CURRENT until 2026-11-24T20:20:21.683358Z, STALE after 2026-11-24T20:30:21.683358Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-24T20:03:51.981186Z · simulations this update: 1 · Odds API calls this update: 1 (credits 3) · reprice 0.21s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-24T21:00:00Z | Chapecoense vs Palmeiras (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | CURRENT entry | CURRENT | 14 | 0 |
| 2026-11-25T03:00:00Z | San Jose Earthquakes vs Houston Dynamo (usa.mls) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 79 | 1 |
| 2026-11-25T23:00:00Z | Atlético Mineiro vs Corinthians (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-26T01:00:00Z | Toluca vs Atlas (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 79 | 1 |
| 2026-11-26T03:10:00Z | Monterrey vs Club América (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 79 | 1 |

## Candidates on CURRENT prices (28; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| San Jose Earthquakes vs Houston Dynamo | Total goals over 2.5 | no | 0.4300 | 0.623 [0.480, 0.753] | +0.176 | +0.086 | 0.51 | - | * | RESEARCH_CANDIDATE |
| Chapecoense vs Palmeiras | Result: away | yes | 0.4550 | 0.646 [0.504, 0.781] | +0.173 | +0.084 | 0.53 | 0.455 | * | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | btts | no | 0.4200 | 0.589 [0.475, 0.693] | +0.152 | +0.083 | 0.5 | - | * | RESEARCH_CANDIDATE |
| Chapecoense vs Palmeiras | Result: home | no | 0.7150 | 0.859 [0.771, 0.934] | +0.130 | +0.077 | 0.79 | 0.713 |  | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | Total goals over 3.5 | no | 0.6600 | 0.812 [0.701, 0.904] | +0.136 | +0.073 | 0.73 | - |  | RESEARCH_CANDIDATE |
| Chapecoense vs Palmeiras | btts | no | 0.3800 | 0.550 [0.425, 0.670] | +0.153 | +0.072 | 0.45 | - | * | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | Total goals over 4.5 | no | 0.8200 | 0.919 [0.854, 0.969] | +0.089 | +0.055 | 0.87 | - |  | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | Total goals over 1.5 | no | 0.2100 | 0.364 [0.236, 0.488] | +0.142 | +0.054 | 0.26 | - |  | RESEARCH_CANDIDATE |
| Chapecoense vs Palmeiras | away wins by more than 1.5 | yes | 0.2400 | 0.405 [0.252, 0.560] | +0.152 | +0.051 | 0.28 | - | * | RESEARCH_CANDIDATE |
| Chapecoense vs Palmeiras | home wins by more than 1.5 | no | 0.8800 | 0.956 [0.917, 0.985] | +0.068 | +0.050 | 0.93 | - |  | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | First-half exact score 0-0 (home-away) | yes | 0.2700 | 0.388 [0.278, 0.492] | +0.104 | +0.033 | 0.3 | - | * | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | First-half total goals over 0.5 | no | 0.2700 | 0.388 [0.278, 0.492] | +0.104 | +0.033 | 0.3 | - | * | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | away team total over 0.5 | no | 0.3100 | 0.433 [0.316, 0.548] | +0.108 | +0.028 | 0.33 | - | * | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | away team total over 1.5 | no | 0.6800 | 0.785 [0.680, 0.878] | +0.090 | +0.026 | 0.7 | - |  | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | home team total over 2.5 | no | 0.7400 | 0.840 [0.725, 0.931] | +0.086 | +0.024 | 0.76 | - |  | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | First-half total goals over 1.5 | no | 0.6400 | 0.748 [0.638, 0.842] | +0.092 | +0.024 | 0.66 | - |  | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | Exact score 1-0 (home-away) | yes | 0.0900 | 0.147 [0.099, 0.193] | +0.051 | +0.021 | 0.11 | - | * | RESEARCH_CANDIDATE |
| Chapecoense vs Palmeiras | home wins by more than 2.5 | no | 0.9600 | 0.989 [0.976, 0.998] | +0.026 | +0.021 | 0.98 | - |  | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | Total goals over 5.5 | no | 0.9300 | 0.969 [0.938, 0.992] | +0.035 | +0.021 | 0.95 | - |  | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | home team total over 1.5 | no | 0.4800 | 0.617 [0.457, 0.760] | +0.119 | +0.020 | 0.5 | - |  | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | First half: both teams to score | no | 0.7900 | 0.864 [0.789, 0.931] | +0.063 | +0.018 | 0.8 | - | * | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | Exact score 0-0 (home-away) | yes | 0.0600 | 0.120 [0.062, 0.179] | +0.056 | +0.015 | 0.07 | - |  | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | Total goals over 0.5 | no | 0.0600 | 0.120 [0.062, 0.179] | +0.056 | +0.015 | 0.07 | - |  | RESEARCH_CANDIDATE |
| Chapecoense vs Palmeiras | away wins by more than 2.5 | yes | 0.1100 | 0.212 [0.099, 0.339] | +0.095 | +0.013 | 0.12 | - |  | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | First-half total goals over 2.5 | no | 0.8700 | 0.922 [0.859, 0.971] | +0.045 | +0.012 | 0.88 | - |  | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | home team total over 0.5 | no | 0.1800 | 0.276 [0.162, 0.393] | +0.086 | +0.007 | 0.18 | - |  | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | Exact score 0-1 (home-away) | yes | 0.0600 | 0.097 [0.055, 0.141] | +0.033 | +0.006 | 0.06 | - |  | RESEARCH_CANDIDATE |
| San Jose Earthquakes vs Houston Dynamo | away team total over 2.5 | no | 0.9000 | 0.939 [0.889, 0.977] | +0.032 | +0.006 | 0.9 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 425
action_NO_QUOTE: 107
action_RESEARCH_CANDIDATE: 28
contract_sides: 560
fixtures: 5
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
