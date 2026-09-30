"""Scheduler reliability repair (docs/SCHEDULER.md): one canonical dispatcher, explicit horizon states,
race-safe paid-call claims, settlement dispatch, heartbeats and reliability metrics."""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from soccer_edge.dispatch.gitstore import ArchiveAppender, ClaimStore, GitStoreError
from soccer_edge.dispatch.horizons import (
    DELIVERED,
    MISSED_BEFORE_WAKE,
    MISSED_EXECUTION_FAILURE,
    NOT_APPLICABLE,
    HorizonRow,
    ScheduledFixture,
    classify_missed,
    delivered_rows,
    plan,
)
from soccer_edge.dispatch.reliability import reliability
from soccer_edge.dispatch.wake import (
    EXTERNAL,
    GITHUB_BACKUP,
    MANUAL,
    decide_wake,
    normalize_source,
    redact,
    settle_due,
)
from soccer_edge.reference.close_attempts import close_attempt_states
from soccer_edge.reference.odds_api_capture import capture
from soccer_edge.reference.odds_budget import BudgetLedger
from tests.test_odds_api_reference import KO, NOW, FakeProvider, _due

ROOT = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def _fx(fid="fx:eng.premier_league:2026-27:eng.arsenal:eng.chelsea", ko=None, source="run_output"):
    return ScheduledFixture(fid, ko or T0 + timedelta(hours=3), "eng.premier_league", source, 40)


def _gen(now):
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------ decision (every trigger, same logic)


def test_nothing_due_is_a_normal_no_op():
    fx = _fx(ko=T0 + timedelta(hours=5))  # next window (T-120) opens in 2h50
    d = decide_wake([fx], _gen(T0), [], [], [], now=T0)
    assert d.capture is False and d.settle is False
    assert d.no_action_reason == "NO_WORK_DUE"
    assert d.next_window_minutes == pytest.approx(170, abs=0.1)


def test_one_horizon_due_requests_capture():
    fx = _fx(ko=T0 + timedelta(minutes=58))
    d = decide_wake([fx], _gen(T0), [], [], [], now=T0)
    assert d.capture and d.n_due == 1 and d.due[0][1] == 60
    # the missed T-120 window is logged, not silently dropped
    assert d.n_missed == 1


def test_two_horizons_caught_in_one_delayed_wake_one_batch():
    fx = _fx(ko=T0 + timedelta(minutes=6))  # inside both (5,17] and (0,7]
    due, missed, _ = plan([fx], [], now=T0)
    assert sorted(d.horizon for d in due) == [5, 15]
    rows = delivered_rows(due, now=T0, batch_id="kd-x", actions=["kalshi_capture:ok"])
    assert {r.state for r in rows} == {DELIVERED} and {r.batch_id for r in rows} == {"kd-x"}
    assert sorted(r.horizon for r in missed) == [30, 60, 120]


def test_after_kickoff_no_pregame_observation_is_manufactured():
    fx = _fx(ko=T0 - timedelta(minutes=1))
    due, missed, _ = plan([fx], [], now=T0)
    assert due == [] and sorted(r.horizon for r in missed) == [5, 15, 30, 60, 120]


def test_missed_states_are_explicit():
    ko = T0
    rows = lambda: [HorizonRow("fx:a:s:h:a", _gen(ko), 15, "missed", _gen(ko))]
    # no wake inside (ko-17, ko-5] -> the scheduler never fired
    (r,) = classify_missed(rows(), [ko - timedelta(minutes=30)], {})
    assert r.state == MISSED_BEFORE_WAKE
    # a wake landed inside the window but nothing was delivered -> execution failure
    (r,) = classify_missed(rows(), [ko - timedelta(minutes=10)], {})
    assert r.state == MISSED_EXECUTION_FAILURE
    # first scheduled after the window closed -> not applicable
    (r,) = classify_missed(rows(), [], {"fx:a:s:h:a": _gen(ko - timedelta(minutes=2))})
    assert r.state == NOT_APPLICABLE


def test_trigger_source_does_not_change_the_decision():
    fx = _fx(ko=T0 + timedelta(minutes=14))
    base = decide_wake([fx], _gen(T0), [], [], [], now=T0)
    assert normalize_source("workflow_dispatch", "external-heartbeat") == EXTERNAL
    assert normalize_source("schedule", "external-heartbeat") == GITHUB_BACKUP
    assert normalize_source("workflow_dispatch", "rm -rf /; $(x)") == MANUAL
    assert normalize_source("repository_dispatch", None) == "repository-dispatch"
    # decide_wake takes no source at all: external heartbeat, backup cron and manual runs share it
    assert "source" not in decide_wake.__code__.co_varnames[: decide_wake.__code__.co_argcount]
    assert base.capture and base.n_due == 1 and base.due[0][1] == 15


def test_capture_in_progress_is_not_queued_twice_and_stale_schedule_refreshes():
    fx = _fx(ko=T0 + timedelta(minutes=14))
    d = decide_wake([fx], _gen(T0), [], [], [], now=T0, capture_in_progress=True)
    assert d.capture is False and d.no_action_reason == "CAPTURE_IN_PROGRESS"
    d = decide_wake([], _gen(T0 - timedelta(hours=4)), [], [], [], now=T0)
    assert d.capture and any("stale" in r for r in d.reasons)


# ------------------------------------------------------------------ settlement dispatch


def _log_row(fid, ko):
    return HorizonRow(fid, _gen(ko), 5, "delivered", _gen(ko), state=DELIVERED)


def test_settlement_due_is_dispatched_once_then_noop():
    ko = T0 - timedelta(hours=4)
    log = [_log_row("fx:x:s:h:a", ko)]
    due, _, fx = settle_due(log, [], [], now=T0)
    assert due and fx == ["fx:x:s:h:a"]
    hb = [
        {"phase": "wake", "started_at": _gen(T0 - timedelta(minutes=5)), "settle_dispatched": True}
    ]
    assert settle_due(log, [], hb, now=T0)[0] is False  # already dispatched: dedupe window
    runs = [
        {"status": "ok", "started_at": _gen(T0 - timedelta(minutes=30)), "pending_fixtures": []}
    ]
    assert settle_due(log, runs, [], now=T0)[0] is False  # settled after the fixture finished
    # results not ready at that run: retried, but only once the retry interval has passed
    runs = [
        {
            "status": "ok",
            "started_at": _gen(T0 - timedelta(hours=1)),
            "pending_fixtures": [{"fixture_id": "fx:x:s:h:a", "kickoff_utc": _gen(ko)}],
        }
    ]
    assert settle_due(log, runs, [], now=T0)[0] is False
    assert settle_due(log, runs, [], now=T0 + timedelta(hours=2, minutes=1))[0] is True


def test_settlement_not_due_before_grace():
    log = [_log_row("fx:x:s:h:a", T0 - timedelta(hours=2))]
    assert settle_due(log, [], [], now=T0)[0] is False


# ------------------------------------------------------------------ race-safe claims (real git)


def _git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def archive_remote(tmp_path):
    bare = tmp_path / "remote.git"
    _git("init", "-q", "--bare", str(bare))
    seed = tmp_path / "seed"
    _git("init", "-q", str(seed))
    _git(
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "seed",
        cwd=seed,
    )
    (seed / "README.md").write_text("archive\n")
    _git("add", "README.md", cwd=seed)
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "readme", cwd=seed)
    _git("push", "-q", str(bare), "HEAD:refs/heads/data-archive", cwd=seed)
    return f"file://{bare}"


def test_claims_first_writer_wins(archive_remote, tmp_path):
    a = ClaimStore(archive_remote, workdir=tmp_path / "a")
    b = ClaimStore(archive_remote, workdir=tmp_path / "b")
    assert a.claim(["x", "y"], {"batch_id": "A"}) == {"x", "y"}
    assert b.claim(["y", "z"], {"batch_id": "B"}) == {"z"}
    assert a.claim(["x"], {"batch_id": "A2"}) == set()  # the same heartbeat twice: no second claim


def test_simultaneous_dispatchers_make_one_paid_call(archive_remote, tmp_path, monkeypatch):
    """Two dispatcher runs race for the same due close (separate runners = separate ledgers); the shared
    claim on data-archive lets exactly one of them pay."""
    import soccer_edge.reference.odds_api_capture as cap
    from soccer_edge.identity.registry import AliasRegistry
    from soccer_edge.reference.odds_budget import BudgetConfig

    registry = AliasRegistry.from_directory(ROOT / "data" / "registry")
    cfg = BudgetConfig.load(ROOT / "config" / "odds_api_budget.json")
    fp = FakeProvider()
    lock = threading.Lock()
    inner = fp.handler

    def handler(request):  # the fake provider is shared; serialise its counters only
        with lock:
            return inner(request)

    fp.handler = handler
    barrier = threading.Barrier(2)
    real_claim = ClaimStore.claim

    def synced_claim(self, ids, meta, namespace="odds_api"):
        barrier.wait(timeout=30)  # both runs reach the claim at the same moment
        return real_claim(self, ids, meta, namespace)

    monkeypatch.setattr(ClaimStore, "claim", synced_claim)
    results = {}

    def run(name):
        store = ClaimStore(archive_remote, workdir=tmp_path / f"claims-{name}")
        results[name] = cap.capture(
            _due(),
            registry=registry,
            out_root=tmp_path / f"out-{name}",
            cfg=cfg,
            now=NOW,
            batch_id=f"kd-{name}",
            client_factory=fp.factory(),
            claim_fn=lambda ids, s=store, n=name: s.claim(ids, {"batch_id": n}),
        )

    threads = [threading.Thread(target=run, args=(n,)) for n in ("a", "b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert len(fp.paid()) == 1
    statuses = sorted(r["per_sport"]["soccer_epl"]["status"] for r in results.values())
    assert statuses == ["NO_ACTION_ALREADY_CLAIMED", "OK"]
    assert sum(r["paid_calls"] for r in results.values()) == 1


def test_claim_failure_fails_closed(tmp_path):
    store = ClaimStore("file:///nonexistent/remote.git", workdir=tmp_path / "c", max_attempts=1)
    assert store.claim(["x"], {"batch_id": "z"}) == set()


def test_heartbeats_append_under_contention(archive_remote, tmp_path):
    rows = [{"phase": "wake", "run_id": str(i), "started_at": _gen(T0)} for i in range(6)]

    def write(i):
        ArchiveAppender(
            archive_remote, workdir=tmp_path / f"hb{i}", paths=("dispatch",)
        ).append_heartbeat(rows[i], day="2026-10-03")

    ts = [threading.Thread(target=write, args=(i,)) for i in range(6)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=120)
    check = tmp_path / "check"
    _git("clone", "-q", "--branch", "data-archive", archive_remote, str(check))
    lines = (check / "dispatch/heartbeats/2026-10-03.jsonl").read_text().splitlines()
    assert sorted(json.loads(x)["run_id"] for x in lines) == [str(i) for i in range(6)]
    # appending the exact same row again is a no-op
    ArchiveAppender(
        archive_remote, workdir=tmp_path / "hb-again", paths=("dispatch",)
    ).append_heartbeat(rows[0], day="2026-10-03")
    _git("pull", "-q", cwd=check)
    assert len((check / "dispatch/heartbeats/2026-10-03.jsonl").read_text().splitlines()) == 6


# ------------------------------------------------------------------ provider outcomes and close states


def test_pinnacle_quoted_nothing_is_attempted_not_missed(tmp_path):
    from soccer_edge.identity.registry import AliasRegistry
    from soccer_edge.reference.odds_budget import BudgetConfig

    registry = AliasRegistry.from_directory(ROOT / "data" / "registry")
    cfg = BudgetConfig.load(ROOT / "config" / "odds_api_budget.json")
    fp = FakeProvider()
    for e in fp.events:
        e["bookmakers"] = []  # Pinnacle lists the events but prices none of them
    st = capture(
        _due(),
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="kd-q",
        client_factory=fp.factory(),
    )
    assert st["paid_calls"] == 1 and st["snapshots"] == 0
    # horizon log: the close horizon was delivered for the first fixture only
    hl = tmp_path / "dispatch" / "horizons.jsonl"
    hl.parent.mkdir(parents=True)
    hl.write_text(
        json.dumps(
            {
                "fixture_id": _due()[0].fixture_id,
                "kickoff_utc": _gen(KO),
                "horizon": 15,
                "status": "delivered",
                "state": "DELIVERED",
            }
        )
        + "\n"
        + json.dumps(
            {
                "fixture_id": "fx:eng.premier_league:2026-27:eng.a:eng.b",
                "kickoff_utc": _gen(KO),
                "horizon": 15,
                "status": "missed",
                "state": "MISSED_BEFORE_WAKE",
            }
        )
        + "\n"
    )
    states = close_attempt_states(tmp_path, now=NOW + timedelta(hours=3))
    assert states[_due()[0].fixture_id]["state"] == "PINNACLE_QUOTED_NOTHING"
    assert states["fx:eng.premier_league:2026-27:eng.a:eng.b"]["state"] == "MISSED_DISPATCHER_CLOSE"


def test_valid_close_and_cluster_is_one_call(tmp_path):
    from soccer_edge.identity.registry import AliasRegistry
    from soccer_edge.reference.odds_budget import BudgetConfig

    registry = AliasRegistry.from_directory(ROOT / "data" / "registry")
    cfg = BudgetConfig.load(ROOT / "config" / "odds_api_budget.json")
    fp = FakeProvider()
    st = capture(
        _due(),
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="kd-v",
        client_factory=fp.factory(),
    )
    assert st["paid_calls"] == 1 and len(fp.paid()) == 1  # two fixtures, one competition, one call
    states = close_attempt_states(tmp_path, now=NOW + timedelta(hours=3))
    assert states[_due()[0].fixture_id]["state"] == "PINNACLE_VALID_CLOSE"
    row = [r for r in BudgetLedger(tmp_path).rows("2026-10-03") if r.get("kind") == "odds"][-1]
    assert row["quoted_fixtures"] == sorted(d.fixture_id for d in _due())


def test_quota_floor_still_enforced_with_claims(tmp_path):
    from soccer_edge.identity.registry import AliasRegistry
    from soccer_edge.reference.odds_budget import BudgetConfig

    registry = AliasRegistry.from_directory(ROOT / "data" / "registry")
    cfg = BudgetConfig.load(ROOT / "config" / "odds_api_budget.json")
    assert (
        cfg.account_reserve_floor,
        cfg.daily_credit_ceiling,
        cfg.close_priority_credits,
        cfg.rolling_30d_credit_ceiling,
    ) == (8000, 150, 45, 2000)
    fp = FakeProvider(remaining=cfg.account_reserve_floor + 1)
    claimed = []
    st = capture(
        _due(),
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="kd-f",
        client_factory=fp.factory(),
        claim_fn=lambda ids: claimed.extend(ids) or set(ids),
    )
    assert fp.paid() == [] and claimed == []  # the guard refuses before any claim or spend
    assert st["per_sport"]["soccer_epl"]["status"].endswith("ACCOUNT_RESERVE_FLOOR")


# ------------------------------------------------------------------ tick-level behaviour


def _tick(monkeypatch, tmp_path, now, actions_seq, schedule):
    import soccer_edge.cli as cli

    calls = []

    def fake_actions(out, due, batch_id, args):
        calls.append([(d.fixture.fixture_id, d.horizon) for d in due])
        return actions_seq.pop(0) if actions_seq else ["kalshi_capture:ok"]

    monkeypatch.setattr(cli, "_dispatch_actions", fake_actions)
    monkeypatch.setattr(
        cli,
        "_dispatch_schedule",
        lambda archive, n: {"generated_at": _gen(now), "fixtures": [f.to_json() for f in schedule]},
    )
    monkeypatch.setattr(cli, "utc_now", lambda: now)
    args = cli.build_parser().parse_args(
        [
            "dispatch",
            "tick",
            "--archive-dir",
            str(tmp_path / "arch"),
            "--out-dir",
            str(tmp_path / "out"),
            "--no-hold",
            "--summary-out",
            str(tmp_path / "tick.json"),
        ]
    )
    (tmp_path / "arch").mkdir(exist_ok=True)
    assert args.func(args) == 0
    return calls, json.loads((tmp_path / "tick.json").read_text())


def test_failed_capture_is_retried_by_the_next_wake(monkeypatch, tmp_path):
    fx = _fx(ko=T0 + timedelta(minutes=14))
    calls, t = _tick(monkeypatch, tmp_path, T0, [["kalshi_capture:error:boom"]], [fx])
    assert calls and t["horizons_delivered"] == 0
    # next wake (same archive state = the log was published without a delivered row) retries
    arch_log = tmp_path / "arch" / "dispatch" / "horizons.jsonl"
    arch_log.parent.mkdir(parents=True, exist_ok=True)
    arch_log.write_text((tmp_path / "out" / "dispatch" / "horizons.jsonl").read_text())
    calls, t = _tick(
        monkeypatch, tmp_path, T0 + timedelta(minutes=5), [["kalshi_capture:ok"]], [fx]
    )
    assert calls and t["horizons_delivered"] >= 1


def test_nothing_due_tick_makes_no_calls(monkeypatch, tmp_path):
    calls, t = _tick(monkeypatch, tmp_path, T0, [], [_fx(ko=T0 + timedelta(hours=6))])
    assert calls == [] and t["paid_calls"] == 0 and t["credits_spent"] == 0 and t["batches"] == 0


# ------------------------------------------------------------------ wake script end to end (offline)


def _run_wake(tmp_path, env_extra):
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_TOKEN", "GITHUB_OUTPUT")}
    env.update(env_extra)
    p = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "kickoff_decide.py"),
            "wake",
            "--archive-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return dict(
        ln.split("=", 1) for ln in p.stdout.splitlines() if "=" in ln and not ln.startswith("{")
    )


def test_wake_script_external_and_backup_both_work(tmp_path):
    now = datetime.now(UTC)
    sched = {"generated_at": _gen(now), "fixtures": [_fx(ko=now + timedelta(hours=8)).to_json()]}
    (tmp_path / "dispatch").mkdir()
    (tmp_path / "dispatch" / "schedule.json").write_text(json.dumps(sched))
    ext = _run_wake(
        tmp_path, {"GITHUB_EVENT_NAME": "workflow_dispatch", "TRIGGER_SOURCE": "external-heartbeat"}
    )
    bak = _run_wake(tmp_path, {"GITHUB_EVENT_NAME": "schedule"})
    assert ext["capture"] == bak["capture"] == "false"
    assert ext["source"] == EXTERNAL and bak["source"] == GITHUB_BACKUP
    rows = [
        json.loads(x)
        for x in next((tmp_path / "dispatch" / "heartbeats").glob("*.jsonl"))
        .read_text()
        .splitlines()
    ]
    assert [r["trigger_source"] for r in rows] == [EXTERNAL, GITHUB_BACKUP]
    assert all(r["no_action_reason"] == "NO_WORK_DUE" and r["status"] == "OK" for r in rows)


# ------------------------------------------------------------------ secrets, reliability, workflow shape


def test_credentials_never_survive_redaction(archive_remote, tmp_path):
    tok = "ghs_" + "A" * 36
    assert tok not in redact(f"https://x-access-token:{tok}@github.com/o/r.git failed")
    assert tok not in redact(f"Authorization: Bearer {tok}")
    bad = ClaimStore(
        f"https://x-access-token:{tok}@127.0.0.1:9/o/r.git", workdir=tmp_path / "r", max_attempts=1
    )
    with pytest.raises(GitStoreError) as e:
        bad._ensure()
        bad._sync()
    assert tok not in str(e.value)


def test_reliability_counts_what_matters():
    now = T0
    hb = [
        {
            "phase": "wake",
            "trigger_source": EXTERNAL,
            "started_at": _gen(now - timedelta(minutes=5 * i)),
            "status": "OK",
            "no_action_reason": "NO_WORK_DUE",
        }
        for i in range(1, 11)
    ]
    hb += [
        {
            "phase": "wake",
            "trigger_source": GITHUB_BACKUP,
            "started_at": _gen(now - timedelta(hours=2)),
            "status": "OK",
        }
    ]
    ko = now - timedelta(hours=1)
    log = [
        HorizonRow("f1", _gen(ko), 15, "delivered", _gen(ko), state=DELIVERED),
        HorizonRow("f1", _gen(ko), 5, "missed", _gen(ko), state=MISSED_BEFORE_WAKE),
        HorizonRow("f2", _gen(ko), 15, "missed", _gen(ko), state=MISSED_BEFORE_WAKE),
        HorizonRow("f2", _gen(ko), 5, "missed", _gen(ko), state=MISSED_EXECUTION_FAILURE),
        HorizonRow("f3", _gen(ko), 5, "missed", _gen(ko), state=NOT_APPLICABLE),
    ]
    r = reliability(
        hb, log, now=now, cadence={"external_heartbeat_minutes": 5, "github_backup_minutes": 10}
    )
    d = r["last_24h"]
    assert d["external_heartbeats_expected"] == 288 and d["external_heartbeats_actual"] == 10
    assert (
        d["github_backup_actual"] == 1
        and d["horizons_eligible"] == 4
        and d["horizons_delivered"] == 1
    )
    assert d["capture_success_rate"] == 0.25 and d["close_success_rate"] == 0.5


def test_workflow_shape_one_dispatcher_all_triggers():
    wf = (ROOT / ".github" / "workflows" / "kickoff-dispatch.yml").read_text()
    for trig in ("workflow_dispatch:", "repository_dispatch:", "schedule:"):
        assert trig in wf
    assert "wake-soccer-dispatcher" in wf
    # the decide step runs for every trigger; no event-specific branching of the decision
    decide = wf.split("\n  capture:\n")[0]
    assert (
        "python3 scripts/kickoff_decide.py wake" in decide
        and "if:" not in decide.split("steps:")[1]
    )
    # only the capture job is in the writer group, and nothing cancels an in-flight capture
    assert decide.count("concurrency:") == 0
    cap = wf.split("\n  capture:\n")[1]
    assert "group: data-writer-archive-kickoff" in cap and "cancel-in-progress: false" in cap
    assert "cancel-in-progress: true" not in wf
    minute = re.search(r'cron:\s*"([^"]+)"', wf).group(1).split()[0]
    assert "0" not in minute.split(",")
    # no credential in any URL query string of the dispatcher files
    assert "?access_token=" not in wf and "apiKey=" not in wf
