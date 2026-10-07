"""Contract settlement over the kernel cells (h, a, h1, a1, first) - the SAME rules as
`pricing/semantics.settle_indicator`, evaluated on the exact state space instead of simulation draws.

`cell_indicator(...)` returns a 0/1 array of shape (G1, G1, G1, G1, 3). A contract whose payout depends on the
world beyond the score (to-advance in a knockout: extra time and penalties use the world's rates) returns
`ADVANCE`, priced by `advance_table`. Anything else the script layer cannot represent exactly raises
`ScriptUnsupported` (it then stays visible as a data gap; nothing is approximated).

Equivalence with settle_indicator is a test (tests/test_game_scripts.py::test_cell_indicator_matches_settlement).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import numpy as np

from soccer_edge.gamescript.kernel import MAX_GOALS
from soccer_edge.gamescript.taxonomy import FT_AWAY, FT_HOME
from soccer_edge.kalshi.taxonomy import MarketFamily, Period


class ScriptUnsupported(Exception):
    pass


ADVANCE = "ADVANCE"


@dataclass(frozen=True)
class CellSpec:
    """The settlement-relevant fields of a contract (as stored on the model board)."""

    family: str
    period: str | None
    side: str | None
    line: float | None
    k: int | None = None

    @staticmethod
    def from_semantics(sem: Any) -> CellSpec:
        return CellSpec(
            sem.family.value,
            sem.period.value if sem.period is not None else None,
            sem.side,
            float(sem.line) if sem.line is not None else None,
            sem.k,
        )

    @staticmethod
    def from_board(c: dict[str, Any]) -> CellSpec:
        line = c.get("line")
        return CellSpec(
            c["family"],
            c.get("period"),
            c.get("side"),
            float(Decimal(str(line))) if line is not None else None,
            c.get("k"),
        )


def _grids(max_goals: int) -> tuple[np.ndarray, ...]:
    g = np.arange(max_goals + 1)
    H, A, H1, A1, F = np.meshgrid(g, g, g, g, np.arange(3), indexing="ij")
    return H, A, H1, A1, F


_GRID_CACHE: dict[int, tuple[np.ndarray, ...]] = {}


def grids(max_goals: int = MAX_GOALS) -> tuple[np.ndarray, ...]:
    if max_goals not in _GRID_CACHE:
        _GRID_CACHE[max_goals] = _grids(max_goals)
    return _GRID_CACHE[max_goals]


def cell_indicator(
    spec: CellSpec, *, requires_winner: bool, max_goals: int = MAX_GOALS
) -> np.ndarray | str:
    H, A, H1, A1, F = grids(max_goals)
    try:
        fam = MarketFamily(spec.family)
    except ValueError as exc:
        raise ScriptUnsupported(f"unknown family {spec.family}") from exc
    period = Period(spec.period) if spec.period else Period.REGULATION
    if period is Period.FIRST_HALF:
        h, a = H1, A1
    elif period is Period.SECOND_HALF:
        h, a = H - H1, A - A1
    elif period in (Period.INCLUDING_ET, Period.INCLUDING_PENS):
        if requires_winner and fam is not MarketFamily.MATCH_WINNER_2WAY:
            raise ScriptUnsupported(
                "goal markets including extra time are not represented by the script layer"
            )
        h, a = (
            H,
            A,
        )  # no extra time is played when no winner is required: full == regulation (engine_v2)
    elif period is Period.REGULATION:
        h, a = H, A
    else:
        raise ScriptUnsupported(f"period {period.value}")
    line = spec.line
    side = spec.side
    if fam in (MarketFamily.TOTAL_GOALS, MarketFamily.FIRST_HALF_TOTAL):
        ind = (h + a) > line
    elif fam in (MarketFamily.TEAM_TOTAL, MarketFamily.FIRST_HALF_TEAM_TOTAL):
        ind = (h if side == "home" else a) > line
    elif fam in (MarketFamily.EXACT_SCORE, MarketFamily.FIRST_HALF_EXACT_SCORE):
        hh, aa = divmod(int(spec.k or 0), 100)
        ind = (h == hh) & (a == aa)
    elif fam in (MarketFamily.BTTS, MarketFamily.FIRST_HALF_BTTS):
        ind = (h > 0) & (a > 0)
    elif fam in (MarketFamily.HANDICAP, MarketFamily.FIRST_HALF_HANDICAP):
        ind = ((h - a) if side == "home" else (a - h)) > line
    elif fam in (
        MarketFamily.MATCH_RESULT_3WAY,
        MarketFamily.FIRST_HALF_RESULT,
        MarketFamily.SECOND_HALF_RESULT,
    ):
        ind = h > a if side == "home" else (a > h if side == "away" else h == a)
    elif fam is MarketFamily.CLEAN_SHEET:
        ind = (a == 0) if side == "home" else (h == 0)
    elif fam is MarketFamily.DRAW_NO_BET:
        ind = (h > a) if side == "home" else (a > h)
    elif fam is MarketFamily.MATCH_WINNER_2WAY:
        if requires_winner:
            return ADVANCE
        # winner_final without a required winner = the regulation result (engine_v2, no first leg)
        ind = (H > A) if side == "home" else (A > H)
    elif fam is MarketFamily.FIRST_TO_SCORE:
        ind = (FT_HOME if side == "home" else FT_AWAY) == F
    else:
        raise ScriptUnsupported(f"family {fam.value} has no exact script-layer settlement")
    if line is None and fam in (
        MarketFamily.TOTAL_GOALS,
        MarketFamily.FIRST_HALF_TOTAL,
        MarketFamily.TEAM_TOTAL,
        MarketFamily.FIRST_HALF_TEAM_TOTAL,
        MarketFamily.HANDICAP,
        MarketFamily.FIRST_HALF_HANDICAP,
    ):
        raise ScriptUnsupported("missing line")
    return np.broadcast_to(ind, H.shape).astype(float)


def advance_home_prob(
    lam: np.ndarray,
    mu: np.ndarray,
    *,
    first_leg_home_goals: int = 0,
    first_leg_away_goals: int = 0,
    away_goals_rule: bool = False,
    two_leg_second_leg: bool = False,
    extra_time_intensity: float = 0.85,
    penalty_home_win_prob: float = 0.5,
    minutes: float = 90.0,
    max_goals: int = MAX_GOALS,
) -> np.ndarray:
    """P_w(home advances | regulation score h-a), shape (W, G1, G1) - engine_v2's knockout rules, exactly:
    aggregate, then (optionally) away goals, then extra time ~ Poisson(rate * intensity * 30/90) per side, then
    a shoot-out won by home with `penalty_home_win_prob`."""
    from scipy.stats import poisson

    g1 = max_goals + 1
    g = np.arange(g1)
    h = g[:, None]
    a = g[None, :]
    agg_h = h + first_leg_home_goals
    agg_a = a + first_leg_away_goals
    out = np.zeros((lam.shape[0], g1, g1))
    decided_home = agg_h > agg_a
    decided_away = agg_a > agg_h
    level = ~(decided_home | decided_away)
    if away_goals_rule and two_leg_second_leg:
        ag_home = np.full_like(a, first_leg_home_goals) + 0 * h
        ag_away = a + 0 * h
        decided_home = decided_home | (level & (ag_home > ag_away))
        decided_away = decided_away | (level & (ag_away > ag_home))
        level = level & (ag_home == ag_away)
    out[:, decided_home] = 1.0
    k = np.arange(30)
    ph = poisson.pmf(k[None, :], (lam * extra_time_intensity * 30.0 / minutes)[:, None])
    pa = poisson.pmf(k[None, :], (mu * extra_time_intensity * 30.0 / minutes)[:, None])
    joint = ph[:, :, None] * pa[:, None, :]
    home_et = np.tril(np.ones((30, 30)), -1)  # i > j
    p_home = (joint * home_et[None]).sum(axis=(1, 2))
    p_lvl = np.einsum("wii->w", joint)
    p_adv_level = p_home + penalty_home_win_prob * p_lvl
    out[:, level] = p_adv_level[:, None]
    return out
