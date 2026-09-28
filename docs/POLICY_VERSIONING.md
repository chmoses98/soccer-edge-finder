# MODEL vs SELECTION vs STAKING: versioned, separable, replayable (Phase 20)

The three layers that turn data into a shadow recommendation are kept apart and versioned independently so that
any result is attributable to exactly one layer's change:

| Layer | What it decides | Identity on every archived record | Where |
|---|---|---|---|
| MODEL | fair probabilities per world | `model_family` (`data_only.world_sim_v1`), `model_version`, `parameter_hash`, `world_hash`, `engine_version` | `prediction_record_v1` |
| SELECTION | which (ticker, side) is a candidate | `SelectionPolicy.version` + `policy_hash()` | `src/soccer_edge/policy/versions.py` |
| STAKING | how much | `StakingPolicy` — `DISABLED` everywhere | same |

## Why replay works without touching history

Every prediction record archives the **full `EdgeAssessment` for both sides** (price, fee, point edge,
fee-adjusted edge, P(edge>0), worst case, bet-up-to). A selection policy is a pure function of that assessment
plus family/horizon/liquidity, so any policy — past, present or hypothetical — can be applied to the archive
after the fact: `soccer replay-policies --archive-dir … --settlements-dir … --out …`. No historical record is
modified; the output is a separate research artefact (`policy_replay_v1`).

## Frozen benchmark selection: `selection_v1`

Mission-1 production selection (`EdgeConfig` defaults + `robust_positive_ev`): fee-adjusted edge ≥ 2 points,
P(edge>0) ≥ 0.80, worst-case (20th-percentile world) edge > 0. Any change to those thresholds in production is
a **new version**, never an edit of `selection_v1`.

Research variants shipped for comparison only (never promoted here): `selection_v1_strict`,
`selection_v1_loose`, `selection_v1_no_favourites` (skip prices > 0.70), `selection_v1_totals_only`,
`selection_v1_3way_only`.

## Accounting in the replay

Flat one-contract taker fills at the archived executable price plus the archived fee; void settles at 0;
unsettled records count as selected-but-open. CLV (side-aware probability points, from `settlement_record_v1`)
is averaged over settled selections. Numbers are diagnostics: with the archive this young they are noise, and
the frozen walk-forward research already shows naive selections lose to the market.

## Rules

* No hindsight filtering: variants are declared up front in code with a hash; results are reported for all of
  them, not the best one.
* Staking stays `DISABLED`; the replay's flat-unit P&L is not a sizing recommendation.
* Promotion of any model or policy still goes through `docs/CALIBRATION.md` and the RESEARCH_ONLY authority.
