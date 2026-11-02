# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261102T185658Z-895945` · generated 2026-11-02T18:56:58.528200Z · trigger `kickoff_chain:T-60` · mode `model_refresh_and_reprice`

**Kalshi prices observed 2026-11-02T18:54:03.019247Z (CURRENT at publish; CURRENT until 2026-11-02T19:14:03.019247Z, STALE after 2026-11-02T19:24:03.019247Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-02T18:56:57.921812Z · simulations this update: 1 · Odds API calls this update: 1 (credits 3) · reprice 0.09s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-02T19:45:00Z | Atalanta vs Parma (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | AGING entry | CURRENT | 3 | 0 |
| 2026-11-02T20:00:00Z | Newcastle United vs Everton (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | CURRENT entry | CURRENT | 3 | 0 |
| 2026-11-02T22:00:00Z | Defensa y Justicia vs Independiente (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-02T22:00:00Z | Platense vs Central Córdoba (arg.primera) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-02T23:00:00Z | Red Bull Bragantino vs Santos (bra.serie_a) | VALID (CURRENT) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-03T22:30:00Z | Chapecoense vs Mirassol (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-04T00:30:00Z | Internacional vs Coritiba (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 29 | 0 |

## Candidates on CURRENT prices (9; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Red Bull Bragantino vs Santos | Total goals over 3.5 | no | 0.5900 | 0.724 [0.572, 0.854] | +0.117 | +0.029 | 0.61 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | btts | no | 0.3700 | 0.491 [0.367, 0.615] | +0.105 | +0.026 | 0.39 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 2.5 | no | 0.3700 | 0.516 [0.352, 0.672] | +0.130 | +0.025 | 0.39 | - |  | RESEARCH_CANDIDATE |
| Atalanta vs Parma | Result: home | no | 0.3300 | 0.487 [0.315, 0.656] | +0.142 | +0.025 | 0.35 | 0.335 | * | RESEARCH_CANDIDATE |
| Atalanta vs Parma | Result: draw | yes | 0.1900 | 0.276 [0.196, 0.357] | +0.075 | +0.022 | 0.21 | 0.189 |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 0.5 | no | 0.0400 | 0.086 [0.039, 0.141] | +0.044 | +0.008 | 0.04 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 1.5 | no | 0.1700 | 0.269 [0.148, 0.397] | +0.089 | +0.008 | 0.17 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 4.5 | no | 0.7900 | 0.862 [0.756, 0.946] | +0.061 | +0.005 | 0.79 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 5.5 | no | 0.9000 | 0.939 [0.878, 0.983] | +0.033 | +0.004 | 0.9 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 87
action_NO_QUOTE: 146
action_RESEARCH_CANDIDATE: 9
contract_sides: 242
fixtures: 7
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
