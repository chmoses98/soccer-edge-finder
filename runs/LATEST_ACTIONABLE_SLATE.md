# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261102T222636Z-3d977f` · generated 2026-11-02T22:26:36.728519Z · trigger `kalshi_capture:slate_refresh` · mode `reprice_only`

**Kalshi prices observed 2026-11-02T22:23:58.758091Z (CURRENT at publish; CURRENT until 2026-11-02T22:43:58.758091Z, STALE after 2026-11-02T22:53:58.758091Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-02T21:57:52.377927Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.09s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-02T23:00:00Z | Red Bull Bragantino vs Santos (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | AGING entry | CURRENT | 14 | 0 |
| 2026-11-03T22:30:00Z | Chapecoense vs Mirassol (bra.serie_a) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-04T00:30:00Z | Internacional vs Coritiba (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |

## Candidates on CURRENT prices (7; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Red Bull Bragantino vs Santos | btts | no | 0.3600 | 0.491 [0.367, 0.615] | +0.115 | +0.036 | 0.39 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 3.5 | no | 0.5900 | 0.724 [0.572, 0.854] | +0.117 | +0.029 | 0.61 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 2.5 | no | 0.3700 | 0.516 [0.352, 0.672] | +0.130 | +0.025 | 0.39 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 1.5 | no | 0.1600 | 0.269 [0.148, 0.397] | +0.100 | +0.018 | 0.17 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 4.5 | no | 0.7800 | 0.862 [0.756, 0.946] | +0.070 | +0.014 | 0.79 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 0.5 | no | 0.0400 | 0.086 [0.039, 0.141] | +0.044 | +0.008 | 0.04 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 5.5 | no | 0.9000 | 0.939 [0.878, 0.983] | +0.033 | +0.004 | 0.9 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 77
action_NO_QUOTE: 60
action_RESEARCH_CANDIDATE: 7
contract_sides: 144
fixtures: 3
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 2

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
