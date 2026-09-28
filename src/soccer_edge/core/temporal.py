"""Universal no-future-information guard (remediation phase 5; audit C4 "guard to add").

Rule: no input used by a prediction may carry `observed_at > decision_time`. The guard is applied to every
input class the pipeline consumes (fixtures, lineups, injuries, weather, results, reference odds, team and
player stats, market snapshots) and fails closed: a violation raises `FutureInformationError` and the run,
or the research fit, does not proceed. Equality is allowed (observed exactly at the decision time).

Two entry points:

* `TemporalGuard(decision_time)` — `.check(observed_at, kind, ref)` for one timestamp, `.check_all(...)`
  for a batch; `.report()` summarises what was checked (kinds, counts, latest observation) so the run
  output can prove the guard ran.
* `assert_no_future_dates(dates, decision_date, kind)` — the date-granularity variant used for results in
  model fitting (`r.date < as_of`): a result dated on/after the decision date is future information.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from soccer_edge.core.errors import SoccerEdgeError
from soccer_edge.core.time import ensure_utc, iso_utc, parse_iso_utc

GUARDED_KINDS = (
    "fixtures",
    "lineups",
    "injuries",
    "weather",
    "results",
    "reference_odds",
    "team_stats",
    "player_stats",
    "market_snapshots",
)


class FutureInformationError(SoccerEdgeError):
    pass


def _as_dt(v: datetime | str) -> datetime:
    if isinstance(v, str):
        return parse_iso_utc(v)
    return ensure_utc(v)


@dataclass
class TemporalGuard:
    decision_time: datetime
    checked: dict[str, int] = field(default_factory=dict)
    latest: dict[str, datetime] = field(default_factory=dict)
    violations: list[dict[str, Any]] = field(default_factory=list)
    fail_fast: bool = True

    def __post_init__(self) -> None:
        self.decision_time = ensure_utc(self.decision_time)

    def check(self, observed_at: datetime | str | None, kind: str, ref: str = "") -> None:
        """Raise when `observed_at` is after the decision time. `None` is skipped (unknown observation
        time is handled by the freshness gate, not by this guard)."""
        if observed_at is None:
            return
        obs = _as_dt(observed_at)
        self.checked[kind] = self.checked.get(kind, 0) + 1
        if kind not in self.latest or obs > self.latest[kind]:
            self.latest[kind] = obs
        if obs > self.decision_time:
            v = {
                "kind": kind,
                "ref": ref,
                "observed_at": iso_utc(obs),
                "decision_time": iso_utc(self.decision_time),
                "lead_seconds": (obs - self.decision_time).total_seconds(),
            }
            self.violations.append(v)
            if self.fail_fast:
                raise FutureInformationError(
                    f"future information: {kind} {ref} observed_at {v['observed_at']} > decision_time {v['decision_time']}"
                )

    def check_all(
        self,
        items: Iterable[Any],
        kind: str,
        *,
        observed_at: Callable[[Any], datetime | str | None],
        ref: Callable[[Any], str] | None = None,
    ) -> int:
        n = 0
        for it in items:
            self.check(observed_at(it), kind, ref(it) if ref else "")
            n += 1
        return n

    def report(self) -> dict[str, Any]:
        return {
            "decision_time": iso_utc(self.decision_time),
            "checked": dict(sorted(self.checked.items())),
            "latest_observed_at": {k: iso_utc(v) for k, v in sorted(self.latest.items())},
            "violations": list(self.violations),
            "ok": not self.violations,
        }


def assert_no_future_dates(
    dates: Iterable[date], decision_date: date, kind: str = "results"
) -> int:
    """Date-granularity guard for training rows: every date must be strictly before the decision date."""
    n = 0
    for d in dates:
        n += 1
        if d >= decision_date:
            raise FutureInformationError(
                f"future information: {kind} dated {d.isoformat()} >= decision date {decision_date.isoformat()}"
            )
    return n
