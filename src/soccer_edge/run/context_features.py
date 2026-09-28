"""Rest and congestion context (Phase 14) — recorded per fixture, not used by any priced family.

rest_days: days since the team's previous match (any competition we have results for, plus finished fixtures);
matches_14d / matches_28d: matches played in the trailing windows. Point-in-time: only matches with a date
strictly before the fixture's kickoff date count, so a replay of an archived run cannot see the future.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from soccer_edge.identity.models import Fixture, FixtureStatus
from soccer_edge.providers.interfaces import MatchResult


@dataclass(frozen=True)
class RestContext:
    rest_days_home: int | None
    rest_days_away: int | None
    matches_14d_home: int
    matches_14d_away: int
    matches_28d_home: int
    matches_28d_away: int
    rest_gap_days: int | None  # home minus away rest; None if either unknown

    def to_json(self) -> dict[str, int | None]:
        return {
            "rest_days_home": self.rest_days_home,
            "rest_days_away": self.rest_days_away,
            "matches_14d_home": self.matches_14d_home,
            "matches_14d_away": self.matches_14d_away,
            "matches_28d_home": self.matches_28d_home,
            "matches_28d_away": self.matches_28d_away,
            "rest_gap_days": self.rest_gap_days,
        }


def team_match_dates(results: list[MatchResult], fixtures: list[Fixture]) -> dict[str, list[date]]:
    dates: dict[str, set[date]] = defaultdict(set)
    for r in results:
        d = date.fromisoformat(r.match_date)
        dates[r.home_team_id].add(d)
        dates[r.away_team_id].add(d)
    for f in fixtures:
        if f.status in (FixtureStatus.FINISHED, FixtureStatus.LIVE):
            d = date.fromisoformat(f.kickoff_date)
            dates[f.home_team_id].add(d)
            dates[f.away_team_id].add(d)
    return {t: sorted(v) for t, v in dates.items()}


def _features(dates: list[date], on: date) -> tuple[int | None, int, int]:
    prior = [d for d in dates if d < on]
    if not prior:
        return None, 0, 0
    last = prior[-1]
    return (
        (on - last).days,
        sum(1 for d in prior if (on - d).days <= 14),
        sum(1 for d in prior if (on - d).days <= 28),
    )


def rest_contexts(fixtures: list[Fixture], results: list[MatchResult]) -> dict[str, RestContext]:
    tmd = team_match_dates(results, fixtures)
    out: dict[str, RestContext] = {}
    for f in fixtures:
        if f.status not in (FixtureStatus.SCHEDULED, FixtureStatus.LIVE):
            continue
        on = date.fromisoformat(f.kickoff_date)
        rh, m14h, m28h = _features(tmd.get(f.home_team_id, []), on)
        ra, m14a, m28a = _features(tmd.get(f.away_team_id, []), on)
        out[f.fixture_id] = RestContext(
            rh,
            ra,
            m14h,
            m14a,
            m28h,
            m28a,
            (rh - ra) if (rh is not None and ra is not None) else None,
        )
    return out
