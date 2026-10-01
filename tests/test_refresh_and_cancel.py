"""Regression tests for the two scheduler cleanups of 2026-10-01:

1. RUN SOCCER refresh trigger: any relevant fixture (any competition) keeps the Kalshi listing fresh; the
   36 h stale-listing spend guard itself is unchanged and still fails closed.
2. Redundant cancelled runs: a wake must recognise a running capture link for its whole lifetime.
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path

from soccer_edge.dispatch.wake import CAPTURE_STALE_AFTER, decide_wake
from soccer_edge.reference.odds_api_capture import SPEND_SCHEDULE_MAX_AGE, capture
from tests.test_odds_api_reference import NOW, FakeProvider, _due

ROOT = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 10, 1, 6, 0, tzinfo=UTC)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sched(*fx):
    return {
        "fixtures": [
            {
                "fixture_id": fid,
                "competition_id": comp,
                "kickoff_utc": ko.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            for fid, comp, ko in fx
        ]
    }


# ------------------------------------------------------------------ 1. refresh trigger


def test_international_break_mls_slate_keeps_listing_fresh():
    dr = _load("decide_run")
    doc = _sched(("fx:usa.mls:2026:usa.seattle:usa.skc", "usa.mls", T0 + timedelta(hours=20)))
    go, reason = dr.decide(
        schedule_doc=doc, openfootball=[{"matches": []}], start=T0, end=T0 + timedelta(hours=48)
    )
    assert go and "usa.mls" in reason and "top5_openfootball=0" in reason


def test_any_supported_competition_counts():
    dr = _load("decide_run")
    for comp in (
        "mex.liga_mx",
        "uefa.champions_league",
        "uefa.nations_league",
        "fifa.friendly",
        "bra.serie_a",
    ):
        doc = _sched((f"fx:{comp}:x:a:b", comp, T0 + timedelta(hours=5)))
        assert dr.decide(
            schedule_doc=doc, openfootball=None, start=T0, end=T0 + timedelta(hours=48)
        )[0]


def test_empty_schedule_no_run_and_no_paid_call(tmp_path):
    dr = _load("decide_run")
    far = _sched(("fx:usa.mls:2026:a:b", "usa.mls", T0 + timedelta(days=5)))  # outside the window
    for doc in ({"fixtures": []}, far):
        go, _ = dr.decide(
            schedule_doc=doc, openfootball=[{"matches": []}], start=T0, end=T0 + timedelta(hours=48)
        )
        assert go is False
    # and the dispatcher on an empty schedule makes no provider request at all
    assert (
        decide_wake([], "2026-10-01T06:00:00Z", [], [], [], now=T0).no_action_reason
        == "NO_WORK_DUE"
    )
    fp = FakeProvider()
    st = capture(
        [],
        registry=None,
        out_root=tmp_path,
        cfg=None,
        now=NOW,
        batch_id="e",
        client_factory=fp.factory(),
    )
    assert st["status"] == "NOTHING_ELIGIBLE" and fp.requests == []


def test_top5_source_still_counts_and_unreadable_sources_run_anyway():
    dr = _load("decide_run")
    of = [{"matches": [{"date": "2026-10-03", "time": "15:00"}]}]
    assert dr.decide(
        schedule_doc={"fixtures": []}, openfootball=of, start=T0, end=T0 + timedelta(hours=72)
    )[0]
    go, reason = dr.decide(
        schedule_doc=None, openfootball=None, start=T0, end=T0 + timedelta(hours=48)
    )
    assert go and "unreadable" in reason


def test_stale_listing_guard_unchanged_and_fails_closed(tmp_path):
    from soccer_edge.identity.registry import AliasRegistry
    from soccer_edge.reference.odds_budget import BudgetConfig

    assert timedelta(hours=36) == SPEND_SCHEDULE_MAX_AGE
    fp = FakeProvider()
    st = capture(
        _due(),
        registry=AliasRegistry.from_directory(ROOT / "data" / "registry"),
        out_root=tmp_path,
        cfg=BudgetConfig.load(ROOT / "config" / "odds_api_budget.json"),
        now=NOW,
        batch_id="s",
        client_factory=fp.factory(),
        schedule_as_of=NOW - timedelta(hours=36, minutes=1),
        claim_fn=lambda ids, rec: set(ids),
    )
    assert fp.paid() == [] and st["per_sport"]["soccer_epl"]["status"].endswith("STALE_SCHEDULE")


# ------------------------------------------------------------------ 2. redundant cancelled runs


def _fake_api(started_minutes_ago, now):
    started = (now - timedelta(minutes=started_minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def api(method, path, body=None):
        if path.endswith("runs?status=in_progress&per_page=20"):
            return 200, {"workflow_runs": [{"id": 111}]}
        if path.endswith("/runs/111/jobs"):
            return 200, {
                "jobs": [{"name": "capture", "status": "in_progress", "started_at": started}]
            }
        return 404, None

    return api


def test_wake_sees_a_running_link_for_its_whole_lifetime(monkeypatch):
    kd = _load("kickoff_decide")
    assert timedelta(minutes=350) < CAPTURE_STALE_AFTER  # longer than the capture job timeout
    # 2026-10-01 00:11: the link had been running 51 min; the old 50 min limit treated it as stale
    for age in (51, 170, 345):
        monkeypatch.setattr(kd, "_api", _fake_api(age, T0))
        assert kd._capture_in_progress("o/r", "999", T0) is True
    # a job lingering beyond any possible link is ignored (a crashed run must not block the chain forever)
    monkeypatch.setattr(kd, "_api", _fake_api(400, T0))
    assert kd._capture_in_progress("o/r", "999", T0) is False
    # and the wake then does not queue a second link
    fx = [
        __import__("soccer_edge.dispatch.horizons", fromlist=["x"]).ScheduledFixture(
            "fx:usa.mls:2026:a:b", T0 + timedelta(hours=14), "usa.mls", "run_output", 3
        )
    ]
    d = decide_wake(fx, "2026-10-01T06:00:00Z", [], [], [], now=T0, capture_in_progress=True)
    assert d.capture is False and d.no_action_reason == "CAPTURE_IN_PROGRESS"
