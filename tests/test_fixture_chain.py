"""Fixture-aware bounded chain (docs/SCHEDULER.md): lifecycle, batching, restarts, runaway protection.

Ticks run with a simulated clock (utc_now / time.sleep patched), the real capture() against a fake
provider, and real git for claims, durable caps and the chain lease."""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from soccer_edge.dispatch.gitstore import ChainLease, ClaimStore
from soccer_edge.dispatch.horizons import ScheduledFixture
from soccer_edge.dispatch.wake import decide_wake
from soccer_edge.identity.registry import AliasRegistry
from soccer_edge.reference.odds_api_capture import DueFixture, capture
from soccer_edge.reference.odds_budget import BudgetConfig
from tests.test_odds_api_reference import KO, KO_LATE, NOW, FakeProvider, _due

ROOT = Path(__file__).resolve().parents[1]
REG = AliasRegistry.from_directory(ROOT / "data" / "registry")
CFG = BudgetConfig.load(ROOT / "config" / "odds_api_budget.json")
A, B = _due()[0].fixture_id, _due()[1].fixture_id


def _z(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def _sched(*pairs):
    return [ScheduledFixture(fid, ko, "eng.premier_league", "run_output", 40) for fid, ko in pairs]


class Clock:
    def __init__(self, t):
        self.t = t

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += timedelta(seconds=s)


def _run_tick(
    monkeypatch, root, clock, schedule, fp, *, limit=330.0, listing_age_h=1.0, claim=None
):
    """One chain link with a simulated clock. Returns (tick summary, paid-call purposes per batch)."""
    import soccer_edge.cli as cli

    batches = []

    def fake_actions(out, due, batch_id, args):
        fx = [
            DueFixture(
                d.fixture.fixture_id,
                d.fixture.competition_id,
                d.fixture.kickoff_utc,
                (d.fixture.kickoff_utc - clock.now()).total_seconds() / 60,
                True,
            )
            for d in due
        ]
        st = capture(
            fx,
            registry=REG,
            out_root=out,
            cfg=CFG,
            now=clock.now(),
            batch_id=batch_id,
            client_factory=fp.factory(),
            schedule_as_of=args.schedule_as_of,
            time_fn=clock.now,
            claim_fn=claim,
        )
        batches.append(
            {
                "at": _z(clock.now()),
                "horizons": sorted(d.horizon for d in due),
                "paid": st["paid_calls"],
                "per_sport": st.get("per_sport", {}),
            }
        )
        return [
            "kalshi_capture:ok",
            f"odds_api:{st['status'].lower()}:credits={st['credits_charged']}:paid={st['paid_calls']}:rows={st['snapshots']}",
        ]

    listing = _z(clock.now() - timedelta(hours=listing_age_h))
    monkeypatch.setattr(cli, "_dispatch_actions", fake_actions)
    monkeypatch.setattr(
        cli,
        "_dispatch_schedule",
        lambda archive, n: {
            "generated_at": _z(n),
            "kalshi_listing_as_of": listing,
            "fixtures": [f.to_json() for f in schedule],
        },
    )
    monkeypatch.setattr(cli, "utc_now", clock.now)
    monkeypatch.setattr(time, "sleep", clock.sleep)
    arch, out = root / "arch", root / "out"
    arch.mkdir(parents=True, exist_ok=True)
    args = cli.build_parser().parse_args(
        [
            "dispatch",
            "tick",
            "--archive-dir",
            str(arch),
            "--out-dir",
            str(out),
            "--chain",
            "--max-tick-minutes",
            str(limit),
            "--summary-out",
            str(root / "tick.json"),
        ]
    )
    assert args.func(args) == 0
    return json.loads((root / "tick.json").read_text()), batches


def _persist(root):
    """What a published link leaves on data-archive for the next link (log + ledger)."""
    arch, out = root / "arch", root / "out"
    for rel in ("dispatch/horizons.jsonl",):
        (arch / rel).parent.mkdir(parents=True, exist_ok=True)
        (arch / rel).write_text((out / rel).read_text())
    for f in (out / "odds_api" / "budget").glob("*.jsonl"):
        d = arch / "odds_api" / "budget"
        d.mkdir(parents=True, exist_ok=True)
        (d / f.name).write_text(f.read_text())


# ------------------------------------------------------------------ decisions


def test_no_fixtures_no_capture_no_link():
    d = decide_wake([], _z(NOW), [], [], [], now=NOW)
    assert d.capture is False and d.no_action_reason == "NO_WORK_DUE"


def test_known_future_window_starts_one_sleeping_link():
    d = decide_wake(_sched((A, NOW + timedelta(hours=5))), _z(NOW), [], [], [], now=NOW)
    assert d.capture and any(r.startswith("chain:") for r in d.reasons)
    d = decide_wake(
        _sched((A, NOW + timedelta(hours=5))),
        _z(NOW),
        [],
        [],
        [],
        now=NOW,
        capture_in_progress=True,
    )
    assert d.capture is False and d.no_action_reason == "CAPTURE_IN_PROGRESS"


# ------------------------------------------------------------------ lifecycle


def test_one_fixture_bounded_lifecycle_pays_only_t60_and_t15(monkeypatch, tmp_path):
    clock = Clock(KO - timedelta(minutes=70))
    fp = FakeProvider()
    t, batches = _run_tick(monkeypatch, tmp_path, clock, _sched((A, KO)), fp)
    # T-120's window (60, 130] is still open at T-70: delivered at once (free Kalshi capture)
    assert [b["horizons"] for b in batches] == [[120], [60], [30], [15], [5]]
    assert [b["at"][11:16] for b in batches] == ["12:50", "13:00", "13:30", "13:45", "13:55"]
    assert [b["paid"] for b in batches] == [0, 1, 0, 1, 0]  # entry at T-60, close at T-15 only
    assert len(fp.paid()) == 2 and t["paid_calls"] == 2 and t["credits_spent"] == 6
    assert t["end_reason"] == "no_future_window" and t["chain_continue"] is False
    assert t["missed_states"] == {}


def test_clustered_fixtures_one_call_per_window(monkeypatch, tmp_path):
    clock = Clock(KO - timedelta(minutes=70))
    fp = FakeProvider()
    fp.events[1]["commence_time"] = _z(KO)  # both fixtures kick off together
    t, batches = _run_tick(monkeypatch, tmp_path, clock, _sched((A, KO), (B, KO)), fp)
    assert len(fp.paid()) == 2  # 2 fixtures x (entry + close) = 2 calls, not 4
    assert {tuple(sorted(r.url.params["eventIds"].split(","))) for r in fp.paid()} == {
        ("ev1", "ev2")
    }


def test_overlapping_clusters_share_calls(monkeypatch, tmp_path):
    # A 14:00, B 14:45: A's T-15 (13:45) and B's T-60 (13:45) land in the same batch -> one call
    clock = Clock(KO - timedelta(minutes=70))
    fp = FakeProvider()
    t, batches = _run_tick(monkeypatch, tmp_path, clock, _sched((A, KO), (B, KO_LATE)), fp)
    assert len(fp.paid()) == 3 and t["credits_spent"] == 9
    shared = next(b for b in batches if b["at"][11:16] == "13:45")
    ps = shared["per_sport"]["soccer_epl"]
    assert ps["close_fixtures"] == 1 and ps["entry_fixtures"] == 1 and shared["paid"] == 1


def test_link_limit_asks_for_a_successor(monkeypatch, tmp_path):
    clock = Clock(KO - timedelta(hours=8))
    fp = FakeProvider()
    t, batches = _run_tick(monkeypatch, tmp_path, clock, _sched((A, KO)), fp, limit=60)
    assert batches == [] and fp.paid() == []  # slept, spent nothing
    assert t["end_reason"] == "link_time_limit" and t["chain_continue"] is True
    assert 58 <= t["elapsed_minutes"] <= 60


# ------------------------------------------------------------------ restarts


def test_interrupted_after_t60_restart_does_not_repay(monkeypatch, tmp_path):
    clock = Clock(KO - timedelta(minutes=70))
    fp = FakeProvider()
    # first link dies right after T-60 (time limit just past 13:00)
    t, b1 = _run_tick(monkeypatch, tmp_path, clock, _sched((A, KO)), fp, limit=12)
    assert [b["horizons"] for b in b1] == [[120], [60]] and len(fp.paid()) == 1
    _persist(tmp_path)
    clock.t = KO - timedelta(minutes=50)  # restart before T-30 / T-15
    t, b2 = _run_tick(monkeypatch, tmp_path, clock, _sched((A, KO)), fp)
    assert [b["horizons"] for b in b2] == [
        [30],
        [15],
        [5],
    ]  # T-60 not repeated, T-15 still delivered
    assert len(fp.paid()) == 2  # only the close was added


def test_restart_after_kickoff_makes_no_fake_close(monkeypatch, tmp_path):
    clock = Clock(KO + timedelta(minutes=2))
    fp = FakeProvider()
    t, batches = _run_tick(monkeypatch, tmp_path, clock, _sched((A, KO)), fp)
    assert batches == [] and fp.paid() == []
    assert sum(t["missed_states"].values()) == 5 and t["chain_continue"] is False


# ------------------------------------------------------------------ spend-time guards


def test_stale_listing_fails_closed(monkeypatch, tmp_path):
    clock = Clock(KO - timedelta(minutes=70))
    fp = FakeProvider()
    t, batches = _run_tick(monkeypatch, tmp_path, clock, _sched((A, KO)), fp, listing_age_h=40)
    assert fp.paid() == [] and batches  # horizons still captured on Kalshi; no paid reference
    assert all(
        b["per_sport"]["soccer_epl"]["status"].endswith("STALE_SCHEDULE")
        for b in batches
        if b["per_sport"]
    )


def test_kickoff_mismatch_and_window_recheck_fail_closed(tmp_path):
    fp = FakeProvider()
    fp.events[0]["commence_time"] = _z(
        KO + timedelta(hours=2)
    )  # provider disagrees with the schedule
    st = capture(
        [_due()[0]],
        registry=REG,
        out_root=tmp_path,
        cfg=CFG,
        now=NOW,
        batch_id="m",
        client_factory=fp.factory(),
        schedule_as_of=NOW,
    )
    assert fp.paid() == [] and st["per_sport"]["soccer_epl"]["status"].endswith(
        "NO_VALID_WINDOW_AT_SPEND"
    )
    # the window closes between planning and spend (slow free calls): the fresh clock refuses
    fp2 = FakeProvider()
    st = capture(
        [_due()[0]],
        registry=REG,
        out_root=tmp_path / "b",
        cfg=CFG,
        now=NOW,
        batch_id="w",
        client_factory=fp2.factory(),
        schedule_as_of=NOW,
        time_fn=lambda: KO + timedelta(seconds=1),
    )
    assert fp2.paid() == []


def test_actions_without_claim_store_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    fp = FakeProvider()
    st = capture(
        _due(),
        registry=REG,
        out_root=tmp_path,
        cfg=CFG,
        now=NOW,
        batch_id="c",
        client_factory=fp.factory(),
        schedule_as_of=NOW,
    )
    assert fp.paid() == [] and st["per_sport"]["soccer_epl"]["status"].endswith("NO_CLAIM_STORE")
    st = capture(
        _due(),
        registry=REG,
        out_root=tmp_path / "x",
        cfg=CFG,
        now=NOW,
        batch_id="c2",
        client_factory=fp.factory(),
        claim_fn=lambda i, r: set(i),
    )
    assert fp.paid() == [] and st["per_sport"]["soccer_epl"]["status"].endswith(
        "SCHEDULE_AGE_UNKNOWN"
    )


# ------------------------------------------------------------------ runaway protection (real git)


def _git(*a, cwd=None):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def remote(tmp_path):
    bare = tmp_path / "r.git"
    _git("init", "-q", "--bare", str(bare))
    seed = tmp_path / "seed"
    _git("init", "-q", str(seed))
    (seed / "README.md").write_text("x\n")
    _git("add", "README.md", cwd=seed)
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "s", cwd=seed)
    _git("push", "-q", str(bare), "HEAD:refs/heads/data-archive", cwd=seed)
    return f"file://{bare}"


def test_infinite_trigger_loop_is_stopped_by_durable_caps(remote, tmp_path):
    """Every trigger is a fresh dispatcher with an EMPTY local ledger (the worst case: publishing broken)
    and a fixture it has never seen; only the durable call records on data-archive can stop it."""
    store = ClaimStore(remote, workdir=tmp_path / "claims")
    caps = {"daily": 9, "rolling_30d": 2000}  # 3 calls at 3 credits
    fp = FakeProvider()
    for i in range(8):
        fp.events[0]["id"] = f"ev-{i}"
        capture(
            [_due()[0]],
            registry=REG,
            out_root=tmp_path / f"o{i}",
            cfg=CFG,
            now=NOW,
            batch_id=f"loop{i}",
            client_factory=fp.factory(),
            schedule_as_of=NOW,
            claim_fn=lambda ids, rec, i=i: (
                store.claim(
                    [f"{x}#{i}" for x in ids], {"batch_id": f"loop{i}"}, call_record=rec, caps=caps
                )
                and set(ids)
            ),
        )
    assert len(fp.paid()) == 3  # 3 x 3 credits = the cap; triggers 4..8 spend nothing
    assert store.last_reason.startswith("DURABLE_DAILY_CAP")


def test_rolling_cap_counts_previous_days(remote, tmp_path):
    store = ClaimStore(remote, workdir=tmp_path / "c")
    caps = {"daily": 150, "rolling_30d": 6}
    for day in ("2026-09-20", "2026-10-02"):
        assert store.claim(
            [f"x{day}"], {}, call_record={"day": day, "call_id": day, "expected_cost": 3}, caps=caps
        )
    assert (
        store.claim(
            ["y"],
            {},
            call_record={"day": "2026-10-03", "call_id": "t", "expected_cost": 3},
            caps=caps,
        )
        == set()
    )
    assert store.last_reason.startswith("DURABLE_30D_CAP")
    # a record older than 30 days no longer counts
    assert store.claim(
        ["z"], {}, call_record={"day": "2026-10-21", "call_id": "u", "expected_cost": 3}, caps=caps
    ) == {"z"}


def test_duplicate_trigger_same_identity_never_pays_twice(remote, tmp_path):
    store = ClaimStore(remote, workdir=tmp_path / "c")
    fp = FakeProvider()
    for i in range(3):  # the same due close, three triggers, three empty ledgers
        capture(
            [_due()[0]],
            registry=REG,
            out_root=tmp_path / f"o{i}",
            cfg=CFG,
            now=NOW,
            batch_id=f"d{i}",
            client_factory=fp.factory(),
            schedule_as_of=NOW,
            claim_fn=lambda ids, rec: store.claim(ids, {}, call_record=rec, caps={"daily": 150}),
        )
    assert len(fp.paid()) == 1


def test_chain_lease_allows_one_link(remote, tmp_path):
    now = datetime(2026, 10, 3, 12, 0)
    a = ChainLease(remote, workdir=tmp_path / "a")
    b = ChainLease(remote, workdir=tmp_path / "b")
    assert a.acquire("run-a", now=now, minutes=345)
    assert not b.acquire("run-b", now=now + timedelta(minutes=10), minutes=345)
    assert a.release("run-a", now=now + timedelta(minutes=20))
    assert b.acquire("run-b", now=now + timedelta(minutes=21), minutes=345)
    # a crashed holder never releases: its lease simply expires
    c = ChainLease(remote, workdir=tmp_path / "c")
    assert c.acquire("run-c", now=now + timedelta(minutes=21 + 346), minutes=345)


def test_chain_decision_cannot_loop_fast():
    import importlib.util

    spec = importlib.util.spec_from_file_location("kd", ROOT / "scripts" / "kickoff_decide.py")
    kd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kd)
    assert kd.chain_decision("success", True, 330)[0] is True
    assert kd.chain_decision("success", False, 330)[0] is False  # no future window: chain stops
    assert kd.chain_decision("success", True, 3)[0] is False  # a too-short link never chains
    assert kd.chain_decision("failure", False, 120)[0] is True  # recovery after a real link failed
    assert kd.chain_decision("failure", False, 1)[0] is False  # fast failure: no restart loop
    assert kd.chain_decision("cancelled", True, 330)[0] is False
