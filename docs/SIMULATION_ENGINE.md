# Simulation engine

`sim/engine.py::simulate(worlds, ctx, cfg, seed)` → `JointOutcome`.

## Mechanics

* N = `n_worlds × draws_per_world` realisations, all vectorised in NumPy.
* 90 regulation minutes; per minute each team scores `Poisson(rate)` where
  `rate = λ_w · profile(t)/90 · state_mult · red_mult`.
* `profile(t)`: rising intensity within each half; second half carries `second_half_share`
  (default 0.54) of goals; mean exactly 1.
* Game state: trailing team attacks ×`trailing_mult_w`, leading team ×`leading_mult_w`
  (aggregate-aware in second legs).
* Red cards: per-minute hazard per team (per world), capped at 2; a team down a man attacks ×0.65
  and its opponent ×1.25 (configurable, unvalidated).
* Half-time scores captured at minute 45; first-goal team and minute recorded.
* Knockouts (`ctx.requires_winner`): level ties play 30' of ET at 0.85 intensity, then a shoot-out
  with P(home)=0.5. Away-goals rule supported when a competition still uses it.
* Player goals (RESEARCH_ONLY): team goals allocated multinomially to players on the pitch using
  per-world goal shares; goals are conserved exactly (`Σ player goals == team goals` per draw).

## Outputs (`JointOutcome`)

`home_ft, away_ft, home_ht, away_ht, home_red, away_red, first_goal_team, first_goal_minute,
home_et, away_et, et_played, pens_played, winner_final, home/away_player_goals, world_index`.
Only `compact_summary()` (1X2, means, BTTS, O2.5, red-card rate, 9×9 score grid, hashes) is ever
stored. Raw realisations are never persisted.

## Benchmarks (this build, GitHub-class CPU, NumPy only)

| Setting | Time |
|---|---|
| fit Dixon-Coles posterior, 20–26 teams, ~750 matches | 20–60 ms |
| generate 1,000 worlds | ~10 ms |
| simulate 1,000 worlds × 100 draws (100k realisations, 90 minutes) | ~1.0 s |
| simulate 2,000 × 100 (200k) | ~1.8 s |
| price 12 contracts from a 100k outcome + coherence audit | ~50 ms |
| RUN SOCCER, 17 fixtures × 12 synthetic contracts, 500 × 100 | ~10 s end to end |

A 40-fixture weekend slate at 1,000 × 100 fits comfortably in a two-minute job. Repricing from the
cache costs milliseconds per contract.

## Correctness tests (`tests/test_simulation.py`, `tests/test_pricing.py`)

reproducibility by seed; HT ≤ FT; result partition sums to 1; ladders monotone; expected goals match
the world rates; red card lowers own scoring and raises the opponent's; state effects raise the draw
rate; with dynamics disabled the engine matches the analytic Dixon-Coles matrix within 1 pt;
knockouts always produce a winner; second-leg aggregate; absent players cannot score and goals are
conserved; wider inputs → wider outputs; lineup confirmation reduces relative dispersion.

## Known simplifications

Stoppage time is folded into the profile; no explicit substitutions; no formation/tactical state;
penalties within regulation are not separated from open play; ET intensity and shoot-out
probability are priors, not estimates; player layer has no data provider in production.

## world_sim_v2 (remediation phase 13; audit B2, §P9) — separately versioned engine

`sim/engine_v2.py` + `pricing/analytic_pricer.py`. The production v1 path (`worlds_v1` +
`minute_engine_v1`) never read the fitted ρ and layered unfitted game-state (×1.08/×0.93) and red-card
multipliers on a λ fitted as a full-match mean, so its full-time distribution was neither the benchmarked
model nor mean-preserving. v2:

1. **Full-time score per world is drawn from the exact per-world Dixon–Coles matrix** (ρ honoured). Every
   full-time family (3-way, totals, team totals, handicaps, BTTS, clean sheet, DNB, exact score) is priced
   **analytically** from those matrices: `p_w` is exact, the interval is the world quantile, `mc_se = 0`.
2. **Timing is conditional on the score and exact**: goal times of a time-inhomogeneous Poisson process
   given the count are i.i.d. from the normalised intensity, so the half-time split is binomial thinning
   with the fitted first-half share (0.441; E0/SP1/D1/I1/F1 2015–2025, 19,859 matches; v1 assumed 0.46),
   the first scorer is home with probability h/(h+a), the first minute is the order statistic. No
   game-state or red-card dynamics: unfitted, not mean-preserving, dropped (recorded in `meta`).
3. **ET/pens** only when a winner is required and the tie is level: Poisson(λ·0.85·30/90) per side, then
   a 50/50 shoot-out (unvalidated priors, flagged).

Reconciliation at the audit's regression points (1,000 worlds × 200 draws, ρ = −0.10):

| λ / μ | quantity | analytic | world_sim_v2 |
|---|---|---|---|
| 2.30 / 0.80 | P(draw) | 0.1914 | 0.1914 |
| 2.30 / 0.80 | E[home] / E[away] | 2.30 / 0.80 | 2.304 / 0.801 |
| 1.52 / 1.13 | P(draw) | 0.2795 | 0.2787 |
| 1.52 / 1.13 | P(O2.5) | 0.4940 | 0.4955 |

Production selection: `RunConfig.engine_version` (`minute_engine_v1` | `world_sim_v2`); the model family
id becomes `data_only.world_sim_v2` so v2 evidence never mixes with v1 cells. The full historical engine
benchmark (analytic vs v1 vs v2 on a stratified subsample, both posteriors) is
`data/research/world_sim_benchmark.json` (`research/dc_v2.py engines`).
