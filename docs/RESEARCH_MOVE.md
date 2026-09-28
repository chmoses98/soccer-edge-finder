# move_v1 — does DATA_ONLY predict sharp open-to-close movement? (NEGATIVE)

Remediation phase 11 (audit §H1). Protocol and code: `research/move_v1.py`; run by `research-move.yml`
on 2026-09-28 (Actions runner; football-data.co.uk direct CSVs are not reachable from every egress).
Result file: `data/research/move_v1.json` (frozen). Pre-registered decision rule: a family "predicts
movement" only if β's 95% lower bound > 0 pooled AND β > 0 in ≥ 5 of 7 seasons AND the directional-accuracy
lower bound > 0.5.

## Sample

11,387 aligned matches, E0/SP1/D1/I1/F1, seasons 2019-20 … 2025-26: Pinnacle opening (`PSH/PSD/PSA`) and
closing (`PSCH/PSCD/PSCA`) 1X2 odds, `P>2.5 / PC>2.5` for totals, power de-vig; the model probability is the
frozen `dc_laplace_v1` walk-forward posterior (weekly refit, results strictly before the match date).

## Result

| family | n (selections) | β | β 95% CI | directional accuracy (CI) | Spearman | LL open / close / model | seasons β > 0 | verdict |
|---|---|---|---|---|---|---|---|---|
| 1X2 (pooled) | 34,161 | −0.006 | [−0.013, +0.002] | 0.476 [0.469, 0.484] | −0.03 | 0.5686 / 0.5673 / 0.5843 | 2 / 7 | **no** |
| 1X2 home | 11,387 | −0.006 | [−0.014, +0.002] | 0.479 | −0.03 | 0.6017 / 0.5999 / 0.6243 | 2 / 7 | no |
| 1X2 draw | 11,387 | −0.005 | [−0.016, +0.006] | 0.459 | −0.00 | 0.5568 / 0.5563 / 0.5622 | 4 / 7 | no |
| 1X2 away | 11,387 | −0.005 | [−0.012, +0.004] | 0.491 | −0.03 | 0.5472 / 0.5458 / 0.5665 | 2 / 7 | no |
| O/U 2.5 | 11,305 | −0.015 | [−0.024, −0.006] | 0.501 | −0.03 | 0.6713 / 0.6687 / 0.6858 | 1 / 7 | no |

* The regression slope of the close-minus-open logit move on the model-minus-open logit gap is zero or
  slightly **negative** in every family; for O/U 2.5 the CI excludes zero on the negative side: where the
  model disagrees with the opening line, the sharp close tends to move *away* from the model.
* Directional accuracy is below 0.5 for 1X2 (0.476, CI entirely below 0.5): the model's sign is a
  (weak) contrarian indicator of where the close goes.
* Magnitude buckets (|model − open| in probability points): the mean close move in the model's direction
  is ≈ 0 in every bucket (−0.0002 … −0.0008); the share of closes moving *against* the model is 51–53% in
  every bucket; the model's own log loss deteriorates sharply with the gap (0.574 → 0.635 in the > 10 pt
  bucket) while the open barely changes — the disagreement is the model's error, as audit B11 found for
  P(edge > 0).
* By league: β ∈ [−0.026, +0.017] (E0 the only positive, not significant); by season: 2 of 7 positive.
* Robustness (matches with ≥ 3 days since the last refit, n = 2,049): β = −0.014 pooled; same verdict.

## Consequence

`dc_laplace_v1` carries **no incremental information about sharp market movement**, in any family. This
closes audit §H hypothesis B for v1: DATA_ONLY cannot earn closing-line value against Pinnacle by
anticipating the close. The reference-anchored `edge_v2` therefore keeps `w_family = 0` (p* = p_ref). The
study will be re-run on `dc_laplace_v2` once its holdout is frozen (`research/move_v1.py --variant
<chosen v2>`); a structural fix that removes the away-level bias does not by itself create movement
information, so the prior expectation is another negative.
