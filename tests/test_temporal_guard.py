"""No-future-information guard (remediation phase 5): unit + property tests."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from soccer_edge.core.temporal import (
    GUARDED_KINDS,
    FutureInformationError,
    TemporalGuard,
    assert_no_future_dates,
)
from soccer_edge.model.strength import DixonColesFitter, MatchRow

T0 = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)


def test_equal_is_allowed_later_is_not():
    g = TemporalGuard(T0)
    g.check(T0, "fixtures", "f")
    g.check(T0 - timedelta(seconds=1), "lineups", "l")
    g.check("2026-09-28T11:59:59Z", "weather", "w")
    with pytest.raises(FutureInformationError):
        g.check(T0 + timedelta(microseconds=1), "reference_odds", "r")
    rep = g.report()
    assert rep["ok"] is False and rep["violations"][0]["kind"] == "reference_odds"
    assert rep["checked"] == {"fixtures": 1, "lineups": 1, "reference_odds": 1, "weather": 1}


def test_none_is_skipped_and_naive_rejected():
    g = TemporalGuard(T0)
    g.check(None, "results")
    assert g.report()["checked"] == {}
    with pytest.raises(ValueError):
        g.check(datetime(2026, 9, 28, 11), "results")


def test_check_all_and_non_fail_fast_mode():
    g = TemporalGuard(T0, fail_fast=False)
    rows = [{"id": i, "obs": T0 + timedelta(minutes=i - 2)} for i in range(5)]
    n = g.check_all(
        rows, "market_snapshots", observed_at=lambda r: r["obs"], ref=lambda r: str(r["id"])
    )
    assert n == 5 and [v["ref"] for v in g.violations] == ["3", "4"]


@settings(max_examples=200, deadline=None)
@given(
    offsets=st.lists(st.integers(min_value=-10_000, max_value=10_000), min_size=1, max_size=30),
    kind=st.sampled_from(GUARDED_KINDS),
)
def test_property_guard_raises_iff_any_observation_is_after_decision(offsets, kind):
    g = TemporalGuard(T0)
    expect_raise = any(o > 0 for o in offsets)
    raised = False
    try:
        for o in offsets:
            g.check(T0 + timedelta(seconds=o), kind)
    except FutureInformationError:
        raised = True
    assert raised == expect_raise


@settings(max_examples=100, deadline=None)
@given(days=st.lists(st.integers(min_value=-400, max_value=30), min_size=1, max_size=50))
def test_property_date_guard(days):
    d0 = date(2026, 9, 28)
    ds = [d0 + timedelta(days=k) for k in days]
    if any(k >= 0 for k in days):
        with pytest.raises(FutureInformationError):
            assert_no_future_dates(ds, d0)
    else:
        assert assert_no_future_dates(ds, d0) == len(ds)


def _rows(n=60, start=date(2026, 1, 1)):
    teams = [f"t{i}" for i in range(6)]
    out = []
    for k in range(n):
        h, a = teams[k % 6], teams[(k * 5 + 1) % 6]
        if h == a:
            a = teams[(k + 1) % 6]
        out.append(MatchRow(start + timedelta(days=k), h, a, k % 3, (k + 1) % 2))
    return out


def test_fitter_strict_mode_refuses_a_future_result_but_lenient_drops_it():
    rows = _rows()
    as_of = rows[-1].date  # the last row is dated ON the decision date → future information
    post = DixonColesFitter().fit(rows, as_of=as_of)  # legacy behaviour: silently dropped
    assert post.n_matches == len(rows) - 1
    with pytest.raises(FutureInformationError):
        DixonColesFitter().fit(rows, as_of=as_of, strict_point_in_time=True)
    post2 = DixonColesFitter().fit(rows[:-1], as_of=as_of, strict_point_in_time=True)
    assert post2.n_matches == len(rows) - 1


def test_fit_competition_is_strict(monkeypatch):
    from soccer_edge.run import modeling

    seen = {}

    class _Fitter:
        def __init__(self, cfg=None):
            pass

        def fit(self, rows, *, as_of, teams=None, strict_point_in_time=False):
            seen["strict"] = strict_point_in_time
            raise RuntimeError("stop")

    monkeypatch.setattr(modeling, "DixonColesFitter", _Fitter)
    with pytest.raises(RuntimeError):
        modeling.fit_competition("c", [], as_of=date(2026, 9, 28))
    assert seen["strict"] is True
