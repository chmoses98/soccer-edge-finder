# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261012T184627Z-608226` · generated 2026-10-12T18:46:27.126955Z · trigger `kickoff_chain:T-15` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-10-12T18:43:51.569047Z (CURRENT at publish; CURRENT until 2026-10-12T19:03:51.569047Z, STALE after 2026-10-12T19:13:51.569047Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-12T18:31:51.541502Z · simulations this update: 0 · Odds API calls this update: 4 (credits 12) · reprice 0.11s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-12T19:00:00Z | Lanús vs Vélez Sarsfield (arg.primera) | INVALIDATED: lineup_changed:published:confirmed | confirmed (CURRENT) | CURRENT close | CURRENT | 14 | 0 |
| 2026-10-12T19:00:00Z | Coritiba vs Botafogo (bra.serie_a) | VALID (CURRENT) | confirmed (CURRENT) | CURRENT close | CURRENT | 14 | 0 |
| 2026-10-12T19:00:00Z | Coventry City vs Newcastle United (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | CURRENT close | CURRENT | 3 | 0 |
| 2026-10-12T19:00:00Z | Levante vs Sevilla (esp.la_liga) | VALID (CURRENT) | unknown (UNAVAILABLE) | CURRENT close | CURRENT | 3 | 0 |
| 2026-10-12T22:30:00Z | Chapecoense vs Athletico Paranaense (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-13T00:00:00Z | Red Bull Bragantino vs Cruzeiro (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |

## Candidates on CURRENT prices (3; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Levante vs Sevilla | Result: home | yes | 0.3300 | 0.477 [0.315, 0.659] | +0.131 | +0.023 | 0.35 | 0.330 | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | btts | no | 0.3900 | 0.509 [0.381, 0.637] | +0.102 | +0.022 | 0.41 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Cruzeiro | Total goals over 3.5 | no | 0.6500 | 0.751 [0.606, 0.876] | +0.085 | +0.002 | 0.65 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 93
action_NO_QUOTE: 88
action_RESEARCH_CANDIDATE: 3
contract_sides: 184
fixtures: 6
fixtures_model_invalidated: 1
fixtures_model_missing: 0
```

Removed (kicked off): 1

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
