# Research results — market_families_v1 (2026-09-28)

Source of truth: `data/research/market_families_v1.json` (result hash inside). Harness:
`research/market_families.py` on the shared walk-forward table (`research/wf_common.py`, same
protocol as `walk_forward_v1`: weekly point-in-time refit, 2019-20 → 2025-26, E0/SP1/D1/I1/F1,
100 posterior samples). Every family is priced from the **same posterior-averaged Dixon-Coles
score matrix per match**; the matrix reproduces the per-sample O/U 2.5 mean to 1e-6.

Market side: proportional de-vig of Bet365 pre-match odds (1X2, Over25/Under25,
HandiHome/HandiAway at HandiSize). Aligned samples are per family (matches with that family's
odds). Paired differences are model − market per match with a bootstrap 95% CI; positive = model
worse.

## Headline table

| family | aligned n | model LL | market LL | paired diff [CI] | model ECE | market ECE | seasons model better |
|---|---|---|---|---|---|---|---|
| 1X2 (3-way) | 12,248 | 1.0010 | **0.9732** | +0.0278 [0.0244, 0.0310] | 0.033 (home) | 0.016 | 0/7 |
| O/U 2.5 | 12,247 | 0.6850 | **0.6712** | +0.0139 [0.0116, 0.0165] | 0.034 | 0.013 | 0/7 |
| Asian handicap (home, stake-weighted) | 12,227 | 0.7154 | **0.6918** | +0.0235 [0.0196, 0.0275] | 0.082 | 0.011 | 0/7 |
| BTTS (no odds; vs prior-season base rate) | 12,248 | 0.6931 | 0.6886 (baseline) | +0.0045 [0.0015, 0.0073] | 0.053 | — | — |

The market wins every family with odds, in every league and every season. For BTTS the model is
**worse than a league base rate** taken from earlier seasons.

## 1X2 by league (model LL / market LL / diff)

E0 0.990/0.968/+0.022 · SP1 0.999/0.970/+0.029 · D1 1.010/0.978/+0.032 · I1 0.997/0.967/+0.030 ·
F1 1.013/0.986/+0.026. Model ECE: home 0.033, draw 0.013, away 0.030 (market 0.016/0.006/0.016).

## Over/under 2.5

Model mean 0.503 vs realised 0.533 (market 0.528): under-prediction of totals in every league,
worst in D1 (0.561 vs 0.612) and E0 (0.515 vs 0.553), smallest in SP1 (0.467 vs 0.468). Per
league the model loses by 0.010–0.019 log loss.

## Asian handicap

* 12,227 aligned matches with a Bet365 line; **52.6% are quarter lines** (stored rounded, e.g.
  −0.3 = −0.25; snapped to the nearest quarter). Line distribution in the JSON; the most common
  are −0.25 (1,993), 0 (1,468), −0.5 (1,399), +0.25 (1,320), −0.75 (1,142).
* Settlement: home goals + HandiSize; quarter lines split the stake over the two neighbouring
  lines; the model reports P(win)/P(push)/P(loss) for the home side and is scored on
  P(win | not pushed) against the decided stake fraction (86.0% of stake on average).
* **Push calibration is off**: model mean P(push) 0.122 vs realised pushed stake 0.141 (the
  model puts too little mass on exact-margin outcomes at the line).
* **Home cover**: model 0.524 conditional home-cover probability vs realised 0.488 vs market
  0.500 (mean overround 2.9%). The model over-rates the home side by 3.6 pts *after* the
  bookmaker's line has already removed the strength difference; that is the home tilt from the
  1X2 study appearing in a market whose line makes it explicit. The tilt is present in all five
  leagues (D1 worst: 0.548 vs 0.492 realised) and on every |line| bucket except ≥ 1.25.
* Log loss gap vs market by league: E0 +0.020, SP1 +0.020, F1 +0.023, I1 +0.026, D1 +0.031;
  quarter lines +0.026, whole/half lines +0.021.
* **Naive rule at quoted Bet365 prices** (informational; Bet365 is not Kalshi), bet when the
  model's conditional probability exceeds the implied probability + edge:

  | edge | home bets | home ROI | model-expected ROI | away bets | away ROI | both ROI |
  |---|---|---|---|---|---|---|
  | +3 pts | 5,075 | −6.0% | +16.8% | 2,767 | −1.5% | −4.4% |
  | +5 pts | 4,074 | −6.8% | +19.2% | 2,041 | −2.1% | −5.2% |
  | +10 pts | 2,068 | −5.9% | +25.6% | 860 | −4.1% | −5.4% |

  The model expects +17 to +26% and realises −4 to −7%: its "edges" are its own miscalibration.
  Away-side bets lose less than home-side bets, consistent with the direction of the tilt, but
  they still lose.

## BTTS and team totals (calibration only, no odds in the dataset)

| target | n | model LL | base-rate LL | model ECE | mean pred | realised |
|---|---|---|---|---|---|---|
| BTTS | 12,248 | 0.6931 | **0.6886** | 0.053 | 0.495 | 0.545 |
| home over 0.5 | 12,248 | **0.5110** | 0.5354 | 0.018 | 0.755 | 0.773 |
| home over 1.5 | 12,248 | **0.6482** | 0.6858 | 0.007 | 0.445 | 0.443 |
| home over 2.5 | 12,248 | **0.4698** | 0.5018 | 0.019 | 0.221 | 0.202 |
| away over 0.5 | 12,248 | **0.5880** | 0.6038 | 0.050 | 0.658 | **0.708** |
| away over 1.5 | 12,248 | **0.6246** | 0.6516 | 0.039 | 0.320 | **0.358** |
| away over 2.5 | 12,248 | **0.3763** | 0.4025 | 0.012 | 0.128 | 0.140 |

Home team totals are well calibrated (within 2 pts). **Away team totals are under-predicted by
4–5 pts on the 0.5 and 1.5 lines in every league**, which is why BTTS (needs the away side to
score) is under-predicted by 5 pts and loses to a base rate, and why O/U 2.5 is low. BTTS
reliability: predicted 0.37 → realised 0.48 (n 1,140); 0.46 → 0.52 (n 5,331); 0.54 → 0.58
(n 4,876).

## Interpretation

One defect explains every family: the model's away scoring rate is too low (aligned mean μ 1.127
vs 1.270 realised away goals; λ 1.524 vs 1.535 home goals). Its origin is structural, not a
tuning constant, and is documented with a candidate fix in `docs/RESEARCH_HOME_BIAS.md`
(`dc_laplace_v1.intercept`). Until that is fixed and re-run, no market family from this posterior
is fit for anything beyond reporting; all families stay `RESEARCH_ONLY` and
`config/authority.json` is unchanged.
