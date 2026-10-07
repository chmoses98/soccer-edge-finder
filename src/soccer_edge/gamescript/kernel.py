"""Exact, world-independent timing kernel of world_sim_v2 and the script map over its cells.

world_sim_v2 draws the full-time score (h, a) from the per-world Dixon-Coles matrix; goal times given the count
are i.i.d. from a piecewise-constant intensity with first-half share s (sim/engine_v2.py). Hence, given (h, a):

* each goal is in the first half independently with probability s:  h1 ~ Bin(h, s), a1 ~ Bin(a, s);
* the goals of one half are exchangeable, so the first scorer is home with probability h1 / (h1 + a1) when the
  first half has a goal, else (h - h1) / ((h - h1) + (a - a1)); no goal -> no first scorer.

`cell_kernel` is P(h1, a1, first | h, a) on the padded grid (G+1, G+1, G+1, G+1, 3). It does not depend on the
world, so the joint over (world, h, a, h1, a1, first) is mats[w, h, a] * kernel[h, a, h1, a1, first] and every
script / market probability is an exact sum. The draw-based production arrays have the same marginals; they are
not used here (their first-scorer draw is independent of their half-time draw, see docs/GAME_SCRIPTS.md §4).

`temporal_kernel` adds DESCRIPTIVE path statistics (minutes leading, lead changes, late goals) by a deterministic,
seeded Monte Carlo over goal orders and times given (h, a, first). It feeds script cards only - never a price.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy.stats import binom

from soccer_edge.gamescript.taxonomy import FT_AWAY, FT_HOME, FT_NONE, INDEX, K, script_of

MAX_GOALS = 10  # sim/engine_v2.score_matrices default (G = 10 -> 11 x 11 score grid)
MINUTES = 90.0


@lru_cache(maxsize=8)
def cell_kernel(first_half_share: float, max_goals: int = MAX_GOALS) -> np.ndarray:
    """P(h1, a1, first | h, a), shape (G1, G1, G1, G1, 3); sums to 1 over (h1, a1, first) for every (h, a)."""
    g1 = max_goals + 1
    g = np.arange(g1)
    # bin[h, h1] = P(h1 | h)
    b = binom.pmf(g[None, :], g[:, None], first_half_share)
    b[np.isnan(b)] = 0.0
    H, A, H1, A1 = np.meshgrid(g, g, g, g, indexing="ij")
    p_split = b[H, H1] * b[A, A1]  # zero when h1 > h or a1 > a
    n1 = H1 + A1
    h2, a2 = H - H1, A - A1
    n2 = h2 + a2
    with np.errstate(invalid="ignore", divide="ignore"):
        home_first = np.where(
            n1 > 0, H1 / np.maximum(n1, 1), np.where(n2 > 0, h2 / np.maximum(n2, 1), 0.0)
        )
    none = (H + A) == 0
    k = np.zeros((g1, g1, g1, g1, 3))
    k[..., FT_NONE] = np.where(none, p_split, 0.0)
    k[..., FT_HOME] = np.where(none, 0.0, p_split * home_first)
    k[..., FT_AWAY] = np.where(none, 0.0, p_split * (1.0 - home_first))
    k = np.where((H1 <= H) & (A1 <= A) & (h2 >= 0) & (a2 >= 0), 1.0, 0.0)[..., None] * k
    k.setflags(write=False)
    return k


@lru_cache(maxsize=2)
def script_map(max_goals: int = MAX_GOALS) -> np.ndarray:
    """script index of each (h, a, first) cell, -1 for impossible cells; shape (G1, G1, 3)."""
    g1 = max_goals + 1
    m = np.full((g1, g1, 3), -1, dtype=int)
    for h in range(g1):
        for a in range(g1):
            for f in (FT_NONE, FT_HOME, FT_AWAY):
                try:
                    m[h, a, f] = INDEX[script_of(h, a, f)]
                except ValueError:
                    continue
    m.setflags(write=False)
    return m


@lru_cache(maxsize=2)
def script_onehot(max_goals: int = MAX_GOALS) -> np.ndarray:
    """(G1, G1, 3, K) one-hot of the script map (impossible cells are all-zero)."""
    m = script_map(max_goals)
    oh = np.zeros((*m.shape, K))
    for s in range(K):
        oh[..., s] = m == s
    oh.setflags(write=False)
    return oh


def first_scorer_given_score(first_half_share: float, max_goals: int = MAX_GOALS) -> np.ndarray:
    """P(first | h, a), shape (G1, G1, 3)."""
    return cell_kernel(first_half_share, max_goals).sum(axis=(2, 3))


def script_given_score(first_half_share: float, max_goals: int = MAX_GOALS) -> np.ndarray:
    """T[h, a, S] = P(script S | h, a); rows sum to one."""
    return np.einsum(
        "haf,hafs->has",
        first_scorer_given_score(first_half_share, max_goals),
        script_onehot(max_goals),
    )


# ------------------------------------------------------------------------------ descriptive temporal kernel

TEMPORAL_FIELDS = (
    "minutes_home_leading",
    "minutes_away_leading",
    "minutes_level",
    "p_lead_changed_hands",  # both sides held the lead at some point
    "p_home_ever_trailed",
    "p_away_ever_trailed",
    "p_level_at_75",
    "p_goal_after_75",
    "mean_first_goal_minute",  # given a goal
)
TEMPORAL_SAMPLES = 3000
TEMPORAL_SEED = 20261007


@lru_cache(maxsize=4)
def temporal_kernel(
    first_half_share: float, max_goals: int = MAX_GOALS, samples: int = TEMPORAL_SAMPLES
) -> np.ndarray:
    """E[stat | h, a, first], shape (G1, G1, 3, len(TEMPORAL_FIELDS)); deterministic (fixed seed per cell).
    Goal times: first half w.p. s, uniform within the half (the engine's piecewise-constant intensity); goal order
    a uniformly random interleaving. Cells with h + a = 0 have their exact values."""
    g1 = max_goals + 1
    out = np.full((g1, g1, 3, len(TEMPORAL_FIELDS)), np.nan)
    half = MINUTES / 2
    for h in range(g1):
        for a in range(g1):
            n = h + a
            if n == 0:
                out[h, a, FT_NONE] = [0.0, 0.0, MINUTES, 0.0, 0.0, 0.0, 1.0, 0.0, np.nan]
                continue
            rng = np.random.default_rng([TEMPORAL_SEED, h, a])
            first_half = rng.random((samples, n)) < first_half_share
            t = np.where(first_half, 0.0, half) + rng.random((samples, n)) * half
            lab = np.zeros((samples, n), dtype=int)
            lab[:, :h] = 1  # 1 home goal, 0 away goal; shuffled by the time order below
            keys = rng.random((samples, n))
            lab = np.take_along_axis(lab, np.argsort(keys, axis=1), axis=1)
            order = np.argsort(t, axis=1)
            t = np.take_along_axis(t, order, axis=1)
            lab = np.take_along_axis(lab, order, axis=1)
            step = np.where(lab == 1, 1, -1)
            diff = np.cumsum(step, axis=1)  # home - away after each goal
            starts = t
            ends = np.concatenate([t[:, 1:], np.full((samples, 1), MINUTES)], axis=1)
            dur = ends - starts
            home_lead = (dur * (diff > 0)).sum(axis=1)
            away_lead = (dur * (diff < 0)).sum(axis=1)
            level = MINUTES - home_lead - away_lead
            home_led = (diff > 0).any(axis=1)
            away_led = (diff < 0).any(axis=1)
            # state at 75': last diff with time <= 75
            before75 = t <= 75.0
            idx75 = before75.sum(axis=1) - 1
            d75 = np.where(
                idx75 >= 0, np.take_along_axis(diff, np.maximum(idx75, 0)[:, None], axis=1)[:, 0], 0
            )
            late = (t > 75.0).any(axis=1)
            first = np.where(lab[:, 0] == 1, FT_HOME, FT_AWAY)
            stats = np.stack(
                [
                    home_lead,
                    away_lead,
                    level,
                    home_led & away_led,
                    away_led,
                    home_led,
                    d75 == 0,
                    late,
                    t[:, 0],
                ],
                axis=1,
            ).astype(float)
            for f in (FT_HOME, FT_AWAY):
                sel = first == f
                if sel.any():
                    out[h, a, f] = stats[sel].mean(axis=0)
    out.setflags(write=False)
    return out
