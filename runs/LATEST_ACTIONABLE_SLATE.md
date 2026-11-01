# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261101T212823Z-f1bd20` · generated 2026-11-01T21:28:23.981778Z · trigger `kickoff_chain:T-120/T-15/T-5` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-11-01T21:23:58.649055Z (CURRENT at publish; CURRENT until 2026-11-01T21:43:58.649055Z, STALE after 2026-11-01T21:53:58.649055Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-01T21:28:05.279263Z · simulations this update: 2 · Odds API calls this update: 2 (credits 6) · reprice 0.72s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-01T21:30:00Z | Newell's Old Boys vs Unión (arg.primera) | INVALIDATED: lineup_changed:published:confirmed | confirmed (CURRENT) | CURRENT close | CURRENT | 14 | 0 |
| 2026-11-01T21:30:00Z | Atlanta United vs Toronto FC (usa.mls) | VALID (CURRENT) | confirmed (CURRENT) | CURRENT close | CURRENT | 77 | 0 |
| 2026-11-01T21:30:00Z | Nashville SC vs New York Red Bulls (usa.mls) | VALID (CURRENT) | confirmed (CURRENT) | CURRENT close | CURRENT | 77 | 0 |
| 2026-11-01T23:00:00Z | Santos Laguna vs Necaxa (mex.liga_mx) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-11-02T00:00:00Z | New England Revolution vs Inter Miami (usa.mls) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-11-02T01:10:00Z | Cruz Azul vs León (mex.liga_mx) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-11-02T01:30:00Z | Los Angeles FC vs Minnesota United (usa.mls) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-11-02T02:45:00Z | Portland Timbers vs Houston Dynamo (usa.mls) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-11-02T17:30:00Z | Sassuolo vs Fiorentina (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-11-02T19:45:00Z | Atalanta vs Parma (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-11-02T20:00:00Z | Newcastle United vs Everton (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 82 | 0 |
| 2026-11-02T22:00:00Z | Defensa y Justicia vs Independiente (arg.primera) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-02T22:00:00Z | Platense vs Central Córdoba (arg.primera) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-02T23:00:00Z | Red Bull Bragantino vs Santos (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |

## Candidates on CURRENT prices (96; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Nashville SC vs New York Red Bulls | btts | no | 0.3600 | 0.659 [0.551, 0.755] | +0.283 | +0.219 | 0.57 | - | * | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | away team total over 0.5 | no | 0.3200 | 0.610 [0.499, 0.715] | +0.275 | +0.206 | 0.52 | - | * | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | away team total over 1.5 | no | 0.6800 | 0.906 [0.846, 0.955] | +0.210 | +0.178 | 0.86 | - |  | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | Total goals over 3.5 | no | 0.4800 | 0.722 [0.567, 0.857] | +0.225 | +0.130 | 0.61 | 0.476 | * | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | Total goals over 2.5 | no | 0.2700 | 0.516 [0.348, 0.677] | +0.232 | +0.120 | 0.38 | - |  | RESEARCH_CANDIDATE |
| New England Revolution vs Inter Miami | away team total over 1.5 | no | 0.4000 | 0.618 [0.472, 0.750] | +0.201 | +0.112 | 0.51 | - | * | RESEARCH_CANDIDATE |
| New England Revolution vs Inter Miami | Result: away | no | 0.5400 | 0.734 [0.607, 0.842] | +0.176 | +0.102 | 0.64 | - | * | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | First half: both teams to score | no | 0.7300 | 0.880 [0.819, 0.941] | +0.136 | +0.096 | 0.83 | - | * | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | Total goals over 4.5 | no | 0.6900 | 0.861 [0.752, 0.947] | +0.156 | +0.095 | 0.78 | - |  | RESEARCH_CANDIDATE |
| New England Revolution vs Inter Miami | Result: home | yes | 0.3100 | 0.510 [0.358, 0.653] | +0.185 | +0.085 | 0.39 | - |  | RESEARCH_CANDIDATE |
| New England Revolution vs Inter Miami | away team total over 2.5 | no | 0.6900 | 0.843 [0.739, 0.927] | +0.138 | +0.082 | 0.77 | - |  | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | First-half total goals over 1.5 | no | 0.5000 | 0.674 [0.548, 0.792] | +0.157 | +0.081 | 0.58 | - | * | RESEARCH_CANDIDATE |
| New England Revolution vs Inter Miami | away wins by more than 1.5 | no | 0.7500 | 0.881 [0.799, 0.943] | +0.118 | +0.075 | 0.82 | - | * | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | away team total over 2.5 | no | 0.9000 | 0.983 [0.966, 0.995] | +0.077 | +0.069 | 0.97 | - |  | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | Total goals over 1.5 | no | 0.1100 | 0.272 [0.148, 0.402] | +0.156 | +0.068 | 0.17 | - |  | RESEARCH_CANDIDATE |
| Santos Laguna vs Necaxa | away team total over 1.5 | no | 0.6300 | 0.774 [0.653, 0.877] | +0.128 | +0.060 | 0.69 | - | * | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | First-half total goals over 0.5 | no | 0.1800 | 0.321 [0.208, 0.432] | +0.131 | +0.060 | 0.23 | - |  | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | Total goals over 5.5 | no | 0.8400 | 0.938 [0.876, 0.983] | +0.088 | +0.058 | 0.9 | - |  | RESEARCH_CANDIDATE |
| New England Revolution vs Inter Miami | away team total over 0.5 | no | 0.1400 | 0.275 [0.170, 0.383] | +0.126 | +0.056 | 0.19 | - |  | RESEARCH_CANDIDATE |
| Santos Laguna vs Necaxa | away team total over 0.5 | no | 0.2700 | 0.421 [0.293, 0.548] | +0.138 | +0.056 | 0.32 | - |  | RESEARCH_CANDIDATE |
| Portland Timbers vs Houston Dynamo | Total goals over 2.5 | no | 0.4000 | 0.572 [0.418, 0.712] | +0.156 | +0.055 | 0.45 | - | * | RESEARCH_CANDIDATE |
| New England Revolution vs Inter Miami | First-half result: away | no | 0.6300 | 0.762 [0.658, 0.852] | +0.115 | +0.054 | 0.68 | - | * | RESEARCH_CANDIDATE |
| Santos Laguna vs Necaxa | btts | no | 0.3700 | 0.516 [0.387, 0.643] | +0.129 | +0.054 | 0.42 | - | * | RESEARCH_CANDIDATE |
| New England Revolution vs Inter Miami | Second-half result: away | no | 0.6200 | 0.753 [0.638, 0.852] | +0.117 | +0.054 | 0.67 | - | * | RESEARCH_CANDIDATE |
| Los Angeles FC vs Minnesota United | btts | no | 0.3700 | 0.512 [0.399, 0.627] | +0.126 | +0.053 | 0.42 | - | * | RESEARCH_CANDIDATE |
| New England Revolution vs Inter Miami | away wins by more than 2.5 | no | 0.8800 | 0.956 [0.917, 0.985] | +0.069 | +0.051 | 0.93 | - |  | RESEARCH_CANDIDATE |
| Atlanta United vs Toronto FC | btts | no | 0.3200 | 0.466 [0.349, 0.589] | +0.131 | +0.051 | 0.36 | - | * | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | Exact score 2-0 (home-away) | yes | 0.0800 | 0.156 [0.122, 0.187] | +0.071 | +0.050 | 0.12 | - | * | RESEARCH_CANDIDATE |
| New England Revolution vs Inter Miami | home wins by more than 1.5 | yes | 0.1500 | 0.301 [0.170, 0.435] | +0.142 | +0.050 | 0.19 | - |  | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | Exact score 1-0 (home-away) | yes | 0.0600 | 0.152 [0.093, 0.211] | +0.088 | +0.049 | 0.1 | - |  | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | First-half exact score 0-0 (home-away) | yes | 0.1900 | 0.321 [0.208, 0.432] | +0.120 | +0.049 | 0.23 | - | * | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | First-half total goals over 2.5 | no | 0.7800 | 0.882 [0.799, 0.951] | +0.090 | +0.048 | 0.83 | - |  | RESEARCH_CANDIDATE |
| Portland Timbers vs Houston Dynamo | Total goals over 3.5 | no | 0.6300 | 0.772 [0.642, 0.880] | +0.126 | +0.048 | 0.67 | - |  | RESEARCH_CANDIDATE |
| Los Angeles FC vs Minnesota United | away team total over 0.5 | no | 0.2900 | 0.426 [0.306, 0.545] | +0.122 | +0.046 | 0.33 | - | * | RESEARCH_CANDIDATE |
| Atlanta United vs Toronto FC | Total goals over 3.5 | no | 0.5400 | 0.693 [0.548, 0.828] | +0.135 | +0.044 | 0.58 | - | * | RESEARCH_CANDIDATE |
| Atlanta United vs Toronto FC | Total goals over 2.5 | no | 0.3200 | 0.481 [0.330, 0.635] | +0.146 | +0.043 | 0.36 | - |  | RESEARCH_CANDIDATE |
| Portland Timbers vs Houston Dynamo | btts | no | 0.4100 | 0.541 [0.426, 0.649] | +0.114 | +0.042 | 0.45 | - | * | RESEARCH_CANDIDATE |
| Portland Timbers vs Houston Dynamo | home team total over 1.5 | no | 0.4200 | 0.585 [0.416, 0.740] | +0.148 | +0.041 | 0.46 | - | * | RESEARCH_CANDIDATE |
| Los Angeles FC vs Minnesota United | away team total over 1.5 | no | 0.6700 | 0.780 [0.669, 0.876] | +0.094 | +0.032 | 0.7 | - |  | RESEARCH_CANDIDATE |
| Nashville SC vs New York Red Bulls | First-half result: away | no | 0.8400 | 0.914 [0.859, 0.961] | +0.065 | +0.031 | 0.87 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 912
action_NO_QUOTE: 640
action_RESEARCH_CANDIDATE: 96
contract_sides: 1648
fixtures: 14
fixtures_model_invalidated: 1
fixtures_model_missing: 0
```

Removed (kicked off): 1

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
