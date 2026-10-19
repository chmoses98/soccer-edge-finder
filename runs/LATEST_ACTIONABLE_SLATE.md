# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261019T124620Z-83102a` · generated 2026-10-19T12:46:20.815223Z · trigger `kalshi_capture:slate_refresh` · mode `reprice_only`

**Kalshi prices observed 2026-10-19T12:43:36.540966Z (CURRENT at publish; CURRENT until 2026-10-19T13:03:36.540966Z, STALE after 2026-10-19T13:13:36.540966Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-19T10:15:59.844663Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.26s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-19T16:30:00Z | Monza vs Cagliari (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-19T18:45:00Z | Parma vs Torino (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-19T19:00:00Z | Tottenham Hotspur vs Coventry City (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-19T19:00:00Z | Getafe vs Rayo Vallecano (esp.la_liga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-19T22:00:00Z | Newell's Old Boys vs Central Córdoba (arg.primera) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-19T23:00:00Z | Corinthians vs Vitória (bra.serie_a) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-20T00:15:00Z | Deportivo Riestra vs Unión (arg.primera) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-21T00:07:00Z | Guadalajara vs Necaxa (mex.liga_mx) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-21T01:00:00Z | FC Juárez vs Atlante (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T01:00:00Z | Atlético San Luis vs Querétaro (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T03:00:00Z | Tigres UANL vs León (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (5; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Corinthians vs Vitória | Result: away | yes | 0.1450 | 0.247 [0.138, 0.364] | +0.093 | +0.015 | 0.15 | - | * | RESEARCH_CANDIDATE |
| Corinthians vs Vitória | away wins by more than 1.5 | yes | 0.0400 | 0.093 [0.037, 0.160] | +0.050 | +0.010 | 0.04 | - | * | RESEARCH_CANDIDATE |
| Tigres UANL vs León | away team total over 0.5 | no | 0.3300 | 0.431 [0.311, 0.551] | +0.085 | +0.006 | 0.33 | - | * | RESEARCH_CANDIDATE |
| Corinthians vs Vitória | Result: home | no | 0.4000 | 0.519 [0.363, 0.673] | +0.103 | +0.005 | 0.4 | - |  | RESEARCH_CANDIDATE |
| Atlético San Luis vs Querétaro | btts | no | 0.4300 | 0.538 [0.408, 0.665] | +0.091 | +0.004 | 0.43 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 435
action_NO_QUOTE: 144
action_RESEARCH_CANDIDATE: 5
contract_sides: 584
fixtures: 11
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
