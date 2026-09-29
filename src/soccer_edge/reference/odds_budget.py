"""Fail-closed credit guard + append-only quota ledger for soccer's use of the SHARED Odds API account.

The account is shared with chmoses98/edge-finder-api (MLB). Soccer is the junior consumer, so every paid
request must pass all of:

1. ACCOUNT RESERVE FLOOR: the provider-reported `x-requests-remaining` observed *in this tick* (the free
   `/sports` call returns it, and it already reflects MLB's spend) minus the request's cost must stay at or
   above `account_reserve_floor`. No fresh remaining-quota evidence -> no paid request.
2. DAILY CEILING (UTC day): soccer credits already charged today + cost <= `daily_credit_ceiling`; entry
   captures may only use the ceiling minus `close_priority_credits`, so closes (the CLV anchor) keep a
   share when a busy day runs out.
3. ROLLING 30-DAY CEILING: soccer credits charged in the last 30 UTC days + cost <= the 30-day ceiling.

The ledger (`odds_api/budget/<UTC date>.jsonl`, published append-only to data-archive) is the only source
of soccer's spend: a retry, a new process or a lost state file cannot reset it. Credits charged come from
the provider's `x-requests-last`; when that header is missing the design cost is charged, never zero.
Every row (free call, paid call, blocked decision, not-configured tick) records the quota headers seen.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from soccer_edge.core.serialization import append_jsonl, read_jsonl
from soccer_edge.core.time import iso_utc

GUARD_VERSION = "SOCCER_ODDS_BUDGET_GUARD_V1_2026_09_29"
LEDGER_DIR = Path("odds_api") / "budget"

STATUS_OK = "OK"
STATUS_BLOCKED = "BLOCKED_BUDGET_GUARD"
STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"
STATUS_FAILED = "REQUEST_FAILED"


@dataclass(frozen=True)
class BudgetConfig:
    bookmakers: tuple[str, ...]
    markets: tuple[str, ...]
    daily_credit_ceiling: int
    close_priority_credits: int
    rolling_30d_credit_ceiling: int
    account_reserve_floor: int
    entry_window_minutes: tuple[float, float]
    close_window_minutes: tuple[float, float]
    event_join_tolerance_minutes: float
    one_side_join_tolerance_minutes: float

    @classmethod
    def load(cls, path: Path) -> BudgetConfig:
        d = json.loads(path.read_text())
        return cls(
            tuple(d["bookmakers"]),
            tuple(d["markets"]),
            int(d["daily_credit_ceiling"]),
            int(d["close_priority_credits"]),
            int(d["rolling_30d_credit_ceiling"]),
            int(d["account_reserve_floor"]),
            tuple(d["entry_window_minutes"]),
            tuple(d["close_window_minutes"]),
            float(d["event_join_tolerance_minutes"]),
            float(d["one_side_join_tolerance_minutes"]),
        )


def _int(v: Any) -> int | None:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


class BudgetLedger:
    def __init__(self, root: Path) -> None:
        self.dir = root / LEDGER_DIR

    def path(self, day: str) -> Path:
        return self.dir / f"{day}.jsonl"

    def rows(self, day: str) -> list[dict[str, Any]]:
        p = self.path(day)
        return read_jsonl(p) if p.exists() else []

    def rows_since(self, now: datetime, days: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for k in range(days):
            out.extend(self.rows((now - timedelta(days=k)).strftime("%Y-%m-%d")))
        return out

    def append(self, now: datetime, row: dict[str, Any]) -> None:
        append_jsonl(
            self.path(now.strftime("%Y-%m-%d")),
            {"guard_version": GUARD_VERSION, "logged_at": iso_utc(now), **row},
        )

    def spent(self, now: datetime, days: int) -> int:
        return sum(int(r.get("credits_charged") or 0) for r in self.rows_since(now, days))

    def fixtures_captured(self, now: datetime, purpose: str) -> set[str]:
        """Fixtures that already have a successful paid capture for `purpose` ('entry' | 'close')."""
        done: set[str] = set()
        for r in self.rows_since(now, 3):
            if r.get("kind") == "odds" and r.get("status") == STATUS_OK:
                done.update(r.get(f"{purpose}_fixtures") or [])
        return done


def charge(quota: dict[str, Any], design_cost: int) -> tuple[int, str]:
    """Credits to record for a request that reached the provider: `x-requests-last`, else the design cost."""
    last = _int(quota.get("x-requests-last"))
    return (last, "PROVIDER_HEADER") if last is not None else (design_cost, "DESIGN_COST_FALLBACK")


def decide(
    ledger: BudgetLedger,
    cfg: BudgetConfig,
    *,
    now: datetime,
    cost: int,
    remaining_now: int | None,
    close_capture: bool,
) -> dict[str, Any]:
    spent_today = ledger.spent(now, 1)
    spent_30d = ledger.spent(now, 30)
    daily_cap = cfg.daily_credit_ceiling - (0 if close_capture else cfg.close_priority_credits)
    out: dict[str, Any] = {
        "spent_today_before": spent_today,
        "spent_30d_before": spent_30d,
        "expected_cost": cost,
        "remaining_evidence": remaining_now,
        "daily_cap_applied": daily_cap,
        "rolling_30d_ceiling": cfg.rolling_30d_credit_ceiling,
        "account_reserve_floor": cfg.account_reserve_floor,
    }
    if remaining_now is None:
        out.update(allowed=False, reason="REMAINING_QUOTA_UNKNOWN")
    elif remaining_now - cost < cfg.account_reserve_floor:
        out.update(allowed=False, reason="ACCOUNT_RESERVE_FLOOR")
    elif spent_today + cost > daily_cap:
        out.update(
            allowed=False, reason="DAILY_CEILING" if close_capture else "DAILY_CEILING_ENTRY_SHARE"
        )
    elif spent_30d + cost > cfg.rolling_30d_credit_ceiling:
        out.update(allowed=False, reason="ROLLING_30D_CEILING")
    else:
        out.update(allowed=True, reason=None)
    return out
