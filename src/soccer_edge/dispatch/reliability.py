"""Rolling scheduler reliability (stdlib only): the quantity that matters is
P(required horizon delivered | fixture existed), not how many cron slots fired.

Inputs: heartbeat rows (every wake, any trigger), the horizon delivery log and the expected heartbeat
cadence (config/dispatch.json). Windows: last 24 h and last 7 days, by horizon window close time.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from soccer_edge.dispatch.horizons import (
    DELIVERED,
    NOT_APPLICABLE,
    HorizonRow,
    _dt,
    _iso,
    row_state,
    window_bounds,
)
from soccer_edge.dispatch.wake import EXTERNAL, GITHUB_BACKUP

CLOSE_HORIZONS = (15, 5)


def _window(
    heartbeats: list[dict[str, Any]],
    log: list[HorizonRow],
    *,
    now: datetime,
    span: timedelta,
    cadence: dict[str, Any],
) -> dict[str, Any]:
    start = now - span
    wakes = [
        h
        for h in heartbeats
        if h.get("phase", "wake") == "wake"
        and h.get("started_at")
        and start <= _dt(h["started_at"]) <= now
    ]
    captures = [
        h
        for h in heartbeats
        if h.get("phase") == "capture"
        and h.get("started_at")
        and start <= _dt(h["started_at"]) <= now
    ]
    by_source = Counter(h.get("trigger_source") for h in wakes)
    minutes = span.total_seconds() / 60
    ext_every = cadence.get("external_heartbeat_minutes")
    gh_every = cadence.get("github_backup_minutes")
    exp_ext = int(minutes // ext_every) if ext_every else None
    exp_gh = int(minutes // gh_every) if gh_every else None
    # horizons whose window closed inside the span
    rows = []
    for r in log:
        try:
            _, closes = window_bounds(_dt(r.kickoff_utc), int(r.horizon))
        except (ValueError, KeyError):
            continue
        if start <= closes <= now:
            rows.append(r)
    states = Counter(row_state(r) for r in rows)
    eligible = [r for r in rows if row_state(r) != NOT_APPLICABLE]
    delivered = [r for r in eligible if row_state(r) == DELIVERED]
    close_fx: dict[str, bool] = {}
    for r in eligible:
        if int(r.horizon) in CLOSE_HORIZONS:
            close_fx[r.fixture_id] = close_fx.get(r.fixture_id, False) or row_state(r) == DELIVERED
    fixtures = {r.fixture_id for r in eligible}
    return {
        "span_hours": round(span.total_seconds() / 3600, 1),
        "heartbeats_actual": len(wakes),
        "heartbeats_by_source": dict(sorted(by_source.items(), key=lambda kv: str(kv[0]))),
        "heartbeats_failed": sum(1 for h in wakes if h.get("status") != "OK"),
        "heartbeats_no_work_due": sum(
            1 for h in wakes if h.get("no_action_reason") == "NO_WORK_DUE"
        ),
        "external_heartbeats_expected": exp_ext,
        "external_heartbeats_actual": by_source.get(EXTERNAL, 0),
        "external_trigger_success": (by_source.get(EXTERNAL, 0) / exp_ext) if exp_ext else None,
        "github_backup_expected": exp_gh,
        "github_backup_actual": by_source.get(GITHUB_BACKUP, 0),
        "github_backup_success": (by_source.get(GITHUB_BACKUP, 0) / exp_gh) if exp_gh else None,
        "capture_runs": len(captures),
        "capture_runs_failed": sum(1 for h in captures if h.get("status") != "OK"),
        "paid_calls": sum(int(h.get("paid_calls") or 0) for h in captures),
        "credits_spent": sum(int(h.get("credits_spent") or 0) for h in captures),
        "fixtures_with_horizons": len(fixtures),
        "horizons_eligible": len(eligible),
        "horizons_delivered": len(delivered),
        "horizons_missed": len(eligible) - len(delivered),
        "horizon_states": dict(sorted(states.items())),
        "capture_success_rate": (len(delivered) / len(eligible)) if eligible else None,
        "close_fixtures_eligible": len(close_fx),
        "close_fixtures_delivered": sum(close_fx.values()),
        "close_success_rate": (sum(close_fx.values()) / len(close_fx)) if close_fx else None,
    }


def reliability(
    heartbeats: list[dict[str, Any]],
    log: list[HorizonRow],
    *,
    now: datetime,
    cadence: dict[str, Any],
) -> dict[str, Any]:
    last = max(
        (h for h in heartbeats if h.get("phase", "wake") == "wake" and h.get("started_at")),
        key=lambda h: h["started_at"],
        default=None,
    )
    return {
        "schema": "dispatch_reliability_v1",
        "generated_at": _iso(now),
        "cadence": cadence,
        "last_wake": None
        if last is None
        else {
            k: last.get(k) for k in ("started_at", "trigger_source", "status", "no_action_reason")
        },
        "last_24h": _window(heartbeats, log, now=now, span=timedelta(hours=24), cadence=cadence),
        "last_7d": _window(heartbeats, log, now=now, span=timedelta(days=7), cadence=cadence),
        "definition": "capture_success_rate = delivered / eligible horizons whose window closed in the span "
        "(NOT_APPLICABLE excluded); close_success_rate = fixtures with a T-15 or T-5 delivery / fixtures "
        "whose close windows closed in the span",
    }
