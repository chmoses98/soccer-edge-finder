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
from soccer_edge.model.strength_v2 import DixonColesFitterV2, StrengthConfigV2
from soccer_edge.providers.interfaces import MatchResult


@dataclass
class CompetitionModel:
    competition_id: str
    posterior: ParameterPosterior
    fitted_at: datetime
    results_used: int
    latest_result_date: date | None
    teams_missing: list[str]
    # per team: schedule strength and raw form over the fit window (gamescript/matchup.py; display only)
    team_context: dict[str, dict] | None = None


def rows_from_results(results: list[MatchResult]) -> list[MatchRow]:
    return [
        MatchRow(
            date.fromisoformat(r.match_date),
            r.home_team_id,
            r.away_team_id,
            r.home_goals,
            r.away_goals,
            neutral=bool(r.neutral_site),
        )
        for r in results
    ]


def fit_competition(
    competition_id: str,
    results: list[MatchResult],
    *,
    as_of: date,
    fixtures: list[Fixture] | None = None,
    config: StrengthConfig | StrengthConfigV2 | None = None,
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
    if isinstance(config, StrengthConfigV2):
        post = DixonColesFitterV2(config).fit(
            rows, as_of=as_of, teams=teams or None, strict_point_in_time=True
        )
    else:
        post = DixonColesFitter(config).fit(
            rows, as_of=as_of, teams=teams or None, strict_point_in_time=True
        )
    known = set(post.teams)
    missing = [t for t in teams if t not in known]
    latest = max((r.date for r in rows), default=None)
    try:
        from soccer_edge.gamescript.matchup import team_context_from_rows

        team_ctx = team_context_from_rows(
            rows,
            post,
            as_of=as_of,
            decay_per_day=float(getattr(post.config, "decay_per_day", 0.0065)),
        )
    except Exception:  # display-only context never blocks a fit
        team_ctx = None
    return CompetitionModel(competition_id, post, utc_now(), len(rows), latest, missing, team_ctx)
