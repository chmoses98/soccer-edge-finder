# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261012T010108Z-c90c9e` · generated 2026-10-12T01:01:08.228287Z · trigger `kickoff_chain:T-15` · mode `reprice_only`

**Kalshi prices observed 2026-10-12T00:58:34.207783Z (CURRENT at publish; CURRENT until 2026-10-12T01:18:34.207783Z, STALE after 2026-10-12T01:28:34.207783Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-12T00:16:04.203758Z · simulations this update: 0 · Odds API calls this update: 1 (credits 3) · reprice 0.11s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-12T01:15:00Z | Pumas UNAM vs Cruz Azul (mex.liga_mx) | VALID (CURRENT) | unconfirmed (CURRENT) | CURRENT close | CURRENT | 79 | 1 |
| 2026-10-12T16:30:00Z | Atalanta vs Venezia (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-12T18:45:00Z | Torino vs Udinese (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-12T19:00:00Z | Lanús vs Vélez Sarsfield (arg.primera) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-12T19:00:00Z | Coritiba vs Botafogo (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-12T19:00:00Z | Coventry City vs Newcastle United (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-12T19:00:00Z | Levante vs Sevilla (esp.la_liga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-12T22:30:00Z | Chapecoense vs Athletico Paranaense (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-13T00:00:00Z | Red Bull Bragantino vs Cruzeiro (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |

## Candidates on CURRENT prices (11; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Pumas UNAM vs Cruz Azul | First team to score: home | yes | 0.4000 | 0.526 [0.388, 0.662] | +0.109 | +0.030 | 0.42 | - | * | RESEARCH_CANDIDATE |
| Pumas UNAM vs Cruz Azul | First team to score: away | no | 0.4800 | 0.590 [0.458, 0.712] | +0.093 | +0.013 | 0.49 | - |  | RESEARCH_CANDIDATE |
| Pumas UNAM vs Cruz Azul | home wins by more than 1.5 | yes | 0.1400 | 0.250 [0.125, 0.399] | +0.102 | +0.006 | 0.14 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | btts | no | 0.4100 | 0.509 [0.391, 0.631] | +0.082 | +0.006 | 0.41 | - | * | RESEARCH_CANDIDATE |
| Pumas UNAM vs Cruz Azul | First-half result: away | no | 0.6700 | 0.752 [0.638, 0.852] | +0.067 | +0.005 | 0.67 | - | * | RESEARCH_CANDIDATE |
| Torino vs Udinese | Result: draw | no | 0.7000 | 0.753 [0.696, 0.805] | +0.038 | +0.004 | 0.7 | - | * | RESEARCH_CANDIDATE |
| Pumas UNAM vs Cruz Azul | Result: away | no | 0.5900 | 0.700 [0.559, 0.827] | +0.094 | +0.003 | 0.59 | 0.524 | * | RESEARCH_CANDIDATE |
| Pumas UNAM vs Cruz Azul | away wins by more than 2.5 | no | 0.9200 | 0.950 [0.905, 0.985] | +0.025 | +0.002 | 0.92 | - |  | RESEARCH_CANDIDATE |
| Pumas UNAM vs Cruz Azul | Result: home | yes | 0.3300 | 0.457 [0.300, 0.621] | +0.111 | +0.001 | 0.33 | 0.260 |  | RESEARCH_CANDIDATE |
| Pumas UNAM vs Cruz Azul | away wins by more than 1.5 | no | 0.8000 | 0.864 [0.772, 0.941] | +0.053 | +0.000 | 0.8 | - |  | RESEARCH_CANDIDATE |
| Pumas UNAM vs Cruz Azul | home wins by more than 2.5 | yes | 0.0500 | 0.115 [0.039, 0.213] | +0.062 | +0.000 | 0.05 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 236
action_NO_QUOTE: 137
action_RESEARCH_CANDIDATE: 11
contract_sides: 384
fixtures: 9
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 1

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
