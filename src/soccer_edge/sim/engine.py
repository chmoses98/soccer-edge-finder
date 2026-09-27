"""Minute-level vectorised match engine.

For each of N = n_worlds x draws_per_world realisations we walk 90 regulation minutes (plus
stoppage folded into the intensity profile). Per minute, each team scores Poisson(rate) goals where

    rate_home(t) = lam_w * profile(t)/90 * state_mult * red_mult

* profile(t): empirical within-match intensity (goals rise through the match; second half
  ~54% of goals) - a smooth ramp normalised to mean 1 over 90 minutes.
* state_mult: trailing teams attack more, leading teams less (per-world multipliers).
* red_mult: a team with a red card attacks less and concedes more.
* half-time scores captured at minute 45; first goal team/minute recorded.
* Knockout ties: if a winner is required and the tie is level after regulation (aggregate-aware),
  30' of extra time at reduced intensity, then a shoot-out (P(home)=0.5 documented prior).

Player goals (RESEARCH_ONLY): team goals allocated multinomially to players on the pitch using
per-world goal shares. This is a scaffold with honest labelling, not a validated player model.

Performance: pure NumPy; ~200k realisations x 90 minutes prices in about a second on a laptop.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from soccer_edge.model.context import MatchContext
from soccer_edge.model.worlds import WorldSet
from soccer_edge.sim.outcome import JointOutcome

ENGINE_VERSION = "minute_engine_v1"


@dataclass(frozen=True)
class SimConfig:
    draws_per_world: int = 100
    minutes: int = 90
    second_half_share: float = (
        0.54  # share of goals scored after HT (empirical top-league figure ~0.53-0.55)
    )
    late_ramp: float = 0.25  # linear intensity increase from start to end of each half
    extra_time_intensity: float = 0.85  # per-minute rate multiplier in ET relative to regulation
    penalty_home_win_prob: float = 0.5
    max_red_per_team: int = 2
    allocate_player_goals: bool = True
    version: str = ENGINE_VERSION


def minute_profile(cfg: SimConfig) -> np.ndarray:
    """Relative intensity per minute; mean exactly 1."""
    n = cfg.minutes
    half = n // 2
    ramp = np.linspace(1.0 - cfg.late_ramp / 2, 1.0 + cfg.late_ramp / 2, half)
    first = ramp * (1 - cfg.second_half_share) * 2
    second = ramp * cfg.second_half_share * 2
    prof = np.concatenate([first, second])
    return prof / prof.mean()


def simulate(worlds: WorldSet, ctx: MatchContext, cfg: SimConfig, seed: int) -> JointOutcome:
    rng = np.random.default_rng(seed)
    W, D = worlds.n_worlds, cfg.draws_per_world
    N = W * D
    widx = np.repeat(np.arange(W, dtype=np.int32), D)
    lam = worlds.lam_home[widx] / cfg.minutes
    mu = worlds.mu_away[widx] / cfg.minutes
    trailing = worlds.trailing_mult[widx]
    leading = worlds.leading_mult[widx]
    red_h_haz = worlds.red_hazard_home[widx]
    red_a_haz = worlds.red_hazard_away[widx]
    own_red = worlds.config.red_own_attack_mult
    opp_red = worlds.config.red_opp_attack_mult
    prof = minute_profile(cfg)

    hg = np.zeros(N, dtype=np.int16)
    ag = np.zeros(N, dtype=np.int16)
    hred = np.zeros(N, dtype=np.int8)
    ared = np.zeros(N, dtype=np.int8)
    first_team = np.zeros(N, dtype=np.int8)
    first_min = np.zeros(N, dtype=np.int16)
    hht = np.zeros(N, dtype=np.int16)
    aht = np.zeros(N, dtype=np.int16)

    # aggregate offset for second legs: positive means this leg's home team leads the tie
    agg_offset = (
        (ctx.first_leg_home_goals - ctx.first_leg_away_goals) if ctx.two_leg_second_leg else 0
    )

    for t in range(cfg.minutes):
        diff = (hg - ag) + agg_offset
        h_state = np.where(diff < 0, trailing, np.where(diff > 0, leading, 1.0))
        a_state = np.where(diff > 0, trailing, np.where(diff < 0, leading, 1.0))
        h_red_mult = np.where(hred > 0, own_red, 1.0) * np.where(ared > 0, opp_red, 1.0)
        a_red_mult = np.where(ared > 0, own_red, 1.0) * np.where(hred > 0, opp_red, 1.0)
        rh = lam * prof[t] * h_state * h_red_mult
        ra = mu * prof[t] * a_state * a_red_mult
        gh = rng.poisson(rh).astype(np.int16)
        ga = rng.poisson(ra).astype(np.int16)
        # first goal bookkeeping (ties within the same minute: coin flip)
        new = (first_team == 0) & ((gh > 0) | (ga > 0))
        both = new & (gh > 0) & (ga > 0)
        coin = rng.random(N) < 0.5
        ft = np.where(gh > 0, 1, 2)
        ft = np.where(both, np.where(coin, 1, 2), ft)
        first_team = np.where(new, ft, first_team).astype(np.int8)
        first_min = np.where(new, t + 1, first_min).astype(np.int16)
        hg += gh
        ag += ga
        # red cards
        rh_card = (rng.random(N) < red_h_haz) & (hred < cfg.max_red_per_team)
        ra_card = (rng.random(N) < red_a_haz) & (ared < cfg.max_red_per_team)
        hred += rh_card.astype(np.int8)
        ared += ra_card.astype(np.int8)
        if t + 1 == cfg.minutes // 2:
            hht = hg.copy()
            aht = ag.copy()

    home_et = np.zeros(N, dtype=np.int16)
    away_et = np.zeros(N, dtype=np.int16)
    et_played = np.zeros(N, dtype=bool)
    pens_played = np.zeros(N, dtype=bool)
    winner = np.where(hg > ag, 1, np.where(hg < ag, 2, 0)).astype(np.int8)

    if ctx.requires_winner:
        agg_h = hg + (ctx.first_leg_home_goals if ctx.two_leg_second_leg else 0)
        agg_a = ag + (ctx.first_leg_away_goals if ctx.two_leg_second_leg else 0)
        tie_level = agg_h == agg_a
        if ctx.away_goals_rule and ctx.two_leg_second_leg:
            # away goals: this leg's away team's goals here vs this leg's home team's goals in leg 1
            away_goals_this = ag
            away_goals_other = ctx.first_leg_home_goals  # home team here was away in leg 1
            decided = tie_level & (away_goals_this != away_goals_other)
            winner = np.where(decided & (away_goals_this > away_goals_other), 2, winner)
            winner = np.where(decided & (away_goals_this < away_goals_other), 1, winner)
            tie_level = tie_level & ~decided
        winner = np.where(~tie_level & (agg_h > agg_a), 1, winner)
        winner = np.where(~tie_level & (agg_h < agg_a), 2, winner)
        et_played = tie_level.copy()
        et_h = lam * cfg.extra_time_intensity * 30
        et_a = mu * cfg.extra_time_intensity * 30
        home_et = np.where(tie_level, rng.poisson(et_h), 0).astype(np.int16)
        away_et = np.where(tie_level, rng.poisson(et_a), 0).astype(np.int16)
        still_level = tie_level & (home_et == away_et)
        winner = np.where(tie_level & (home_et > away_et), 1, winner)
        winner = np.where(tie_level & (home_et < away_et), 2, winner)
        pens_played = still_level.copy()
        pen_home = rng.random(N) < cfg.penalty_home_win_prob
        winner = np.where(still_level, np.where(pen_home, 1, 2), winner).astype(np.int8)

    out = JointOutcome(
        n_worlds=W,
        draws_per_world=D,
        world_index=widx,
        home_ft=hg,
        away_ft=ag,
        home_ht=hht,
        away_ht=aht,
        home_red=hred,
        away_red=ared,
        first_goal_team=first_team,
        first_goal_minute=first_min,
        home_et=home_et,
        away_et=away_et,
        et_played=et_played,
        pens_played=pens_played,
        winner_final=winner,
        seed=seed,
        engine_version=cfg.version,
        world_hash=worlds.world_hash(),
        meta={"draws_per_world": D, "requires_winner": ctx.requires_winner},
    )
    if cfg.allocate_player_goals and worlds.home_goal_shares is not None:
        out.home_player_goals, out.home_players_on = _allocate(
            rng, hg, worlds.home_goal_shares, worlds.home_players_on, widx
        )
    if cfg.allocate_player_goals and worlds.away_goal_shares is not None:
        out.away_player_goals, out.away_players_on = _allocate(
            rng, ag, worlds.away_goal_shares, worlds.away_players_on, widx
        )
    return out


def _allocate(
    rng: np.random.Generator,
    goals: np.ndarray,
    shares: np.ndarray,
    on: np.ndarray,
    widx: np.ndarray,
):
    """Multinomial allocation of team goals to players who appear in that world (vectorised via cumsum)."""
    sh = shares[widx]  # (N, k)
    on_n = on[widx]
    k = sh.shape[1]
    N = goals.shape[0]
    counts = np.zeros((N, k), dtype=np.int16)
    tot = sh.sum(axis=1)
    valid = tot > 0
    if not valid.any():
        return counts, on_n
    cum = np.cumsum(sh, axis=1)
    cum = np.where(tot[:, None] > 0, cum / np.where(tot[:, None] > 0, tot[:, None], 1), 1.0)
    maxg = int(goals.max()) if N else 0
    for g in range(maxg):
        active = (goals > g) & valid
        if not active.any():
            break
        u = rng.random(N)
        idx = (u[:, None] > cum).sum(axis=1)
        idx = np.minimum(idx, k - 1)
        rows = np.nonzero(active)[0]
        counts[rows, idx[rows]] += 1
    return counts, on_n
