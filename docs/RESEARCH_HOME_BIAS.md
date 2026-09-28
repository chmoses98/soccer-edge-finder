# Research results — home_bias_v1 (2026-09-28)

Source of truth: `data/research/home_bias_v1.json` (result hash inside). Harness:
`research/home_bias.py` on the shared walk-forward table (`research/wf_common.py`), which
re-runs the `walk_forward_v1` protocol exactly (weekly point-in-time refit, burn-in 2017-18,
hybrid warm-up 2018-19, **12,248 aligned matches** 2019-20 → 2025-26, E0/SP1/D1/I1/F1, 100
posterior samples) and reproduces the frozen numbers (data 1.00099, market 0.97321, paired diff
+0.0278 [0.0244, 0.0310]; >10 pt bucket n 2,653, data 0.458 / realised 0.397 / market 0.396).

Alternative configurations are separately named candidates built with `dataclasses.replace`
(never by editing `StrengthConfig`); one candidate (`dc_laplace_v1.intercept*`) needs a new
parameter and lives in `research/dc_intercept.py`. `config/authority.json` is untouched.

## The question

When DATA_ONLY disagrees with the market by more than 10 points on P(home) it over-rates the
home side by 6 points. Why?

## The answer in one paragraph

The bias is not a subgroup effect and not a tuning constant. **The frozen fitter has no scoring
intercept**: `lam = exp(att_h − def_a + γ)`, `mu = exp(att_a − def_h)`, with a soft penalty
pinning mean attack and mean defence to zero. The away baseline is therefore stuck near exp(0)
whatever the league's real level, while γ (prior 0.25 ± 0.15) has to carry the *home scoring
level* rather than the home/away ratio. On the aligned sample the model's mean home rate is right
(λ 1.524 vs 1.535 goals) but its mean away rate is **11% low (μ 1.127 vs 1.270)** in every
league, so it gives +2.9 pts too much P(home), −1.9 pts P(away) and −3.0 pts P(over 2.5) on *all*
matches. The tilt is largest exactly where a strong away side should score a lot (away favourites
at P(fav) ≥ 0.7: model rate 2.13 vs 2.78 realised goals), which is why the > 10 pt disagreements
are 72% "data above market" and concentrated on away favourites. Adding a single intercept
(`dc_laplace_v1.intercept`) removes the bucket bias (+0.061 → +0.007) and the mean tilt; it does
not by itself close the log-loss gap to the market, which is a separate information problem
(decay too fast, shrinkage too strong: `dc_laplace_v1.intercept_decay003` is the best candidate,
−0.0087 log loss vs v1, still +0.019 behind the market, HYBRID weight still 1.00).

## Verdicts

| # | hypothesis | verdict | key evidence |
|---|---|---|---|
| H1 | γ too large / slow | **SUPPORTED as a symptom** | γ̂ 0.295 vs market-implied 0.216 vs realised log goal ratio 0.190 (40 league-seasons, 70% with γ̂ > market + 0.05). A tight prior (`gamma_sd005`) cuts bucket bias to +0.026 and gains −0.0016 LL; decay 0.003 gains −0.0068 but leaves the bias (+0.084). γ is large because it absorbs the missing intercept (H8). |
| H2 | league/season heterogeneity | **PARTIAL** | Bias > 0.03 in 4/5 leagues and 6/7 seasons, so it is broad; but it scales with the league's away scoring (D1 +0.111, SP1 +0.012, exactly as H8 predicts) and 2020-21 adds +0.059 (empty stadiums: realised log ratio 0.05 in E0, 0.01 in F1, γ̂ adapted only from 0.30 to 0.24). |
| H3 | promoted-team priors | **REJECTED** | Thin-history matches are 6.7% of the sample and 8.1% of the bucket (enrichment 1.21×, below the 1.5× rule); bias inside the bucket is the same with or without them (+0.057 vs +0.062). Prior-mean variants move LL by < 0.001. |
| H4 | shrinkage / away favourites | **SUPPORTED** | Bucket bias rises monotonically with market P(away): −0.145 (< 0.2), +0.048, +0.122, +0.150, +0.178, +0.150 (≥ 0.6). Data under-rates away favourites by −0.062/−0.118/−0.155/−0.195 at P(fav) < 0.5/0.5–0.6/0.6–0.7/≥ 0.7 (market −0.02 to −0.05). Same mechanism as H8 plus genuine over-shrinkage (`team_sd060`: −0.0028 LL, home ECE 0.025). |
| H5 | staleness | **PARTIAL** | Days since refit: no effect (3-way gap 0.0266 at 0 days vs 0.0282 at 5–6). Matchdays 1–5 are worse (gap 0.0395 vs 0.025 later; bucket bias +0.077 vs +0.047 late), an early-season thin-data effect, +0.014 excess over the baseline tilt. Not the cause. |
| H6 | selection / regression to the mean | **PARTIAL (market right, no structure)** | Data > market by > 10 pts (n 1,923): realised 0.282, market 0.297, data 0.434. Data < market (n 730): realised 0.697, market 0.656, data 0.521. Walk-forward logistic blend gives the data weight −0.15 to +0.05 and does not beat the market in either bucket (−0.0004 [−0.0018, +0.0010]). 72% of large disagreements are on the "data above market" side, so it is a tilt plus noise, not pure selection. |
| H7 | rest / schedule | **REJECTED** | The pre-stated rule fired only on the equal-rest bucket (bias +0.039 vs +0.029 baseline), i.e. on the global tilt; on excess bias over the baseline no rest-difference bucket (n ≥ 300) qualifies (range −0.014 to +0.039, no monotone pattern; the market's own deviations move with them). Domestic-only rest is a weak proxy. |
| H8 | structural: no intercept (added after H1–H7 ran) | **SUPPORTED** | μ under-predicts away goals by 0.143 per match in every league; intercept candidates set μ to 1.251 (κ̂ ≈ 0.17–0.18, γ̂ falls to 0.21 ≈ market-implied 0.216) and remove the bucket bias (+0.007 / +0.010 / −0.011). `intercept_sd060` and `intercept_decay003` beat v1 with CIs excluding 0. |

## H1 detail: fitted γ vs market-implied vs realised

Per league-season (all 40 in the JSON), the fitted γ averages 0.295 (sd ≈ 0.07 at each refit),
the market-implied mean log(λ/μ) — obtained by inverting the market 1X2 spread and O/U 2.5 into
Poisson rates per match, then averaging so team strengths cancel — is 0.216, and the realised
log(mean home goals / mean away goals) is 0.190. The gap is present in every league (D1 largest,
γ̂ 0.30–0.42 vs realised 0.08–0.34). Inside the "data above market" bucket the market's rates are
λ 1.25 / μ 1.62 against the model's 1.50 / 1.25: the disagreement is almost entirely about how
much the *away* side scores, not about home advantage per se.

Candidates (aligned n 12,248; positive = worse):

| candidate | 1X2 LL | vs market [CI] | vs v1 [CI] | O/U LL | home ECE | γ̂ | bucket n | data / realised / market | bias |
|---|---|---|---|---|---|---|---|---|---|
| dc_laplace_v1 (frozen) | 1.00099 | +0.0278 [0.0244, 0.0310] | — | 0.6850 | 0.033 | 0.295 | 2,653 | 0.458 / 0.397 / 0.396 | +0.062 |
| .decay003 | 0.99421 | +0.0210 | **−0.0068 [−0.0083, −0.0053]** | 0.6819 | 0.031 | 0.288 | 1,640 | 0.462 / 0.378 / 0.395 | +0.084 |
| .decay010 | 1.00752 | +0.0343 | +0.0065 | 0.6877 | 0.034 | 0.298 | 3,444 | 0.463 / 0.395 / 0.403 | +0.068 |
| .gamma_sd005 | 0.99943 | +0.0262 | −0.0016 [−0.0024, −0.0007] | 0.6858 | 0.029 | 0.266 | 2,382 | 0.456 / 0.430 / 0.420 | +0.026 |
| .gamma_sd050 | 1.00162 | +0.0284 | +0.0006 | 0.6851 | 0.035 | 0.306 | 2,836 | 0.460 / 0.376 / 0.386 | +0.084 |
| .newteam_mean000 | 1.00166 | +0.0284 | +0.0007 | 0.6854 | 0.032 | 0.296 | 2,698 | 0.457 / 0.389 / 0.393 | +0.067 |
| .newteam_mean-030 | 1.00065 | +0.0274 | −0.0003 [−0.0009, +0.0002] | 0.6850 | 0.033 | 0.293 | 2,680 | 0.462 / 0.403 / 0.399 | +0.058 |
| .team_sd060 | 0.99822 | +0.0250 | −0.0028 [−0.0042, −0.0013] | 0.6876 | 0.025 | 0.277 | 2,303 | 0.490 / 0.420 / 0.429 | +0.070 |
| .intercept | 0.99991 | +0.0267 | −0.0011 [−0.0024, +0.0004] | 0.6829 | 0.028 | 0.211 | 2,332 | 0.461 / 0.454 / 0.455 | **+0.007** |
| .intercept_sd060 | 0.99726 | +0.0240 | −0.0037 [−0.0055, −0.0019] | 0.6860 | **0.012** | 0.211 | 1,974 | 0.473 / 0.464 / 0.460 | +0.010 |
| .intercept_decay003 | **0.99231** | **+0.0191 [0.0164, 0.0216]** | **−0.0087 [−0.0104, −0.0069]** | **0.6797** | 0.021 | 0.207 | 1,398 | 0.470 / 0.481 / 0.476 | −0.011 |

The walk-forward HYBRID weight is 1.00 in every scored season for every candidate: none adds
information on top of the market.

## H2 detail

Bucket bias by league: D1 +0.111 (n 488), F1 +0.085, I1 +0.058, E0 +0.048, SP1 +0.012 (n 484).
The ordering follows realised away goals per game (D1 1.42, E0 1.32, I1 1.27, F1 1.26, SP1 1.11):
the closer a league's away scoring is to the fitter's implicit exp(0) baseline, the smaller the
tilt. By season: 2020-21 +0.109, 2023-24 +0.094, others +0.009 to +0.053. Note the provider
splits seasons at 1 July, so the COVID-delayed end of 2019-20 (June–July 2020, empty stadiums)
is labelled 2020-21; that season contains nearly all empty-stadium matches and ~45 rounds.

## H4 detail: favourite calibration (data P(fav) − realised; market in brackets)

| P(fav) bin | home favourite | away favourite |
|---|---|---|
| < 0.5 | +0.030 (0.000) | −0.062 (−0.019) |
| 0.5–0.6 | −0.005 (+0.003) | −0.118 (−0.025) |
| 0.6–0.7 | −0.083 (−0.043) | −0.155 (−0.034) |
| ≥ 0.7 | −0.049 (+0.008) | −0.195 (−0.048) |

With `intercept_sd060` the away-favourite errors shrink to −0.013 / −0.052 / −0.079 / −0.108 and
home favourites to +0.010 / −0.008 / −0.077 / −0.032 (JSON `H8 → favourite_calibration`): the
intercept removes the asymmetric part; the residual under-rating of *all* strong favourites is
shrinkage (prior sd 0.35 on attack/defence with a 107-day half-life leaves ~40 effective matches
per team). The Elo cross-check agrees: bucket bias +0.138 when the away side is ≥ 200 Elo
stronger, −0.117 when the home side is.

## H6 detail

Walk-forward recalibration (fitted on earlier seasons only): Platt slope on logit(P_data) is
1.18–1.22 every season, i.e. the model is *under-confident* overall while being *tilted* toward
home; a Platt-calibrated data model still over-rates the "data above market" bucket by +0.120.
The two-feature blend puts weight 0.98–1.19 on the market and −0.15 to +0.05 on the data. The
market's own error is small in both signed buckets (−0.015 and +0.041 realised − market on n
1,923 and 730). The market is simply right; the model's deviation carries no usable structure.

## What this means for the system

1. `data_only.dc_laplace_v1` has a structural specification defect (missing intercept). It stays
   `RESEARCH_ONLY`; nothing here touches `config/authority.json`.
2. The fix is a model change, not a prior tweak: a new versioned family (`dc_laplace_v2`) with a
   global scoring intercept, slower decay (0.003) and re-examined shrinkage, then a fresh
   `walk_forward_v2` run on the same aligned sample, judged against `walk_forward_v1` and the
   market. `research/dc_intercept.py` is the reference implementation of the intercept.
3. Even the best candidate here (`intercept_decay003`) is +0.019 log loss behind Bet365's
   pre-match price with a HYBRID weight of 1.00: fixing the bias makes the model *honest*, not
   *informative*. The production question remains Kalshi vs a sharp reference, not model vs
   Bet365.
4. Runtime: base table 170 s, each candidate 4–10 min under shared CPU (11 walk-forwards in
   total, cached under `data/cache/research/`), the three studies 79 s / 17 s / 12 s on the cache.
