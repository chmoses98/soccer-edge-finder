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
