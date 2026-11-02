# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261102T170211Z-0e7e61` · generated 2026-11-02T17:02:11.865941Z · trigger `kickoff_chain:T-30` · mode `reprice_only`

**Kalshi prices observed 2026-11-02T16:59:27.310736Z (CURRENT at publish; CURRENT until 2026-11-02T17:19:27.310736Z, STALE after 2026-11-02T17:29:27.310736Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-02T16:32:20.759676Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.08s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-02T17:30:00Z | Sassuolo vs Fiorentina (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | AGING entry | CURRENT | 3 | 0 |
| 2026-11-02T19:45:00Z | Atalanta vs Parma (ita.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-02T20:00:00Z | Newcastle United vs Everton (eng.premier_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-02T22:00:00Z | Defensa y Justicia vs Independiente (arg.primera) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-02T22:00:00Z | Platense vs Central Córdoba (arg.primera) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 3 | 0 |
| 2026-11-02T23:00:00Z | Red Bull Bragantino vs Santos (bra.serie_a) | VALID (AGING) | unconfirmed (STALE) | UNAVAILABLE | CURRENT | 29 | 0 |
| 2026-11-03T22:30:00Z | Chapecoense vs Mirassol (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-04T00:30:00Z | Internacional vs Coritiba (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |

## Candidates on CURRENT prices (8; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Sassuolo vs Fiorentina | Result: away | no | 0.5900 | 0.733 [0.570, 0.866] | +0.126 | +0.036 | 0.62 | 0.599 | * | RESEARCH_CANDIDATE |
| Sassuolo vs Fiorentina | Result: home | yes | 0.3300 | 0.501 [0.314, 0.685] | +0.155 | +0.030 | 0.35 | 0.341 |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | btts | no | 0.3700 | 0.486 [0.366, 0.607] | +0.100 | +0.022 | 0.39 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 2.5 | no | 0.3700 | 0.510 [0.351, 0.667] | +0.123 | +0.019 | 0.38 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 3.5 | no | 0.6000 | 0.718 [0.571, 0.851] | +0.101 | +0.012 | 0.61 | - |  | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 1.5 | no | 0.1700 | 0.264 [0.150, 0.390] | +0.084 | +0.002 | 0.17 | - |  | RESEARCH_CANDIDATE |
| Atalanta vs Parma | Result: draw | yes | 0.2100 | 0.276 [0.196, 0.357] | +0.055 | +0.001 | 0.21 | - | * | RESEARCH_CANDIDATE |
| Red Bull Bragantino vs Santos | Total goals over 5.5 | no | 0.9000 | 0.937 [0.877, 0.982] | +0.031 | +0.001 | 0.9 | - |  | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 94
action_NO_QUOTE: 42
action_RESEARCH_CANDIDATE: 8
contract_sides: 144
fixtures: 8
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
