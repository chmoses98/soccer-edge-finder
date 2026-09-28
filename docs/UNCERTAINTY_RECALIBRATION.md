# Uncertainty recalibration — `recalibration_v1` (2026-09-28)

Source of truth: `data/research/recalibration_v1.json`
(result hash `sha256:52b05ba227573ff248f8b2b111650180e036dfa19494cdb0c835eedcbf1b873d`, data content hash
`sha256:ef224cf2c252f07a842b3bcfd4ba5c718c25cedd8937ffa174a74b86b5ba4221`). Harness: `research/recalibration.py`.
Every number below is copied from that file; nothing here was tuned by hand. Baseline entry:
`config/frozen_baselines.json → baselines.recalibration_v1`.

## Question and sample

`walk_forward_v1` found that the DATA_ONLY 80% posterior interval on P(home) contains the de-vigged
Bet365 probability in 92.9% of matches (mean width 0.295). That *looks* over-dispersed, but the
market is not ground truth. This study asks the realised outcomes first and the market second, and
estimates corrections strictly walk-forward.

Same sample as `walk_forward_v1`: E0, SP1, D1, I1, F1; burn-in 2017-18; DATA_ONLY `dc_laplace_v1`
refit weekly, 100 posterior samples per match; 14,010 scored predictions (2018-19 .. 2025-26) of which
**12,248 aligned** (2019-20 .. 2025-26) are evaluated. The collector reproduces the frozen v1 interval
exactly (k = 1, posterior only: width 0.2945, market-inside 0.9285 — identical to `walk_forward_v1`).

Two knobs are studied:

* `k` — a multiplier on the posterior parameter **sd** (the Laplace covariance scaled by k²). Because
  log rates are linear in the parameters, `theta_mean + k (theta − theta_mean)` is applied *exactly*
  to cached posterior deviations; no refits per candidate.
* the worlds_v1 shared log-rate inflation (`sigma_model_log_rate` 0.05 ⊕ `sigma_environment` 0.03 =
  0.058 sd, common to both teams). Red-card and game-state draws of `worlds_v1` are not represented in
  this proxy (they barely touch P(home) pre-match).

A horizon-specific scale **cannot be studied historically**: the redistribution holds one pre-match
Bet365 snapshot per match and no time-to-kickoff or lineup information.

## Pre-stated decision rule (from the module docstring, written before any number was seen)

* **R1** Outcome-based evidence is primary: `k_hat` from the grouped goal-residual estimator (below),
  pooled over the scored seasons, cluster-bootstrap 95% CI over (league, season, team).
* **R2** A change from k = 1 is supported only if the CI excludes 1.0 **and** the per-season `k_hat`
  lies on the same side of 1.0 in ≥ 5 of the 7 aligned seasons.
* **R3** Prefer the global scale; a league- or region-specific scale is adopted only if its
  walk-forward out-of-sample grouped Gaussian log score beats the global candidate in ≥ 5/7 seasons
  and overall (paired bootstrap CI excluding 0).
* **R4** The shared world-layer inflation is judged by the totals PIT variance (nominal 1/12): a change
  is supported only if the current setting's PIT-variance z exceeds |2| and the alternative brings it
  inside |2|.
* **R5** The market-inside rate must move toward 80% under any adopted candidate (sanity) but is not
  targeted and cannot by itself justify a change.
* **R6** Guardrail: the adopted candidate must not worsen the overall 1X2 log loss by more than 0.001.

## Why outcomes alone cannot see the width per match — and what can

For one match, `E[(y − p̂)²] = p̂(1 − p̂)` under the model *whatever* the posterior width: a single
Bernoulli outcome cannot split the predictive variance into aleatoric and epistemic parts. PIT
histograms and log-loss dispersion are therefore reported but were expected (and turned out) to be
insensitive to k — they respond to *bias*, not width (see below).

The test with power is grouped: a team's parameter error is shared by its matches inside a short
window, so the model implies a specific covariance between the goal residuals of the same team.
With weekly refits the forecast for match *j* has usually already learned from match *i*, and under a
correctly calibrated Bayesian model sequential forecast errors are *uncorrelated* (innovation
whiteness); a too-wide posterior over-reacts (negative cross products), a too-narrow one under-reacts
(positive). The moment condition used is

    E[r_i r_j] = k² M_ij − 1{refit between i and j} · M_ij

where `M` is the delta-method covariance of the expected-goal rates under the posterior in force at
the group's first match (parameter error treated as persistent inside the window), so
`k² = (Σ r_i r_j + Σ_refit-pairs M_ij) / Σ M_ij`. Groups are (team, season, 28-day window) × {goals
for, goals against}; residuals `goals − posterior-mean rate` are de-meaned by the league-level mean
residual of *earlier* seasons. Aleatoric over-dispersion only enters the diagonal and drops out.
Approximations (documented in the JSON notes): plug-in rates, persistence inside the window, and the
Kalman-gain factor `rate/(M_ii + rate) ≈ 0.97` is omitted (it would lower `k_hat` by ≈ 0.01).
The unit tests recover k on synthetic groups with and without refits between matches.

## Results

### Outcome-based estimator (R1)

| quantity | value |
|---|---|
| groups (≥ 2 obs) | 15,968 (15,246) |
| Σ cross residual products | −2,672 |
| Σ model cross-cov, all pairs / refit-separated pairs | 10,557 / 9,665 (91.5% of pairs refit-separated) |
| **k_hat pooled (2018-19 .. 2025-26)** | **0.814**, 95% CI **0.728 – 0.889** |
| k_hat, aligned seasons only | 0.797 |
| k_hat, raw (not de-meaned) residuals | 0.861 |
| k_hat by window 14 / 28 / 56 days | 0.795 / 0.814 / 0.847 |
| φ (aleatoric dispersion vs Poisson) | 0.953 |

Reading: the model predicts `E[Σ r_i r_j] = k²·10,557 − 9,665`, i.e. **+892 at k = 1** (only the 8.5%
of pairs not separated by a refit keep their full cross-covariance). The observed sum is **−2,672**,
well below that, which gives `k² = (−2,672 + 9,665) / 10,557 = 0.662`, k = 0.81: the residual
correlation that survives the weekly refits is smaller than a k = 1 posterior implies. The direction
is consistent across sensitivity choices (0.80 – 0.86).

| season | k_hat (in-season) | | league | k_hat (CI) |
|---|---|---|---|---|
| 2018-19 (warm-up) | 0.937 | | D1 | 0.844 (0.64 – 1.02) |
| 2019-20 | 0.654 | | E0 | 0.824 (0.59 – 1.00) |
| 2020-21 | 0.963 | | F1 | 0.854 (0.65 – 1.04) |
| 2021-22 | 0.897 | | I1 | 0.941 (0.72 – 1.09) |
| 2022-23 | 1.037 | | SP1 | **0.535 (0.18 – 0.74)** |
| 2023-24 | 0.711 | | | |
| 2024-25 | 0.728 | | | |
| 2025-26 | 0.000 (clipped) | | | |

Six of seven aligned seasons sit below 1 (2022-23 is the exception); per-season estimates are noisy
(the in-season value for 2025-26 is negative and clipped to 0). SP1 is the one league whose posterior
is clearly too wide on its own; the other four are individually compatible with 1.

### Market reference (secondary, descriptive)

Standardised disagreement `z = (p_data − p_market) / sd_p` (k = 1, posterior only), aligned sample:
sd z **0.667**, RMS z 0.699, mean z **+0.211**, share |z| < 1.28 = 0.94, market-implied k = 0.687.

| league | market-implied k | sd z | mean z | outcome k_hat |
|---|---|---|---|---|
| D1 | 0.698 | 0.61 | +0.36 | 0.844 |
| E0 | 0.735 | 0.71 | +0.22 | 0.824 |
| F1 | 0.657 | 0.64 | +0.20 | 0.854 |
| I1 | 0.694 | 0.68 | +0.20 | 0.941 |
| SP1 | 0.648 | 0.65 | +0.10 | 0.535 |

| P(home) tercile | range | mean (data − market) | market-implied k | sd z |
|---|---|---|---|---|
| T1 | 0.06 – 0.39 | **+0.042** | 0.729 | 0.63 |
| T2 | 0.39 – 0.52 | +0.026 | 0.670 | 0.65 |
| T3 | 0.52 – 0.92 | +0.004 | 0.668 | 0.67 |

The market-implied scale (≈ 0.69) is below the outcome-based one (0.81) because the disagreement
mixes genuine parameter uncertainty with the systematic home over-rating already documented in
`RESEARCH_RESULTS.md` (mean z > 0 everywhere, largest for weak home sides). A scale factor cannot and
should not absorb bias; the tercile structure is a bias pattern, not a dispersion pattern.

### Per-match diagnostics along the k grid (aligned sample, worlds_v1 shared inflation on)

| k | width | market inside | sd z | log loss | Brier | PIT 1X2 var | PIT totals var (z) | LL z | group score (in-sample) |
|---|---|---|---|---|---|---|---|---|---|
| 0.3 | 0.092 | 0.431 | 2.05 | 0.99987 | 0.59710 | 0.0819 | 0.0827 (−0.9) | −1.0 | −2.1709 |
| 0.5 | 0.151 | 0.645 | 1.26 | 1.00001 | 0.59717 | 0.0818 | 0.0820 (−2.0) | −1.1 | −2.1691 |
| 0.6 | 0.180 | 0.731 | 1.06 | 1.00013 | 0.59723 | 0.0816 | 0.0815 (−2.8) | −1.2 | −2.1681 |
| 0.7 | 0.209 | 0.800 | 0.92 | 1.00028 | 0.59732 | 0.0815 | 0.0809 (−3.7) | −1.2 | −2.1675 |
| **0.8** | **0.238** | **0.856** | 0.81 | 1.00047 | 0.59742 | 0.0813 | 0.0802 (−4.7) | −1.3 | **−2.1672** |
| 0.9 | 0.267 | 0.899 | 0.73 | 1.00071 | 0.59755 | 0.0812 | 0.0794 (−5.9) | −1.4 | −2.1672 |
| **1.0 (current)** | **0.295** | **0.929** | 0.67 | 1.00100 | 0.59770 | 0.0810 | 0.0785 (−7.1) | −1.4 | −2.1676 |
| 1.2 | 0.351 | 0.967 | 0.57 | 1.00173 | 0.59809 | 0.0805 | 0.0766 (−10.1) | −1.5 | −2.1697 |
| 1.5 | 0.431 | 0.990 | 0.48 | 1.00327 | 0.59891 | 0.0799 | 0.0731 (−15.2) | −1.6 | −2.1764 |

(Full grid 0.3 – 1.5 in steps of 0.1, with and without the shared inflation, in the JSON.)

* **PIT (1X2, ordinal away < draw < home)**: variance 0.081 for every k; histogram tilted
  `[0.100, 0.108, 0.109, 0.107, 0.103, 0.105, 0.097, 0.087, 0.090, 0.093]` — too many away results
  relative to the predictive. This is the home-bias signature, and it is invisible to k, as predicted.
* **PIT (total goals)**: variance below 1/12 at every k (z −7.1 at k = 1, still −5.2 with no world
  inflation at k ≈ 0.89), histogram rising `[0.082 … 0.110, 0.106, 0.095]` — realised totals sit
  higher than predicted (O2.5 mean 0.504 vs 0.533 realised) and goals are slightly *under*-dispersed
  relative to Poisson (φ = 0.95). The totals predictive is over-dispersed for reasons unrelated to the
  posterior width, so R4 correctly refuses to attribute it to the world layer.
* **Log-loss dispersion**: realised loss is ~1.3 σ *below* what the predictive expects (z −1.0 … −1.6)
  for all k — again no k signal.
* **Log loss of the integrated predictive** falls monotonically as k shrinks, down to the grid edge
  (0.99987 at k = 0.3 vs 1.00100 at k = 1). This is a Jensen effect (integration over a wide posterior
  pulls probabilities toward the middle) and cannot identify k on its own; it is recorded as a
  supplementary, post-hoc diagnostic in the JSON, not used in the decision.
* The in-sample grouped score peaks at k ≈ 0.8 – 0.9, consistent with the estimator.

### Walk-forward candidates (fit on seasons < S, applied to S; aligned sample)

| candidate | mean k applied | width | market inside | sd z | log loss | Brier | ECE | PIT totals var (z) | OOS group score |
|---|---|---|---|---|---|---|---|---|---|
| current_worlds_v1 (k = 1 + inflation) | 1.000 | 0.295 | 0.929 | 0.67 | 1.00100 | 0.59770 | 0.033 | 0.0785 (−7.1) | −2.1690 |
| posterior_only_wf_v1 (k = 1, no inflation) | 1.000 | 0.294 | 0.928 | 0.67 | 1.00099 | 0.59769 | 0.033 | 0.0789 (−6.6) | −2.1690 |
| **global_outcome_k** | **0.885** | **0.263** | **0.892** | 0.74 | **1.00068** | 0.59753 | 0.032 | 0.0795 (−5.7) | **−2.1687** |
| league_outcome_k | 0.857 | 0.254 | 0.858 | 0.84 | 1.00051 | 0.59745 | 0.032 | 0.0795 (−5.7) | −2.1686 |
| global_market_k (market-referenced) | 0.725 | 0.216 | 0.815 | 0.89 | 1.00032 | 0.59734 | 0.031 | 0.0807 (−3.9) | −2.1686 |
| tercile_market_k (market-referenced) | 0.728 | 0.217 | 0.818 | 0.89 | 1.00035 | 0.59736 | 0.031 | 0.0807 (−4.0) | −2.1685 |
| fixed k = 0.6 (a-priori expectation, not walk-forward) | 0.600 | 0.180 | 0.731 | 1.06 | 1.00013 | 0.59723 | 0.030 | 0.0815 (−2.8) | −2.1691 |
| no_world_inflation_global_outcome_k | 0.885 | 0.262 | 0.892 | 0.75 | 1.00068 | 0.59752 | 0.032 | 0.0799 (−5.2) | −2.1687 |

| season | n | k fitted (outcome, prior seasons) | k fitted (market) | current width / inside | outcome-k width / inside | LL current / outcome-k | group score current / outcome-k |
|---|---|---|---|---|---|---|---|
| 2019-20 | 1,449 | 0.937 | 0.729 | 0.304 / 0.895 | 0.286 / 0.866 | 1.0016 / 1.0015 | −2.1061 / −2.1052 |
| 2020-21 | 2,013 | 0.819 | 0.745 | 0.293 / 0.902 | 0.242 / 0.822 | 1.0084 / 1.0081 | −2.2424 / −2.2455 |
| 2021-22 | 1,795 | 0.886 | 0.744 | 0.288 / 0.926 | 0.257 / 0.892 | 1.0057 / 1.0053 | −2.1875 / −2.1873 |
| 2022-23 | 1,796 | 0.889 | 0.731 | 0.296 / 0.939 | 0.265 / 0.913 | 0.9974 / 0.9971 | −2.2235 / −2.2245 |
| 2023-24 | 1,732 | 0.922 | 0.716 | 0.294 / 0.943 | 0.273 / 0.921 | 0.9894 / 0.9890 | −2.1469 / −2.1463 |
| 2024-25 | 1,731 | 0.892 | 0.708 | 0.295 / 0.953 | 0.265 / 0.925 | 0.9967 / 0.9964 | −2.1542 / −2.1528 |
| 2025-26 | 1,732 | 0.872 | 0.697 | 0.296 / 0.941 | 0.260 / 0.908 | 1.0068 / 1.0063 | −2.1117 / −2.1087 |

Paired out-of-sample grouped log score (per group, bootstrap 95% CI):

| comparison | mean diff | CI95 | seasons better |
|---|---|---|---|
| global_outcome_k − current | +0.00027 | [−0.00037, +0.00083] | 5 / 7 |
| league_outcome_k − global_outcome_k | +0.00008 | [−0.00097, +0.00110] | 4 / 7 |
| global_market_k − global_outcome_k | +0.00013 | [−0.00057, +0.00078] | 4 / 7 |
| fixed 0.6 − global_outcome_k | −0.00039 | [−0.00143, +0.00050] | 4 / 7 |

The Gaussian group score is a proper score for the variance but has little power at this sample
size: none of the paired differences is significant. The decision therefore rests on the estimator
(R1/R2), as pre-stated, with the score used only to rank structures (R3).

## Decision (rule applied mechanically; JSON `decision`)

| rule | outcome |
|---|---|
| R2: CI excludes 1 | yes (0.728 – 0.889) |
| R2: seasons on the same side | 6 / 7 |
| R3: league-specific beats global | no (4/7, CI includes 0) — region-specific only exists as a market-referenced variant and is not adopted |
| R4: world-layer inflation change | **not supported** (totals PIT z −7.1 → −5.2; the over-dispersion is not the inflation's doing) |
| R5: market-inside moves toward 0.8 | yes (0.929 → 0.892 walk-forward; 0.856 at the pooled k = 0.8) |
| R6: log-loss guardrail | passes (1.00100 → 1.00068, an improvement) |
| **chosen** | **`global_outcome_k`: a single global multiplier on the posterior sd** |

**Recommended value: `posterior_sd_scale = 0.8`** (pooled estimate 0.81; sensitivity range
0.80 – 0.86; walk-forward values applied to individual seasons 0.82 – 0.94). The a-priori expectation
of 0.5 – 0.7 stated in the task is **not** supported by the outcomes: k = 0.6 lies outside the CI and
would make the intervals too narrow for the persistence the goals actually show, even though it would
put the market-inside rate near 73%. Reaching "80% market-inside" is not an outcome-based target; the
gap that remains at k = 0.8 (85.6% inside, mean z +0.21) is mostly bias, which belongs to the
home-advantage / favourite-shrinkage workstream, not to the uncertainty layer.

Keep `sigma_model_log_rate = 0.05` and `sigma_environment = 0.03`: they change P(home) width by
< 0.001 and the totals evidence points elsewhere (Poisson dispersion, mean level).

## What a versioned `worlds_v2` would change (not implemented here)

1. `WorldConfig`: add `posterior_sd_scale: float = 0.8`, set `version = "worlds_v2"`; `worlds_v1`
   stays frozen with scale 1.0.
2. `WorldGenerator.generate`: replace `params = post.sample(n_worlds, rng)` by
   `params = post.mean + cfg.posterior_sd_scale * (post.sample(n_worlds, rng) − post.mean)`. The
   `ParameterPosterior` itself is untouched (it remains the evidence-based Laplace covariance); the
   scale is a *model-calibration* term of the world layer, which is where `docs/UNCERTAINTY_MODEL.md`
   already places specification error.
3. Expected effect at k = 0.8 (from the grid): P(home) 80% interval width 0.295 → 0.238,
   market-inside 0.929 → 0.856, 1X2 log loss 1.00100 → 1.00047, `P(edge > 0)` less timid (see
   `docs/PEDGE_CALIBRATION.md` for why that does not make it more useful against a sharp reference).
4. `world_hash` changes through `cfg.__dict__`, so archived records remain distinguishable; the
   `interval_calibration` health metric in `settle.py` keeps working unchanged.
5. Re-run `research/recalibration.py` after any strength-model change (home bias fix, promoted-team
   priors): the estimator is about the *posterior as fitted*, and a better-specified model may move
   `k_hat` back toward 1. SP1's own estimate (0.53) suggests looking at that league's fit before
   considering per-league scales.

## Runtime and reproducibility

`PYTHONPATH=src python research/recalibration.py` (defaults: `data/cache/Matches.csv`, 100 posterior
samples). Collection 468 s on an idle container (1,761 s in the frozen run, which shared the machine
with other jobs); analysis 357 s. Per-match posterior deviations are cached in
`data/cache/recalibration_cache_v1.npz` (+ `.pkl` with posteriors, both git-ignored) and reused by
`research/pedge_eval.py`; `--reuse-cache` skips the refits. Unit tests:
`pytest -q tests/test_research_recalibration.py`.
