# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261026T215744Z-07f13d` · generated 2026-10-26T21:57:44.759678Z · trigger `kickoff_chain:T-60/T-5` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-10-26T21:55:00.056189Z (CURRENT at publish; CURRENT until 2026-10-26T22:15:00.056189Z, STALE after 2026-10-26T22:25:00.056189Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-26T21:57:42.758599Z · simulations this update: 1 · Odds API calls this update: 1 (credits 3) · reprice 0.21s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-26T22:00:00Z | Unión vs Estudiantes de La Plata (arg.primera) | INVALIDATED: lineup_changed:published:confirmed | confirmed (CURRENT) | CURRENT close | CURRENT | 14 | 0 |
| 2026-10-26T22:30:00Z | Coritiba vs Grêmio (bra.serie_a) | INVALIDATED: lineup_changed:published:confirmed | confirmed (CURRENT) | AGING entry | CURRENT | 14 | 0 |
| 2026-10-26T23:00:00Z | Flamengo vs Atlético Mineiro (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | CURRENT entry | CURRENT | 14 | 0 |
| 2026-10-27T00:15:00Z | Instituto vs Deportivo Riestra (arg.primera) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-27T17:30:00Z | Sassuolo vs Lazio (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 32 | 0 |
| 2026-10-27T19:45:00Z | AS Roma vs Cagliari (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-27T19:45:00Z | Torino vs Como (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-28T17:30:00Z | AC Milan vs Bologna (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-28T17:30:00Z | Parma vs Udinese (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-28T17:30:00Z | Venezia vs Inter Milan (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 32 | 0 |
| 2026-10-28T19:45:00Z | Genoa vs Juventus (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 32 | 0 |
| 2026-10-28T19:45:00Z | Monza vs Napoli (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (6; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Flamengo vs Atlético Mineiro | Result: home | no | 0.2300 | 0.368 [0.220, 0.519] | +0.125 | +0.026 | 0.25 | 0.222 | * | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | home wins by more than 1.5 | no | 0.4600 | 0.609 [0.434, 0.768] | +0.132 | +0.024 | 0.48 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | home wins by more than 2.5 | no | 0.6900 | 0.799 [0.656, 0.912] | +0.094 | +0.016 | 0.7 | - |  | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | Result: draw | yes | 0.1550 | 0.227 [0.148, 0.301] | +0.063 | +0.013 | 0.16 | 0.147 |  | RESEARCH_CANDIDATE |
| AS Roma vs Cagliari | Result: home | no | 0.2700 | 0.400 [0.228, 0.583] | +0.116 | +0.011 | 0.28 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | Total goals over 0.5 | no | 0.0400 | 0.087 [0.036, 0.147] | +0.045 | +0.008 | 0.04 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_MODEL_INVALIDATED: 28
action_NO_EDGE: 69
action_NO_QUOTE: 971
action_RESEARCH_CANDIDATE: 6
contract_sides: 1074
fixtures: 12
fixtures_model_invalidated: 2
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
