# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261019T174418Z-65fc70` · generated 2026-10-19T17:44:18.601200Z · trigger `kickoff_chain:T-60` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-10-19T17:41:23.420511Z (CURRENT at publish; CURRENT until 2026-10-19T18:01:23.420511Z, STALE after 2026-10-19T18:11:23.420511Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-19T17:44:18.046806Z · simulations this update: 1 · Odds API calls this update: 1 (credits 3) · reprice 0.36s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-19T18:45:00Z | Parma vs Torino (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | CURRENT entry | CURRENT | 3 | 0 |
| 2026-10-19T19:00:00Z | Tottenham Hotspur vs Coventry City (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-19T19:00:00Z | Getafe vs Rayo Vallecano (esp.la_liga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-19T22:00:00Z | Newell's Old Boys vs Central Córdoba (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-19T23:00:00Z | Corinthians vs Vitória (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-20T00:15:00Z | Deportivo Riestra vs Unión (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-21T00:07:00Z | Guadalajara vs Necaxa (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T01:00:00Z | FC Juárez vs Atlante (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T01:00:00Z | Atlético San Luis vs Querétaro (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T03:00:00Z | Tigres UANL vs León (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (4; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Corinthians vs Vitória | Result: home | no | 0.3800 | 0.526 [0.365, 0.674] | +0.129 | +0.026 | 0.4 | - | * | RESEARCH_CANDIDATE |
| Corinthians vs Vitória | Result: away | yes | 0.1450 | 0.248 [0.136, 0.368] | +0.094 | +0.017 | 0.16 | - |  | RESEARCH_CANDIDATE |
| Corinthians vs Vitória | away wins by more than 1.5 | yes | 0.0400 | 0.092 [0.039, 0.157] | +0.049 | +0.008 | 0.04 | - | * | RESEARCH_CANDIDATE |
| Corinthians vs Vitória | home wins by more than 1.5 | no | 0.6500 | 0.757 [0.615, 0.877] | +0.091 | +0.007 | 0.65 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 529
action_NO_QUOTE: 215
action_RESEARCH_CANDIDATE: 4
contract_sides: 748
fixtures: 10
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
