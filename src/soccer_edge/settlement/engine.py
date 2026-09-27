"""Pure settlement: (Semantics, official result) -> YES/NO/VOID/REFUSED with evidence.

Refusal-first: when the result lacks what the contract needs (e.g. no HT score for a first-half
contract, abandoned match, unknown ET rule) we REFUSE rather than guess. Kalshi's own `result`
is stored as a cross-check, never as the primary settlement input.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from soccer_edge.identity.models import FixtureStatus
from soccer_edge.kalshi.taxonomy import MarketFamily, Period
from soccer_edge.pricing.semantics import Semantics


class SettlementOutcome(str, Enum):
    YES = "yes"
    NO = "no"
    VOID = "void"
    REFUSED_NO_RESULT = "refused_no_result"
    REFUSED_ABANDONED = "refused_abandoned"
    REFUSED_MISSING_PERIOD_DATA = "refused_missing_period_data"
    REFUSED_UNSUPPORTED = "refused_unsupported"
    REFUSED_PLAYER_DATA = "refused_player_data"


@dataclass(frozen=True)
class OfficialResult:
    fixture_id: str
    status: FixtureStatus
    home_ft: int | None
    away_ft: int | None
    home_ht: int | None = None
    away_ht: int | None = None
    home_et: int | None = None  # goals in extra time only
    away_et: int | None = None
    winner_after_pens: str | None = None  # 'home' | 'away' | None
    first_scorer_team: str | None = None
    player_goals: dict[str, int] | None = None  # player_id -> goals (regulation)
    source: str = ""
    observed_at: datetime | None = None


@dataclass(frozen=True)
class Settlement:
    ticker: str
    outcome: SettlementOutcome
    evidence: dict[str, Any]
    kalshi_result: str | None = None
    agrees_with_kalshi: bool | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "outcome": self.outcome.value,
            "evidence": self.evidence,
            "kalshi_result": self.kalshi_result,
            "agrees_with_kalshi": self.agrees_with_kalshi,
        }


def settle(
    sem: Semantics,
    res: OfficialResult,
    *,
    player_id: str | None = None,
    kalshi_result: str | None = None,
) -> Settlement:
    ev: dict[str, Any] = {
        "fixture_id": res.fixture_id,
        "status": res.status.value,
        "source": res.source,
    }
    if res.status in (FixtureStatus.ABANDONED, FixtureStatus.CANCELLED):
        return _fin(sem, SettlementOutcome.REFUSED_ABANDONED, ev, kalshi_result)
    if res.status is not FixtureStatus.FINISHED or res.home_ft is None or res.away_ft is None:
        return _fin(sem, SettlementOutcome.REFUSED_NO_RESULT, ev, kalshi_result)
    if sem.period is Period.FIRST_HALF:
        if res.home_ht is None or res.away_ht is None:
            return _fin(sem, SettlementOutcome.REFUSED_MISSING_PERIOD_DATA, ev, kalshi_result)
        h, a = res.home_ht, res.away_ht
    elif sem.period is Period.SECOND_HALF:
        if res.home_ht is None or res.away_ht is None:
            return _fin(sem, SettlementOutcome.REFUSED_MISSING_PERIOD_DATA, ev, kalshi_result)
        h, a = res.home_ft - res.home_ht, res.away_ft - res.away_ht
    elif sem.period in (Period.INCLUDING_ET, Period.INCLUDING_PENS):
        h = res.home_ft + (res.home_et or 0)
        a = res.away_ft + (res.away_et or 0)
    else:
        h, a = res.home_ft, res.away_ft
    ev.update({"home": h, "away": a, "period": sem.period.value})
    fam = sem.family
    line = float(sem.line) if sem.line is not None else None
    yes: bool | None
    if fam in (MarketFamily.TOTAL_GOALS, MarketFamily.FIRST_HALF_TOTAL):
        yes = (h + a) > line
    elif fam is MarketFamily.TEAM_TOTAL:
        yes = (h if sem.side == "home" else a) > line
    elif fam is MarketFamily.HANDICAP:
        yes = ((h - a) if sem.side == "home" else (a - h)) > line
    elif fam in (
        MarketFamily.MATCH_RESULT_3WAY,
        MarketFamily.FIRST_HALF_RESULT,
        MarketFamily.SECOND_HALF_RESULT,
    ):
        yes = {"home": h > a, "away": a > h, "draw": h == a}[sem.side or "draw"]
    elif fam in (MarketFamily.EXACT_SCORE, MarketFamily.FIRST_HALF_EXACT_SCORE):
        hh, aa = divmod(int(sem.k or 0), 100)
        yes = h == hh and a == aa
    elif fam in (MarketFamily.FIRST_HALF_BTTS,):
        yes = h > 0 and a > 0
    elif fam in (MarketFamily.FIRST_HALF_HANDICAP,):
        yes = ((h - a) if sem.side == "home" else (a - h)) > line
    elif fam in (MarketFamily.FIRST_HALF_TEAM_TOTAL,):
        yes = (h if sem.side == "home" else a) > line
    elif fam is MarketFamily.BTTS:
        yes = h > 0 and a > 0
    elif fam is MarketFamily.CLEAN_SHEET:
        yes = (a == 0) if sem.side == "home" else (h == 0)
    elif fam is MarketFamily.DRAW_NO_BET:
        if h == a:
            return _fin(sem, SettlementOutcome.VOID, ev, kalshi_result)
        yes = (h > a) if sem.side == "home" else (a > h)
    elif fam is MarketFamily.MATCH_WINNER_2WAY:
        w = res.winner_after_pens or ("home" if h > a else "away" if a > h else None)
        if w is None:
            return _fin(sem, SettlementOutcome.REFUSED_MISSING_PERIOD_DATA, ev, kalshi_result)
        yes = w == sem.side
    elif fam is MarketFamily.FIRST_TO_SCORE:
        if res.first_scorer_team is None:
            return _fin(sem, SettlementOutcome.REFUSED_MISSING_PERIOD_DATA, ev, kalshi_result)
        yes = res.first_scorer_team == sem.side
    elif fam is MarketFamily.PLAYER_GOALS:
        if res.player_goals is None or player_id is None or player_id not in res.player_goals:
            return _fin(sem, SettlementOutcome.REFUSED_PLAYER_DATA, ev, kalshi_result)
        yes = res.player_goals[player_id] >= (sem.k or 1)
    else:
        return _fin(sem, SettlementOutcome.REFUSED_UNSUPPORTED, ev, kalshi_result)
    return _fin(sem, SettlementOutcome.YES if yes else SettlementOutcome.NO, ev, kalshi_result)


def _fin(
    sem: Semantics, outcome: SettlementOutcome, ev: dict[str, Any], kalshi_result: str | None
) -> Settlement:
    agrees = None
    if kalshi_result in ("yes", "no") and outcome in (SettlementOutcome.YES, SettlementOutcome.NO):
        agrees = kalshi_result == outcome.value
    return Settlement(sem.ticker, outcome, ev, kalshi_result, agrees)
