"""One wake of the canonical dispatcher: what (if anything) is due right now? (stdlib only)

Every trigger — the external heartbeat, the GitHub schedule backup, a manual dispatch, a
repository_dispatch — runs exactly this decision. The trigger carries no work description; the dispatcher
reads the durable state on data-archive and decides:

* capture: some required horizon (T-120/60/30/15/5) is satisfiable now, newly missed horizons need logging,
  or the fixture schedule is stale;
* settle: a fixture with predictions finished (kickoff + grace) since the last settlement run, or the last
  run left fixtures pending and is old enough to retry;
* otherwise NO_WORK_DUE, which is a normal, successful, zero-cost outcome.

Each wake appends one heartbeat row (dispatch/heartbeats/<UTC date>.jsonl) so "no work was due" is
distinguishable from "the dispatcher never ran" and from "it ran and failed".
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from soccer_edge.dispatch.horizons import (
    HorizonRow,
    ScheduledFixture,
    _dt,
    _iso,
    minutes_until_next_window,
    plan,
)

HEARTBEAT_DIR = "dispatch/heartbeats"
SETTLE_RUNS_LOG = "dispatch/settle_runs.jsonl"
RELIABILITY_FILE = "dispatch/reliability.json"

# trigger sources: the external heartbeat sends only its identity, never work
EXTERNAL = "external-heartbeat"
GITHUB_BACKUP = "github-schedule-backup"
MANUAL = "manual"
REPOSITORY_DISPATCH = "repository-dispatch"
DISPATCHER = "dispatcher"
_KNOWN_SOURCES = {EXTERNAL, GITHUB_BACKUP, MANUAL, REPOSITORY_DISPATCH, DISPATCHER}

SCHEDULE_MAX_AGE = timedelta(hours=3)  # older schedule -> a capture tick rebuilds it
SETTLE_GRACE = timedelta(
    hours=3, minutes=15
)  # settle_ledger waits kickoff + 3 h (grace) before settling
SETTLE_LOOKBACK = timedelta(hours=72)
SETTLE_RETRY_AFTER = timedelta(hours=3)  # pending results: retry at most this often
SETTLE_DEDUPE = timedelta(minutes=90)  # never dispatch settlement twice inside this window
CAPTURE_STALE_AFTER = timedelta(minutes=50)  # an "in progress" capture older than this is ignored


def normalize_source(event_name: str | None, requested: str | None) -> str:
    """Map (GitHub event, requested source label) to a known trigger source. Free text is never trusted."""
    req = (requested or "").strip().lower()
    if event_name == "schedule":
        return GITHUB_BACKUP
    if req in _KNOWN_SOURCES:
        return req
    if event_name == "repository_dispatch":
        return REPOSITORY_DISPATCH
    return MANUAL


@dataclass
class WakeDecision:
    capture: bool
    settle: bool
    reasons: list[str] = field(default_factory=list)
    n_due: int = 0
    n_missed: int = 0
    due: list[tuple[str, int, float]] = field(default_factory=list)
    next_window_minutes: float | None = None
    fixtures_examined: int = 0
    settle_fixtures: list[str] = field(default_factory=list)
    no_action_reason: str | None = None


def _heartbeat_rows(heartbeats: list[dict[str, Any]], *, phase: str | None = None) -> list[dict]:
    return [h for h in heartbeats if phase is None or h.get("phase") == phase]


def settle_due(
    log: list[HorizonRow],
    settle_runs: list[dict[str, Any]],
    heartbeats: list[dict[str, Any]],
    *,
    now: datetime,
) -> tuple[bool, str, list[str]]:
    """Is a settlement run due? Returns (due, reason, fixture ids that triggered it)."""
    recent_dispatch = [
        h
        for h in heartbeats
        if h.get("settle_dispatched") and now - _dt(h["started_at"]) < SETTLE_DEDUPE
    ]
    if recent_dispatch:
        return False, "settlement dispatched within the dedupe window", []
    runs = sorted(
        (r for r in settle_runs if r.get("status") == "ok" and r.get("started_at")),
        key=lambda r: r["started_at"],
    )
    last = runs[-1] if runs else None
    last_start = _dt(last["started_at"]) if last else None
    if last_start is not None and now - last_start < SETTLE_DEDUPE:
        return False, "settlement ran within the dedupe window", []
    kickoffs: dict[str, datetime] = {}
    for r in log:
        kickoffs.setdefault(r.fixture_id, _dt(r.kickoff_utc))
    finished = [
        fid
        for fid, ko in kickoffs.items()
        if now - SETTLE_LOOKBACK <= ko
        and ko + SETTLE_GRACE <= now
        and (last_start is None or ko + SETTLE_GRACE > last_start)
    ]
    if finished:
        return (
            True,
            f"{len(finished)} fixture(s) finished since the last settlement",
            sorted(finished),
        )
    if last is not None and now - last_start >= SETTLE_RETRY_AFTER:
        pending = [
            p["fixture_id"]
            for p in last.get("pending_fixtures") or []
            if p.get("kickoff_utc") and now - SETTLE_LOOKBACK <= _dt(p["kickoff_utc"])
        ]
        if pending:
            return True, f"retry {len(pending)} fixture(s) left pending", sorted(set(pending))
    return False, "no finished fixture awaiting settlement", []


def decide_wake(
    schedule: list[ScheduledFixture],
    schedule_generated_at: str | None,
    log: list[HorizonRow],
    settle_runs: list[dict[str, Any]],
    heartbeats: list[dict[str, Any]],
    *,
    now: datetime,
    capture_in_progress: bool = False,
    force: bool = False,
) -> WakeDecision:
    due, missed, upcoming = plan(schedule, log, now=now)
    d = WakeDecision(capture=False, settle=False)
    d.fixtures_examined = len(schedule)
    d.n_due, d.n_missed = len(due), len(missed)
    d.due = [(x.fixture.fixture_id, x.horizon, round(x.minutes_to_kickoff, 1)) for x in due]
    d.next_window_minutes = minutes_until_next_window(upcoming)
    stale = schedule_generated_at is None or now - _dt(schedule_generated_at) > SCHEDULE_MAX_AGE
    wants = []
    if due:
        wants.append(f"{len(due)} horizon(s) due")
    if missed:
        wants.append(f"{len(missed)} newly missed horizon(s) to log")
    if stale:
        wants.append("schedule stale or missing")
    if force:
        wants.append("forced")
    if wants and capture_in_progress and not force:
        d.reasons.append(
            "capture already in progress (it re-plans every loop); not queuing another"
        )
    elif wants:
        d.capture = True
        d.reasons.extend(wants)
    s_due, s_reason, s_fx = settle_due(log, settle_runs, heartbeats, now=now)
    d.settle = s_due
    d.settle_fixtures = s_fx
    d.reasons.append(f"settle: {s_reason}")
    if not d.capture and not d.settle:
        d.no_action_reason = (
            "CAPTURE_IN_PROGRESS" if (wants and capture_in_progress) else "NO_WORK_DUE"
        )
    return d


def heartbeat_row(
    *,
    run_id: str,
    run_attempt: str,
    source: str,
    event_name: str,
    sha: str,
    requested_at: str | None,
    started_at: datetime,
    completed_at: datetime,
    decision: WakeDecision | None,
    phase: str = "wake",
    status: str = "OK",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema": "dispatch_heartbeat_v1",
        "phase": phase,  # wake | capture
        "run_id": run_id,
        "run_attempt": run_attempt,
        "trigger_source": source,
        "event_name": event_name,
        "commit_sha": sha,
        "requested_at": requested_at,
        "started_at": _iso(started_at),
        "completed_at": _iso(completed_at),
        "status": status,  # OK | FAILED
    }
    if decision is not None:
        row.update(
            {
                "fixtures_examined": decision.fixtures_examined,
                "horizons_due": decision.n_due,
                "horizons_newly_missed": decision.n_missed,
                "due": decision.due[:40],
                "capture_requested": decision.capture,
                "settle_dispatched": False,  # set by the caller after a successful dispatch
                "settle_fixtures": decision.settle_fixtures[:40],
                "no_action_reason": decision.no_action_reason,
                "reasons": decision.reasons,
                "next_window_minutes": None
                if decision.next_window_minutes is None
                else round(decision.next_window_minutes, 1),
            }
        )
    if extra:
        row.update(extra)
    return row


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                out.append(json.loads(ln))
            except ValueError:
                continue
    return out


def load_heartbeats(root: Path, *, now: datetime, days: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for k in range(days):
        day = (now - timedelta(days=k)).strftime("%Y-%m-%d")
        rows.extend(load_jsonl(root / HEARTBEAT_DIR / f"{day}.jsonl"))
    return rows


def wake_times(heartbeats: list[dict[str, Any]]) -> list[datetime]:
    """Start times of every dispatcher wake that ran (any status)."""
    out = []
    for h in heartbeats:
        if h.get("phase", "wake") == "wake" and h.get("started_at"):
            try:
                out.append(_dt(h["started_at"]))
            except ValueError:
                continue
    return out


_TOKEN_RE = re.compile(
    r"(x-access-token:)[^@\s]+@|(Bearer\s+)[A-Za-z0-9_\-\.]+|gh[pousr]_[A-Za-z0-9]{20,}"
)


def redact(text: str) -> str:
    """Strip GitHub credentials from any message before it is printed or stored."""
    return _TOKEN_RE.sub(
        lambda m: (m.group(1) or m.group(2) or "") + "***" + ("@" if m.group(1) else ""), text
    )


def now_utc() -> datetime:
    return datetime.now(UTC)


def asdict_decision(d: WakeDecision) -> dict[str, Any]:
    return asdict(d)
