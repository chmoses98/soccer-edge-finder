# `P(edge > 0)` — what it measures, how it will be evaluated, and the historical proxy (`pedge_proxy_v1`)

Source of truth: `data/research/pedge_proxy_v1.json` (result hash inside; it records the
`recalibration_v1` result hash it was built on). Code: `research/pedge_eval.py`. Baseline entry:
`config/frozen_baselines.json → baselines.pedge_proxy_v1`. Numbers below are copied from the JSON.

## What the field is

`pricing/edge.py` computes, for a contract side, `p_edge_positive = mean_w[ p_w > breakeven ]`: the
share of the model's own posterior worlds in which the model's probability clears price + fee. The
pipeline archives it as `probability_edge_positive` and prints it as `P(edge>0)=NN%`.

Three things it is **not**:

1. Not the probability that the contract wins (that is `fair_probability`).
2. Not the probability that the bet is +EV against the truth. It has no term for the model's
   systematic error relative to a sharper reference; it only says how far the model's own centre is
   from the price, measured in units of the model's own dispersion.
3. Not something the outcome data can "calibrate" in the reliability-diagram sense. The sentence in
   `docs/CALIBRATION.md` ("among contracts with P(edge>0)=0.8, roughly 80% should realise a positive
   fee-adjusted return in expectation") mixes two quantities: a contract with 20% fair probability
   and 95% P(edge>0) is expected to *lose* 80% of the time. What can be tested is whether higher
   buckets have higher **mean** realised return (and whether the claimed fee-adjusted edge is
   realised on average), which is what the tooling below does.

It also inherits the posterior width: a too-wide posterior makes it timid, a too-narrow one bold.
`docs/UNCERTAINTY_RECALIBRATION.md` found the posterior sd should be scaled by ≈ 0.8; the proxy below
shows what that does to the buckets.

## Evaluation infrastructure (`research/pedge_eval.py`)

Pure functions (unit-tested in `tests/test_research_recalibration.py`):

* `quadratic_fee(price)`, `breakeven(price)` — 7% quadratic taker fee, multiplier 1.
* `p_edge_positive(draws, breakeven)` — exactly the `edge.py` statistic from per-world probabilities.
* `bin_index(p)` with buckets `<0.6, 0.6-0.7, 0.7-0.8, 0.8-0.9, 0.9-0.95, >=0.95`.
* `rows_from_records(predictions, settlements)` — flattens archived `prediction_record_v1` rows
  (`edge.yes` / `edge.no` from `EdgeAssessment.to_json`) joined to `settlement_record_v1` by
  `prediction_record_id`: realised fee-adjusted return `won − price − fee_per_contract`, CLV in the
  side's units (`clv_yes_points`, sign flipped for NO), and "beats reference" when a
  `reference_probability` is present on the record (or its recommendation).
* `bucket_table(rows)` — per bucket: n, mean P(edge>0), mean claimed fee-adjusted edge, n settled,
  mean realised return (+ SE), hit rate, mean CLV, share beating the reference.
* `monotonicity(table)` — Spearman rank correlation between bucket order and a bucket statistic.

CLI:

    PYTHONPATH=src python research/pedge_eval.py records --predictions <predictions.jsonl ...> \
        --settlements <settlements.jsonl ...> [--out report.json]
    PYTHONPATH=src python research/pedge_eval.py proxy          # historical study below

The `records` path is what the prospective loop should run once `soccer settle` has produced
settlements; it needs no model code.

## Historical proxy study

Market = de-vigged Bet365 pre-match 1X2 (the same 12,248 aligned matches as `walk_forward_v1`);
price = market probability; fee = 0.07·p(1−p); candidates = every (match, side) = 36,744 rows.
DATA_ONLY posterior draws come from the `recalibration_v1` cache (100 draws per match). Two realised
returns are reported: at the fee-adjusted de-vigged price (the Kalshi-like analogue) and at the actual
Bet365 decimal odds (vig included). Bet365 is a sharp book, so both are expected to be negative
overall — the only question is whether higher buckets are *relatively* better.

### Current configuration (`worlds_v1`: k = 1 + shared inflation)

| P(edge>0) bucket | n | mean P(edge>0) | claimed fee-adj edge | realised (de-vig + fee) ± SE | realised at Bet365 odds | hit rate | mean price |
|---|---|---|---|---|---|---|---|
| <0.6 | 27,521 | 0.32 | −0.040 | −0.007 ± 0.003 | −0.034 | 0.363 | 0.356 |
| 0.6–0.7 | 3,765 | 0.64 | +0.038 | −0.029 ± 0.007 | −0.103 | 0.273 | 0.289 |
| 0.7–0.8 | 2,887 | 0.74 | +0.065 | −0.040 ± 0.008 | −0.160 | 0.242 | 0.270 |
| 0.8–0.9 | 1,803 | 0.84 | +0.094 | −0.038 ± 0.009 | −0.157 | 0.207 | 0.234 |
| 0.9–0.95 | 546 | 0.92 | +0.124 | −0.027 ± 0.016 | −0.131 | 0.189 | 0.205 |
| ≥0.95 | 222 | 0.97 | +0.161 | −0.013 ± 0.027 | −0.017 | 0.189 | 0.192 |

Spearman(bucket, realised de-vig return) = **−0.03**; (bucket, Bet365 return) = +0.09;
(bucket, hit rate) = **−0.94**.

`edge_v1` selection proxy (fee-adjusted edge ≥ 0.02, P(edge>0) ≥ 0.80, 20th-percentile world > 0):
2,529 candidates (6.9%), claimed edge **+10.7%**, realised **−3.3%** at de-vig + fee, **−13.6%** at
Bet365 odds, hit rate 20% (1,485 home / 545 draw / 499 away).

### With the recalibrated posterior (`global_outcome_k` walk-forward, mean k = 0.885)

| P(edge>0) bucket | n | claimed fee-adj edge | realised (de-vig + fee) ± SE | realised at Bet365 odds | hit rate |
|---|---|---|---|---|---|
| <0.6 | 26,882 | −0.042 | −0.006 ± 0.003 | −0.033 | 0.365 |
| 0.6–0.7 | 3,602 | +0.034 | −0.030 ± 0.007 | −0.106 | 0.277 |
| 0.7–0.8 | 2,960 | +0.058 | −0.033 ± 0.008 | −0.109 | 0.253 |
| 0.8–0.9 | 2,098 | +0.085 | −0.043 ± 0.009 | −0.206 | 0.214 |
| 0.9–0.95 | 720 | +0.111 | −0.035 ± 0.014 | −0.133 | 0.189 |
| ≥0.95 | 482 | +0.143 | −0.019 ± 0.018 | −0.056 | 0.191 |

Spearman(bucket, realised) = −0.37; selection proxy 3,246 candidates (8.8%), claimed +9.9%, realised
−3.9% / −17.6%, hit 20%. The posterior-only configuration (no shared inflation) is within noise of the
current one (JSON `configs.posterior_only`).

### What the proxy says

* **Higher P(edge>0) does not mean higher realised return.** Every bucket above 0.6 loses 2–4 cents
  per contract at fee-adjusted fair prices and 10–20% at Bet365 odds; the ranking across buckets is
  flat (Spearman ≈ 0) or wrong-signed. The claimed edge rises monotonically from +4% to +16% while the
  realised return does not move — the claimed-minus-realised gap *grows* with the bucket
  (+0.07 → +0.17), which is exactly what "the field ranks model–market disagreement, and the market is
  right" looks like.
* **Hit rate falls as P(edge>0) rises** (36% → 19%) because the high buckets are populated by
  longshots (mean price 0.36 → 0.19): the posterior is relatively widest, and the model most
  optimistic, on draws and weak sides. Reading `P(edge>0)=95%` as confidence in a win is therefore
  actively misleading.
* **Recalibrating the width does not help.** Scaling the posterior by ≈ 0.89 moves 260 more rows into
  the ≥ 0.95 bucket and makes the selection rule fire 28% more often, with the same negative returns.
  A narrower posterior makes the field bolder, not better: the missing ingredient is a bias term
  relative to the reference market, not dispersion.
* Per season (JSON `by_season`) the top buckets are negative in 5–6 of 7 seasons for both
  configurations; the one-sided positives (e.g. 2021-22 ≥ 0.95 at +4%) are on n ≈ 30–60.
* CLV is not available historically (no closing line in the redistribution); the `records` path
  computes it from captured close quotes.

## Recommendation on the field name

Yes — `probability_edge_positive` / "P(edge>0)" overstates. It reads as a probability about the world
(that the bet is good, or that it wins) when it is a **model-internal agreement statistic**: the share
of the model's own worlds in which the model disagrees with the price by more than the fee. Against a
sharp reference it carried no information about realised returns in 12,248 matches.

Proposed label, to be introduced in a versioned contract rather than by renaming `edge_v1` fields:

* field: `share_worlds_positive_ev` (or `model_support_positive_ev`);
* UI text: "model-internal support for +EV: NN% of the model's own scenarios clear the fee. Not a win
  probability; not validated against outcomes";
* keep `probability_edge_positive` in `edge_v1` / `prediction_record_v1` for archive continuity and
  mark it as deprecated-in-name in the schema docs.

## What a versioned `edge_v2` would change (not implemented here)

1. Compute the world statistic on the **recalibrated** worlds (`worlds_v2`, posterior sd × 0.8) — it
   changes the number but, as shown, not its usefulness.
2. Add a **reference-aware** statistic: `P(p_model − p_reference > fee + b)` where the reference is
   the captured consensus/de-vigged bookmaker probability and `b` is an empirical bias allowance
   estimated walk-forward from the disagreement study (mean data − market +0.026 on P(home), up to
   +0.042 for weak home sides). This is the quantity that could be calibrated prospectively against
   realised returns and CLV.
3. Make the robust-EV gate (`min_p_edge_positive = 0.80`) conditional on the reference-aware version
   when a reference exists, and never on the model-internal share alone.
4. Report both statistics in the record (`edge.yes.share_worlds_positive_ev`,
   `edge.yes.p_positive_ev_vs_reference`) so that the `records` evaluation can bucket on either.
5. Leave authority unchanged: nothing here is prospective evidence; the proxy is against a sharp book
   at pre-match prices, and the production question (thin Kalshi book vs reference + model) is
   answered only by the settlement loop.

## Runtime

`proxy` runs in ~35 s from the cache (52 s including cache load); the cache is built by
`research/recalibration.py` (or by `pedge_eval.py proxy` itself when absent, which then refits, ≈ 8
minutes on an idle container).
