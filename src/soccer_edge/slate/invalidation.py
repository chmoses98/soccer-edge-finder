"""Deterministic invalidation of cached fixture probabilities (docs/ACTIONABLE_SLATE.md §Invalidation).

A cached probability stays valid while every pricing input that produced it is unchanged. A reprice
re-observes the inputs it can read cheaply and compares them with the fingerprint stored on the board:

* model version / engine / world layer differs from the configured production versions;
* kickoff moved by more than KICKOFF_TOLERANCE (ESPN fixture list, else the dispatch schedule);
* venue / neutral-site flag changed;
* stage changed, or the fixture is now postponed / cancelled;
* lineup changed: an XI was published, or a published XI changed (the ESPN sheet's content hash).
  An unpublished sheet is not a lineup input ('none' before and after).

A pure Kalshi price move is NOT an input: it never invalidates. Competition and stage are also part of the
canonical fixture id, so a competition/stage re-assignment arrives as a new fixture (validity MISSING).
No player-availability (injury) provider is wired: availability enters only through XI publication.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from soccer_edge.core.time import ensure_utc
from soccer_edge.slate.observations import FixtureContext, LineupObservation

KICKOFF_TOLERANCE = timedelta(minutes=5)

# production defaults of `soccer run` / `soccer dispatch tick` (a test keeps the CLI defaults equal)
DEFAULT_MODEL_VERSION = "dc_laplace_v1"
DEFAULT_ENGINE_VERSION = "world_sim_v2"
DEFAULT_WORLDS_VERSION = "worlds_v1"


def expected_versions(
    model_version: str = DEFAULT_MODEL_VERSION,
    engine_version: str = DEFAULT_ENGINE_VERSION,
    worlds_version: str = DEFAULT_WORLDS_VERSION,
) -> dict[str, str]:
    return {
        "model_version": model_version,
        "engine_version": engine_version,
        "worlds_version": worlds_version,
    }


def _dt(v: Any) -> datetime | None:
    if not v:
        return None
    if isinstance(v, datetime):
        return ensure_utc(v)
    return ensure_utc(datetime.fromisoformat(str(v).replace("Z", "+00:00")))


def current_kickoff(entry: dict[str, Any], ctx: FixtureContext) -> datetime | None:
    fid = entry["fixture_id"]
    cur = ctx.fixtures.get(fid) or {}
    ko = _dt(cur.get("kickoff_utc")) or _dt((ctx.schedule.get(fid) or {}).get("kickoff_utc"))
    return ko or _dt(entry["inputs"].get("kickoff_utc"))


def invalidation_reasons(
    entry: dict[str, Any],
    *,
    ctx: FixtureContext,
    lineup: LineupObservation | None,
    versions: dict[str, str] | None = None,
) -> list[str]:
    inp = entry.get("inputs") or {}
    fid = entry["fixture_id"]
    reasons: list[str] = []
    for k, want in (versions or {}).items():
        if want is not None and inp.get(k) != want:
            reasons.append(f"model_version_changed:{k}:{inp.get(k)}->{want}")
    cached_ko = _dt(inp.get("kickoff_utc"))
    ko = current_kickoff(entry, ctx)
    if cached_ko and ko and abs(ko - cached_ko) > KICKOFF_TOLERANCE:
        reasons.append(f"kickoff_changed:{inp.get('kickoff_utc')}->{ko.isoformat()}")
    cur = ctx.fixtures.get(fid)
    if cur is not None:
        if bool(cur.get("neutral_site")) != bool(inp.get("neutral_site")):
            reasons.append(
                f"venue_changed:neutral_site {inp.get('neutral_site')}->{cur.get('neutral_site')}"
            )
        if cur.get("stage") and inp.get("stage") and cur["stage"] != inp["stage"]:
            reasons.append(f"stage_changed:{inp.get('stage')}->{cur['stage']}")
        status = str(cur.get("status") or "").lower()
        if status in ("postponed", "cancelled", "canceled", "abandoned", "rescheduled"):
            reasons.append(f"fixture_status:{status}")
    old_key = inp.get("lineup_key") or "none"
    new_key = lineup.key if lineup is not None else "none"
    if new_key != old_key:
        state = lineup.state if lineup is not None else "unknown"
        reasons.append(f"lineup_changed:{'published' if old_key == 'none' else 'revised'}:{state}")
    return reasons
