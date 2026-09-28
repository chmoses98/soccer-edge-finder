# Rest, congestion and calendar features — `context_features_v1` (Phase 14)

Source of truth: `data/research/context_features_v1.json` (result hash
`sha256:b148f22983794dc95ccf9857af6e4811beed856c18a0b14473f267a8413f5cb6`). Harness: `research/context_features.py`,
run on the per-match predictions of `multi_league_v1` (`data/research/multi_league_v1_predictions.csv`, domestic
aligned sample E0/SP1/D1/I1/F1, n = 12,338, seasons scored walk-forward 2020-21 → 2026-27).

## Question

Do rest days, fixture congestion or calendar position carry information about the 1X2 outcome **beyond** what
(a) the market, (b) the frozen `dc_laplace_v1` posterior, (c) the multi-league posterior already encode?

## Features (point-in-time, domestic league matches only)

| block | features |
|---|---|
| rest | days since each team's previous match, home − away difference |
| congestion | matches in the trailing 7 / 14 / 28 days per team, home − away differences |
| calendar | first-five-matchday flag per team, first match after a ≥ 21-day league break |

Cups and UEFA matches are absent from the historical CSV, so rest is an upper bound and congestion a lower
bound (the production `run/context_features.py` uses every competition with results and does not share this
limitation).

## Method

For each reference forecast, a multinomial logistic regression on the reference's own logits **plus one
feature block** is fitted on prior seasons only and scored on the next season (walk-forward). The comparison
that matters is against the *recalibrated* reference (logits alone, refitted the same way), so a gain cannot come
from merely re-scaling an over- or under-confident forecast. Paired bootstrap 95% CIs on the log-loss difference.

## Results (log-loss change; negative = features help)

| reference | block | vs recalibrated reference [95% CI] | vs raw reference [95% CI] |
|---|---|---|---|
| market (Bet365 de-vigged) | rest | +0.00000 [−0.0005, +0.0005] | −0.0001 [−0.0013, +0.0010] |
| market | congestion | −0.0011 [−0.0021, −0.0001] | −0.0012 [−0.0026, +0.0001] |
| market | calendar | −0.0002 [−0.0008, +0.0004] | −0.0003 [−0.0015, +0.0008] |
| market | all | −0.0020 [−0.0032, −0.0008] | −0.0021 [−0.0036, −0.0006] |
| `dc_laplace_v1` | rest | 0.0000 [−0.0006, +0.0005] | (recalibration alone −0.0040) |
| `dc_laplace_v1` | congestion | −0.0015 [−0.0025, −0.0004] | |
| `dc_laplace_v1` | all | −0.0021 [−0.0034, −0.0008] | |
| `multi_league_v1` | rest | 0.0000 [−0.0005, +0.0005] | |
| `multi_league_v1` | congestion | −0.0011 [−0.0021, −0.0002] | |
| `multi_league_v1` | all | −0.0019 [−0.0031, −0.0007] | |

Rest-difference buckets show no monotone market residual (realised − market P(home): −0.017 at equal rest,
+0.027 for the 381 matches where the home side had ≥ 3 days less rest, +0.009 / −0.007 / −0.002 elsewhere).

## Reading

* **Rest days carry no residual information** against any reference; the apparent gain "vs raw" for the model
  references is entirely the logit recalibration (slope/intercept), which is the home-bias finding again.
* **Congestion** (7/14/28-day match counts) carries a statistically detectable but practically negligible
  signal: ≈ −0.001 log loss, about 4% of the model-vs-market gap, and it is the same size on top of the market,
  i.e. the market does not fully price it either — at ~0.1% of log loss it cannot move a selection.
* Calendar flags add nothing once congestion is in.
* Nothing here changes pricing. Rest and congestion stay **context fields** on every record
  (`run/context_features.py`) so the prospective ledger can re-test them on Kalshi prices; a future `dc_laplace_v2`
  may carry congestion as a covariate only if the prospective test agrees.

Status: RESEARCH_ONLY. `config/authority.json` untouched.
