# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261109T010241Z-2353be` · generated 2026-11-09T01:02:41.255598Z · trigger `kalshi_capture:slate_refresh` · mode `reprice_only`

**Kalshi prices observed 2026-11-09T00:59:42.019241Z (CURRENT at publish; CURRENT until 2026-11-09T01:19:42.019241Z, STALE after 2026-11-09T01:29:42.019241Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-08T21:33:59.510963Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.12s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-09T02:10:00Z | León vs Guadalajara (mex.liga_mx) | VALID (CURRENT) | unconfirmed (AGING) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (18; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| León vs Guadalajara | away team total over 1.5 | no | 0.4800 | 0.664 [0.527, 0.794] | +0.167 | +0.082 | 0.56 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | away team total over 2.5 | no | 0.7600 | 0.872 [0.785, 0.947] | +0.100 | +0.052 | 0.81 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | away team total over 0.5 | no | 0.1800 | 0.314 [0.203, 0.432] | +0.123 | +0.048 | 0.22 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | btts | no | 0.4000 | 0.533 [0.407, 0.651] | +0.116 | +0.034 | 0.43 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | Total goals over 3.5 | no | 0.6500 | 0.775 [0.647, 0.885] | +0.109 | +0.033 | 0.68 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | Total goals over 2.5 | no | 0.4300 | 0.576 [0.423, 0.720] | +0.129 | +0.030 | 0.45 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | away wins by more than 1.5 | no | 0.7400 | 0.838 [0.736, 0.920] | +0.085 | +0.028 | 0.76 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | Total goals over 4.5 | no | 0.8200 | 0.897 [0.815, 0.961] | +0.066 | +0.022 | 0.84 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | First half: away wins by more than 1.5 | no | 0.8700 | 0.932 [0.879, 0.981] | +0.054 | +0.022 | 0.89 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | Total goals over 1.5 | no | 0.2000 | 0.321 [0.196, 0.451] | +0.110 | +0.020 | 0.21 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | away wins by more than 2.5 | no | 0.8900 | 0.942 [0.891, 0.980] | +0.046 | +0.019 | 0.91 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | Result: away | no | 0.5100 | 0.634 [0.488, 0.767] | +0.107 | +0.014 | 0.52 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | Exact score 1-0 (home-away) | yes | 0.0600 | 0.107 [0.064, 0.153] | +0.043 | +0.013 | 0.07 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | Total goals over 5.5 | no | 0.9200 | 0.958 [0.916, 0.989] | +0.033 | +0.012 | 0.93 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | First-half result: away | no | 0.6300 | 0.723 [0.608, 0.822] | +0.076 | +0.012 | 0.64 | - | * | RESEARCH_CANDIDATE |
| León vs Guadalajara | Exact score 0-0 (home-away) | yes | 0.0600 | 0.103 [0.051, 0.161] | +0.039 | +0.001 | 0.06 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | Total goals over 0.5 | no | 0.0600 | 0.103 [0.051, 0.161] | +0.039 | +0.001 | 0.06 | - |  | RESEARCH_CANDIDATE |
| León vs Guadalajara | Exact score 2-0 (home-away) | yes | 0.0400 | 0.064 [0.034, 0.094] | +0.021 | +0.000 | 0.04 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 120
action_NO_QUOTE: 16
action_RESEARCH_CANDIDATE: 18
contract_sides: 154
fixtures: 1
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
