# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261104T213012Z-e07e3f` · generated 2026-11-04T21:30:12.566789Z · trigger `kickoff_chain:T-60` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-11-04T21:27:18.372142Z (CURRENT at publish; CURRENT until 2026-11-04T21:47:18.372142Z, STALE after 2026-11-04T21:57:18.372142Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-04T21:30:08.489881Z · simulations this update: 2 · Odds API calls this update: 1 (credits 3) · reprice 0.18s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-04T22:30:00Z | Athletico Paranaense vs Vasco da Gama (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | CURRENT entry | CURRENT | 14 | 0 |
| 2026-11-04T22:30:00Z | Flamengo vs Grêmio (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | CURRENT entry | CURRENT | 14 | 0 |
| 2026-11-05T00:30:00Z | Botafogo vs Atlético Mineiro (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-05T00:30:00Z | São Paulo vs Corinthians (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-05T18:00:00Z | Aldosivi vs River Plate (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-05T22:15:00Z | Gimnasia La Plata vs Belgrano (arg.primera) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-05T22:30:00Z | Palmeiras vs Remo (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-06T00:30:00Z | Cruzeiro vs Bahia (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-06T19:30:00Z | Hamburger SV vs Borussia Mönchengladbach (ger.bundesliga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-06T19:45:00Z | Toulouse vs Strasbourg (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 59 | 0 |
| 2026-11-06T19:45:00Z | Venezia vs Udinese (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 71 | 0 |

## Candidates on CURRENT prices (39; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Botafogo vs Atlético Mineiro | Result: home | no | 0.3800 | 0.612 [0.462, 0.752] | +0.215 | +0.125 | 0.5 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | home wins by more than 1.5 | no | 0.6400 | 0.818 [0.704, 0.915] | +0.162 | +0.100 | 0.74 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Result: away | yes | 0.1600 | 0.329 [0.201, 0.466] | +0.160 | +0.072 | 0.22 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | home wins by more than 2.5 | no | 0.8300 | 0.931 [0.869, 0.979] | +0.091 | +0.063 | 0.89 | - |  | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Total goals over 3.5 | no | 0.6100 | 0.758 [0.612, 0.881] | +0.132 | +0.049 | 0.66 | - | * | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Total goals over 2.5 | no | 0.3900 | 0.558 [0.389, 0.714] | +0.152 | +0.046 | 0.43 | - |  | RESEARCH_CANDIDATE |
| Venezia vs Udinese | Result: away | yes | 0.3100 | 0.517 [0.295, 0.742] | +0.192 | +0.035 | 0.34 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Grêmio | home wins by more than 1.5 | no | 0.3200 | 0.481 [0.312, 0.647] | +0.146 | +0.033 | 0.35 | - | * | RESEARCH_CANDIDATE |
| Venezia vs Udinese | Result: home | no | 0.5700 | 0.739 [0.544, 0.909] | +0.152 | +0.033 | 0.6 | - |  | RESEARCH_CANDIDATE |
| Athletico Paranaense vs Vasco da Gama | home wins by more than 1.5 | yes | 0.2100 | 0.360 [0.203, 0.528] | +0.138 | +0.030 | 0.23 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Grêmio | Result: home | no | 0.1400 | 0.261 [0.143, 0.393] | +0.113 | +0.030 | 0.16 | 0.125 | * | RESEARCH_CANDIDATE |
| Athletico Paranaense vs Vasco da Gama | Result: home | yes | 0.4350 | 0.581 [0.420, 0.735] | +0.129 | +0.026 | 0.46 | 0.421 | * | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Total goals over 1.5 | no | 0.1800 | 0.305 [0.173, 0.440] | +0.115 | +0.026 | 0.2 | - |  | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Total goals over 4.5 | no | 0.8000 | 0.884 [0.788, 0.959] | +0.073 | +0.025 | 0.82 | - |  | RESEARCH_CANDIDATE |
| Flamengo vs Grêmio | home wins by more than 2.5 | no | 0.5400 | 0.689 [0.523, 0.838] | +0.132 | +0.025 | 0.56 | - |  | RESEARCH_CANDIDATE |
| Flamengo vs Grêmio | Total goals over 2.5 | no | 0.2600 | 0.412 [0.244, 0.588] | +0.139 | +0.025 | 0.28 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | away wins by more than 1.5 | yes | 0.0600 | 0.141 [0.067, 0.231] | +0.078 | +0.023 | 0.08 | - |  | RESEARCH_CANDIDATE |
| Flamengo vs Grêmio | Total goals over 3.5 | no | 0.4700 | 0.623 [0.441, 0.793] | +0.136 | +0.022 | 0.49 | - |  | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Result: draw | yes | 0.1350 | 0.214 [0.129, 0.294] | +0.071 | +0.019 | 0.15 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Grêmio | Result: draw | yes | 0.1000 | 0.169 [0.099, 0.243] | +0.063 | +0.016 | 0.11 | 0.083 |  | RESEARCH_CANDIDATE |
| Flamengo vs Grêmio | Total goals over 4.5 | no | 0.6700 | 0.787 [0.636, 0.912] | +0.101 | +0.016 | 0.68 | - |  | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Result: home | no | 0.2000 | 0.311 [0.177, 0.445] | +0.100 | +0.013 | 0.21 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Result: draw | yes | 0.2250 | 0.282 [0.232, 0.334] | +0.045 | +0.012 | 0.23 | - |  | RESEARCH_CANDIDATE |
| Athletico Paranaense vs Vasco da Gama | Result: away | no | 0.7100 | 0.802 [0.691, 0.902] | +0.077 | +0.012 | 0.72 | 0.702 |  | RESEARCH_CANDIDATE |
| Flamengo vs Grêmio | Total goals over 5.5 | no | 0.8200 | 0.892 [0.791, 0.968] | +0.062 | +0.010 | 0.83 | - |  | RESEARCH_CANDIDATE |
| Athletico Paranaense vs Vasco da Gama | home wins by more than 2.5 | yes | 0.0900 | 0.188 [0.076, 0.324] | +0.092 | +0.008 | 0.09 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Total goals over 3.5 | no | 0.6700 | 0.768 [0.636, 0.881] | +0.082 | +0.008 | 0.67 | - | * | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | btts | no | 0.5600 | 0.652 [0.542, 0.756] | +0.075 | +0.007 | 0.56 | - | * | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Total goals over 0.5 | no | 0.0500 | 0.100 [0.045, 0.162] | +0.047 | +0.006 | 0.05 | - |  | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | home wins by more than 2.5 | no | 0.6700 | 0.772 [0.616, 0.896] | +0.087 | +0.006 | 0.67 | - | * | RESEARCH_CANDIDATE |
| São Paulo vs Corinthians | Result: home | yes | 0.3650 | 0.486 [0.338, 0.638] | +0.104 | +0.006 | 0.37 | - | * | RESEARCH_CANDIDATE |
| São Paulo vs Corinthians | Result: away | no | 0.6750 | 0.762 [0.643, 0.866] | +0.072 | +0.005 | 0.68 | - |  | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | home wins by more than 1.5 | no | 0.4400 | 0.564 [0.385, 0.720] | +0.107 | +0.005 | 0.44 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Total goals over 2.5 | no | 0.4500 | 0.567 [0.412, 0.713] | +0.099 | +0.004 | 0.45 | - |  | RESEARCH_CANDIDATE |
| São Paulo vs Corinthians | home wins by more than 1.5 | yes | 0.1500 | 0.252 [0.131, 0.393] | +0.093 | +0.003 | 0.15 | - | * | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Total goals over 5.5 | no | 0.9200 | 0.951 [0.899, 0.988] | +0.025 | +0.003 | 0.92 | - |  | RESEARCH_CANDIDATE |
| Flamengo vs Grêmio | Total goals over 1.5 | no | 0.1100 | 0.197 [0.092, 0.319] | +0.080 | +0.003 | 0.11 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | Total goals over 0.5 | no | 0.0600 | 0.103 [0.051, 0.159] | +0.039 | +0.001 | 0.06 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Atlético Mineiro | away wins by more than 2.5 | yes | 0.0200 | 0.048 [0.017, 0.090] | +0.027 | +0.001 | 0.02 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 145
action_NO_QUOTE: 382
action_RESEARCH_CANDIDATE: 39
contract_sides: 566
fixtures: 11
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
