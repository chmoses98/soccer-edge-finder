"""Kickoff-timed horizon scheduling (remediation phase 6; audit §K capture requirement, §I1).

GitHub cron delivers only a fraction of its slots, so no single tick can be relied on. The design is a
cheap frequent dispatcher: every tick reads the fixture schedule and the durable delivery log, works out
which required horizons are *satisfiable now*, and runs one bounded capture batch when any are. A missed
tick is caught up by the next one as long as the horizon's validity window is still open; a horizon whose
window closed without a capture is logged as MISSED (never silently lost). Every tick is idempotent
(delivered horizons are never re-logged) and one concurrency group bounds the work.

Required horizons (minutes before kickoff): 120, 60, 30, 15, 5. Each has a validity window
[lower, upper] in minutes-to-kickoff: a capture anywhere inside the window delivers the horizon and the
*achieved* minutes are recorded so the true precision is measured rather than assumed.

    horizon  window (minutes to kickoff)
    120      (60, 130]
    60       (30, 66]
    30       (15, 33]
    15       (5, 17]
    5        (0, 7]

This module is stdlib-only so the dispatcher's decide job can run it without installing the package.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REQUIRED_HORIZONS: tuple[int, ...] = (120, 60, 30, 15, 5)
# (lower_exclusive, upper_inclusive) in minutes to kickoff
HORIZON_WINDOWS: dict[int, tuple[float, float]] = {
    120: (60, 130),
    60: (30, 66),
    30: (15, 33),
    15: (5, 17),
    5: (0, 7),
}
SCHEDULE_LOOKAHEAD_MINUTES = 130
STATE_LOG = "dispatch/horizons.jsonl"
FIRST_SEEN_FILE = "dispatch/first_seen.json"

# terminal horizon states (PENDING is computed for horizons whose window has not closed yet)
DELIVERED = "DELIVERED"
MISSED_BEFORE_WAKE = "MISSED_BEFORE_WAKE"  # no dispatcher wake landed inside the window
MISSED_EXECUTION_FAILURE = "MISSED_EXECUTION_FAILURE"  # a wake landed inside it but did not deliver
NOT_APPLICABLE = "NOT_APPLICABLE"  # the fixture entered the schedule after the window had closed
PENDING = "PENDING"
SCHEDULE_FILE = "dispatch/schedule.json"
DIAGNOSTICS_FILE = "dispatch/diagnostics.json"


def _dt(v: str | datetime) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    return datetime.fromisoformat(v.replace("Z", "+00:00"))


def _iso(d: datetime) -> str:
    return d.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class ScheduledFixture:
    fixture_id: str
    kickoff_utc: datetime
    competition_id: str
    source: str  # 'run_output' (has Kalshi markets) | 'espn'
    markets_discovered: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "kickoff_utc": _iso(self.kickoff_utc),
            "competition_id": self.competition_id,
            "source": self.source,
            "markets_discovered": self.markets_discovered,
        }

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> ScheduledFixture:
        return cls(
            d["fixture_id"],
            _dt(d["kickoff_utc"]),
            d.get("competition_id", ""),
            d.get("source", ""),
            int(d.get("markets_discovered") or 0),
        )


@dataclass
class HorizonRow:
    """One line of the append-only delivery log."""

    fixture_id: str
    kickoff_utc: str
    horizon: int
    status: str  # delivered | missed
    logged_at: str
    achieved_minutes: float | None = None
    lateness_minutes: float | None = None  # horizon - achieved (positive = later than nominal)
    batch_id: str | None = None
    actions: list[str] = field(default_factory=list)
    # explicit terminal state (scheduler repair, 2026-09-30; older rows carry None = legacy):
    # DELIVERED | MISSED_BEFORE_WAKE | MISSED_EXECUTION_FAILURE | NOT_APPLICABLE
    state: str | None = None
    reason: str | None = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DueHorizon:
    fixture: ScheduledFixture
    horizon: int
    minutes_to_kickoff: float

    @property
    def due_now(self) -> bool:
        lo, hi = HORIZON_WINDOWS[self.horizon]
        return lo < self.minutes_to_kickoff <= hi


def horizon_for_minutes(minutes_to_kickoff: float) -> int | None:
    """Which required horizon a capture at this distance delivers (None outside every window)."""
    for h in REQUIRED_HORIZONS:
        lo, hi = HORIZON_WINDOWS[h]
        if lo < minutes_to_kickoff <= hi:
            return h
    return None


def load_log(path: Path) -> list[HorizonRow]:
    if not path.exists():
        return []
    out = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            d = json.loads(ln)
            out.append(HorizonRow(**{k: d.get(k) for k in HorizonRow.__dataclass_fields__}))
    return out


def append_log(path: Path, rows: list[HorizonRow]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r.to_json(), sort_keys=True, separators=(",", ":")) + "\n")


def load_schedule(path: Path) -> list[ScheduledFixture]:
    if not path.exists():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    return [ScheduledFixture.from_json(d) for d in doc.get("fixtures", [])]


def logged_keys(log: list[HorizonRow]) -> set[tuple[str, int]]:
    return {(r.fixture_id, r.horizon) for r in log}


def plan(
    schedule: list[ScheduledFixture], log: list[HorizonRow], *, now: datetime
) -> tuple[list[DueHorizon], list[HorizonRow], list[DueHorizon]]:
    """(due now, newly missed rows to log, upcoming) for one tick.

    * due now: (fixture, horizon) whose window contains `now` and which has no log row yet;
    * missed: (fixture, horizon) whose window has fully closed (now is past its lower bound) with no log
      row — logged once so the gap is explicit;
    * upcoming: the next satisfiable (fixture, horizon) per fixture whose window opens later, ordered by
      opening time (used by the hold logic).
    """
    done = logged_keys(log)
    due: list[DueHorizon] = []
    missed: list[HorizonRow] = []
    upcoming: list[DueHorizon] = []
    for fx in schedule:
        mtk = (fx.kickoff_utc - now).total_seconds() / 60
        for h in REQUIRED_HORIZONS:
            if (fx.fixture_id, h) in done:
                continue
            lo, hi = HORIZON_WINDOWS[h]
            if lo < mtk <= hi:
                due.append(DueHorizon(fx, h, mtk))
            elif mtk <= lo:
                missed.append(
                    HorizonRow(fx.fixture_id, _iso(fx.kickoff_utc), h, "missed", _iso(now))
                )
            elif mtk > hi:
                upcoming.append(DueHorizon(fx, h, mtk))
    upcoming.sort(key=lambda d: d.minutes_to_kickoff - HORIZON_WINDOWS[d.horizon][1])
    return due, missed, upcoming


def minutes_until_next_window(upcoming: list[DueHorizon]) -> float | None:
    """Minutes from now until the earliest upcoming window opens (None when nothing is upcoming)."""
    if not upcoming:
        return None
    d = upcoming[0]
    return max(0.0, d.minutes_to_kickoff - HORIZON_WINDOWS[d.horizon][1])


def delivered_rows(
    due: list[DueHorizon], *, now: datetime, batch_id: str, actions: list[str]
) -> list[HorizonRow]:
    rows = []
    for d in due:
        mtk = (d.fixture.kickoff_utc - now).total_seconds() / 60
        rows.append(
            HorizonRow(
                d.fixture.fixture_id,
                _iso(d.fixture.kickoff_utc),
                d.horizon,
                "delivered",
                _iso(now),
                achieved_minutes=round(mtk, 2),
                lateness_minutes=round(d.horizon - mtk, 2),
                batch_id=batch_id,
                actions=list(actions),
                state=DELIVERED,
            )
        )
    return rows


def window_bounds(kickoff: datetime, horizon: int) -> tuple[datetime, datetime]:
    """(opens, closes) of a horizon's validity window in wall-clock time."""
    lo, hi = HORIZON_WINDOWS[horizon]
    return kickoff - timedelta(minutes=hi), kickoff - timedelta(minutes=lo)


def classify_missed(
    rows: list[HorizonRow], wake_times: list[datetime], first_seen: dict[str, str]
) -> list[HorizonRow]:
    """Give every newly missed row an explicit state:

    * NOT_APPLICABLE when the fixture was first scheduled after the window had already closed;
    * MISSED_EXECUTION_FAILURE when at least one dispatcher wake started inside the window (the
      dispatcher ran but the horizon was not delivered: a failed capture, a stale decision, ...);
    * MISSED_BEFORE_WAKE otherwise (no wake at all inside the window: the scheduler never fired).
    """
    out = []
    for r in rows:
        opens, closes = window_bounds(_dt(r.kickoff_utc), int(r.horizon))
        seen = first_seen.get(r.fixture_id)
        if seen is not None and _dt(seen) >= closes:
            r.state, r.reason = (
                NOT_APPLICABLE,
                f"first scheduled {seen}, window closed {_iso(closes)}",
            )
        elif any(opens <= t <= closes for t in wake_times):
            n = sum(1 for t in wake_times if opens <= t <= closes)
            r.state, r.reason = (
                MISSED_EXECUTION_FAILURE,
                f"{n} dispatcher wake(s) inside the window",
            )
        else:
            r.state, r.reason = MISSED_BEFORE_WAKE, "no dispatcher wake inside the window"
        out.append(r)
    return out


def row_state(r: HorizonRow) -> str:
    """Terminal state of a log row; legacy rows (before explicit states) map from their status."""
    if r.state:
        return r.state
    return DELIVERED if r.status == "delivered" else MISSED_BEFORE_WAKE


def diagnostics(
    log: list[HorizonRow], schedule: list[ScheduledFixture], *, now: datetime
) -> dict[str, Any]:
    """Horizon-delivery diagnostics: per-horizon delivered/missed rates, achieved-minute distribution,
    lateness, and fixtures still pending."""
    per_h: dict[int, dict[str, Any]] = {
        h: {"delivered": 0, "missed": 0, "achieved_minutes": [], "lateness_minutes": []}
        for h in REQUIRED_HORIZONS
    }
    fixtures_seen: set[str] = set()
    for r in log:
        fixtures_seen.add(r.fixture_id)
        slot = per_h.get(int(r.horizon))
        if slot is None:
            continue
        slot[r.status] = slot.get(r.status, 0) + 1
        if r.status == "delivered" and r.achieved_minutes is not None:
            slot["achieved_minutes"].append(float(r.achieved_minutes))
            slot["lateness_minutes"].append(float(r.lateness_minutes or 0.0))

    def _q(xs: list[float], q: float) -> float | None:
        if not xs:
            return None
        s = sorted(xs)
        i = min(len(s) - 1, max(0, round(q * (len(s) - 1))))
        return round(s[i], 2)

    out_h = {}
    for h, slot in per_h.items():
        n = slot["delivered"] + slot["missed"]
        out_h[str(h)] = {
            "delivered": slot["delivered"],
            "missed": slot["missed"],
            "delivery_rate": (slot["delivered"] / n) if n else None,
            "achieved_minutes_median": _q(slot["achieved_minutes"], 0.5),
            "achieved_minutes_p10": _q(slot["achieved_minutes"], 0.1),
            "achieved_minutes_p90": _q(slot["achieved_minutes"], 0.9),
            "lateness_minutes_median": _q(slot["lateness_minutes"], 0.5),
            "lateness_minutes_max": max(slot["lateness_minutes"])
            if slot["lateness_minutes"]
            else None,
        }
    pending = [
        fx.to_json()
        for fx in schedule
        if fx.kickoff_utc > now
        and any((fx.fixture_id, h) not in logged_keys(log) for h in REQUIRED_HORIZONS)
    ]
    deliv = sum(v["delivered"] for v in out_h.values())
    miss = sum(v["missed"] for v in out_h.values())
    return {
        "schema": "horizon_diagnostics_v1",
        "generated_at": _iso(now),
        "required_horizons": list(REQUIRED_HORIZONS),
        "windows": {str(h): list(w) for h, w in HORIZON_WINDOWS.items()},
        "fixtures_tracked": len(fixtures_seen),
        "delivered_total": deliv,
        "missed_total": miss,
        "delivery_rate_total": (deliv / (deliv + miss)) if (deliv + miss) else None,
        "by_horizon": out_h,
        "pending_fixtures": pending[:100],
        "n_pending_fixtures": len(pending),
    }


def build_schedule(
    *,
    run_output: dict[str, Any] | None,
    espn_fixtures: list[dict[str, Any]],
    priced_competitions: set[str],
    now: datetime,
    lookahead_hours: float = 72,
) -> dict[str, Any]:
    """Fixtures that need kickoff-timed captures: every event of the latest RUN SOCCER output (they have
    Kalshi markets) plus ESPN fixtures of priced competitions (so a fixture the last run did not see, or a
    day with no run yet, still gets covered)."""
    horizon_end = now + timedelta(hours=lookahead_hours)
    out: dict[str, ScheduledFixture] = {}
    for ev in (run_output or {}).get("events", []):
        try:
            ko = _dt(ev["start_time"])
        except (KeyError, ValueError):
            continue
        if now - timedelta(hours=3) <= ko <= horizon_end:
            out[ev["event_id"]] = ScheduledFixture(
                ev["event_id"],
                ko,
                ev.get("league_id") or ev.get("league", ""),
                "run_output",
                int(ev.get("markets_discovered") or 0),
            )
    for fx in espn_fixtures:
        comp = fx.get("competition_id", "")
        if comp not in priced_competitions or fx.get("fixture_id") in out:
            continue
        try:
            ko = _dt(fx["kickoff_utc"])
        except (KeyError, ValueError, TypeError):
            continue
        if now - timedelta(hours=3) <= ko <= horizon_end:
            out[fx["fixture_id"]] = ScheduledFixture(fx["fixture_id"], ko, comp, "espn")
    fixtures = sorted(out.values(), key=lambda f: f.kickoff_utc)
    return {
        "schema": "dispatch_schedule_v1",
        "generated_at": _iso(now),
        "lookahead_hours": lookahead_hours,
        "fixtures": [f.to_json() for f in fixtures],
    }
