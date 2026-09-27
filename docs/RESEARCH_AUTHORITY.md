# Research authority

Authority is a property of a **cell**: `MODEL FAMILY × MARKET FAMILY × HORIZON`. It is stored in
`config/authority.json` (`AuthorityMatrix`), defaults to `RESEARCH_ONLY` for every cell, and is
only ever changed by a human in a reviewed PR.

| State | Meaning | Surfaces as |
|---|---|---|
| `RESEARCH_ONLY` | implemented; no prospective evidence | `shadow_recommendations` only (labelled, never actionable) |
| `SHADOW` | prospective evidence accruing; not yet skilled | `shadow_recommendations` |
| `LIMITED` | beats market and calibrated on ≥300 settled | `recommendations` with confidence label "limited" |
| `TRUSTED` | ≥1000 settled, sustained skill, honest intervals | `recommendations` |

## Promotion rules (`authority/policy.py::PROMOTION_RULES`, written before any evaluation)

| To | min settled | skill vs market (market LL − model LL) | mean CLV (pts) | max ECE | 80% interval coverage |
|---|---|---|---|---|---|
| SHADOW | 100 | ≥ −0.02 | ≥ −0.01 | ≤ 0.08 | — |
| LIMITED | 300 | ≥ 0.00 | ≥ 0.00 | ≤ 0.05 | in [0.70, 0.90] |
| TRUSTED | 1000 | ≥ +0.005 | ≥ +0.005 | ≤ 0.03 | in [0.75, 0.85] |

* Evidence unit = a settled, archived, prospective contract-prediction with a pre-kickoff market
  snapshot at the cell's horizon. Ladder duplicates count once per (fixture, family).
* No leapfrogging: `recommend_state` never proposes more than one step above the current state.
* Demotion is immediate on any red flag (settlement disagreement rate, ECE drift, negative CLV
  over a rolling window) — enforced procedurally, see `docs/HANDOFF.md`.
* Aggregate ROI over a small sample never promotes anything.

## Current matrix

All cells `RESEARCH_ONLY`. The historical walk-forward (see `docs/RESEARCH_RESULTS.md`) is
*retrospective* evidence and does not count toward promotion; it exists to decide which families
deserve prospective shadow capture at all.
