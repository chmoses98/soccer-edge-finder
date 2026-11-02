# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261102T225740Z-fc7ee0` · generated 2026-11-02T22:57:40.974588Z · trigger `kickoff_chain:T-5` · mode `reprice_only`

**Kalshi prices observed 2026-11-02T22:55:00.067557Z (CURRENT at publish; CURRENT until 2026-11-02T23:15:00.067557Z, STALE after 2026-11-02T23:25:00.067557Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-02T22:31:17.286525Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.09s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-02T23:00:00Z | Red Bull Bragantino vs Santos (bra.serie_a) | VALID (CURRENT) | confirmed (CURRENT) | CURRENT close | CURRENT | 14 | 0 |
| 2026-11-03T22:30:00Z | Chapecoense vs Mirassol (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-04T00:30:00Z | Internacional vs Coritiba (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |

## Candidates on CURRENT prices (6; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Red Bull Bragantino vs Santos | btts | no | 0.3500 | 0.491 [0.367, 0.615] | +0.125 | +0.046 | 0.39 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 3.5 | no | 0.5800 | 0.724 [0.572, 0.854] | +0.127 | +0.039 | 0.61 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 2.5 | no | 0.3700 | 0.516 [0.352, 0.672] | +0.130 | +0.025 | 0.39 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 4.5 | no | 0.7700 | 0.862 [0.756, 0.946] | +0.080 | +0.024 | 0.79 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 1.5 | no | 0.1600 | 0.269 [0.148, 0.397] | +0.100 | +0.018 | 0.17 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 5.5 | no | 0.8900 | 0.939 [0.878, 0.983] | +0.042 | +0.014 | 0.9 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 78
action_NO_QUOTE: 60
action_RESEARCH_CANDIDATE: 6
contract_sides: 144
fixtures: 3
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 2

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
