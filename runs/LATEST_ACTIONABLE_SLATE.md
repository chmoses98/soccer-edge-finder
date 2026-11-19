# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261119T023917Z-533f2b` · generated 2026-11-19T02:39:17.668633Z · trigger `run_soccer` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-11-19T02:22:26.952675Z (CURRENT at publish; CURRENT until 2026-11-19T02:42:26.952675Z, STALE after 2026-11-19T02:52:26.952675Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-19T02:38:03.162335Z · simulations this update: 9 · Odds API calls this update: 0 (credits 0) · reprice 0.37s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-19T22:30:00Z | Vasco da Gama vs Internacional (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-19T22:30:00Z | Vitória vs Red Bull Bragantino (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-20T00:30:00Z | São Paulo vs Fluminense (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-20T00:30:00Z | Orlando City vs FC Cincinnati (usa.mls) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 81 | 1 |
| 2026-11-20T03:00:00Z | Seattle Sounders vs Real Salt Lake (usa.mls) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 81 | 1 |
| 2026-11-20T19:30:00Z | Bayern Munich vs 1. FC Köln (ger.bundesliga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 79 | 1 |
| 2026-11-20T19:45:00Z | Troyes vs Le Havre (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 79 | 1 |
| 2026-11-20T23:00:00Z | Vélez Sarsfield vs Belgrano (arg.primera) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 5 | 0 |
| 2026-11-21T01:00:00Z | Puebla vs Atlético San Luis (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 79 | 1 |

## Candidates on CURRENT prices (53; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Orlando City vs FC Cincinnati | match_winner_2way | no | 0.5000 | 0.790 [0.658, 0.912] | +0.273 | +0.193 | 0.69 | - | * | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | Result: home | yes | 0.4000 | 0.611 [0.454, 0.761] | +0.195 | +0.091 | 0.49 | - | * | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | btts | no | 0.3700 | 0.539 [0.425, 0.649] | +0.153 | +0.079 | 0.44 | - | * | RESEARCH_CANDIDATE |
| Puebla vs Atlético San Luis | btts | no | 0.4100 | 0.578 [0.453, 0.689] | +0.151 | +0.077 | 0.48 | - | * | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | Result: away | no | 0.6300 | 0.791 [0.675, 0.896] | +0.144 | +0.070 | 0.7 | - |  | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | Total goals over 3.5 | no | 0.6000 | 0.761 [0.627, 0.872] | +0.144 | +0.070 | 0.67 | - | * | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | Total goals over 2.5 | no | 0.3800 | 0.558 [0.403, 0.699] | +0.162 | +0.067 | 0.44 | - |  | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | home wins by more than 1.5 | yes | 0.2200 | 0.413 [0.251, 0.577] | +0.181 | +0.066 | 0.28 | - | * | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | away team total over 1.5 | no | 0.6200 | 0.757 [0.645, 0.856] | +0.121 | +0.056 | 0.67 | - | * | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | match_winner_2way | no | 0.6200 | 0.763 [0.648, 0.872] | +0.126 | +0.054 | 0.67 | - | * | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | away team total over 0.5 | no | 0.2600 | 0.400 [0.287, 0.514] | +0.127 | +0.053 | 0.31 | - |  | RESEARCH_CANDIDATE |
| Puebla vs Atlético San Luis | Total goals over 2.5 | no | 0.4500 | 0.618 [0.462, 0.759] | +0.151 | +0.049 | 0.49 | - | * | RESEARCH_CANDIDATE |
| Puebla vs Atlético San Luis | Total goals over 3.5 | no | 0.6700 | 0.807 [0.685, 0.908] | +0.122 | +0.048 | 0.71 | - |  | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | away wins by more than 1.5 | no | 0.8100 | 0.907 [0.838, 0.964] | +0.086 | +0.046 | 0.85 | - |  | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | Total goals over 1.5 | no | 0.1700 | 0.306 [0.186, 0.430] | +0.126 | +0.046 | 0.21 | - |  | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | away team total over 1.5 | no | 0.4400 | 0.587 [0.440, 0.727] | +0.130 | +0.044 | 0.48 | - | * | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | First-half result: away | no | 0.6800 | 0.793 [0.698, 0.882] | +0.098 | +0.043 | 0.72 | - | * | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | Total goals over 4.5 | no | 0.7900 | 0.888 [0.800, 0.955] | +0.087 | +0.042 | 0.83 | - |  | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | home wins by more than 2.5 | yes | 0.1000 | 0.244 [0.114, 0.387] | +0.138 | +0.040 | 0.13 | - |  | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | away team total over 2.5 | no | 0.7100 | 0.821 [0.709, 0.915] | +0.097 | +0.040 | 0.75 | - |  | RESEARCH_CANDIDATE |
| Puebla vs Atlético San Luis | Total goals over 4.5 | no | 0.8300 | 0.915 [0.843, 0.971] | +0.076 | +0.036 | 0.86 | - |  | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | First-half total goals over 1.5 | no | 0.5900 | 0.708 [0.588, 0.812] | +0.101 | +0.033 | 0.62 | - | * | RESEARCH_CANDIDATE |
| Puebla vs Atlético San Luis | Total goals over 1.5 | no | 0.2200 | 0.359 [0.223, 0.495] | +0.127 | +0.033 | 0.25 | - |  | RESEARCH_CANDIDATE |
| Puebla vs Atlético San Luis | away team total over 1.5 | no | 0.6400 | 0.761 [0.636, 0.866] | +0.104 | +0.032 | 0.67 | - | * | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | First-half result: home | yes | 0.3400 | 0.472 [0.338, 0.612] | +0.116 | +0.031 | 0.37 | - |  | RESEARCH_CANDIDATE |
| Puebla vs Atlético San Luis | away team total over 0.5 | no | 0.2800 | 0.406 [0.279, 0.529] | +0.112 | +0.029 | 0.3 | - |  | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | away team total over 2.5 | no | 0.8600 | 0.926 [0.869, 0.970] | +0.057 | +0.028 | 0.88 | - |  | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | First-half exact score 0-0 (home-away) | yes | 0.2400 | 0.345 [0.238, 0.452] | +0.093 | +0.027 | 0.26 | - | * | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | First-half total goals over 0.5 | no | 0.2400 | 0.345 [0.238, 0.452] | +0.093 | +0.027 | 0.26 | - |  | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | Total goals over 5.5 | no | 0.9000 | 0.954 [0.907, 0.986] | +0.047 | +0.026 | 0.92 | - |  | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | away wins by more than 2.5 | no | 0.9200 | 0.965 [0.932, 0.990] | +0.040 | +0.024 | 0.94 | - |  | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | First team to score: home | yes | 0.5100 | 0.623 [0.508, 0.742] | +0.095 | +0.023 | 0.53 | - | * | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | away team total over 0.5 | no | 0.1600 | 0.252 [0.153, 0.359] | +0.083 | +0.018 | 0.17 | - |  | RESEARCH_CANDIDATE |
| Puebla vs Atlético San Luis | First-half exact score 0-0 (home-away) | yes | 0.2800 | 0.381 [0.268, 0.502] | +0.087 | +0.016 | 0.29 | - | * | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | First half: both teams to score | no | 0.7700 | 0.840 [0.759, 0.911] | +0.057 | +0.016 | 0.78 | - | * | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | Second-half result: away | no | 0.6900 | 0.786 [0.678, 0.882] | +0.081 | +0.015 | 0.7 | - | * | RESEARCH_CANDIDATE |
| Seattle Sounders vs Real Salt Lake | Exact score 1-0 (home-away) | yes | 0.0800 | 0.129 [0.083, 0.173] | +0.044 | +0.015 | 0.09 | - | * | RESEARCH_CANDIDATE |
| Vitória vs Red Bull Bragantino | btts | no | 0.4200 | 0.532 [0.404, 0.650] | +0.095 | +0.014 | 0.43 | - | * | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | First half: away wins by more than 1.5 | no | 0.9000 | 0.945 [0.899, 0.981] | +0.039 | +0.014 | 0.91 | - | * | RESEARCH_CANDIDATE |
| Orlando City vs FC Cincinnati | Second-half result: home | yes | 0.3900 | 0.517 [0.378, 0.662] | +0.110 | +0.013 | 0.4 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 806
action_NO_QUOTE: 123
action_RESEARCH_CANDIDATE: 53
contract_sides: 982
fixtures: 9
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
