"""Analytic full-time pricing from per-world Dixon-Coles matrices (remediation phase 13).

For every full-time family the per-world probability p_w is an exact sum over the score matrix; the fair
probability is the mean over worlds and the interval is the world quantile - no Monte Carlo noise
(`mc_se = 0`, `effective_draws = n_worlds`). Path-dependent families (half-time, first scorer, to-advance,
player goals) are not analytic here and fall back to the v2 engine draws.
"""

from __future__ import annotations

import numpy as np

from soccer_edge.kalshi.taxonomy import MarketFamily, Period
from soccer_edge.pricing.pricer import PricedProbability
from soccer_edge.pricing.semantics import Semantics, UnsupportedSemantics

ANALYTIC_FAMILIES = {
    MarketFamily.MATCH_RESULT_3WAY,
    MarketFamily.TOTAL_GOALS,
    MarketFamily.TEAM_TOTAL,
    MarketFamily.HANDICAP,
    MarketFamily.BTTS,
    MarketFamily.CLEAN_SHEET,
    MarketFamily.DRAW_NO_BET,
    MarketFamily.EXACT_SCORE,
}


def is_analytic(sem: Semantics) -> bool:
    return sem.family in ANALYTIC_FAMILIES and sem.period is Period.REGULATION


def indicator_matrix(sem: Semantics, max_goals: int) -> np.ndarray:
    """(G+1, G+1) 0/1 matrix of scores (home i, away j) that settle YES."""
    g = np.arange(max_goals + 1)
    h = g[:, None]
    a = g[None, :]
    fam, side = sem.family, sem.side
    line = float(sem.line) if sem.line is not None else None
    if fam is MarketFamily.MATCH_RESULT_3WAY:
        ind = {"home": h > a, "away": a > h, "draw": h == a}[side or "draw"]
    elif fam is MarketFamily.TOTAL_GOALS:
        ind = (h + a) > line
    elif fam is MarketFamily.TEAM_TOTAL:
        ind = (h if side == "home" else a) > line
    elif fam is MarketFamily.HANDICAP:
        ind = ((h - a) if side == "home" else (a - h)) > line
    elif fam is MarketFamily.BTTS:
        ind = (h > 0) & (a > 0)
    elif fam is MarketFamily.CLEAN_SHEET:
        ind = (a == 0) if side == "home" else (h == 0)
    elif fam is MarketFamily.DRAW_NO_BET:
        ind = (h > a) if side == "home" else (a > h)
    elif fam is MarketFamily.EXACT_SCORE:
        hh, aa = divmod(int(sem.k or 0), 100)
        ind = (h == hh) & (a == aa)
    else:
        raise UnsupportedSemantics(f"{fam.value} is not analytic")
    return np.broadcast_to(ind, (max_goals + 1, max_goals + 1)).astype(float)


def price_analytic(
    sem: Semantics, mats: np.ndarray, *, interval_level: float = 0.80
) -> PricedProbability:
    """`mats`: (W, G+1, G+1) per-world score matrices."""
    if not is_analytic(sem):
        raise UnsupportedSemantics(f"{sem.family.value}/{sem.period.value} is not analytic")
    max_goals = mats.shape[1] - 1
    ind = indicator_matrix(sem, max_goals)
    pw = np.einsum("wij,ij->w", mats, ind)
    # DRAW_NO_BET is priced as P(win) to match `settle_indicator` (a draw is a VOID at settlement, which
    # the indicator/payoff path treats as a non-win); kept identical to v1 semantics on purpose
    fair = float(pw.mean())
    lo_q, hi_q = (1 - interval_level) / 2, 1 - (1 - interval_level) / 2
    return PricedProbability(
        ticker=sem.ticker,
        fair_mean=fair,
        fair_median=float(np.median(pw)),
        p_low=float(np.quantile(pw, lo_q)),
        p_high=float(np.quantile(pw, hi_q)),
        interval_level=interval_level,
        param_sd=float(pw.std()),
        mc_se=0.0,
        n_worlds=int(mats.shape[0]),
        n_draws=int(mats.shape[0]),
        effective_draws=int(mats.shape[0]),
        world_probs=pw,
        description=sem.description,
    )
