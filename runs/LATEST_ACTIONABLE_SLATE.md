# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261012T235725Z-cc5e57` · generated 2026-10-12T23:57:25.169280Z · trigger `kickoff_chain:T-5` · mode `reprice_only`

**Kalshi prices observed 2026-10-12T23:55:00.024004Z (CURRENT at publish; CURRENT until 2026-10-13T00:15:00.024004Z, STALE after 2026-10-13T00:25:00.024004Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-12T23:31:06.595813Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.05s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-13T00:00:00Z | Red Bull Bragantino vs Cruzeiro (bra.serie_a) | VALID (CURRENT) | confirmed (CURRENT) | CURRENT close | CURRENT | 14 | 0 |

## Candidates on CURRENT prices (7; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Red Bull Bragantino vs Cruzeiro | btts | no | 0.3800 | 0.509 [0.381, 0.637] | +0.112 | +0.032 | 0.41 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | Total goals over 2.5 | no | 0.4100 | 0.548 [0.384, 0.705] | +0.121 | +0.017 | 0.42 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | Total goals over 1.5 | no | 0.1900 | 0.294 [0.169, 0.430] | +0.093 | +0.007 | 0.19 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | Total goals over 0.5 | no | 0.0500 | 0.097 [0.046, 0.160] | +0.044 | +0.006 | 0.05 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | Total goals over 3.5 | no | 0.6500 | 0.751 [0.606, 0.876] | +0.085 | +0.002 | 0.65 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | Total goals over 4.5 | no | 0.8200 | 0.880 [0.784, 0.956] | +0.050 | +0.000 | 0.82 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | Total goals over 5.5 | no | 0.9200 | 0.949 [0.897, 0.987] | +0.024 | +0.000 | 0.92 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 21
action_RESEARCH_CANDIDATE: 7
contract_sides: 28
fixtures: 1
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
