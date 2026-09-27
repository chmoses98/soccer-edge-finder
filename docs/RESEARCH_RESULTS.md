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
* Market-as-oracle check (added in the re-run; see JSON `interval_calibration_p_home`): share of
  matches where the de-vigged market probability lies inside our interval, and the share of matches
  where |data − market| ≤ 0.05/0.10/0.15. With a 0.29 mean width against a mean absolute
  disagreement of a few points, coverage of the oracle is far above 80%: **the posterior +
  inflation is over-dispersed** and `P(edge > 0)` from it is therefore *too conservative*, not too
  bold. This is the first calibration item on the roadmap.

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
