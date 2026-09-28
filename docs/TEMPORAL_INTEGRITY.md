# Temporal integrity: the no-future-information guard

Status: implemented (pre-launch remediation, phase 5). Applies to production RUN SOCCER and to the
historical walk-forward research fits.

## Rule

No input used by a prediction may have `observed_at > decision_time`. Equality is allowed. The guard fails
closed: a violation raises `FutureInformationError` and the run (or the research fit) does not proceed.
Inputs whose observation time is unknown (`None`) are not the guard's business; the freshness gate rejects
them when they are too old.

## Where it runs

| input class | check | where |
|---|---|---|
| fixtures | `fixtures_observed_at ≤ as_of` | `run/pipeline.py::temporal_guard_for_inputs` |
| results (training data) | `results_observed_at ≤ as_of`; every model's `latest_result_date < as_of.date()`; the fitter refuses any row dated on/after `as_of` when called with `strict_point_in_time=True` (production `fit_competition`, research `wf_common`) | pipeline + `model/strength.py::DixonColesFitter.fit` + `research/dc_intercept.py` |
| market snapshots | `discovery.started_at`, `discovery.finished_at ≤ as_of` | pipeline |
| reference odds | `reference_observed_at ≤ as_of` | pipeline |
| lineups / weather / injuries / team & player stats | `observed_at ≤ as_of` for every context object that carries one (none is populated in production today; the guard is wired so that wiring them in cannot leak) | pipeline |
| model fit time | `fitted_at ≤ as_of` | pipeline |

The pipeline records the guard's report (`checked` counts per kind, latest observation per kind,
violations) under `freshness.temporal_guard` in `run_output.v1.json`, so a production run proves the guard
ran and found nothing.

## What it protects against

* A refit that accidentally includes a result dated on the decision day (`r.date < as_of` used to drop it
  silently; production now raises instead of relying on the filter).
* A cached HTTP response, lineup or weather row stamped after the decision time being used as a pregame
  input.
* Research leakage: the walk-forward loop hands the fitter only rows dated before the fit date, and the
  fitter now asserts it.

## Tests

`tests/test_temporal_guard.py`: unit tests (equality allowed, later rejected, naive timestamps rejected,
batch mode), hypothesis property tests (`raises ⇔ any observation after the decision time`, for every
guarded kind; date-granularity variant), fitter strict/lenient behaviour, `fit_competition` strictness.
`tests/test_run_pipeline.py`: a future `results_observed_at` or `fixtures_observed_at` aborts the run; the
guard report is present and clean on a normal run.
