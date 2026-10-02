"""Which due fixtures need a MODEL refresh at this kickoff-chain batch (docs/ACTIONABLE_SLATE.md §Cadence).

Every batch captures Kalshi (free) and reprices the whole slate from the cached board. A model run is
added only for these due fixtures:

    T-60   primary refresh: fixture/context inputs re-read, fast model run scoped to the fixture, entry
           Pinnacle reference already captured by the same batch (existing approved cadence).
    T-15   lineups/context refreshed first; the model reruns only if a material input changed since the
           cached probability (invalidation.py), or if no refresh happened since the T-60 window opened
           (T-60 missed). The Pinnacle close is the existing approved T-15 capture.
    T-120, T-30, T-5
           reprice only, unless the cached model is invalidated or missing for a fixture with Kalshi markets.
    between horizons (periodic free refresh)
           a scoped model run only for scheduled fixtures that entered the lookahead without ever being
           modelled (`unmodelled_fixtures`), each attempted once per link.

`mode`: 'selective' (default), 'every' (legacy `--with-run`: a model run at every due horizon),
'off' (never; reprice only). A refresh never triggers a paid reference call: the paid calls are decided by
the odds-API action's own purpose windows and claims, independently of this plan.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from soccer_edge.slate.invalidation import invalidation_reasons
from soccer_edge.slate.observations import FixtureContext, LineupObservation

PRIMARY_HORIZON = 60
SECONDARY_HORIZON = 15
T60_WINDOW_OPENS = timedelta(minutes=66)  # dispatch/horizons.py HORIZON_WINDOWS[60] upper bound


def _dt(v: Any) -> datetime:
    return datetime.fromisoformat(str(v).replace("Z", "+00:00"))


def refresh_plan(
    due: list[Any],
    board: dict[str, Any],
    *,
    ctx: FixtureContext,
    lineups: dict[str, LineupObservation],
    versions: dict[str, str] | None,
    mode: str = "selective",
) -> dict[str, str]:
    """fixture_id -> reason, for the due (fixture, horizon) pairs that need a model run now."""
    need: dict[str, str] = {}
    if mode == "off":
        return need
    entries = board.get("fixtures") or {}
    for d in sorted(due, key=lambda d: -d.horizon):
        fx = d.fixture
        fid = fx.fixture_id
        h = int(d.horizon)
        if fid in need:
            continue
        if mode == "every":
            need[fid] = f"T-{h}:every_horizon"
            continue
        has_markets = fx.source == "run_output" or int(fx.markets_discovered or 0) > 0
        entry = entries.get(fid)
        if entry is None:
            if has_markets:
                need[fid] = f"T-{h}:model_missing"
            continue
        reasons = invalidation_reasons(entry, ctx=ctx, lineup=lineups.get(fid), versions=versions)
        if reasons:
            need[fid] = f"T-{h}:invalidated:{reasons[0]}"
        elif h == PRIMARY_HORIZON:
            need[fid] = "T-60:primary_refresh"
        elif h == SECONDARY_HORIZON:
            generated = _dt(entry["model_generated_at"])
            if generated < fx.kickoff_utc - T60_WINDOW_OPENS:
                need[fid] = "T-15:no_model_refresh_since_t60"
    return need


def refresh_window_hours(due: list[Any], fixture_ids: set[str], now: datetime) -> int:
    """Smallest whole-hour window covering the fixtures to refresh (at least 3 h, the fast-run default)."""
    mins = [
        (d.fixture.kickoff_utc - now).total_seconds() / 60
        for d in due
        if d.fixture.fixture_id in fixture_ids
    ]
    return max(3, int(max(mins, default=0) // 60) + 2)


def unmodelled_fixtures(
    schedule: list[Any],
    board: dict[str, Any],
    *,
    now: datetime,
    lookahead_hours: float,
    attempted: set[str],
) -> list[Any]:
    """Scheduled fixtures inside the slate lookahead that no model run has priced yet (not on the board),
    excluding ones already attempted by this link. They entered the rolling window after the last full
    RUN SOCCER (whose window ended earlier), so without a scoped model run the slate would omit them.
    A fixture without Kalshi markets prices nothing and is not retried by the same link."""
    end = now + timedelta(hours=lookahead_hours)
    on_board = set((board.get("fixtures") or {}).keys())
    return [
        fx
        for fx in schedule
        if now < fx.kickoff_utc <= end
        and fx.fixture_id not in on_board
        and fx.fixture_id not in attempted
    ]
