# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261008T064611Z-a4b146` · generated 2026-10-08T06:46:11.066044Z · trigger `kalshi_capture` · mode `reprice_only`

**Kalshi prices observed 2026-10-08T06:43:33.121598Z (CURRENT at publish; CURRENT until 2026-10-08T07:03:33.121598Z, STALE after 2026-10-08T07:13:33.121598Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-07T20:48:27.974644Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.18s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-08T22:30:00Z | Santos vs Flamengo (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-08T23:00:00Z | Athletico Paranaense vs Atlético Mineiro (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-09T00:30:00Z | Fluminense vs Coritiba (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-09T00:30:00Z | Palmeiras vs Bahia (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-09T18:30:00Z | Borussia Dortmund vs Werder Bremen (ger.bundesliga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 79 | 0 |
| 2026-10-09T18:45:00Z | Lens vs Lyon (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 32 | 0 |
| 2026-10-09T19:00:00Z | Málaga vs Espanyol (esp.la_liga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 71 | 0 |
| 2026-10-10T01:00:00Z | Puebla vs León (mex.liga_mx) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-10T03:00:00Z | Tigres UANL vs Toluca (mex.liga_mx) | VALID (AGING) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |

## Candidates on CURRENT prices (11; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Athletico Paranaense vs Atlético Mineiro | Result: home | yes | 0.2600 | 0.501 [0.343, 0.670] | +0.227 | +0.117 | 0.37 | - | * | RESEARCH_CANDIDATE |
| Athletico Paranaense vs Atlético Mineiro | home wins by more than 1.5 | yes | 0.0900 | 0.273 [0.139, 0.433] | +0.177 | +0.076 | 0.16 | - | * | RESEARCH_CANDIDATE |
| Puebla vs León | btts | no | 0.4500 | 0.577 [0.453, 0.695] | +0.109 | +0.035 | 0.48 | - | * | RESEARCH_CANDIDATE |
| Athletico Paranaense vs Atlético Mineiro | home wins by more than 2.5 | yes | 0.0300 | 0.123 [0.042, 0.229] | +0.091 | +0.026 | 0.05 | - |  | RESEARCH_CANDIDATE |
| Tigres UANL vs Toluca | btts | no | 0.4100 | 0.531 [0.399, 0.656] | +0.104 | +0.020 | 0.42 | - | * | RESEARCH_CANDIDATE |
| Santos vs Flamengo | Result: away | no | 0.4650 | 0.591 [0.439, 0.748] | +0.109 | +0.010 | 0.47 | - | * | RESEARCH_CANDIDATE |
| Palmeiras vs Bahia | btts | no | 0.4500 | 0.555 [0.425, 0.677] | +0.088 | +0.007 | 0.45 | - | * | RESEARCH_CANDIDATE |
| Puebla vs León | away wins by more than 1.5 | no | 0.8300 | 0.887 [0.805, 0.955] | +0.047 | +0.006 | 0.83 | - | * | RESEARCH_CANDIDATE |
| Tigres UANL vs Toluca | Total goals over 2.5 | no | 0.4500 | 0.575 [0.403, 0.726] | +0.107 | +0.005 | 0.45 | - | * | RESEARCH_CANDIDATE |
| Puebla vs León | Total goals over 2.5 | no | 0.5100 | 0.621 [0.447, 0.772] | +0.093 | +0.000 | 0.51 | - | * | RESEARCH_CANDIDATE |
| Puebla vs León | Total goals over 3.5 | no | 0.7300 | 0.809 [0.670, 0.915] | +0.065 | +0.000 | 0.73 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 174
action_NO_QUOTE: 467
action_RESEARCH_CANDIDATE: 11
contract_sides: 652
fixtures: 9
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
