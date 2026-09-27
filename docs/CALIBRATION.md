# Calibration and evaluation

## Metrics (`evaluation/metrics.py`)

Brier, log loss (binary and multiclass), reliability bins, expected calibration error (ECE),
sharpness, interval coverage / interval calibration, CLV in probability points
(`POSITIVE_IS_GOOD`: YES → close − entry; NO → entry − close, both in YES units), fee-adjusted
realised EV, bootstrap CIs on paired differences.

## Slices required before any authority change

probability bucket · market family · competition · horizon · lineup-confirmed vs not ·
favourite/underdog · totals region · home/away · model family · season.

## Walk-forward protocol (`research/walk_forward.py`, pre-registered as `walk_forward_v1`)

* Chronological only; DATA_ONLY refit weekly on matches strictly before the date.
* MARKET_ONLY = proportional de-vig of Bet365 *pre-match* 1X2 (closing lines are not in the
  GitHub redistribution; the runner can fetch them from football-data.co.uk — roadmap).
* HYBRID = logit blend with a weight fitted only on earlier seasons' predictions.
* Baselines: prior-season base rates; home-advantage-only Poisson.
* Aligned sample = matches with all five predictions; first scored season is hybrid warm-up and
  excluded from the aligned comparison.
* Reported: overall / by league / by season log loss, Brier, ECE(home); O/U 2.5 for DATA vs
  MARKET; disagreement analysis (>5/10/15 pts on P(home)); 80% interval calibration of P(home);
  paired log-loss differences vs market with bootstrap 95% CI; naive betting at Bet365 prices as a
  sanity check (informational — Bet365 is not Kalshi).
* Outputs: `data/research/walk_forward_v1.json` with a result hash and the data content hash.

Results and their interpretation are in `docs/RESEARCH_RESULTS.md` (written from the frozen JSON;
never edited by hand without re-running).

## Calibrating uncertainty itself

`interval_calibration(p, lo, hi, y, level)` groups by predicted probability and checks whether
the realised rate falls inside the bin's average interval. Coverage far below the nominal level
means intervals are too narrow (raise `sigma_model_log_rate` or widen priors); far above means
too wide (over-hedged P(edge>0)). The same machinery will be applied to `P(edge>0)` once settled
prospective contracts exist: among contracts with P(edge>0)=0.8, roughly 80% should realise a
positive fee-adjusted return in expectation.

## Prospective evaluation (what runs automatically once data accrues)

`soccer settle` (roadmap workflow `settle-evaluate.yml`) joins archived prediction records with
official results (openfootball) and captured close quotes, settles each contract with
`settlement/engine.py`, and emits `ModelHealthV1` rows per (model family × market family ×
horizon). Promotion proposals come from `authority.recommend_state`; a human applies them via
`config/authority.json` in a reviewed PR.
