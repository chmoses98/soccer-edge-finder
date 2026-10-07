# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261007T235826Z-af34a9` · generated 2026-10-07T23:58:26.324583Z · trigger `kalshi_capture:slate_refresh` · mode `reprice_only`

**Kalshi prices observed 2026-10-07T23:56:05.790295Z (CURRENT at publish; CURRENT until 2026-10-08T00:16:05.790295Z, STALE after 2026-10-08T00:26:05.790295Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-07T23:28:33.667181Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.26s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-08T00:30:00Z | Cruzeiro vs São Paulo (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | AGING entry | CURRENT | 14 | 0 |
| 2026-10-08T22:30:00Z | Santos vs Flamengo (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-08T23:00:00Z | Athletico Paranaense vs Atlético Mineiro (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-09T00:30:00Z | Fluminense vs Coritiba (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-09T00:30:00Z | Palmeiras vs Bahia (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-09T18:30:00Z | Borussia Dortmund vs Werder Bremen (ger.bundesliga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 79 | 0 |
| 2026-10-09T18:45:00Z | Lens vs Lyon (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 32 | 0 |
| 2026-10-09T19:00:00Z | Málaga vs Espanyol (esp.la_liga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 71 | 0 |

## Candidates on CURRENT prices (4; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Athletico Paranaense vs Atlético Mineiro | Result: home | yes | 0.2550 | 0.501 [0.343, 0.670] | +0.232 | +0.122 | 0.37 | - | * | RESEARCH_CANDIDATE |
| Athletico Paranaense vs Atlético Mineiro | home wins by more than 1.5 | yes | 0.0900 | 0.273 [0.139, 0.433] | +0.177 | +0.076 | 0.16 | - | * | RESEARCH_CANDIDATE |
| Athletico Paranaense vs Atlético Mineiro | home wins by more than 2.5 | yes | 0.0400 | 0.123 [0.042, 0.229] | +0.080 | +0.015 | 0.05 | - |  | RESEARCH_CANDIDATE |
| Santos vs Flamengo | Result: away | no | 0.4750 | 0.591 [0.439, 0.748] | +0.099 | +0.000 | 0.47 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 153
action_NO_QUOTE: 467
action_RESEARCH_CANDIDATE: 4
contract_sides: 624
fixtures: 8
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 2

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
