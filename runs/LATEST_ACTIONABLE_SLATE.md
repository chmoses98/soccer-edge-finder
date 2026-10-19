# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261019T223259Z-b8b12c` · generated 2026-10-19T22:32:59.128146Z · trigger `kickoff_chain:T-30` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-10-19T22:30:12.641375Z (CURRENT at publish; CURRENT until 2026-10-19T22:50:12.641375Z, STALE after 2026-10-19T23:00:12.641375Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-19T22:32:57.251541Z · simulations this update: 1 · Odds API calls this update: 0 (credits 0) · reprice 0.35s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-19T23:00:00Z | Corinthians vs Vitória (bra.serie_a) | VALID (CURRENT) | confirmed (CURRENT) | AGING entry | CURRENT | 14 | 0 |
| 2026-10-20T00:15:00Z | Deportivo Riestra vs Unión (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-21T00:07:00Z | Guadalajara vs Necaxa (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T01:00:00Z | FC Juárez vs Atlante (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T01:00:00Z | Atlético San Luis vs Querétaro (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T03:00:00Z | Tigres UANL vs León (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (2; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Corinthians vs Vitória | Result: home | no | 0.3950 | 0.526 [0.365, 0.674] | +0.114 | +0.011 | 0.4 | 0.354 | * | RESEARCH_CANDIDATE |
| Corinthians vs Vitória | Result: away | yes | 0.1550 | 0.248 [0.136, 0.368] | +0.084 | +0.007 | 0.16 | 0.127 |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 514
action_NO_QUOTE: 156
action_RESEARCH_CANDIDATE: 2
contract_sides: 672
fixtures: 6
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 1

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
