"""Deterministic settlement semantics: ContractSpec + fixture association -> YES indicator array.

The mapping is declarative and *does not read titles* for settlement: family, side, line, period
come from the classified spec; the fixture association tells us which physical team is 'home'.
Unsupported combinations raise `UnsupportedSemantics` so coverage can disposition them.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np

from soccer_edge.kalshi.taxonomy import ContractSpec, MarketFamily, Period
from soccer_edge.sim.outcome import JointOutcome


class UnsupportedSemantics(Exception):
    pass


@dataclass(frozen=True)
class Semantics:
    """Resolved semantics for one contract against one fixture."""

    ticker: str
    family: MarketFamily
    period: Period
    side: str | None  # 'home' | 'away' | 'draw' | None
    line: Decimal | None
    k: int | None = None
    player_slot: tuple[str, int] | None = None  # ('home'|'away', index into world player arrays)
    description: str = ""

    def settle(self, out: JointOutcome) -> np.ndarray:
        return settle_indicator(self, out)


def resolve_semantics(
    spec: ContractSpec, *, side_is_home: bool | None, player_slot: tuple[str, int] | None = None
) -> Semantics:
    fam = spec.family
    side: str | None
    if fam in (
        MarketFamily.HANDICAP,
        MarketFamily.TEAM_TOTAL,
        MarketFamily.CLEAN_SHEET,
        MarketFamily.DRAW_NO_BET,
        MarketFamily.MATCH_WINNER_2WAY,
    ):
        if side_is_home is None:
            raise UnsupportedSemantics(
                f"{spec.ticker}: side team could not be resolved to home/away"
            )
        side = "home" if side_is_home else "away"
    elif fam is MarketFamily.MATCH_RESULT_3WAY:
        if spec.side_team_code == "DRAW":
            side = "draw"
        elif side_is_home is None:
            raise UnsupportedSemantics(f"{spec.ticker}: result leg team unresolved")
        else:
            side = "home" if side_is_home else "away"
    elif fam is MarketFamily.PLAYER_GOALS:
        if player_slot is None:
            raise UnsupportedSemantics(f"{spec.ticker}: player not in lineup model")
        side = player_slot[0]
    else:
        side = None
    if (
        fam
        in (
            MarketFamily.TOTAL_GOALS,
            MarketFamily.TEAM_TOTAL,
            MarketFamily.HANDICAP,
            MarketFamily.FIRST_HALF_TOTAL,
        )
        and spec.line is None
    ):
        raise UnsupportedSemantics(f"{spec.ticker}: missing line")
    if fam not in SUPPORTED:
        raise UnsupportedSemantics(f"{spec.ticker}: family {fam.value} has no pricer")
    if spec.period not in (
        Period.REGULATION,
        Period.FIRST_HALF,
        Period.INCLUDING_PENS,
        Period.INCLUDING_ET,
    ):
        raise UnsupportedSemantics(f"{spec.ticker}: period {spec.period.value} unsupported")
    return Semantics(
        spec.ticker,
        fam,
        spec.period,
        side,
        spec.line,
        spec.k,
        player_slot,
        description=_describe(fam, side, spec),
    )


SUPPORTED = frozenset(
    {
        MarketFamily.MATCH_RESULT_3WAY,
        MarketFamily.HANDICAP,
        MarketFamily.TOTAL_GOALS,
        MarketFamily.TEAM_TOTAL,
        MarketFamily.BTTS,
        MarketFamily.CLEAN_SHEET,
        MarketFamily.DRAW_NO_BET,
        MarketFamily.FIRST_HALF_TOTAL,
        MarketFamily.FIRST_HALF_RESULT,
        MarketFamily.MATCH_WINNER_2WAY,
        MarketFamily.FIRST_TO_SCORE,
        MarketFamily.PLAYER_GOALS,
    }
)


def _describe(fam: MarketFamily, side: str | None, spec: ContractSpec) -> str:
    if fam is MarketFamily.TOTAL_GOALS:
        return f"Total goals over {spec.line}"
    if fam is MarketFamily.TEAM_TOTAL:
        return f"{side} team total over {spec.line}"
    if fam is MarketFamily.HANDICAP:
        return f"{side} wins by more than {spec.line}"
    if fam is MarketFamily.MATCH_RESULT_3WAY:
        return f"Result: {side}"
    if fam is MarketFamily.PLAYER_GOALS:
        return f"{spec.player_name or spec.player_code}: {spec.k}+ goals"
    return fam.value


def _period_goals(sem: Semantics, out: JointOutcome) -> tuple[np.ndarray, np.ndarray]:
    if sem.period is Period.FIRST_HALF:
        return out.home_ht, out.away_ht
    if sem.period in (Period.INCLUDING_ET, Period.INCLUDING_PENS):
        return out.home_full, out.away_full
    return out.home_ft, out.away_ft


def settle_indicator(sem: Semantics, out: JointOutcome) -> np.ndarray:
    h, a = _period_goals(sem, out)
    fam = sem.family
    line = float(sem.line) if sem.line is not None else None
    if fam is MarketFamily.TOTAL_GOALS or fam is MarketFamily.FIRST_HALF_TOTAL:
        return (h + a) > line
    if fam is MarketFamily.TEAM_TOTAL:
        g = h if sem.side == "home" else a
        return g > line
    if fam is MarketFamily.HANDICAP:
        margin = (h - a) if sem.side == "home" else (a - h)
        return margin > line
    if fam is MarketFamily.MATCH_RESULT_3WAY or fam is MarketFamily.FIRST_HALF_RESULT:
        if sem.side == "home":
            return h > a
        if sem.side == "away":
            return a > h
        return h == a
    if fam is MarketFamily.BTTS:
        return (h > 0) & (a > 0)
    if fam is MarketFamily.CLEAN_SHEET:
        return (a == 0) if sem.side == "home" else (h == 0)
    if fam is MarketFamily.DRAW_NO_BET:
        # YES iff side wins; draws void -> represented as NaN-free by returning win indicator with
        # push mask handled by caller (kalshi has no push; DNB contracts would settle 50/50 or void)
        return (h > a) if sem.side == "home" else (a > h)
    if fam is MarketFamily.MATCH_WINNER_2WAY:
        return out.winner_final == (1 if sem.side == "home" else 2)
    if fam is MarketFamily.FIRST_TO_SCORE:
        return out.first_goal_team == (1 if sem.side == "home" else 2)
    if fam is MarketFamily.PLAYER_GOALS:
        arr = out.home_player_goals if sem.side == "home" else out.away_player_goals
        if arr is None or sem.player_slot is None:
            raise UnsupportedSemantics(f"{sem.ticker}: no player goal allocation available")
        return arr[:, sem.player_slot[1]] >= (sem.k or 1)
    raise UnsupportedSemantics(f"{sem.ticker}: no settlement rule for {fam.value}")
