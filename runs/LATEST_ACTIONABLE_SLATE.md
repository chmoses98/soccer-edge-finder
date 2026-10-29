# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261029T131428Z-4c660d` · generated 2026-10-29T13:14:28.052033Z · trigger `kalshi_capture:slate_refresh+new_fixtures` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-10-29T13:11:40.747708Z (CURRENT at publish; CURRENT until 2026-10-29T13:31:40.747708Z, STALE after 2026-10-29T13:41:40.747708Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-29T12:44:22.000240Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.19s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-29T17:30:00Z | Frosinone vs Lecce (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-29T19:45:00Z | Fiorentina vs Atalanta (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-29T22:30:00Z | Atlético Mineiro vs Cruzeiro (bra.serie_a) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-29T23:00:00Z | Vasco da Gama vs Flamengo (bra.serie_a) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-30T00:30:00Z | Grêmio vs Athletico Paranaense (bra.serie_a) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-30T18:00:00Z | Le Havre vs Paris Saint-Germain (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-30T19:30:00Z | SV Elversberg vs Mainz 05 (ger.bundesliga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-30T20:05:00Z | Lille vs Lens (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-30T23:00:00Z | Corinthians vs Mirassol (bra.serie_a) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-31T01:00:00Z | FC Juárez vs Querétaro (mex.liga_mx) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-31T01:00:00Z | Atlético San Luis vs Atlas (mex.liga_mx) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-31T03:00:00Z | Puebla vs Pumas UNAM (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-31T12:30:00Z | Chelsea vs Manchester United (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |

## Candidates on CURRENT prices (11; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Le Havre vs Paris Saint-Germain | Result: away | no | 0.2000 | 0.544 [0.362, 0.715] | +0.333 | +0.214 | 0.4 | - | * | RESEARCH_CANDIDATE |
| Le Havre vs Paris Saint-Germain | Result: home | yes | 0.0800 | 0.287 [0.147, 0.444] | +0.202 | +0.097 | 0.17 | - |  | RESEARCH_CANDIDATE |
| Le Havre vs Paris Saint-Germain | Result: draw | yes | 0.1300 | 0.257 [0.196, 0.320] | +0.119 | +0.077 | 0.2 | - |  | RESEARCH_CANDIDATE |
| SV Elversberg vs Mainz 05 | Result: away | no | 0.5600 | 0.732 [0.522, 0.910] | +0.155 | +0.033 | 0.59 | - | * | RESEARCH_CANDIDATE |
| SV Elversberg vs Mainz 05 | Result: home | yes | 0.3100 | 0.518 [0.274, 0.770] | +0.193 | +0.025 | 0.33 | - |  | RESEARCH_CANDIDATE |
| Puebla vs Pumas UNAM | away team total over 0.5 | no | 0.2100 | 0.313 [0.198, 0.428] | +0.091 | +0.014 | 0.22 | - | * | RESEARCH_CANDIDATE |
| Atlético San Luis vs Atlas | Result: home | yes | 0.3600 | 0.489 [0.339, 0.656] | +0.113 | +0.011 | 0.37 | - | * | RESEARCH_CANDIDATE |
| Puebla vs Pumas UNAM | away team total over 1.5 | no | 0.5500 | 0.663 [0.518, 0.791] | +0.096 | +0.009 | 0.55 | - |  | RESEARCH_CANDIDATE |
| Corinthians vs Mirassol | Result: away | yes | 0.1950 | 0.290 [0.171, 0.416] | +0.084 | +0.006 | 0.2 | - | * | RESEARCH_CANDIDATE |
| Puebla vs Pumas UNAM | away team total over 2.5 | no | 0.8100 | 0.872 [0.778, 0.945] | +0.051 | +0.002 | 0.81 | - |  | RESEARCH_CANDIDATE |
| FC Juárez vs Querétaro | btts | no | 0.4400 | 0.533 [0.411, 0.651] | +0.076 | +0.001 | 0.44 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 383
action_NO_QUOTE: 114
action_RESEARCH_CANDIDATE: 11
contract_sides: 508
fixtures: 13
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
