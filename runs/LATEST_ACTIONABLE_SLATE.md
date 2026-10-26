# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261026T222736Z-f81e20` · generated 2026-10-26T22:27:36.688610Z · trigger `kickoff_chain:T-5` · mode `reprice_only`

**Kalshi prices observed 2026-10-26T22:25:00.056270Z (CURRENT at publish; CURRENT until 2026-10-26T22:45:00.056270Z, STALE after 2026-10-26T22:55:00.056270Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-26T22:05:21.729663Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.20s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-26T22:30:00Z | Coritiba vs Grêmio (bra.serie_a) | VALID (CURRENT) | confirmed (CURRENT) | CURRENT close | CURRENT | 14 | 0 |
| 2026-10-26T23:00:00Z | Flamengo vs Atlético Mineiro (bra.serie_a) | INVALIDATED: lineup_changed:published:confirmed | confirmed (CURRENT) | AGING entry | CURRENT | 14 | 0 |
| 2026-10-27T00:15:00Z | Instituto vs Deportivo Riestra (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-27T17:30:00Z | Sassuolo vs Lazio (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 32 | 0 |
| 2026-10-27T19:45:00Z | AS Roma vs Cagliari (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-27T19:45:00Z | Torino vs Como (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-28T17:30:00Z | AC Milan vs Bologna (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-28T17:30:00Z | Parma vs Udinese (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-28T17:30:00Z | Venezia vs Inter Milan (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 32 | 0 |
| 2026-10-28T19:45:00Z | Genoa vs Juventus (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 32 | 0 |
| 2026-10-28T19:45:00Z | Monza vs Napoli (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (1; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| AS Roma vs Cagliari | Result: home | no | 0.2700 | 0.400 [0.228, 0.583] | +0.116 | +0.011 | 0.28 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_MODEL_INVALIDATED: 27
action_NO_EDGE: 75
action_NO_QUOTE: 943
action_RESEARCH_CANDIDATE: 1
contract_sides: 1046
fixtures: 11
fixtures_model_invalidated: 1
fixtures_model_missing: 0
```

Removed (kicked off): 1

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
