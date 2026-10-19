# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261019T221243Z-a1db6c` · generated 2026-10-19T22:12:43.124051Z · trigger `kickoff_chain:T-120` · mode `reprice_only`

**Kalshi prices observed 2026-10-19T22:10:02.144344Z (CURRENT at publish; CURRENT until 2026-10-19T22:30:02.144344Z, STALE after 2026-10-19T22:40:02.144344Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-19T21:57:47.685838Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.47s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-19T23:00:00Z | Corinthians vs Vitória (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | AGING entry | CURRENT | 14 | 0 |
| 2026-10-20T00:15:00Z | Deportivo Riestra vs Unión (arg.primera) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-21T00:07:00Z | Guadalajara vs Necaxa (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T01:00:00Z | FC Juárez vs Atlante (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T01:00:00Z | Atlético San Luis vs Querétaro (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T03:00:00Z | Tigres UANL vs León (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (3; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Corinthians vs Vitória | Result: away | yes | 0.1500 | 0.248 [0.136, 0.368] | +0.089 | +0.012 | 0.16 | 0.127 | * | RESEARCH_CANDIDATE |
| Corinthians vs Vitória | Result: home | no | 0.3950 | 0.526 [0.365, 0.674] | +0.114 | +0.011 | 0.4 | 0.354 |  | RESEARCH_CANDIDATE |
| Corinthians vs Vitória | away wins by more than 1.5 | yes | 0.0400 | 0.092 [0.039, 0.157] | +0.049 | +0.008 | 0.04 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 510
action_NO_QUOTE: 159
action_RESEARCH_CANDIDATE: 3
contract_sides: 672
fixtures: 6
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 1

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
