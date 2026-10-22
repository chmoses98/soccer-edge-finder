# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261022T022255Z-bb0b24` · generated 2026-10-22T02:22:55.890997Z · trigger `kalshi_capture:slate_refresh` · mode `reprice_only`

**Kalshi prices observed 2026-10-22T02:20:17.177406Z (CURRENT at publish; CURRENT until 2026-10-22T02:40:17.177406Z, STALE after 2026-10-22T02:50:17.177406Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-22T02:08:04.702758Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.13s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-22T03:10:00Z | Pachuca vs Cruz Azul (mex.liga_mx) | VALID (CURRENT) | unconfirmed (CURRENT) | CURRENT entry | CURRENT | 77 | 0 |
| 2026-10-22T03:10:00Z | Santos Laguna vs Pumas UNAM (mex.liga_mx) | VALID (CURRENT) | unconfirmed (CURRENT) | CURRENT entry | CURRENT | 77 | 0 |
| 2026-10-23T18:30:00Z | VfB Stuttgart vs Borussia Mönchengladbach (ger.bundesliga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T18:45:00Z | Brest vs Nice (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T18:45:00Z | Torino vs Monza (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T19:00:00Z | Ipswich Town vs Nottingham Forest (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-23T23:00:00Z | Cruzeiro vs Remo (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 11 | 3 |
| 2026-10-24T01:00:00Z | Necaxa vs FC Juárez (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (9; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Pachuca vs Cruz Azul | Result: away | no | 0.5600 | 0.686 [0.531, 0.820] | +0.109 | +0.021 | 0.58 | 0.572 | * | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | away team total over 1.5 | no | 0.4900 | 0.622 [0.464, 0.769] | +0.114 | +0.012 | 0.5 | - | * | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | Result: home | yes | 0.3000 | 0.440 [0.277, 0.615] | +0.126 | +0.012 | 0.31 | 0.311 |  | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | away wins by more than 1.5 | no | 0.7800 | 0.855 [0.753, 0.937] | +0.063 | +0.007 | 0.78 | - | * | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | away team total over 2.5 | no | 0.7600 | 0.844 [0.732, 0.936] | +0.071 | +0.007 | 0.76 | - |  | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | away wins by more than 2.5 | no | 0.9100 | 0.945 [0.892, 0.983] | +0.030 | +0.005 | 0.91 | - |  | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | First half: away wins by more than 1.5 | no | 0.8900 | 0.932 [0.869, 0.981] | +0.035 | +0.003 | 0.89 | - | * | RESEARCH_CANDIDATE |
| Santos Laguna vs Pumas UNAM | away team total over 1.5 | no | 0.5500 | 0.661 [0.503, 0.794] | +0.093 | +0.002 | 0.55 | - | * | RESEARCH_CANDIDATE |
| Pachuca vs Cruz Azul | First-half result: away | no | 0.6500 | 0.738 [0.618, 0.843] | +0.072 | +0.002 | 0.65 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 429
action_NO_QUOTE: 70
action_RESEARCH_CANDIDATE: 9
contract_sides: 508
fixtures: 8
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
