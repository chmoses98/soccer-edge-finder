# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261022T132343Z-dd7df2` · generated 2026-10-22T13:23:43.925123Z · trigger `run_soccer` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-10-22T13:08:24.458217Z (CURRENT at publish; CURRENT until 2026-10-22T13:28:24.458217Z, STALE after 2026-10-22T13:38:24.458217Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-22T13:22:53.257379Z · simulations this update: 10 · Odds API calls this update: 0 (credits 0) · reprice 0.31s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-23T18:30:00Z | VfB Stuttgart vs Borussia Mönchengladbach (ger.bundesliga) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-23T18:45:00Z | Brest vs Nice (fra.ligue_1) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-23T18:45:00Z | Torino vs Monza (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-23T19:00:00Z | Ipswich Town vs Nottingham Forest (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 81 | 0 |
| 2026-10-23T23:00:00Z | Cruzeiro vs Remo (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 21 | 8 |
| 2026-10-24T01:00:00Z | Necaxa vs FC Juárez (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-24T03:00:00Z | Atlante vs Atlético San Luis (mex.liga_mx) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-24T11:30:00Z | Aston Villa vs Manchester City (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 83 | 0 |
| 2026-10-24T13:00:00Z | Cagliari vs Bologna (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |
| 2026-10-24T13:00:00Z | Como vs Sassuolo (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 77 | 0 |

## Candidates on CURRENT prices (12; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Brest vs Nice | btts | no | 0.4000 | 0.540 [0.395, 0.679] | +0.123 | +0.032 | 0.43 | - | * | RESEARCH_CANDIDATE |
| Cagliari vs Bologna | btts | no | 0.5000 | 0.620 [0.483, 0.741] | +0.103 | +0.022 | 0.52 | - | * | RESEARCH_CANDIDATE |
| Atlante vs Atlético San Luis | btts | no | 0.4200 | 0.541 [0.409, 0.668] | +0.104 | +0.020 | 0.43 | - | * | RESEARCH_CANDIDATE |
| Brest vs Nice | away team total over 0.5 | no | 0.2700 | 0.399 [0.253, 0.545] | +0.115 | +0.019 | 0.28 | - | * | RESEARCH_CANDIDATE |
| Brest vs Nice | away team total over 1.5 | no | 0.6300 | 0.749 [0.600, 0.876] | +0.103 | +0.018 | 0.64 | - |  | RESEARCH_CANDIDATE |
| Cagliari vs Bologna | Result: away | no | 0.6200 | 0.736 [0.592, 0.861] | +0.100 | +0.015 | 0.63 | - | * | RESEARCH_CANDIDATE |
| Cagliari vs Bologna | away wins by more than 1.5 | no | 0.8500 | 0.909 [0.831, 0.967] | +0.050 | +0.012 | 0.86 | - | * | RESEARCH_CANDIDATE |
| Cagliari vs Bologna | away wins by more than 2.5 | no | 0.9500 | 0.974 [0.943, 0.994] | +0.021 | +0.010 | 0.96 | - |  | RESEARCH_CANDIDATE |
| Cagliari vs Bologna | Result: home | yes | 0.3100 | 0.444 [0.282, 0.615] | +0.119 | +0.006 | 0.31 | - |  | RESEARCH_CANDIDATE |
| Torino vs Monza | Result: draw | no | 0.7200 | 0.783 [0.712, 0.854] | +0.049 | +0.005 | 0.72 | - | * | RESEARCH_CANDIDATE |
| Brest vs Nice | away team total over 2.5 | no | 0.8700 | 0.918 [0.839, 0.976] | +0.040 | +0.003 | 0.87 | - |  | RESEARCH_CANDIDATE |
| Aston Villa vs Manchester City | Exact score 1-0 (home-away) | yes | 0.0400 | 0.071 [0.030, 0.113] | +0.028 | +0.001 | 0.04 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 1134
action_NO_QUOTE: 302
action_RESEARCH_CANDIDATE: 12
contract_sides: 1448
fixtures: 10
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
