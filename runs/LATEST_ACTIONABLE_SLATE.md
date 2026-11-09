# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261109T010846Z-fc2690` · generated 2026-11-09T01:08:46.537923Z · trigger `kickoff_chain:T-60` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-11-09T01:05:24.562970Z (CURRENT at publish; CURRENT until 2026-11-09T01:25:24.562970Z, STALE after 2026-11-09T01:35:24.562970Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-09T01:08:32.897255Z · simulations this update: 1 · Odds API calls this update: 1 (credits 3) · reprice 0.12s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-09T02:10:00Z | León vs Guadalajara (mex.liga_mx) | VALID (CURRENT) | unconfirmed (CURRENT) | CURRENT entry | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (20; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| León vs Guadalajara | away team total over 1.5 | no | 0.4800 | 0.663 [0.511, 0.789] | +0.165 | +0.082 | 0.56 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | away team total over 2.5 | no | 0.7600 | 0.871 [0.772, 0.944] | +0.098 | +0.052 | 0.81 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | away team total over 0.5 | no | 0.1800 | 0.312 [0.193, 0.425] | +0.122 | +0.047 | 0.22 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | btts | no | 0.4000 | 0.536 [0.411, 0.651] | +0.119 | +0.042 | 0.44 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | Total goals over 2.5 | no | 0.4300 | 0.579 [0.421, 0.721] | +0.132 | +0.034 | 0.46 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | Total goals over 3.5 | no | 0.6600 | 0.777 [0.645, 0.885] | +0.102 | +0.027 | 0.68 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | Total goals over 4.5 | no | 0.8200 | 0.898 [0.814, 0.961] | +0.068 | +0.025 | 0.84 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | away wins by more than 1.5 | no | 0.7400 | 0.835 [0.724, 0.920] | +0.082 | +0.023 | 0.76 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | Result: away | no | 0.5000 | 0.630 [0.479, 0.763] | +0.112 | +0.022 | 0.52 | 0.506 | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | First half: away wins by more than 1.5 | no | 0.8700 | 0.932 [0.879, 0.981] | +0.054 | +0.022 | 0.89 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | away wins by more than 2.5 | no | 0.8900 | 0.941 [0.884, 0.980] | +0.044 | +0.017 | 0.9 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | Exact score 1-0 (home-away) | yes | 0.0600 | 0.107 [0.064, 0.151] | +0.043 | +0.015 | 0.07 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | Total goals over 1.5 | no | 0.2100 | 0.323 [0.194, 0.450] | +0.102 | +0.014 | 0.22 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | Total goals over 5.5 | no | 0.9200 | 0.958 [0.915, 0.989] | +0.033 | +0.014 | 0.93 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | First-half result: away | no | 0.6300 | 0.722 [0.608, 0.822] | +0.075 | +0.012 | 0.64 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | First-half total goals over 0.5 | no | 0.2700 | 0.357 [0.248, 0.472] | +0.073 | +0.004 | 0.27 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | First-half total goals over 1.5 | no | 0.6300 | 0.717 [0.598, 0.822] | +0.070 | +0.002 | 0.63 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | First-half total goals over 2.5 | no | 0.8600 | 0.906 [0.839, 0.961] | +0.038 | +0.002 | 0.86 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | Exact score 0-0 (home-away) | yes | 0.0600 | 0.104 [0.051, 0.162] | +0.040 | +0.001 | 0.06 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | Total goals over 0.5 | no | 0.0600 | 0.104 [0.051, 0.162] | +0.040 | +0.001 | 0.06 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 118
action_NO_QUOTE: 16
action_RESEARCH_CANDIDATE: 20
contract_sides: 154
fixtures: 1
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
