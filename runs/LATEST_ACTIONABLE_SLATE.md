# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261026T202934Z-1d5ef0` · generated 2026-10-26T20:29:34.720521Z · trigger `kickoff_chain:T-120` · mode `reprice_only`

**Kalshi prices observed 2026-10-26T20:26:55.579555Z (CURRENT at publish; CURRENT until 2026-10-26T20:46:55.579555Z, STALE after 2026-10-26T20:56:55.579555Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-26T20:14:34.454689Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.13s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-26T22:00:00Z | Unión vs Estudiantes de La Plata (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-26T22:30:00Z | Coritiba vs Grêmio (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-26T23:00:00Z | Flamengo vs Atlético Mineiro (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-10-27T00:15:00Z | Instituto vs Deportivo Riestra (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-27T17:30:00Z | Sassuolo vs Lazio (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-27T19:45:00Z | AS Roma vs Cagliari (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-27T19:45:00Z | Torino vs Como (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-28T17:30:00Z | AC Milan vs Bologna (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-28T17:30:00Z | Parma vs Udinese (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-28T17:30:00Z | Venezia vs Inter Milan (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-28T19:45:00Z | Genoa vs Juventus (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-10-28T19:45:00Z | Monza vs Napoli (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |

## Candidates on CURRENT prices (6; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Flamengo vs Atlético Mineiro | Result: home | no | 0.2250 | 0.368 [0.220, 0.519] | +0.130 | +0.031 | 0.25 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | home wins by more than 1.5 | no | 0.4600 | 0.609 [0.434, 0.768] | +0.132 | +0.024 | 0.48 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | Result: draw | yes | 0.1500 | 0.227 [0.148, 0.301] | +0.068 | +0.019 | 0.16 | - |  | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | home wins by more than 2.5 | no | 0.6900 | 0.799 [0.656, 0.912] | +0.094 | +0.016 | 0.7 | - |  | RESEARCH_CANDIDATE |
| AS Roma vs Cagliari | Result: home | no | 0.2700 | 0.400 [0.228, 0.583] | +0.116 | +0.011 | 0.28 | - | * | RESEARCH_CANDIDATE |
| Flamengo vs Atlético Mineiro | Total goals over 1.5 | no | 0.1700 | 0.271 [0.139, 0.408] | +0.091 | +0.003 | 0.17 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 97
action_NO_QUOTE: 117
action_RESEARCH_CANDIDATE: 6
contract_sides: 220
fixtures: 12
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
