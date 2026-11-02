# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261102T065115Z-b5081c` · generated 2026-11-02T06:51:15.983693Z · trigger `kalshi_capture:slate_refresh` · mode `reprice_only`

**Kalshi prices observed 2026-11-02T06:48:34.706841Z (CURRENT at publish; CURRENT until 2026-11-02T07:08:34.706841Z, STALE after 2026-11-02T07:18:34.706841Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-02T06:20:56.946003Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.12s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-02T17:30:00Z | Sassuolo vs Fiorentina (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-02T19:45:00Z | Atalanta vs Parma (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-02T20:00:00Z | Newcastle United vs Everton (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-02T22:00:00Z | Defensa y Justicia vs Independiente (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-02T22:00:00Z | Platense vs Central Córdoba (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-02T23:00:00Z | Red Bull Bragantino vs Santos (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-03T22:30:00Z | Chapecoense vs Mirassol (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-04T00:30:00Z | Internacional vs Coritiba (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |

## Candidates on CURRENT prices (4; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Sassuolo vs Fiorentina | Result: away | no | 0.6000 | 0.733 [0.570, 0.866] | +0.116 | +0.026 | 0.62 | - | * | RESEARCH_CANDIDATE |
| Sassuolo vs Fiorentina | Result: home | yes | 0.3400 | 0.501 [0.314, 0.685] | +0.145 | +0.020 | 0.35 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | btts | no | 0.3800 | 0.486 [0.366, 0.607] | +0.090 | +0.012 | 0.39 | - | * | RESEARCH_CANDIDATE |
| Atalanta vs Parma | Result: draw | yes | 0.2100 | 0.276 [0.196, 0.357] | +0.055 | +0.001 | 0.21 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 98
action_NO_QUOTE: 42
action_RESEARCH_CANDIDATE: 4
contract_sides: 144
fixtures: 8
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
