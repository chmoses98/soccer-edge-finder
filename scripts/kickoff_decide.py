"""Canonical dispatcher wake (stdlib only: no pip install, runs in seconds). docs/SCHEDULER.md.

Every trigger runs this same decision: the external heartbeat (workflow_dispatch source=external-heartbeat),
the GitHub schedule backup, a repository_dispatch or a manual run. The trigger carries no work; this reads
the durable state on data-archive and decides.

    wake       decide capture / settlement, dispatch settlement when due, record a heartbeat row,
               print GitHub outputs (capture=true|false, settle_dispatched=..., reason=...)
    complete   record the capture job's completion row (delivered horizons, paid calls, credits, status)

A wake where nothing is due is a normal success: no capture job, no paid call, exit 0. Credentials come
only from the environment (GITHUB_TOKEN) and are redacted from every printed message.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soccer_edge.dispatch.gitstore import ArchiveAppender, github_remote_url  # noqa: E402
from soccer_edge.dispatch.horizons import (  # noqa: E402
    SCHEDULE_FILE,
    STATE_LOG,
    HorizonRow,
    ScheduledFixture,
)
from soccer_edge.dispatch.reliability import reliability  # noqa: E402
from soccer_edge.dispatch.wake import (  # noqa: E402
    CAPTURE_STALE_AFTER,
    SETTLE_RUNS_LOG,
    decide_wake,
    heartbeat_row,
    load_heartbeats,
    load_jsonl,
    normalize_source,
    redact,
)

API = "https://api.github.com"


def _api(method: str, path: str, body: dict | None = None) -> tuple[int, dict | None]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return 0, None
    req = urllib.request.Request(
        f"{API}{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


def _load_state(root: Path, now: datetime):
    sched_doc = {}
    p = root / SCHEDULE_FILE
    if p.exists():
        sched_doc = json.loads(p.read_text(encoding="utf-8"))
    schedule = [ScheduledFixture.from_json(d) for d in sched_doc.get("fixtures", [])]
    log = [
        HorizonRow(**{k: d.get(k) for k in HorizonRow.__dataclass_fields__})
        for d in load_jsonl(root / STATE_LOG)
    ]
    heartbeats = load_heartbeats(root, now=now)
    settle_runs = load_jsonl(root / SETTLE_RUNS_LOG)
    return schedule, sched_doc.get("generated_at"), log, heartbeats, settle_runs


def _capture_in_progress(repo: str, run_id: str, now: datetime) -> bool:
    """Is another run's capture job already working (it re-plans every loop, so it covers this wake)?"""
    code, data = _api(
        "GET",
        f"/repos/{repo}/actions/workflows/kickoff-dispatch.yml/runs?status=in_progress&per_page=20",
    )
    if code != 200 or not data:
        return False
    for run in data.get("workflow_runs", []):
        if str(run.get("id")) == str(run_id):
            continue
        c2, jobs = _api("GET", f"/repos/{repo}/actions/runs/{run['id']}/jobs")
        for j in (jobs or {}).get("jobs", []) if c2 == 200 else []:
            if (
                j.get("name") == "capture"
                and j.get("status") == "in_progress"
                and j.get("started_at")
            ):
                started = datetime.fromisoformat(j["started_at"].replace("Z", "+00:00"))
                if now - started < CAPTURE_STALE_AFTER:
                    return True
    return False


def _cadence() -> dict:
    try:
        d = json.loads((ROOT / "config" / "dispatch.json").read_text())
        return {k: d[k] for k in ("external_heartbeat_minutes", "github_backup_minutes") if k in d}
    except (OSError, ValueError):
        return {}


def _reliability_fn(now: datetime):
    def build(root: Path) -> dict:
        _, _, log, heartbeats, _ = _load_state(root, now)
        return reliability(heartbeats, log, now=now, cadence=_cadence())

    return build


def _outputs(**kv) -> None:
    lines = [f"{k}={v}" for k, v in kv.items()]
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def cmd_wake(a: argparse.Namespace) -> int:
    started = datetime.now(UTC)
    repo = os.environ.get("GITHUB_REPOSITORY", "chmoses98/soccer-edge-finder")
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    event = os.environ.get("GITHUB_EVENT_NAME", "workflow_dispatch")
    source = normalize_source(event, os.environ.get("TRIGGER_SOURCE"))
    force = os.environ.get("FORCE", "").lower() == "true"
    appender = None
    root = Path(a.archive_dir) if a.archive_dir else None
    state_ok = True
    if root is None:
        url = github_remote_url()
        if url is None:
            print("no GITHUB_TOKEN: cannot read the archive; requesting a capture tick to be safe")
            _outputs(
                capture="true",
                settle_dispatched="false",
                heartbeat_recorded="false",
                reason="no_token",
            )
            return 0
        appender = ArchiveAppender(url, paths=("dispatch",))
        try:
            appender._ensure()
            appender._sync()
            root = appender.dir
        except (
            Exception
        ) as exc:  # archive unreadable: fail open for capture (the tick is idempotent)
            print(redact(f"archive read failed: {exc}"))
            state_ok = False
    if not state_ok:
        _outputs(
            capture="true",
            settle_dispatched="false",
            heartbeat_recorded="false",
            reason="archive_unreadable",
        )
        return 0
    schedule, gen_at, log, heartbeats, settle_runs = _load_state(root, started)
    in_progress = False if a.archive_dir else _capture_in_progress(repo, run_id, started)
    d = decide_wake(
        schedule,
        gen_at,
        log,
        settle_runs,
        heartbeats,
        now=started,
        capture_in_progress=in_progress,
        force=force,
    )
    settle_dispatched = False
    if d.settle and not a.archive_dir:
        code, _ = _api(
            "POST",
            f"/repos/{repo}/actions/workflows/settle-evaluate.yml/dispatches",
            {"ref": os.environ.get("DEFAULT_BRANCH") or "main", "inputs": {"source": "dispatcher"}},
        )
        settle_dispatched = code in (200, 204)
        d.reasons.append(f"settle dispatch HTTP {code}")
    code, run = (0, None) if a.archive_dir else _api("GET", f"/repos/{repo}/actions/runs/{run_id}")
    row = heartbeat_row(
        run_id=run_id,
        run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        source=source,
        event_name=event,
        sha=os.environ.get("GITHUB_SHA", "")[:12],
        requested_at=(run or {}).get("created_at"),
        started_at=started,
        completed_at=datetime.now(UTC),
        decision=d,
    )
    row["settle_dispatched"] = settle_dispatched
    if d.settle and not settle_dispatched and not a.archive_dir:
        row["no_action_reason"] = row.get("no_action_reason") or "SETTLE_DISPATCH_FAILED"
    recorded = False
    if appender is not None:
        try:
            recorded = appender.append_heartbeat(
                row, day=started.strftime("%Y-%m-%d"), reliability=_reliability_fn(started)
            )
        except Exception as exc:
            print(redact(f"heartbeat not recorded: {exc}"))
    elif a.archive_dir:
        p = Path(a.archive_dir) / "dispatch" / "heartbeats" / f"{started:%Y-%m-%d}.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        recorded = True
    print(
        json.dumps(
            {
                k: row[k]
                for k in (
                    "trigger_source",
                    "horizons_due",
                    "horizons_newly_missed",
                    "capture_requested",
                    "settle_dispatched",
                    "no_action_reason",
                    "reasons",
                )
            },
            default=str,
        )
    )
    _outputs(
        capture="true" if d.capture else "false",
        settle_dispatched="true" if settle_dispatched else "false",
        heartbeat_recorded="true" if recorded else "false",
        source=source,
        reason=(d.no_action_reason or "; ".join(d.reasons))[:200].replace("\n", " "),
    )
    return 0


def cmd_complete(a: argparse.Namespace) -> int:
    now = datetime.now(UTC)
    summary = {}
    with contextlib.suppress(OSError, ValueError):
        summary = json.loads(Path(a.tick_summary).read_text())
    status = "OK" if a.status == "success" else "FAILED"
    source = normalize_source(os.environ.get("GITHUB_EVENT_NAME"), os.environ.get("TRIGGER_SOURCE"))
    row = heartbeat_row(
        run_id=os.environ.get("GITHUB_RUN_ID", "local"),
        run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        source=source,
        event_name=os.environ.get("GITHUB_EVENT_NAME", ""),
        sha=os.environ.get("GITHUB_SHA", "")[:12],
        requested_at=None,
        started_at=datetime.fromisoformat(summary["started_at"].replace("Z", "+00:00"))
        if summary.get("started_at")
        else now,
        completed_at=now,
        decision=None,
        phase="capture",
        status=status,
        extra={
            k: summary.get(k)
            for k in (
                "batches",
                "horizons_delivered",
                "horizons_missed_logged",
                "missed_states",
                "paid_calls",
                "credits_spent",
                "odds_api",
                "hold_minutes",
            )
        },
    )
    url = github_remote_url()
    if url is None:
        print(json.dumps(row, default=str))
        return 0
    try:
        ok = ArchiveAppender(url, paths=("dispatch",)).append_heartbeat(
            row, day=now.strftime("%Y-%m-%d"), reliability=_reliability_fn(now)
        )
        print(f"capture completion recorded={ok} status={status}")
    except Exception as exc:
        print(redact(f"capture completion not recorded: {exc}"))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    w = sub.add_parser("wake")
    w.add_argument(
        "--archive-dir", default=None, help="local archive (tests/offline); no API, no push"
    )
    c = sub.add_parser("complete")
    c.add_argument("--tick-summary", required=True)
    c.add_argument("--status", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "complete":
        return cmd_complete(a)
    if a.cmd is None:
        a = ap.parse_args(["wake", *(argv or sys.argv[1:])])
    return cmd_wake(a)


if __name__ == "__main__":
    raise SystemExit(main())
