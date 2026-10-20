# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261020T054750Z-471be9` · generated 2026-10-20T05:47:50.500096Z · trigger `kalshi_capture` · mode `reprice_only`

**Kalshi prices observed 2026-10-20T05:44:54.453850Z (CURRENT at publish; CURRENT until 2026-10-20T06:04:54.453850Z, STALE after 2026-10-20T06:14:54.453850Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-19T23:27:47.195072Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.47s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-21T00:07:00Z | Guadalajara vs Necaxa (mex.liga_mx) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T01:00:00Z | FC Juárez vs Atlante (mex.liga_mx) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T01:00:00Z | Atlético San Luis vs Querétaro (mex.liga_mx) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T03:00:00Z | Tigres UANL vs León (mex.liga_mx) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-21T23:00:00Z | FC Cincinnati vs D.C. United (usa.mls) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (4; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Atlético San Luis vs Querétaro | btts | no | 0.4200 | 0.538 [0.408, 0.665] | +0.101 | +0.014 | 0.43 | - | * | RESEARCH_CANDIDATE |
| Tigres UANL vs León | away team total over 0.5 | no | 0.3300 | 0.431 [0.311, 0.551] | +0.085 | +0.006 | 0.33 | - | * | RESEARCH_CANDIDATE |
| Tigres UANL vs León | away team total over 1.5 | no | 0.7000 | 0.783 [0.674, 0.879] | +0.069 | +0.004 | 0.7 | - |  | RESEARCH_CANDIDATE |
| Tigres UANL vs León | btts | no | 0.4400 | 0.539 [0.423, 0.656] | +0.082 | +0.004 | 0.44 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 611
action_NO_QUOTE: 155
action_RESEARCH_CANDIDATE: 4
contract_sides: 770
fixtures: 5
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
