# Research results — walk_forward_v1 (2026-09-27)

Source of truth: `data/research/walk_forward_v1.json` (result hash and data content hash inside).
Protocol: `docs/CALIBRATION.md#walk-forward-protocol`; harness `research/walk_forward.py`.
Data: club-football-match-data redistribution of football-data.co.uk, divisions E0/SP1/D1/I1/F1,
burn-in 2017-18, scored 2019-20 → 2025-26 (2018-19 is hybrid warm-up), **12,248 aligned matches**
(14,010 predictions before alignment). DATA_ONLY refit weekly, strictly point-in-time, integrated
over 100 posterior samples. MARKET_ONLY = proportional de-vig of **Bet365 pre-match** 1X2 (not
closing).

## Headline: the market wins, the data model adds nothing on top of it

| family | log loss (1X2) | Brier (3-way) | ECE P(home) |
|---|---|---|---|
| market_only.bet365_prematch_v1 | **0.9732** | **0.5786** | 0.016 |
| hybrid.logit_blend_v1 | 0.9732 | 0.5786 | 0.016 |
| data_only.dc_laplace_v1 | 1.0010 | 0.5977 | 0.033 |
| baseline.league_base_rates | 1.0748 | 0.6506 | 0.008 |
| baseline.home_advantage_only | 1.0749 | 0.6506 | 0.007 |

* Paired per-match log-loss difference DATA_ONLY − MARKET = **+0.0278**, bootstrap 95% CI
  **[0.0244, 0.0310]** (positive = worse than market). The gap is stable across all five leagues
  (0.022–0.030) and all seven seasons.
* **HYBRID weight fitted walk-forward = 1.00 in every season** (grid 0.00–1.00 step 0.05): the
  optimal logit blend uses the market only. DATA_ONLY carries no incremental information relative to
  a bookmaker's pre-match 1X2 in this specification.
* DATA_ONLY beats both naive baselines by ~0.074 log loss, so the model is not broken — it is
  simply a worse forecaster than a sharp bookmaker, as every sibling sport found.

## Disagreement: when the model and the market differ, the market is right

| |P(home) gap| > | n | data LL | market LL | realised home rate | data mean | market mean |
|---|---|---|---|---|---|---|
| 0.05 | 6,694 | 0.619 | 0.582 | 0.404 | 0.455 | 0.415 |
| 0.10 | 2,653 | 0.624 | 0.565 | 0.397 | 0.458 | 0.396 |
| 0.15 | 702 | 0.641 | 0.549 | 0.366 | 0.470 | 0.376 |

The model's disagreements are dominated by **over-rating home sides** (data mean 0.46–0.47 vs
realised 0.37–0.40). This points at the home-advantage term (a single decayed competition parameter
shrunk to a 0.25 prior) and at attack shrinkage for favourites. It is a concrete calibration target,
not a reason to tune blindly.

## Over/under 2.5 (n = 12,247)

| family | log loss | Brier | ECE | mean prediction | base rate |
|---|---|---|---|---|---|
| market_only (Bet365 O/U 2.5) | **0.6712** | **0.2392** | 0.013 | 0.528 | 0.533 |
| data_only (DC posterior) | 0.6850 | 0.2459 | 0.034 | 0.503 | 0.533 |

DATA_ONLY under-predicts totals by ~3 points on average (0.503 vs 0.533 realised): the Poisson
rates are slightly low, consistent with shrinkage toward zero on the log scale.

## Are the intervals honest? No — too wide

* 80% posterior interval on P(home): mean width **0.295**.
* Grouped realised rates fall inside the bin-average interval in 99.9% of weighted bins (a weak
  test, reported for completeness).
* Market-as-oracle check (JSON `interval_calibration_p_home`): the de-vigged market probability
  lies inside our 80% interval in **92.9%** of matches; mean |data − market| = **0.065**;
  |data − market| ≤ 0.05 / 0.10 / 0.15 in 45% / 78% / 94% of matches. Against a 0.29 mean width,
  the posterior + inflation is **over-dispersed**: `P(edge > 0)` computed from it is too
  conservative, not too bold. First calibration item on the roadmap (target: oracle-inside ≈ 80%).

## Naive betting sanity check (informational; Bet365 ≠ Kalshi)

Backing the home side at Bet365 prices whenever DATA_ONLY exceeded the implied probability by
>3/5/10 points: 4,791 / 3,609 / 1,390 bets, ROI **−14.1% / −14.5% / −12.1%**. Exactly what the
log-loss gap predicts; there is no hidden betting edge behind a worse forecaster.

## What this means for the system

1. Every family stays `RESEARCH_ONLY`. Nothing here supports real-money authority.
2. The production question that *could* hold an edge is not "model vs Bet365" but "Kalshi's thin
   soccer book vs a sharp reference + a calibrated model" — hence roadmap item 3 (ingest
   football-data.co.uk `fixtures.csv` reference odds at capture time and evaluate Kalshi mid vs
   reference vs DATA_ONLY prospectively).
3. The uncertainty layer needs calibration before `P(edge>0)` is used for anything but reporting.
4. Negative results are recorded as the baseline (`config/frozen_baselines.json`); any model change
   must beat `walk_forward_v1` on the same aligned sample with a new versioned run.

## Phase 2 studies (2026-09-28) — pointers

The v1 numbers above stay frozen. Seven follow-up studies re-implement the same protocol
(`research/wf_common.py` reproduces n = 12,248, data 1.00099 / market 0.97321 exactly) and are documented in:

| study | doc | result file | one-line outcome |
|---|---|---|---|
| home bias | `docs/RESEARCH_HOME_BIAS.md` | `data/research/home_bias_v1.json` | structural: missing scoring intercept → away goals under-predicted ~11%; `dc_laplace_v2` candidate, still behind market |
| disagreement | `docs/RESEARCH_DISAGREEMENT.md` | `data/research/disagreement_v1.json` | no informative subgroup (0/116 cells) |
| market families | `docs/RESEARCH_MARKET_FAMILIES.md` | `data/research/market_families_v1.json` | market wins every family/league/season |
| uncertainty recalibration | `docs/UNCERTAINTY_RECALIBRATION.md` | `data/research/recalibration_v1.json` | k̂ = 0.81 [0.73, 0.89] → `posterior_sd_scale = 0.8` for a versioned `worlds_v2` |
| P(edge>0) | `docs/PEDGE_CALIBRATION.md` | `data/research/pedge_proxy_v1.json` | not predictive of realised return; rename in a versioned `edge_v2` |
| multi-league | `docs/MULTI_LEAGUE_MODEL.md` | `data/research/multi_league_v1.json` | −0.002 LL vs v1, +0.026 vs market; ≈ Elo on UEFA |
| context features | `docs/RESEARCH_CONTEXT_FEATURES.md` | `data/research/context_features_v1.json` | rest: nothing; congestion ≈ −0.001 LL; context-only |

Net: no retrospective evidence of information beyond a sharp bookmaker; what changed is that the model's
defects are now named (intercept, width, statistic semantics) and every future change is a new version with a
frozen comparison. Prospective evidence against Kalshi prices is the only remaining route (`docs/CALIBRATION.md`).


## move_v1 — open-to-close movement (remediation phase 11)

Protocol and code: `research/move_v1.py`; runner-side workflow `research-move.yml` (football-data.co.uk
direct CSVs are reachable only from Actions). Result file: `data/research/move_v1.json` (committed by the
workflow). Decision rule pre-registered in the module docstring: β lower bound > 0 pooled, β > 0 in ≥ 5/7
seasons, directional accuracy lower bound > 0.5 — otherwise a preserved negative result.

**Result (2026-09-28): NEGATIVE.** 1X2 β = −0.006 [−0.013, +0.002], directional accuracy 0.476 (below
chance); O/U 2.5 β = −0.015 [−0.024, −0.006]; every league, season and magnitude bucket ≈ 0 or negative.
DATA_ONLY v1 has no information about sharp movement. See `docs/RESEARCH_MOVE.md`.

## Lineup oracle (phase 19) and xG history (phase 20)

Result files `data/research/lineup_oracle_v1.json` and `data/research/xg_history_v1.json` are produced by
`lineup-backfill.yml` and `research-xg.yml` (both need network reachability the development container does
not have). Their status at handoff is recorded in docs/HANDOFF.md; until the files exist both studies are
`NOT_EVALUATED`.

## intl_hier_v1 one-time holdout (phase 17)

`data/research/intl_hier_selection.json` / `intl_hier_holdout.json`; full write-up in
docs/INTERNATIONAL_MODEL.md. Holdout 2022-2026 (n=4,563): log loss 0.8671 vs pool 0.9716 vs Elo 0.8739;
paired CIs below zero against both; 3 of 8 pre-registered criteria FAIL (friendlies vs Elo, per-match
heavy-favourite pricing at Elo gap >= 400, neutral-site goal calibration) -> not promoted, shadows gated.

## Structural model error per family (phase 15)

`data/research/sigma_struct_v1.json` (docs/UNCERTAINTY_MODEL.md): walk-forward sd of logit(model) -
logit(Bet365 de-vigged) is ~0.33 (1X2, home/away 0.37, draw 0.18) and ~0.27 (O/U 2.5) in logit units,
~0.065 probability points, nearly identical across dc_laplace_v1 and v2 variants. Used only by edge_v2,
where the model weight is 0 today.

## Lineup oracle result (phase 19)

STOP under the pre-registered rule: perfect-XI 1X2 gain -0.0009 [-0.0048, +0.0035] on 1,061 matches
(O/U 2.5 -0.0046 [-0.0081, -0.0008]); four of five leagues chose no adjustment. docs/LINEUPS.md.

## xg_strength_v1 one-time holdout (phase 20)

PASS: paired 1X2 log-loss gain +0.0061 [0.0041, 0.0082] over the goal-only dc_laplace_v2 fit on the
2021-22..2022-23 holdout (n = 3,638), omega = 0.75 chosen on 2017-18..2020-21; O/U 2.5 +0.0046. Stays
RESEARCH_ONLY (historical xG source retired; prospective feed unverified). docs/XG_DATA_AUDIT.md.

## dc_laplace_v2 selection + one-time holdout + engine reconciliation (phases 12-14)

Chosen d0030_s060 on 2019-24; holdout 2024-26 (n = 3,463): 1X2 log loss 0.99203 vs v1 1.00179 (paired
-0.0098 [-0.0141, -0.0056]), away level ratio 0.994 vs 0.898, home ECE 0.018 vs 0.033, but 4 of 9
pre-registered criteria FAIL (per-league levels, O/U significance, >10 pt disagreement bias -0.056,
intercept LR share 0.56) -> model default stays v1. world_sim_v1 shows systematic draw (-1.1 pt) and
BTTS (+1.3 pt) gaps to the exact matrix; world_sim_v2 reconciles within Monte Carlo error.
docs/RESEARCH_DC_V2.md.
