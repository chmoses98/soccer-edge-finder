# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261018T183301Z-d27466` · generated 2026-10-18T18:33:01.537818Z · trigger `kickoff_chain:T-30/T-15` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-10-18T18:30:00.030040Z (CURRENT at publish; CURRENT until 2026-10-18T18:50:00.030040Z, STALE after 2026-10-18T19:00:00.030040Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-18T18:32:59.749582Z · simulations this update: 2 · Odds API calls this update: 2 (credits 6) · reprice 0.17s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-18T18:45:00Z | Lyon vs Nice (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | CURRENT close | CURRENT | 3 | 0 |
| 2026-10-18T18:45:00Z | Juventus vs Lazio (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | CURRENT close | CURRENT | 3 | 0 |
| 2026-10-18T19:00:00Z | Fluminense vs Santos (bra.serie_a) | VALID (CURRENT) | confirmed (CURRENT) | AGING entry | CURRENT | 14 | 0 |
| 2026-10-18T19:00:00Z | Grêmio vs Cruzeiro (bra.serie_a) | VALID (CURRENT) | confirmed (CURRENT) | AGING entry | CURRENT | 14 | 0 |
| 2026-10-18T19:00:00Z | Real Madrid vs Sevilla (esp.la_liga) | VALID (CURRENT) | unknown (UNAVAILABLE) | AGING entry | CURRENT | 3 | 0 |
| 2026-10-18T21:00:00Z | Estudiantes de La Plata vs San Lorenzo (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-18T21:00:00Z | FC Cincinnati vs Columbus Crew (usa.mls) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-18T21:30:00Z | Bahia vs Flamengo (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-18T22:30:00Z | Remo vs Red Bull Bragantino (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-18T23:15:00Z | Belgrano vs River Plate (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-19T01:00:00Z | Monterrey vs Pachuca (mex.liga_mx) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-19T16:30:00Z | Monza vs Cagliari (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-19T18:45:00Z | Parma vs Torino (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-19T19:00:00Z | Tottenham Hotspur vs Coventry City (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-19T19:00:00Z | Getafe vs Rayo Vallecano (esp.la_liga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-19T22:00:00Z | Newell's Old Boys vs Central Córdoba (arg.primera) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-19T23:00:00Z | Corinthians vs Vitória (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-20T00:15:00Z | Deportivo Riestra vs Unión (arg.primera) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |

## Candidates on CURRENT prices (21; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Monterrey vs Pachuca | home team total over 1.5 | no | 0.4000 | 0.584 [0.399, 0.755] | +0.167 | +0.054 | 0.45 | - | * | RESEARCH_CANDIDATE |
| Monterrey vs Pachuca | home team total over 2.5 | no | 0.6800 | 0.814 [0.670, 0.929] | +0.119 | +0.043 | 0.72 | - |  | RESEARCH_CANDIDATE |
| Lyon vs Nice | Result: away | no | 0.7500 | 0.857 [0.756, 0.946] | +0.094 | +0.036 | 0.78 | 0.744 | * | RESEARCH_CANDIDATE |
| Monterrey vs Pachuca | home wins by more than 1.5 | no | 0.6500 | 0.779 [0.647, 0.896] | +0.113 | +0.034 | 0.68 | - | * | RESEARCH_CANDIDATE |
| Lyon vs Nice | Result: home | yes | 0.4900 | 0.645 [0.481, 0.811] | +0.138 | +0.029 | 0.51 | 0.493 |  | RESEARCH_CANDIDATE |
| Monterrey vs Pachuca | home team total over 0.5 | no | 0.1400 | 0.255 [0.132, 0.388] | +0.106 | +0.021 | 0.16 | - |  | RESEARCH_CANDIDATE |
| Monterrey vs Pachuca | Result: home | no | 0.4200 | 0.564 [0.404, 0.723] | +0.127 | +0.020 | 0.43 | - | * | RESEARCH_CANDIDATE |
| FC Cincinnati vs Columbus Crew | away team total over 1.5 | no | 0.4700 | 0.601 [0.447, 0.747] | +0.114 | +0.016 | 0.48 | - | * | RESEARCH_CANDIDATE |
| Monterrey vs Pachuca | home wins by more than 2.5 | no | 0.8400 | 0.908 [0.828, 0.971] | +0.058 | +0.015 | 0.85 | - |  | RESEARCH_CANDIDATE |
| Monterrey vs Pachuca | First-half result: home | no | 0.5700 | 0.674 [0.548, 0.782] | +0.087 | +0.012 | 0.58 | - | * | RESEARCH_CANDIDATE |
| FC Cincinnati vs Columbus Crew | Result: home | yes | 0.4100 | 0.548 [0.374, 0.714] | +0.121 | +0.012 | 0.42 | - | * | RESEARCH_CANDIDATE |
| Bahia vs Flamengo | btts | no | 0.4000 | 0.508 [0.380, 0.636] | +0.091 | +0.010 | 0.4 | - | * | RESEARCH_CANDIDATE |
| FC Cincinnati vs Columbus Crew | away team total over 0.5 | no | 0.1700 | 0.264 [0.157, 0.379] | +0.084 | +0.009 | 0.17 | - |  | RESEARCH_CANDIDATE |
| FC Cincinnati vs Columbus Crew | away wins by more than 1.5 | no | 0.8300 | 0.887 [0.799, 0.957] | +0.048 | +0.006 | 0.83 | - | * | RESEARCH_CANDIDATE |
| FC Cincinnati vs Columbus Crew | away wins by more than 2.5 | no | 0.9300 | 0.957 [0.913, 0.989] | +0.023 | +0.005 | 0.93 | - |  | RESEARCH_CANDIDATE |
| Monterrey vs Pachuca | Total goals over 3.5 | no | 0.6300 | 0.737 [0.582, 0.868] | +0.090 | +0.004 | 0.63 | - | * | RESEARCH_CANDIDATE |
| Remo vs Red Bull Bragantino | btts | no | 0.4100 | 0.513 [0.387, 0.636] | +0.086 | +0.003 | 0.41 | - | * | RESEARCH_CANDIDATE |
| FC Cincinnati vs Columbus Crew | away team total over 2.5 | no | 0.7500 | 0.830 [0.717, 0.925] | +0.067 | +0.003 | 0.75 | - |  | RESEARCH_CANDIDATE |
| Remo vs Red Bull Bragantino | away wins by more than 1.5 | no | 0.7900 | 0.857 [0.757, 0.936] | +0.056 | +0.002 | 0.79 | - | * | RESEARCH_CANDIDATE |
| Remo vs Red Bull Bragantino | away wins by more than 2.5 | no | 0.9200 | 0.950 [0.901, 0.985] | +0.025 | +0.002 | 0.92 | - |  | RESEARCH_CANDIDATE |
| Monterrey vs Pachuca | Total goals over 0.5 | no | 0.0500 | 0.092 [0.040, 0.151] | +0.039 | +0.001 | 0.05 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 423
action_NO_QUOTE: 204
action_RESEARCH_CANDIDATE: 21
contract_sides: 648
fixtures: 18
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 1

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
