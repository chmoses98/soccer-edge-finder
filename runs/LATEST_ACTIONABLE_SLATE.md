# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261105T024212Z-c27d8e` · generated 2026-11-05T02:42:12.211866Z · trigger `kalshi_capture` · mode `reprice_only`

**Kalshi prices observed 2026-11-05T02:39:18.777229Z (CURRENT at publish; CURRENT until 2026-11-05T02:59:18.777229Z, STALE after 2026-11-05T03:09:18.777229Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-04T23:13:32.242776Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.16s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-05T18:00:00Z | Aldosivi vs River Plate (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-05T22:15:00Z | Gimnasia La Plata vs Belgrano (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-05T22:30:00Z | Palmeiras vs Remo (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-06T00:30:00Z | Cruzeiro vs Bahia (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-06T19:30:00Z | Hamburger SV vs Borussia Mönchengladbach (ger.bundesliga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-06T19:45:00Z | Toulouse vs Strasbourg (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 59 | 0 |
| 2026-11-06T19:45:00Z | Venezia vs Udinese (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 71 | 0 |
| 2026-11-06T23:00:00Z | Vitória vs Fluminense (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |

## Candidates on CURRENT prices (13; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Palmeiras vs Remo | Total goals over 2.5 | no | 0.3800 | 0.558 [0.389, 0.714] | +0.162 | +0.056 | 0.43 | - | * | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Total goals over 3.5 | no | 0.6100 | 0.758 [0.612, 0.881] | +0.132 | +0.049 | 0.66 | - |  | RESEARCH_CANDIDATE |
| Venezia vs Udinese | Result: away | yes | 0.3100 | 0.517 [0.295, 0.742] | +0.192 | +0.035 | 0.34 | - | * | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Total goals over 4.5 | no | 0.7900 | 0.884 [0.788, 0.959] | +0.083 | +0.035 | 0.82 | - |  | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Total goals over 1.5 | no | 0.1800 | 0.305 [0.173, 0.440] | +0.115 | +0.026 | 0.2 | - |  | RESEARCH_CANDIDATE |
| Venezia vs Udinese | Result: home | no | 0.5800 | 0.739 [0.544, 0.909] | +0.142 | +0.023 | 0.6 | - |  | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Result: draw | yes | 0.1350 | 0.214 [0.129, 0.294] | +0.071 | +0.019 | 0.15 | - | * | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Total goals over 0.5 | no | 0.0400 | 0.100 [0.045, 0.162] | +0.057 | +0.017 | 0.05 | - |  | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | home wins by more than 1.5 | no | 0.4300 | 0.564 [0.385, 0.720] | +0.117 | +0.015 | 0.44 | - | * | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Result: home | no | 0.2000 | 0.311 [0.177, 0.445] | +0.100 | +0.013 | 0.21 | - |  | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | btts | no | 0.5600 | 0.652 [0.542, 0.756] | +0.075 | +0.007 | 0.56 | - | * | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | home wins by more than 2.5 | no | 0.6700 | 0.772 [0.616, 0.896] | +0.087 | +0.006 | 0.67 | - |  | RESEARCH_CANDIDATE |
| Palmeiras vs Remo | Total goals over 5.5 | no | 0.9200 | 0.951 [0.899, 0.988] | +0.025 | +0.003 | 0.92 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 88
action_NO_QUOTE: 321
action_RESEARCH_CANDIDATE: 13
contract_sides: 422
fixtures: 8
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
