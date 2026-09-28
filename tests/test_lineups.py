from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from soccer_edge.model.context import LineupState
from soccer_edge.model.lineups import (
    LineupObservation,
    LineupStateTracker,
    estimate_team,
    observations_from_snapshots,
)

T0 = datetime(2026, 10, 10, 15, tzinfo=UTC)


def _hist():
    obs = []
    for k in range(6):  # six team sheets, weekly
        ko = T0 - timedelta(days=7 * (k + 1))
        for pid, started, in_squad in (
            ("a", True, True),
            ("b", k % 2 == 0, True),
            ("c", False, True),
            ("d", False, k < 2),
        ):
            obs.append(LineupObservation(pid, "eng.arsenal", f"ev{k}", ko, started, in_squad))
    return obs


def test_unconfirmed_estimates_are_shrunk_and_ordered():
    state, est = estimate_team(_hist(), team_id="eng.arsenal", as_of=T0)
    assert state is LineupState.UNKNOWN
    by = {e.player_id: e for e in est}
    assert 0.85 < by["a"].p_start < 1.0  # ever-present starter, shrunk toward prior
    assert 0.35 < by["b"].p_start < 0.7  # rotates
    assert by["c"].p_start < 0.2 and by["c"].p_bench > 0.6  # bench regular
    assert by["d"].p_unavailable > 0.4  # dropped from the last four sheets
    assert est[0].player_id == "a"
    for e in est:
        assert abs(e.p_start + e.p_bench + e.p_unavailable - 1) < 1e-9
        assert e.exp_minutes_if_start == 80.0 and e.exp_minutes_if_bench == 15.0


def test_confirmed_xi_is_deterministic_and_future_history_is_refused():
    state, est = estimate_team(
        _hist(), team_id="eng.arsenal", as_of=T0, confirmed_xi={"a": True, "c": False}
    )
    assert state is LineupState.CONFIRMED
    assert {e.player_id: e.p_start for e in est} == {"a": 1.0, "c": 0.0}
    bad = _hist() + [
        LineupObservation("z", "eng.arsenal", "future", T0 + timedelta(hours=1), True, True)
    ]
    with pytest.raises(ValueError, match="backward leakage"):
        estimate_team(bad, team_id="eng.arsenal", as_of=T0)


def test_observations_from_snapshots_take_last_published_per_event():
    rows = [
        {
            "espn_event_id": "1",
            "published": True,
            "captured_at": "2026-10-01T12:00:00+00:00",
            "kickoff_utc": "2026-10-01T14:00:00+00:00",
            "home_espn_id": "359",
            "away_espn_id": "364",
            "home": [{"athlete_id": "p1", "starter": True}],
            "away": [{"athlete_id": "p9", "starter": False}],
        },
        {
            "espn_event_id": "1",
            "published": True,
            "captured_at": "2026-10-01T16:30:00+00:00",
            "kickoff_utc": "2026-10-01T14:00:00+00:00",
            "home_espn_id": "359",
            "away_espn_id": "364",
            "home": [{"athlete_id": "p1", "starter": True}, {"athlete_id": "p2", "starter": False}],
            "away": [],
        },
        {
            "espn_event_id": "2",
            "published": False,
            "captured_at": "2026-10-02T10:00:00+00:00",
            "kickoff_utc": "2026-10-02T14:00:00+00:00",
            "home_espn_id": "359",
            "away_espn_id": "1",
            "home": [],
            "away": [],
        },
    ]
    obs = observations_from_snapshots(rows, {"359": "eng.arsenal", "364": "eng.liverpool"})
    assert {(o.player_id, o.team_id, o.started) for o in obs} == {
        ("espn:p1", "eng.arsenal", True),
        ("espn:p2", "eng.arsenal", False),
    }


def test_state_tracker_records_transitions_once():
    tr = LineupStateTracker()
    ko = T0
    assert tr.observe(
        "f1", "unconfirmed", ko - timedelta(hours=6), source="espn", minutes_to_kickoff=360
    )
    assert not tr.observe(
        "f1", "unconfirmed", ko - timedelta(hours=3), source="espn", minutes_to_kickoff=180
    )
    assert tr.observe(
        "f1", "confirmed", ko - timedelta(minutes=70), source="espn", minutes_to_kickoff=70
    )
    assert tr.transitions[-1]["previous"] == "unconfirmed"
    assert tr.confirmation_lead_minutes() == [70.0]
