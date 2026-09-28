"""world_sim_v2: score-first simulation that reproduces the fitted Dixon-Coles distribution exactly
(remediation phase 13; audit B2, §P9).

`minute_engine_v1` simulated 90 Poisson minutes with configured game-state and red-card multipliers and
never read the fitted rho, so its full-time distribution was neither the benchmarked model nor
mean-preserving (favourite expected goals -2 ... -3%; draw +/-1.5 pt; O2.5 -1.2 pt). v2 separates the two
questions:

1. **Full-time score** per world is drawn from the exact per-world Dixon-Coles matrix
   `score_matrices(lam_w, mu_w, rho_w)` - the same matrix every historical benchmark scored. Full-time
   families are priced analytically from that matrix (`pricing/analytic_pricer.py`); the draws here only
   serve path-dependent families.
2. **Timing**, conditional on the score: for a time-inhomogeneous Poisson process, goal times given the
   number of goals are i.i.d. from the normalised intensity, so half-time score, first scorer and first
   minute follow *exactly* from the fitted score distribution and a first-half intensity share
   (`first_half_share`, fitted 0.441 on E0/SP1/D1/I1/F1 2015-2025 HT/FT goals - see
   docs/SIMULATION_ENGINE.md). No game-state or red-card dynamics: they are not fitted and cannot be
   mean-preserving by construction, so they are dropped rather than carried.
3. **Extra time / penalties** (to-advance contracts only): when a winner is required and the leg is
   level on aggregate, ET goals ~ Poisson(lam_w * 30/90 * et_intensity) per side; still level -> a 50/50
   shoot-out. These priors are unvalidated (as in v1) and flagged in the outcome meta.

The output is a `JointOutcome` with the same arrays v1 produced, so semantics, pricer, expression
reducer and sim cache consume it unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from soccer_edge.model.context import MatchContext
from soccer_edge.model.worlds import WorldSet
from soccer_edge.sim.outcome import JointOutcome

ENGINE_VERSION_V2 = "world_sim_v2"
FIRST_HALF_SHARE_FITTED = (
    0.441  # E0/SP1/D1/I1/F1 2015-07 -> 2025, 19,859 matches (HTHG+HTAG)/(FTHG+FTAG)
)


@dataclass(frozen=True)
class SimConfigV2:
    draws_per_world: int = 100
    minutes: int = 90
    first_half_share: float = FIRST_HALF_SHARE_FITTED
    extra_time_intensity: float = 0.85
    penalty_home_win_prob: float = 0.5
    max_goals: int = 10
    allocate_player_goals: bool = True
    version: str = ENGINE_VERSION_V2


def score_matrices(
    lam: np.ndarray, mu: np.ndarray, rho: np.ndarray, max_goals: int = 10
) -> np.ndarray:
    """Exact per-world Dixon-Coles score matrices, shape (W, G+1, G+1), each summing to one."""
    from scipy.stats import poisson

    g = np.arange(max_goals + 1)
    ph = poisson.pmf(g[None, :], lam[:, None])  # (W, G+1)
    pa = poisson.pmf(g[None, :], mu[:, None])
    m = ph[:, :, None] * pa[:, None, :]
    m[:, 0, 0] *= 1 - lam * mu * rho
    m[:, 0, 1] *= 1 + lam * rho
    m[:, 1, 0] *= 1 + mu * rho
    m[:, 1, 1] *= 1 - rho
    m = np.clip(m, 0, None)
    return m / m.sum(axis=(1, 2), keepdims=True)


def _sample_scores(
    mats: np.ndarray, draws: int, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    W, G1, _ = mats.shape
    flat = mats.reshape(W, G1 * G1)
    cdf = np.cumsum(flat, axis=1)
    u = rng.random((W, draws))
    idx = np.empty((W, draws), dtype=int)
    for w in range(W):
        idx[w] = np.searchsorted(cdf[w], u[w], side="right")
    idx = np.clip(idx, 0, G1 * G1 - 1)
    return (idx // G1).reshape(-1), (idx % G1).reshape(-1)


def _first_minute(k: np.ndarray, cfg: SimConfigV2, rng: np.random.Generator) -> np.ndarray:
    """Minute of the earliest of k i.i.d. goal times from the piecewise-constant intensity (k >= 1):
    inverse CDF of the minimum, F_min(t) = 1 - (1 - F(t))^k."""
    s = cfg.first_half_share
    half = cfg.minutes / 2
    u = rng.random(k.shape)
    q = 1.0 - (1.0 - u) ** (1.0 / np.maximum(k, 1))  # quantile of F
    return np.where(q < s, (q / s) * half, half + ((q - s) / (1 - s)) * half)


def simulate_v2(worlds: WorldSet, ctx: MatchContext, cfg: SimConfigV2, seed: int) -> JointOutcome:
    rng = np.random.default_rng(seed)
    W, D = worlds.n_worlds, cfg.draws_per_world
    N = W * D
    widx = np.repeat(np.arange(W), D)
    mats = score_matrices(worlds.lam_home, worlds.mu_away, worlds.rho, cfg.max_goals)
    home_ft, away_ft = _sample_scores(mats, D, rng)

    # timing conditional on the score (exact): for a time-inhomogeneous Poisson process the goal times
    # given the count are i.i.d. from the normalised intensity, so the half-time split is binomial
    # thinning with the first-half share, the first scorer is home w.p. h/(h+a), and the first minute is
    # the minimum of h+a i.i.d. times
    home_ht = rng.binomial(home_ft, cfg.first_half_share)
    away_ht = rng.binomial(away_ft, cfg.first_half_share)
    total = home_ft + away_ft
    any_goal = total > 0
    u = rng.random(N)
    first_team = np.where(any_goal, np.where(u * np.maximum(total, 1) < home_ft, 1, 2), 0)
    first_minute = np.where(any_goal, _first_minute(total, cfg, rng), -1.0)
    # extra time / penalties when a winner is required and the tie is level
    home_et = np.zeros(N, dtype=int)
    away_et = np.zeros(N, dtype=int)
    et_played = np.zeros(N, dtype=bool)
    pens_played = np.zeros(N, dtype=bool)
    agg_home = home_ft + ctx.first_leg_home_goals
    agg_away = away_ft + ctx.first_leg_away_goals
    winner = np.where(agg_home > agg_away, 1, np.where(agg_away > agg_home, 2, 0))
    if ctx.requires_winner:
        level = winner == 0
        if ctx.away_goals_rule and ctx.two_leg_second_leg:
            # away goals: this leg's away side scored away_ft; first-leg away goals were the home side's
            ag_home = ctx.first_leg_home_goals  # goals the home side scored away in leg 1
            ag_away = away_ft
            level = level & (ag_home == ag_away)
            winner = np.where(
                level,
                0,
                np.where(
                    (winner == 0) & (ag_home > ag_away),
                    1,
                    np.where((winner == 0) & (ag_away > ag_home), 2, winner),
                ),
            )
        if level.any():
            et_rate_h = worlds.lam_home[widx] * cfg.extra_time_intensity * (30.0 / cfg.minutes)
            et_rate_a = worlds.mu_away[widx] * cfg.extra_time_intensity * (30.0 / cfg.minutes)
            home_et[level] = rng.poisson(et_rate_h[level])
            away_et[level] = rng.poisson(et_rate_a[level])
            et_played |= level
            still = level & (home_et == away_et)
            winner = np.where(
                level & (home_et > away_et), 1, np.where(level & (away_et > home_et), 2, winner)
            )
            if still.any():
                pens_played |= still
                pen_home = rng.random(N) < cfg.penalty_home_win_prob
                winner = np.where(still, np.where(pen_home, 1, 2), winner)
    # player goal allocation (conditional on the score; multinomial over goal shares)
    home_player_goals = away_player_goals = None
    if cfg.allocate_player_goals and worlds.home_goal_shares is not None:
        home_player_goals = _allocate(home_ft, worlds.home_goal_shares[widx], rng)
    if cfg.allocate_player_goals and worlds.away_goal_shares is not None:
        away_player_goals = _allocate(away_ft, worlds.away_goal_shares[widx], rng)
    return JointOutcome(
        n_worlds=W,
        draws_per_world=D,
        world_index=widx,
        home_ft=home_ft,
        away_ft=away_ft,
        home_ht=home_ht,
        away_ht=away_ht,
        home_red=np.zeros(N, dtype=int),
        away_red=np.zeros(N, dtype=int),
        first_goal_team=first_team,
        first_goal_minute=first_minute,
        home_et=home_et,
        away_et=away_et,
        et_played=et_played,
        pens_played=pens_played,
        winner_final=winner,
        home_player_goals=home_player_goals,
        away_player_goals=away_player_goals,
        home_players_on=worlds.home_players_on[widx]
        if worlds.home_players_on is not None
        else None,
        away_players_on=worlds.away_players_on[widx]
        if worlds.away_players_on is not None
        else None,
        seed=seed,
        engine_version=cfg.version,
        world_hash=worlds.world_hash(),
        meta={
            "score_model": "exact per-world Dixon-Coles matrix (rho honoured)",
            "timing": f"i.i.d. goal times, first-half share {cfg.first_half_share}",
            "dynamics_dropped": ["game_state_multipliers", "red_cards"],
            "unvalidated": ["extra_time_intensity", "penalty_home_win_prob"],
        },
    )


def _allocate(goals: np.ndarray, shares: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    N, k = shares.shape
    out = np.zeros((N, k), dtype=int)
    for i in range(N):
        g = int(goals[i])
        if g == 0:
            continue
        p = shares[i]
        if p.sum() <= 0:
            continue
        out[i] = rng.multinomial(g, p / p.sum())
    return out
