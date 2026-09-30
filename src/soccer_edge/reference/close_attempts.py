"""Why does (or doesn't) a fixture have an external reference close? One explicit state per fixture.

The distinction matters for every CLV statistic: a fixture where the dispatcher never attempted the close
window says nothing about Pinnacle, and a fixture where Pinnacle was asked and quoted nothing says nothing
about the dispatcher. Evidence is read from the archive only:

* dispatch/horizons.jsonl     which close horizons (T-15, T-5) the dispatcher delivered or missed
* odds_api/budget/*.jsonl     every close attempt the reference capture made or declined, and why
* reference/*/oddsapi-*.jsonl which attempted fixtures actually came back with Pinnacle rows

States (most informative wins):

    PINNACLE_VALID_CLOSE        close call made, Pinnacle rows returned for the fixture
    PINNACLE_QUOTED_NOTHING     close call made, Pinnacle had no price for the fixture
    CLOSE_REQUEST_FAILED        close call made, provider error
    CLOSE_BLOCKED_BUDGET        close window reached, the quota guard refused the call
    NO_REFERENCE_EVENT          close window reached, the provider listed no joinable event
    SPORT_NOT_ACTIVE            close window reached, the competition's key is not active at the provider
    NO_SPORT_KEY                close window reached, the competition has no provider key
    DISPATCHER_CLOSE_NO_ATTEMPT close horizon delivered, but no reference attempt was recorded
                                (reference capture not configured yet, or fixture not Kalshi-listed)
    MISSED_DISPATCHER_CLOSE     neither close horizon was delivered: the dispatcher never attempted it
    PENDING                     the close windows have not closed yet
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

CLOSE_HORIZONS = (15, 5)

_RANK = [
    "PINNACLE_VALID_CLOSE",
    "PINNACLE_QUOTED_NOTHING",
    "CLOSE_REQUEST_FAILED",
    "CLOSE_BLOCKED_BUDGET",
    "NO_REFERENCE_EVENT",
    "SPORT_NOT_ACTIVE",
    "NO_SPORT_KEY",
]
_LEDGER_STATUS = {
    "BLOCKED_BUDGET_GUARD": "CLOSE_BLOCKED_BUDGET",
    "REQUEST_FAILED": "CLOSE_REQUEST_FAILED",
    "NO_JOINED_EVENTS": "NO_REFERENCE_EVENT",
    "SPORT_NOT_ACTIVE": "SPORT_NOT_ACTIVE",
    "NO_SPORT_KEY": "NO_SPORT_KEY",
}


def _jsonl(path: Path) -> list[dict[str, Any]]:
    out = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                out.append(json.loads(ln))
            except ValueError:
                continue
    return out


def close_attempt_states(archive_root: Path, *, now: datetime) -> dict[str, dict[str, Any]]:
    root = Path(archive_root)
    evidence: dict[str, list[str]] = {}
    batches: dict[str, str] = {}

    def add(fid: str, state: str, batch: str | None) -> None:
        evidence.setdefault(fid, []).append(state)
        if batch:
            batches.setdefault(fid, batch)

    quoted_by_batch: dict[str, set[str]] = {}
    for p in sorted(root.glob("reference/*/oddsapi-*.jsonl")):
        for r in _jsonl(p):
            if r.get("bookmaker") == "pinnacle" and r.get("batch_id"):
                quoted_by_batch.setdefault(r["batch_id"], set()).add(r.get("fixture_id"))
    for p in sorted(root.glob("odds_api/budget/*.jsonl")):
        for r in _jsonl(p):
            if r.get("kind") != "odds":
                continue
            close = r.get("close_fixtures") or []
            status = r.get("status")
            if status == "OK":
                quoted = set(r.get("quoted_fixtures") or []) | quoted_by_batch.get(
                    r.get("batch_id"), set()
                )
                for f in close:
                    add(
                        f,
                        "PINNACLE_VALID_CLOSE" if f in quoted else "PINNACLE_QUOTED_NOTHING",
                        r.get("batch_id"),
                    )
                for f in r.get("unjoined_fixtures") or []:
                    add(f, "NO_REFERENCE_EVENT", r.get("batch_id"))
            elif status in _LEDGER_STATUS:
                for f in close:
                    add(f, _LEDGER_STATUS[status], r.get("batch_id"))
    delivered: dict[str, bool] = {}
    kickoff: dict[str, str] = {}
    hp = root / "dispatch" / "horizons.jsonl"
    for r in _jsonl(hp) if hp.exists() else []:
        if int(r.get("horizon") or 0) not in CLOSE_HORIZONS:
            continue
        fid = r["fixture_id"]
        kickoff[fid] = r.get("kickoff_utc")
        ok = r.get("status") == "delivered" and (r.get("state") in (None, "DELIVERED"))
        delivered[fid] = delivered.get(fid, False) or ok
    out: dict[str, dict[str, Any]] = {}
    for fid in set(evidence) | set(delivered):
        states = evidence.get(fid, [])
        if states:
            state = min(states, key=_RANK.index)
        elif delivered.get(fid):
            state = "DISPATCHER_CLOSE_NO_ATTEMPT"
        else:
            state = "MISSED_DISPATCHER_CLOSE"
        out[fid] = {
            "state": state,
            "close_horizon_delivered": bool(delivered.get(fid)),
            "batch_id": batches.get(fid),
        }
    return out


def attempt_for(
    states: dict[str, dict[str, Any]], fixture_id: str, kickoff: datetime, now: datetime
) -> dict:
    """State for one fixture, PENDING before kickoff and MISSED_DISPATCHER_CLOSE when nothing was logged."""
    if fixture_id in states:
        return states[fixture_id]
    if kickoff > now:
        return {"state": "PENDING", "close_horizon_delivered": False, "batch_id": None}
    return {"state": "MISSED_DISPATCHER_CLOSE", "close_horizon_delivered": False, "batch_id": None}
