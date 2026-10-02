"""Cheap, offline reads of what the archive already holds: Pinnacle rows, lineups, fixture context.

A reprice reads only files. Nothing in this module makes a network call: the Pinnacle reference is whatever
the kickoff chain's budget-guarded T-60 entry / T-15 close captures already wrote under
`reference/<day>/oddsapi-*.jsonl[.gz]`; lineups are the ESPN sync rows under `lineups/<day>/`; fixture
context is the latest `fixtures/espn/<day>/*.json` and `dispatch/schedule.json`.

`roots` are searched newest-first (a link's work dir before the archive clone); for every key the latest
observation wins, so a capture written seconds ago in the work dir supersedes the archive.
"""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from soccer_edge.core.serialization import read_json_or
from soccer_edge.core.time import ensure_utc

RefKey = tuple[str, str, str, Decimal | None]  # (fixture_id, market, selection, line)


def _dt(v: Any) -> datetime | None:
    if not v:
        return None
    try:
        return ensure_utc(datetime.fromisoformat(str(v).replace("Z", "+00:00")))
    except ValueError:
        return None


def _days(now: datetime, back: int) -> list[str]:
    return [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(back + 1)]


def _iter_jsonl(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    try:
        with opener(path, "rt", encoding="utf-8") as fh:
            for ln in fh:
                if ln.strip():
                    try:
                        yield json.loads(ln)
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return


# ------------------------------------------------------------------------------------------- reference


def pinnacle_rows(roots: list[Path], *, now: datetime, days_back: int = 2) -> dict[RefKey, dict]:
    """Latest Pinnacle row per (fixture, market, selection, line) captured at or before `now`."""
    out: dict[RefKey, dict] = {}
    for root in roots:
        for day in _days(now, days_back):
            d = root / "reference" / day
            if not d.is_dir():
                continue
            for f in sorted([*d.glob("oddsapi-*.jsonl"), *d.glob("oddsapi-*.jsonl.gz")]):
                for r in _iter_jsonl(f):
                    if r.get("bookmaker") != "pinnacle":
                        continue
                    cap = _dt(r.get("captured_at"))
                    if cap is None or cap > now:
                        continue
                    line = r.get("line")
                    key = (
                        r["fixture_id"],
                        r["market"],
                        r["selection"],
                        Decimal(str(line)) if line is not None else None,
                    )
                    cur = out.get(key)
                    if cur is None or cap > _dt(cur["captured_at"]):
                        out[key] = r
    return out


# ------------------------------------------------------------------------------------------- fixtures


@dataclass
class FixtureContext:
    """Latest fixture facts observable without a model run."""

    as_of: datetime | None = None  # when the fixture list was observed
    fixtures: dict[str, dict[str, Any]] = field(default_factory=dict)  # fixture_id -> facts
    espn_event_ids: dict[str, str] = field(default_factory=dict)  # fixture_id -> espn event id
    schedule: dict[str, dict[str, Any]] = field(default_factory=dict)  # dispatch/schedule.json rows


def fixture_context(roots: list[Path]) -> FixtureContext:
    ctx = FixtureContext()
    best: tuple[datetime, Path] | None = None
    for root in roots:
        files = sorted((root / "fixtures" / "espn").glob("*/*.json"))
        if not files:
            continue
        doc = read_json_or(files[-1], {}) or {}
        as_of = _dt(doc.get("as_of"))
        if as_of and (best is None or as_of > best[0]):
            best = (as_of, files[-1])
    if best is not None:
        doc = read_json_or(best[1], {}) or {}
        ctx.as_of = best[0]
        for row in doc.get("fixtures", []):
            fid = row.get("fixture_id")
            if not fid:
                continue
            ctx.fixtures[fid] = {
                "kickoff_utc": row.get("kickoff_utc"),
                "neutral_site": bool(row.get("neutral_site")),
                "stage": row.get("stage"),
                "competition_id": row.get("competition_id"),
                "status": row.get("status"),
            }
            if row.get("espn_event_id"):
                ctx.espn_event_ids[fid] = str(row["espn_event_id"])
    for root in roots:
        doc = read_json_or(root / "dispatch" / "schedule.json", None)
        if doc and doc.get("fixtures"):
            for row in doc["fixtures"]:
                ctx.schedule.setdefault(row["fixture_id"], row)
            break
    return ctx


# ------------------------------------------------------------------------------------------- lineups


@dataclass(frozen=True)
class LineupObservation:
    state: str  # unconfirmed | confirmed | post_hoc
    key: str  # 'none' while no XI is published, else the sheet's content hash
    last_change_at: datetime | None  # captured_at of the latest stored (change-suppressed) row
    checked_at: datetime | None  # last lineup sync covering this league (>= last_change_at)
    league: str | None

    def to_json(self) -> dict[str, Any]:
        from soccer_edge.core.time import iso_utc

        return {
            "state": self.state,
            "key": self.key,
            "last_change_at": iso_utc(self.last_change_at) if self.last_change_at else None,
            "checked_at": iso_utc(self.checked_at) if self.checked_at else None,
        }


def lineup_key(row: dict[str, Any]) -> str:
    return str(row.get("content_hash")) if row.get("published") else "none"


def lineup_observations(
    roots: list[Path], espn_event_ids: dict[str, str], *, now: datetime, days_back: int = 2
) -> dict[str, LineupObservation]:
    """fixture_id -> latest lineup observation at or before `now` (only fixtures with an ESPN event id)."""
    wanted = {eid: fid for fid, eid in espn_event_ids.items()}
    latest: dict[str, dict] = {}
    for root in roots:
        for day in _days(now, days_back):
            d = root / "lineups" / day
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.jsonl")):
                for r in _iter_jsonl(f):
                    eid = str(r.get("espn_event_id"))
                    if eid not in wanted:
                        continue
                    cap = _dt(r.get("captured_at"))
                    if cap is None or cap > now:
                        continue
                    cur = latest.get(eid)
                    if cur is None or cap > _dt(cur["captured_at"]):
                        latest[eid] = r
    sync_at, sync_leagues = None, set()
    for root in roots:
        st = read_json_or(root / "STATUS.json", None) or {}
        at = _dt(st.get("as_of"))
        if at and at <= now and (sync_at is None or at > sync_at):
            sync_at, sync_leagues = at, set(st.get("leagues") or [])
    out: dict[str, LineupObservation] = {}
    for eid, r in latest.items():
        changed = _dt(r.get("captured_at"))
        checked = changed
        if sync_at and r.get("league") in sync_leagues and (changed is None or sync_at > changed):
            checked = sync_at
        out[wanted[eid]] = LineupObservation(
            state=str(r.get("lineup_state") or "unconfirmed"),
            key=lineup_key(r),
            last_change_at=changed,
            checked_at=checked,
            league=r.get("league"),
        )
    return out
