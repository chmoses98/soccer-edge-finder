# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261012T085312Z-cb6364` · generated 2026-10-12T08:53:12.693066Z · trigger `kalshi_capture:slate_refresh` · mode `reprice_only`

**Kalshi prices observed 2026-10-12T08:50:49.094183Z (CURRENT at publish; CURRENT until 2026-10-12T09:10:49.094183Z, STALE after 2026-10-12T09:20:49.094183Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-12T04:52:46.653439Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.11s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-12T16:30:00Z | Atalanta vs Venezia (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-12T18:45:00Z | Torino vs Udinese (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-12T19:00:00Z | Lanús vs Vélez Sarsfield (arg.primera) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-12T19:00:00Z | Coritiba vs Botafogo (bra.serie_a) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-12T19:00:00Z | Coventry City vs Newcastle United (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-12T19:00:00Z | Levante vs Sevilla (esp.la_liga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-12T22:30:00Z | Chapecoense vs Athletico Paranaense (bra.serie_a) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-13T00:00:00Z | Red Bull Bragantino vs Cruzeiro (bra.serie_a) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |

## Candidates on CURRENT prices (1; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Torino vs Udinese | Result: draw | no | 0.7000 | 0.753 [0.696, 0.805] | +0.038 | +0.004 | 0.7 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 107
action_NO_QUOTE: 118
action_RESEARCH_CANDIDATE: 1
contract_sides: 226
fixtures: 8
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
