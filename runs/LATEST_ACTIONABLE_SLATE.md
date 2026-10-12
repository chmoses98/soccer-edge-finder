# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261012T202730Z-54679e` · generated 2026-10-12T20:27:30.168014Z · trigger `kickoff_chain:T-120/T-60` · mode `reprice_only`

**Kalshi prices observed 2026-10-12T20:25:02.931824Z (CURRENT at publish; CURRENT until 2026-10-12T20:45:02.931824Z, STALE after 2026-10-12T20:55:02.931824Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-12T16:56:56.005007Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.10s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-12T22:30:00Z | Chapecoense vs Athletico Paranaense (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-13T00:00:00Z | Red Bull Bragantino vs Cruzeiro (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |

## Candidates on CURRENT prices (5; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Red Bull Bragantino vs Cruzeiro | btts | no | 0.3900 | 0.509 [0.381, 0.637] | +0.102 | +0.022 | 0.41 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | Total goals over 2.5 | no | 0.4200 | 0.548 [0.384, 0.705] | +0.111 | +0.007 | 0.42 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | Total goals over 1.5 | no | 0.1900 | 0.294 [0.169, 0.430] | +0.093 | +0.007 | 0.19 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | Total goals over 3.5 | no | 0.6500 | 0.751 [0.606, 0.876] | +0.085 | +0.002 | 0.65 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | Total goals over 5.5 | no | 0.9200 | 0.949 [0.897, 0.987] | +0.024 | +0.000 | 0.92 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 51
action_NO_QUOTE: 60
action_RESEARCH_CANDIDATE: 5
contract_sides: 116
fixtures: 2
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
