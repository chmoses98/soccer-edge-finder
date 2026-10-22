# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261022T030740Z-358eda` · generated 2026-10-22T03:07:40.124265Z · trigger `kickoff_chain:T-5` · mode `reprice_only`

**Kalshi prices observed 2026-10-22T03:05:00.029765Z (CURRENT at publish; CURRENT until 2026-10-22T03:25:00.029765Z, STALE after 2026-10-22T03:35:00.029765Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-22T02:08:04.702758Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.14s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-22T03:10:00Z | Pachuca vs Cruz Azul (mex.liga_mx) | VALID (CURRENT) | unconfirmed (CURRENT) | CURRENT close | CURRENT | 77 | 0 |
| 2026-10-22T03:10:00Z | Santos Laguna vs Pumas UNAM (mex.liga_mx) | VALID (CURRENT) | unconfirmed (CURRENT) | CURRENT close | CURRENT | 77 | 0 |
| 2026-10-23T18:30:00Z | VfB Stuttgart vs Borussia Mönchengladbach (ger.bundesliga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T18:45:00Z | Brest vs Nice (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T18:45:00Z | Torino vs Monza (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T19:00:00Z | Ipswich Town vs Nottingham Forest (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T23:00:00Z | Cruzeiro vs Remo (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 11 | 3 |
| 2026-10-24T01:00:00Z | Necaxa vs FC Juárez (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (14; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Pachuca vs Cruz Azul | Result: away | no | 0.5500 | 0.686 [0.531, 0.820] | +0.119 | +0.031 | 0.58 | 0.557 | * | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | away wins by more than 1.5 | no | 0.7600 | 0.855 [0.753, 0.937] | +0.082 | +0.026 | 0.78 | - | * | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | away team total over 1.5 | no | 0.4800 | 0.622 [0.464, 0.769] | +0.124 | +0.023 | 0.5 | - | * | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | away team total over 0.5 | no | 0.1700 | 0.280 [0.166, 0.403] | +0.100 | +0.019 | 0.18 | - |  | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | away team total over 2.5 | no | 0.7500 | 0.844 [0.732, 0.936] | +0.081 | +0.016 | 0.76 | - |  | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | away wins by more than 2.5 | no | 0.9000 | 0.945 [0.892, 0.983] | +0.039 | +0.015 | 0.91 | - |  | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | Result: home | yes | 0.3000 | 0.440 [0.277, 0.615] | +0.126 | +0.012 | 0.31 | 0.294 |  | RESEARCH_CANDIDATE |
| Santos Laguna vs Pumas UNAM | away team total over 0.5 | no | 0.2100 | 0.312 [0.189, 0.431] | +0.090 | +0.009 | 0.21 | - | * | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | Exact score 2-0 (home-away) | yes | 0.0400 | 0.068 [0.038, 0.097] | +0.025 | +0.004 | 0.04 | - | * | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | First half: away wins by more than 1.5 | no | 0.8900 | 0.932 [0.869, 0.981] | +0.035 | +0.003 | 0.89 | - | * | RESEARCH_CANDIDATE |
| Santos Laguna vs Pumas UNAM | away team total over 1.5 | no | 0.5500 | 0.661 [0.503, 0.794] | +0.093 | +0.002 | 0.55 | - |  | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | First-half result: away | no | 0.6500 | 0.738 [0.618, 0.843] | +0.072 | +0.002 | 0.65 | - | * | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | home wins by more than 1.5 | yes | 0.1300 | 0.238 [0.111, 0.393] | +0.100 | +0.002 | 0.13 | - |  | RESEARCH_CANDIDATE |
| Santos Laguna vs Pumas UNAM | Exact score 2-0 (home-away) | yes | 0.0500 | 0.076 [0.044, 0.109] | +0.023 | +0.001 | 0.05 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 427
action_NO_QUOTE: 67
action_RESEARCH_CANDIDATE: 14
contract_sides: 508
fixtures: 8
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
