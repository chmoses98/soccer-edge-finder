# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261007T091550Z-25a175` · generated 2026-10-07T09:15:50.601240Z · trigger `kalshi_capture` · mode `reprice_only`

**Kalshi prices observed 2026-10-07T09:13:14.850576Z (CURRENT at publish; CURRENT until 2026-10-07T09:33:14.850576Z, STALE after 2026-10-07T09:43:14.850576Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-10-07T01:42:52.733903Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.15s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-10-07T22:30:00Z | Red Bull Bragantino vs Mirassol (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-07T22:30:00Z | Internacional vs Corinthians (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-07T22:30:00Z | Remo vs Grêmio (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-07T23:00:00Z | Vitória vs Chapecoense (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-07T23:30:00Z | Botafogo vs Vasco da Gama (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-08T00:30:00Z | Cruzeiro vs São Paulo (bra.serie_a) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-08T22:30:00Z | Santos vs Flamengo (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-08T23:00:00Z | Athletico Paranaense vs Atlético Mineiro (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-09T00:30:00Z | Fluminense vs Coritiba (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-10-09T00:30:00Z | Palmeiras vs Bahia (bra.serie_a) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |

## Candidates on CURRENT prices (10; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|
| Athletico Paranaense vs Atlético Mineiro | Result: home | yes | 0.2550 | 0.501 [0.343, 0.670] | +0.232 | +0.122 | 0.37 | - | * | RESEARCH_CANDIDATE |
| Athletico Paranaense vs Atlético Mineiro | home wins by more than 1.5 | yes | 0.0900 | 0.273 [0.139, 0.433] | +0.177 | +0.076 | 0.16 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Vasco da Gama | Result: away | no | 0.5750 | 0.734 [0.604, 0.851] | +0.142 | +0.064 | 0.64 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Vasco da Gama | Result: home | yes | 0.3100 | 0.478 [0.321, 0.639] | +0.153 | +0.048 | 0.35 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Vasco da Gama | away wins by more than 1.5 | no | 0.8000 | 0.890 [0.811, 0.954] | +0.079 | +0.036 | 0.83 | - | * | RESEARCH_CANDIDATE |
| Botafogo vs Vasco da Gama | home wins by more than 1.5 | yes | 0.1400 | 0.258 [0.131, 0.406] | +0.110 | +0.015 | 0.15 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Vasco da Gama | away wins by more than 2.5 | no | 0.9300 | 0.964 [0.929, 0.990] | +0.029 | +0.013 | 0.94 | - |  | RESEARCH_CANDIDATE |
| Botafogo vs Vasco da Gama | home wins by more than 2.5 | yes | 0.0500 | 0.115 [0.039, 0.213] | +0.062 | +0.002 | 0.05 | - |  | RESEARCH_CANDIDATE |
| Vitória vs Chapecoense | Result: away | yes | 0.1600 | 0.253 [0.137, 0.379] | +0.084 | +0.001 | 0.16 | - | * | RESEARCH_CANDIDATE |
| Santos vs Flamengo | Result: away | no | 0.4750 | 0.591 [0.439, 0.748] | +0.099 | +0.000 | 0.47 | - | * | RESEARCH_CANDIDATE |

## Counts

```
action_NO_EDGE: 269
action_NO_QUOTE: 1
action_RESEARCH_CANDIDATE: 10
contract_sides: 280
fixtures: 10
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
