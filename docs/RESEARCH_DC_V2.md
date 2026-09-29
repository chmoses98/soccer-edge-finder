# dc_laplace_v2 selection, one-time holdout, and engine reconciliation (remediation phases 12-14)

Protocol: `research/dc_v2.py` (pre-registered before any holdout number was seen); results
`data/research/dc_v2_selection.json`, `dc_v2_holdout.json`, `world_sim_benchmark.json`, produced by
`research-dc-v2.yml` run 36505634302 (2026-09-29T01:05Z; data hash ef224cf2..., the frozen benchmark's
football-data redistribution). The holdout was scored once; the selection file is not re-chosen.

## Selection (design seasons 2019-20..2023-24, n = 8,785 aligned matches)

Grid decay xi in {0.0065, 0.004, 0.003} x team prior sd s in {0.35, 0.50, 0.60}; criterion 1X2 log loss.

| variant | 1X2 log loss | O/U 2.5 | home ECE | away level ratio |
|---|---|---|---|---|
| dc_laplace_v1 (production) | 1.00068 | 0.68448 | 0.0338 | **0.884** |
| v2 d0065 s035 | 0.99879 | 0.68188 | 0.0247 | 0.994 |
| v2 d0040 s050 | 0.99220 | 0.68139 | 0.0148 | 0.992 |
| v2 d0030 s050 | 0.99082 | 0.67988 | 0.0166 | 0.991 |
| **v2 d0030 s060 (chosen)** | **0.99034** | 0.67996 | 0.0137 | 0.991 |

Every v2 variant fixes the away-level defect (audit B2/D: v1 under-predicts away goals by 12 %) and beats v1.
The chosen configuration sits at the grid corner (slowest decay, widest prior): a wider grid might do
better, and that would be a new pre-registration, not a re-run of this holdout. Market 1X2 log loss on
the same matches: 0.97383.

## One-time holdout (2024-25 + 2025-26, n = 3,463)

| | v1 | v2 (d0030 s060) | market |
|---|---|---|---|
| 1X2 log loss | 1.00179 | **0.99203** | 0.97165 |
| paired v2 - v1 | | -0.00976 [-0.01408, -0.00557] | |
| O/U 2.5 log loss | 0.68640 | 0.68365 (paired -0.00275 [-0.00601, +0.00021]) | 0.67319 |
| Brier 1X2 | 0.5980 | 0.5913 | |
| ECE home / draw / away | 0.033 / 0.014 / 0.028 | 0.018 / 0.019 / 0.015 | |
| home / away level ratio (pooled) | 1.002 / 0.898 | 1.009 / 0.994 | |
| per league home ratio | | D1 1.005, E0 1.046, F1 0.991, I1 1.042, SP1 0.960 | |
| per league away ratio | | D1 0.969, E0 1.013, F1 1.003, I1 0.989, SP1 0.994 | |
| gap to market (1X2) | +0.0301 [0.0245, 0.0360] | +0.0204 [0.0153, 0.0252] | |
| hybrid weight (fit on prior seasons) | market 1.0 | market 1.0 | |
| >10 pt disagreement bucket: p_home - realised | +0.032 (n=648) | -0.056 (n=322) | |
| intercept LR >= 6.63 share of league-season fits | | 0.56 (25 fits) | |

Acceptance (pre-registered, all must hold):

| criterion | result |
|---|---|
| away level error <= 2 % (pooled) | PASS (0.6 %) |
| home level error <= 2 % (pooled) | PASS (0.9 %) |
| away level error <= 2 % in every league | **FAIL** (D1 -3.1 %) |
| home level error <= 2 % in every league | **FAIL** (E0 +4.6 %, I1 +4.2 %, SP1 -4.0 %) |
| home ECE <= 0.020 | PASS (0.018) |
| 1X2 log loss better than v1, CI upper < 0 | PASS |
| O/U 2.5 log loss better than v1, CI upper < 0 | **FAIL** (CI reaches +0.0002) |
| >10 pt disagreement bias <= 0.02 | **FAIL** (-0.056: where the model disagrees with the market by more than 10 points, the market is right) |
| intercept LR >= 6.63 in >= 90 % of fits | **FAIL** (56 %) |
| **all pass** | **NO** |

Reading, without softening: dc_laplace_v2 is a better model than v1 on every headline metric and it
removes the structural away-goal bias the audit identified. It still does not meet its own acceptance:
per-league goal levels drift by up to 4.6 % over a single season and a half (partly sampling noise at
n ~ 600-750 per league, but the criterion was written that way), totals improve without statistical
significance, and the disagreement bucket shows that a v2 disagreement with the market is a sign the
model is wrong, not the market. The hybrid weight of 1.0 on the market in every season says the same
thing the audit said: as a source of edge against a market, neither posterior carries information the
market lacks. **Production defaults stay `dc_laplace_v1` for the model** (the audit's rule: promote only
on acceptance); v2 remains runnable through `--model-version dc_laplace_v2` and is the base for
`xg_strength_v1` (docs/XG_DATA_AUDIT.md) and for any future re-registration.

## Engine reconciliation (`world_sim_benchmark.json`; 1,500 stratified matches, 200 worlds x 50 draws)

Absolute gaps of each engine's full-time probabilities to the exact per-world Dixon-Coles matrix,
same posterior and worlds:

| engine | draw gap mean / mean-abs / p95 | home gap mean / mean-abs | O/U 2.5 mean-abs | BTTS gap mean | E[goals] ratio home / away |
|---|---|---|---|---|---|
| world_sim_v1 (production minute engine), v1 posterior | +0.0109 / 0.0114 / 0.024 | -0.0065 / 0.0073 | 0.0067 | +0.0135 | 0.986 / 1.002 |
| world_sim_v2, v1 posterior | +0.0001 / 0.0035 / 0.009 | +0.0000 / 0.0037 | 0.0038 | +0.0001 | 1.000 / 1.000 |
| world_sim_v1, v2 posterior | +0.0090 / 0.0099 / 0.022 | -0.0052 / 0.0065 | 0.0069 | +0.0125 | 0.990 / 0.999 |
| world_sim_v2, v2 posterior | -0.0001 / 0.0033 / 0.008 | +0.0002 / 0.0036 | 0.0037 | -0.0001 | 1.000 / 1.000 |

Audit regression points (lambda/mu/rho -0.1): at 2.30/0.80 the production engine prices the draw at
0.174 against the analytic 0.191 (v2: 0.192); at 1.52/1.13, 0.256 vs 0.279 (v2: 0.279); at 1.00/1.90,
0.220 vs 0.242 (v2: 0.241). The minute engine's draw deficit of about 1-2 points and BTTS excess of
about 1.3 points are systematic (the audit's B2), not Monte Carlo noise; world_sim_v2 reconciles to
within its own Monte Carlo error (mean-abs 0.35 pt at 200 x 50; full-time families are priced
analytically in production, so the residual is zero there). world_sim_v2 meets its acceptance (honours
rho, mean-preserving, analytic full-time pricing, regression points within 0.1 pt); its adoption as the
production engine is an owner-visible switch (`--engine-version world_sim_v2`), independent of the
model decision above, and reversible by flag; records carry `engine_version` either way.
