# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261007T022657Z-6c4534` · generated 2026-10-07T02:26:57.667741Z · trigger `kickoff_chain:T-5` · mode `reprice_only`

**Kalshi prices observed 2026-10-07T02:24:31.162865Z (CURRENT at publish; CURRENT until 2026-10-07T02:44:31.162865Z, STALE after 2026-10-07T02:54:31.162865Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-07T01:42:52.733903Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.19s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-07T02:30:00Z | Mexico vs Chile (fifa.friendly) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 23 | 0 |
| 2026-10-07T22:30:00Z | Red Bull Bragantino vs Mirassol (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-07T22:30:00Z | Internacional vs Corinthians (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-07T22:30:00Z | Remo vs Grêmio (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-07T23:00:00Z | Vitória vs Chapecoense (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-07T23:30:00Z | Botafogo vs Vasco da Gama (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-08T00:30:00Z | Cruzeiro vs São Paulo (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-08T22:30:00Z | Santos vs Flamengo (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-08T23:00:00Z | Athletico Paranaense vs Atlético Mineiro (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-09T00:30:00Z | Fluminense vs Coritiba (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-09T00:30:00Z | Palmeiras vs Bahia (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |

## Candidates on CURRENT prices (7; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Athletico Paranaense vs Atlético Mineiro | Result: home | yes | 0.2550 | 0.501 [0.343, 0.670] | +0.232 | +0.122 | 0.37 | - | * | RESEARCH_CANDIDATE |
| Athletico Paranaense vs Atlético Mineiro | home wins by more than 1.5 | yes | 0.0900 | 0.273 [0.139, 0.433] | +0.177 | +0.076 | 0.16 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Vasco da Gama | Result: away | no | 0.6150 | 0.734 [0.604, 0.851] | +0.102 | +0.025 | 0.64 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Vasco da Gama | Result: home | yes | 0.3400 | 0.478 [0.321, 0.639] | +0.122 | +0.018 | 0.35 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Vasco da Gama | away wins by more than 1.5 | no | 0.8200 | 0.890 [0.811, 0.954] | +0.060 | +0.017 | 0.83 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Vasco da Gama | away wins by more than 2.5 | no | 0.9300 | 0.964 [0.929, 0.990] | +0.029 | +0.013 | 0.94 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Vasco da Gama | home wins by more than 1.5 | yes | 0.1500 | 0.258 [0.131, 0.406] | +0.099 | +0.004 | 0.15 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_EXCLUDED_BY_GATE: 5
action_NO_EDGE: 313
action_NO_QUOTE: 1
action_RESEARCH_CANDIDATE: 7
contract_sides: 326
fixtures: 11
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Removed (kicked off): 1

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
