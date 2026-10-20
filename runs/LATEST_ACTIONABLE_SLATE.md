# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261020T001519Z-c1204e` · generated 2026-10-20T00:15:19.047128Z · trigger `kalshi_capture` · mode `reprice_only`

**Kalshi prices observed 2026-10-20T00:12:20.207185Z (CURRENT at publish; CURRENT until 2026-10-20T00:32:20.207185Z, STALE after 2026-10-20T00:42:20.207185Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-19T23:27:47.195072Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.29s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-21T00:07:00Z | Guadalajara vs Necaxa (mex.liga_mx) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T01:00:00Z | FC Juárez vs Atlante (mex.liga_mx) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T01:00:00Z | Atlético San Luis vs Querétaro (mex.liga_mx) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T03:00:00Z | Tigres UANL vs León (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T23:00:00Z | FC Cincinnati vs D.C. United (usa.mls) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (0; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|

## Counts

```
action_NO_EDGE: 610
action_NO_QUOTE: 160
contract_sides: 770
fixtures: 5
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 1

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
