"""Assemble point-in-time model inputs per competition and fit the DATA_ONLY posterior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from soccer_edge.core.time import utc_now
from soccer_edge.identity.models import Fixture
from soccer_edge.model.strength import (
    DixonColesFitter,
    MatchRow,
    ParameterPosterior,
    StrengthConfig,
)
from soccer_edge.providers.interfaces import MatchResult


@dataclass
class CompetitionModel:
    competition_id: str
    posterior: ParameterPosterior
    fitted_at: datetime
    results_used: int
    latest_result_date: date | None
    teams_missing: list[str]


def rows_from_results(results: list[MatchResult]) -> list[MatchRow]:
    return [
        MatchRow(
            date.fromisoformat(r.match_date),
            r.home_team_id,
            r.away_team_id,
            r.home_goals,
            r.away_goals,
        )
        for r in results
    ]


def fit_competition(
    competition_id: str,
    results: list[MatchResult],
    *,
    as_of: date,
    fixtures: list[Fixture] | None = None,
    config: StrengthConfig | None = None,
    lookback_days: int = 730,
) -> CompetitionModel:
    rows = [
        r
        for r in rows_from_results(results)
        if (as_of - r.date).days <= lookback_days and r.date < as_of
    ]
    teams = sorted(
        {f.home_team_id for f in fixtures or []} | {f.away_team_id for f in fixtures or []}
    )
    post = DixonColesFitter(config).fit(
        rows, as_of=as_of, teams=teams or None, strict_point_in_time=True
    )
    known = set(post.teams)
    missing = [t for t in teams if t not in known]
    latest = max((r.date for r in rows), default=None)
    return CompetitionModel(competition_id, post, utc_now(), len(rows), latest, missing)
