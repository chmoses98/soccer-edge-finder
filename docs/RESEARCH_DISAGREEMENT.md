# Research results — disagreement_v1 (2026-09-28)

Source of truth: `data/research/disagreement_v1.json` (result hash inside). Harness:
`research/disagreement.py` on the shared walk-forward table built by `research/wf_common.py`
(identical protocol to `walk_forward_v1`: weekly point-in-time refit, burn-in 2017-18, hybrid
warm-up 2018-19, **12,248 aligned matches** 2019-20 → 2025-26, E0/SP1/D1/I1/F1, 100 posterior
samples). The aligned 3-way numbers reproduce the frozen run exactly (data 1.00099 vs 1.0010,
market 0.97321, paired diff +0.0278 [0.0244, 0.0310]).

## Question and pre-registered rule

Is there *any* subgroup in which `data_only.dc_laplace_v1` is reliably better than the de-vigged
Bet365 pre-match price? Targets P(home), P(draw), P(away), O/U 2.5. A cell is **informative** only
if n ≥ 200, the bootstrap 95% CI of the paired per-match log-loss difference (data − market)
excludes 0 in favour of the data model, and the data model wins in ≥ 4 of the 7 scored seasons.
Expected answer: no informative subgroup.

## Answer: no informative subgroup

* **116 cells tested, 0 informative.** In **112** the market is *reliably* better (CI > 0 and
  market wins in ≥ 4 seasons). Of the other 4, three have n < 200 (52, 165 and 36 matches, all
  with the market ahead) and one, P(away) with data above market by 10–15 pts (n 287), has a CI
  that includes zero (+0.022 [−0.011, +0.054]) with the data model better in 1 of 7 seasons.
  Expected false positives at 5% would have been ~6; we found none even before the
  season-consistency filter.
* The best cell for the data model is the "no disagreement" band (|gap| < 0.05) on each target:
  diff +0.0031 [+0.0015, +0.0047], data better in at most 1 of 7 seasons.

### Overall per target (aligned)

| target | n | data LL | market LL | realised | data mean | market mean |
|---|---|---|---|---|---|---|
| home | 12,248 | 0.6247 | 0.6030 | 0.431 | **0.460** | 0.436 |
| draw | 12,248 | 0.5623 | 0.5570 | 0.253 | 0.242 | 0.248 |
| away | 12,248 | 0.5673 | 0.5490 | 0.317 | **0.298** | 0.316 |
| over 2.5 | 12,247 | 0.6850 | 0.6712 | 0.533 | **0.503** | 0.528 |

The model is tilted on the *whole* sample, not just where it disagrees: +2.9 pts on home, −1.9 on
away, −1.1 on draw, −3.0 on over 2.5. The market is within 0.5 pts on all four.

### By disagreement size and sign (data − market)

P(home):

| band | n | realised | data | market | paired diff | data-better seasons |
|---|---|---|---|---|---|---|
| < −0.15 | 165 | 0.697 | 0.494 | 0.675 | +0.094 | 0/7 |
| [−0.15, −0.10) | 565 | 0.697 | 0.529 | 0.650 | +0.058 | 0/7 |
| [−0.10, −0.05) | 1,329 | 0.604 | 0.519 | 0.590 | +0.017 | 0/7 |
| [−0.05, +0.05) | 5,554 | 0.463 | 0.466 | 0.462 | +0.003 | 1/7 |
| [+0.05, +0.10) | 2,712 | 0.312 | 0.421 | 0.347 | +0.026 | 0/7 |
| [+0.10, +0.15) | 1,386 | 0.289 | 0.423 | 0.302 | +0.042 | 0/7 |
| ≥ +0.15 | 537 | 0.264 | 0.463 | 0.283 | +0.092 | 0/7 |

P(away) and O/U 2.5 show the same shape (JSON `by_disagreement`): in every band the realised rate
sits on the market mean, and the penalty grows monotonically with the size of the model's
deviation. The signed bands are asymmetric in *count* (4,635 matches with data above market by
> 5 pts on P(home) vs 2,059 below), which is the mean tilt above, not a subgroup.

### By bucket family (3-way 1X2 paired diff, data − market; all CIs > 0, data-better seasons 0/7)

| family | cells (n; diff) |
|---|---|
| league | E0 0.022 · F1 0.026 · SP1 0.029 · I1 0.030 · D1 0.032 |
| favourite side | home fav (7,925) 0.020 · **away fav (4,323) 0.043** |
| market P(fav) terciles (cuts 0.443/0.567) | low 0.022 · mid 0.027 · high 0.035 |
| promoted involved | no (9,331) 0.025 · yes (2,917) 0.037 |
| thin history (< 8 eff. matches) | established (11,425) 0.027 · thin (823) 0.039 |
| season stage (matchday terciles 13/25) | early 0.031 · mid 0.026 · late 0.026 |
| strength uncertainty (sd log λ/μ terciles 0.375/0.399) | low 0.022 · mid 0.027 · high 0.034 |
| scoring environment (λ+μ terciles 2.43/2.80) | low 0.027 · mid 0.031 · high 0.026 |

Where the gap is *largest* is itself informative about the mechanism (not about an edge): away
favourites (data P(home) 0.320 vs realised 0.223 vs market 0.248), strong favourites, and thin
history. This matches the home-bias diagnosis in `docs/RESEARCH_HOME_BIAS.md`: the model
under-predicts away scoring and shrinks favourites too hard.

## What this means

1. There is no subgroup, by size or sign of disagreement, league, favourite, season stage,
   uncertainty or scoring environment, where DATA_ONLY should be preferred to the market. The
   HYBRID weight of 1.00 is correct everywhere.
2. The model's disagreement with the market is a *signal about the model* (a monotone error
   direction), which is what a calibration fix must target, not a subgroup to trade.
3. All families stay `RESEARCH_ONLY`. Nothing here changes `config/authority.json`.
