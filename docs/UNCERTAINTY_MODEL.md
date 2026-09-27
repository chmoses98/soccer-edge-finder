# Uncertainty model

## Three kinds, kept distinct

| Kind | Where it lives | How it enters the contract probability |
|---|---|---|
| **Aleatoric** (match randomness) | `sim/engine.py`: Poisson goal arrivals per minute, red-card Bernoullis, shoot-outs | integrated by the `draws_per_world` realisations *within* each world; produces `p_w` |
| **Parameter** (what we do not know about the teams/context) | `model/worlds.py`: posterior draws of attack/defence/home advantage/rho; lineup availability draws; competition environment; red-card hazard | integrated *across* worlds; `fair = mean_w p_w`; interval = quantiles of `p_w` |
| **Model** (specification error) | `WorldConfig.sigma_model_log_rate` inflation on log rates; game-state multipliers drawn with sd; family mixing at the family layer | widens the spread of `p_w` beyond the posterior alone |

`P(edge > 0)` and the worst-case edge are computed on the same `p_w` distribution that prices the
contract, so uncertainty is not a decoration added afterwards.

## Where the widths come from (evidence status)

| Input | Representation | Source of the width | Status |
|---|---|---|---|
| Team attack / defence | Gaussian posterior (Laplace at the MAP) | inverse observed information of the time-decayed Dixon-Coles likelihood + per-team prior | evidence-based; widens for thin history automatically |
| Promoted / new teams | prior mean −0.15 (attack, defence), prior sd 0.45 vs 0.35 | configured defaults; **to be estimated** from promoted-team seasons in the historical set (roadmap) | configured |
| Home advantage | posterior over γ (prior N(0.25, 0.15²)) | data | evidence-based |
| Dixon-Coles ρ | posterior (prior sd 0.08) | data | evidence-based |
| Lineup availability | per-player P(play), importance share, goal share; `CONFIRMED` collapses P(play) to 0/1 | no provider yet → production uses `lineup_state=unknown` and no players | scaffold, tested |
| Competition environment | log-normal sd 0.03 | configured | configured; calibration research will tune |
| Red cards | Gamma around 0.12/team/match (shape 20) | literature/top-league base rate | configured |
| Game-state behaviour | trailing ×1.08, leading ×0.93, sd 0.04 | Dixon & Robinson-style effects | configured, unvalidated |
| Model inflation | log-normal sd 0.05 on rates | placeholder | **must be calibrated** by interval-coverage research |
| Weather, referee, travel, tactics, goalkeeper | not modelled | — | listed in `WorldSet.components["not_modelled"]` |

## Correlated worlds

Dependencies are explicit in `WorldGenerator.generate`:

* absent player → team attack multiplier ↓ → goal shares renormalised over players on the pitch
  (so an absent striker cannot score and his share moves to teammates);
* environment and model inflation draws are shared by both teams (a high-scoring world is
  high-scoring for both);
* red-card hazard is per team per world; its *effect* on both teams' rates is applied inside the
  match engine as the state evolves;
* game-state multipliers are per world, so "this is a world where teams protect leads" is coherent
  across the whole match.

Not yet represented: formation state, opponent adaptation to a missing star, congestion-driven
rotation, and the joint distribution across *different fixtures* (worlds are independent across
fixtures today, so cross-fixture portfolio correlation is zero by construction).

## Calibrating the uncertainty itself

`evaluation.metrics.interval_calibration` groups predictions by probability bin and asks whether
the realised frequency falls inside the average interval. The walk-forward research reports the
80% interval coverage for P(home) (`data/research/walk_forward_v1.json →
interval_calibration_p_home`). The promotion rules in `authority/policy.py` require the 80%
interval coverage to sit in [0.70, 0.90] for LIMITED and [0.75, 0.85] for TRUSTED.
