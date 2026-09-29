# Uncertainty model

## Three kinds, kept distinct

| Kind | Where it lives | How it enters the contract probability |
|---|---|---|
| **Aleatoric** (match randomness) | `sim/engine.py`: Poisson goal arrivals per minute, red-card Bernoullis, shoot-outs | integrated by the `draws_per_world` realisations *within* each world; produces `p_w` |
| **Parameter** (what we do not know about the teams/context) | `model/worlds.py`: posterior draws of attack/defence/home advantage/rho; lineup availability draws; competition environment; red-card hazard | integrated *across* worlds; `fair = mean_w p_w`; interval = quantiles of `p_w` |
| **Model** (specification error) | `WorldConfig.sigma_model_log_rate` inflation on log rates; game-state multipliers drawn with sd; family mixing at the family layer | widens the spread of `p_w` beyond the posterior alone |

`P(edge > 0)` and the worst-case edge are computed on the same `p_w` distribution that prices the
contract, so uncertainty is not a decoration added afterwards.

## Where the widths come from (evidence status)

| Input | Representation | Source of the width | Status |
|---|---|---|---|
| Team attack / defence | Gaussian posterior (Laplace at the MAP) | inverse observed information of the time-decayed Dixon-Coles likelihood + per-team prior | evidence-based; widens for thin history automatically |
| Promoted / new teams | prior mean −0.15 (attack, defence), prior sd 0.45 vs 0.35 | configured defaults; **to be estimated** from promoted-team seasons in the historical set (roadmap) | configured |
| Home advantage | posterior over γ (prior N(0.25, 0.15²)) | data | evidence-based |
| Dixon-Coles ρ | posterior (prior sd 0.08) | data | evidence-based |
| Lineup availability | per-player P(play), importance share, goal share; `CONFIRMED` collapses P(play) to 0/1 | no provider yet → production uses `lineup_state=unknown` and no players | scaffold, tested |
| Competition environment | log-normal sd 0.03 | configured | configured; calibration research will tune |
| Red cards | Gamma around 0.12/team/match (shape 20) | literature/top-league base rate | configured |
| Game-state behaviour | trailing ×1.08, leading ×0.93, sd 0.04 | Dixon & Robinson-style effects | configured, unvalidated |
| Model inflation | log-normal sd 0.05 on rates | placeholder | **must be calibrated** by interval-coverage research |
| Weather, referee, travel, tactics, goalkeeper | not modelled | — | listed in `WorldSet.components["not_modelled"]` |

## Correlated worlds

Dependencies are explicit in `WorldGenerator.generate`:

* absent player → team attack multiplier ↓ → goal shares renormalised over players on the pitch
  (so an absent striker cannot score and his share moves to teammates);
* environment and model inflation draws are shared by both teams (a high-scoring world is
  high-scoring for both);
* red-card hazard is per team per world; its *effect* on both teams' rates is applied inside the
  match engine as the state evolves;
* game-state multipliers are per world, so "this is a world where teams protect leads" is coherent
  across the whole match.

Not yet represented: formation state, opponent adaptation to a missing star, congestion-driven
rotation, and the joint distribution across *different fixtures* (worlds are independent across
fixtures today, so cross-fixture portfolio correlation is zero by construction).

## Calibrating the uncertainty itself

`evaluation.metrics.interval_calibration` groups predictions by probability bin and asks whether
the realised frequency falls inside the average interval. The walk-forward research reports the
80% interval coverage for P(home) (`data/research/walk_forward_v1.json →
interval_calibration_p_home`). The promotion rules in `authority/policy.py` require the 80%
interval coverage to sit in [0.70, 0.90] for LIMITED and [0.75, 0.85] for TRUSTED.

## worlds_v2 (remediation phase 15; audit section F)

`worlds_v1` stays frozen (k = 1, hand-set inflation sd 0.05, environment sd 0.03); archived records made
with it remain reproducible. `worlds_v2` (`model/worlds.py::worlds_v2_config`, `soccer run
--worlds-version worlds_v2`) decomposes the three things v1 mixed:

| term | worlds_v1 | worlds_v2 |
|---|---|---|
| parameter uncertainty | raw Laplace posterior (k = 1) | Laplace x `posterior_sd_scale` (k re-estimated on `dc_laplace_v2` by `research/recalibration.py --model-version dc_laplace_v2`; adopted only when the audit's F4 rule passes, else 1.0; `WORLDS_V2_K_STATUS` says which) |
| Monte Carlo noise in the interval | binomial (draws per world) | none for full-time families under `world_sim_v2` (exact per-world probability from the DC matrix) |
| hand-set model inflation | log-normal sd 0.05 on rates | removed |
| structural model error | (inside the inflation term) | separate per-family term `sigma_struct(family)` used only by edge_v2 (`research/sigma_struct.py`, `data/research/sigma_struct_v1.json`) |
| environment jitter | sd 0.03 | sd 0.03 (unchanged) |

The scale is a property of the world layer: `params = mean + k * (sample - mean)`, and because log
rates are linear in the parameters this scales the sd of every log rate by exactly k
(`tests/test_uncertainty_v2.py`). The world components (and therefore the archived `world_hash` and the
record's `worlds_version`) carry the version and the scale.

### Structural term (walk-forward, Bet365 de-vigged reference; retail, hence an upper bound)

sd of `logit(p_model) - logit(p_reference)` over 14,009 scored walk-forward predictions (top-5 leagues,
2019-20 to 2025-26), pooled; the per-family point value edge_v2 consumes is the season-maximum logit sd
converted at the pooled points-per-logit ratio (the conservative end):

| variant | 1X2 sd logit (pooled / season max) | 1X2 sd points | O/U 2.5 sd logit | O/U 2.5 sd points | edge_v2 points (1X2 / O/U) |
|---|---|---|---|---|---|
| dc_laplace_v1 | 0.330 / 0.375 | 0.066 | 0.273 | 0.066 | 0.075 / 0.068 |
| dc_laplace_v1.intercept | 0.326 / 0.374 | 0.063 | 0.268 | 0.064 | 0.072 / 0.067 |
| dc_laplace_v2 d0065 s035 | 0.326 / 0.375 | 0.063 | 0.268 | 0.064 | 0.072 / 0.067 |
| dc_laplace_v2 d0065 s050 | 0.308 / 0.352 | 0.061 | 0.301 | 0.071 | 0.069 / 0.073 |

Draw sides disperse far less (sd logit 0.18) than home/away (0.37). The figures are what a model-weighted
`p*` would have to carry as sigma_struct; today `w_family = 0` for every family (audit section G), so
`p* = p_reference` and the term changes no selection. Families without a historical reference (2-way
winner, DNB, handicaps, BTTS, exact score, halves, player markets) are NOT_ESTIMATED and keep edge_v2's
default. A sharp reference would lower these numbers; a retail one cannot raise the true value above them.

### Coverage report (F4 acceptance in production)

`soccer uncertainty report --settlements-dir <archive>/settlements` (run by `settle-evaluate.yml`,
published as `evaluation/uncertainty_coverage.v1.json`) reports per cell (model family x worlds version x
market family x horizon) the grouped-estimator coverage of the 80 % interval against outcomes, the
interval's mean width and, as a sanity diagnostic only, the share of entry Kalshi mids inside the
interval. Verdicts: WITHIN_BAND [0.70, 0.90] / OUTSIDE_BAND / INSUFFICIENT (< 30 settled). The promotion
evaluator applies the same estimator as a gate; this report only makes it visible per worlds version.
