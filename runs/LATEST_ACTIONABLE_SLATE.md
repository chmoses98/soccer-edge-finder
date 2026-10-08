# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261008T114237Z-b0843c` · generated 2026-10-08T11:42:37.585360Z · trigger `kalshi_capture:slate_refresh+new_fixtures` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-10-08T11:40:10.587608Z (CURRENT at publish; CURRENT until 2026-10-08T12:00:10.587608Z, STALE after 2026-10-08T12:10:10.587608Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-08T11:42:37.105948Z · simulations this update: 1 · Odds API calls this update: 0 (credits 0) · reprice 0.05s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-08T22:30:00Z | Santos vs Flamengo (bra.serie_a) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-08T23:00:00Z | Athletico Paranaense vs Atlético Mineiro (bra.serie_a) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-09T00:30:00Z | Fluminense vs Coritiba (bra.serie_a) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-09T00:30:00Z | Palmeiras vs Bahia (bra.serie_a) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-09T18:30:00Z | Borussia Dortmund vs Werder Bremen (ger.bundesliga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-09T18:45:00Z | Lens vs Lyon (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-09T19:00:00Z | Málaga vs Espanyol (esp.la_liga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-10T01:00:00Z | Puebla vs León (mex.liga_mx) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-10T03:00:00Z | Tigres UANL vs Toluca (mex.liga_mx) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-10T11:30:00Z | Arsenal vs Leeds United (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |

## Candidates on CURRENT prices (14; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Athletico Paranaense vs Atlético Mineiro | Result: home | yes | 0.2750 | 0.501 [0.343, 0.670] | +0.212 | +0.101 | 0.37 | - | * | RESEARCH_CANDIDATE |
| Athletico Paranaense vs Atlético Mineiro | home wins by more than 1.5 | yes | 0.1000 | 0.273 [0.139, 0.433] | +0.167 | +0.065 | 0.16 | - | * | RESEARCH_CANDIDATE |
| Arsenal vs Leeds United | Result: home | no | 0.2900 | 0.473 [0.308, 0.645] | +0.169 | +0.056 | 0.34 | - | * | RESEARCH_CANDIDATE |
| Puebla vs León | btts | no | 0.4500 | 0.577 [0.453, 0.695] | +0.109 | +0.035 | 0.48 | - | * | RESEARCH_CANDIDATE |
| Santos vs Flamengo | Result: away | no | 0.4550 | 0.591 [0.439, 0.748] | +0.119 | +0.020 | 0.47 | - | * | RESEARCH_CANDIDATE |
| Arsenal vs Leeds United | Result: away | yes | 0.1100 | 0.211 [0.104, 0.342] | +0.094 | +0.015 | 0.12 | - |  | RESEARCH_CANDIDATE |
| Athletico Paranaense vs Atlético Mineiro | home wins by more than 2.5 | yes | 0.0400 | 0.123 [0.042, 0.229] | +0.080 | +0.015 | 0.05 | - |  | RESEARCH_CANDIDATE |
| Arsenal vs Leeds United | Result: draw | yes | 0.1900 | 0.262 [0.190, 0.331] | +0.061 | +0.014 | 0.2 | - |  | RESEARCH_CANDIDATE |
| Tigres UANL vs Toluca | btts | no | 0.4200 | 0.531 [0.399, 0.656] | +0.094 | +0.010 | 0.42 | - | * | RESEARCH_CANDIDATE |
| Palmeiras vs Bahia | btts | no | 0.4500 | 0.555 [0.425, 0.677] | +0.088 | +0.007 | 0.45 | - | * | RESEARCH_CANDIDATE |
| Santos vs Flamengo | Result: home | yes | 0.2200 | 0.333 [0.198, 0.494] | +0.101 | +0.004 | 0.22 | - |  | RESEARCH_CANDIDATE |
| Santos vs Flamengo | away wins by more than 2.5 | no | 0.8700 | 0.915 [0.845, 0.971] | +0.037 | +0.002 | 0.87 | - | * | RESEARCH_CANDIDATE |
| Santos vs Flamengo | home wins by more than 1.5 | yes | 0.0800 | 0.155 [0.067, 0.271] | +0.070 | +0.002 | 0.08 | - |  | RESEARCH_CANDIDATE |
| Santos vs Flamengo | away wins by more than 1.5 | no | 0.7100 | 0.793 [0.672, 0.900] | +0.069 | +0.001 | 0.71 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 177
action_NO_QUOTE: 121
action_RESEARCH_CANDIDATE: 14
contract_sides: 312
fixtures: 10
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
