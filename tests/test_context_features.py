from __future__ import annotations

from datetime import datetime

from soccer_edge.identity.models import Fixture, FixtureStatus
from soccer_edge.providers.interfaces import MatchResult
from soccer_edge.run.context_features import rest_contexts


def _fx(fid, h, a, d, status=FixtureStatus.SCHEDULED):
    return Fixture(
        fixture_id=fid,
        competition_id="c",
        season_id="s",
        home_team_id=h,
        away_team_id=a,
        kickoff_utc=datetime.fromisoformat(d + "T15:00:00+00:00"),
        kickoff_date=d,
        status=status,
    )


def _res(h, a, d):
    return MatchResult(
        fixture_id=f"r:{h}:{a}:{d}",
        competition_id="c",
        season_id="s",
        match_date=d,
        home_team_id=h,
        away_team_id=a,
        home_goals=1,
        away_goals=0,
    )


def test_rest_and_congestion_are_point_in_time():
    results = [
        _res("A", "B", "2026-09-01"),
        _res("C", "A", "2026-09-05"),
        _res("A", "D", "2026-09-08"),
        _res("B", "C", "2026-09-12"),
        _res("A", "B", "2026-09-30"),
    ]  # last one is AFTER the fixture
    fixtures = [
        _fx("f1", "A", "B", "2026-09-15"),
        _fx("f0", "C", "D", "2026-09-13", FixtureStatus.FINISHED),
        _fx("f2", "E", "A", "2026-09-16"),
    ]
    ctx = rest_contexts(fixtures, results)
    c = ctx["f1"]
    assert (
        c.rest_days_home == 7 and c.rest_days_away == 3
    )  # A last played 09-08, B on 09-12; 09-30 ignored
    assert (
        c.matches_14d_home == 3 and c.matches_28d_home == 3 and c.matches_14d_away == 2
    )  # 09-01 is exactly 14 days out
    assert c.rest_gap_days == 4
    assert ctx["f2"].rest_days_home is None and ctx["f2"].matches_14d_home == 0  # E never seen
    assert "f0" not in ctx  # finished fixtures get no forward-looking context
    assert (
        ctx["f2"].rest_days_away == 8
    )  # A vs the 09-16 fixture; finished fixture C-D on 09-13 counted for C/D only
    assert ctx["f1"].to_json()["rest_gap_days"] == 4
