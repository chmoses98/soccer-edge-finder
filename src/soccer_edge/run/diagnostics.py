"""Coverage diagnostics: WHY is each non-priced contract not priced, and does it matter now?

Buckets every discovered contract by disposition x {current_tradable, future_not_open, past}, by
competition, by family, and extracts the ranked list of unknown team names so registry work can be
prioritised by *currently executable* surface rather than by historical junk.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from soccer_edge.core.time import ensure_utc, iso_utc
from soccer_edge.kalshi.coverage import CoverageLedger, Disposition
from soccer_edge.kalshi.taxonomy import COMPETITION_CODES, Scope

UEFA_CODES = {
    "UCL",
    "UCLW",
    "UEL",
    "UECL",
    "UEFANL",
    "UEFANLGROUP",
    "UEFAEURO",
    "UCLLEAGUE",
    "UEFASUPERCUP",
    "UEFASC",
}
INTERNATIONAL_CODES = {
    "WC",
    "WCW",
    "FIFAW",
    "INTLFRIENDLY",
    "CONCACAFNL",
    "CONCACAFGC",
    "COPAAMERICA",
    "AFCON",
    "UEFANL",
    "UEFANLGROUP",
    "UEFAEURO",
}
_UNKNOWN_TEAM = re.compile(r"unknown team '([^']+)'")


def _region(code: str | None) -> str:
    if code is None:
        return "unknown"
    if code in UEFA_CODES:
        return (
            "uefa_club"
            if code in {"UCL", "UCLW", "UEL", "UECL", "UCLLEAGUE", "UEFASUPERCUP", "UEFASC"}
            else "international"
        )
    if code in INTERNATIONAL_CODES:
        return "international"
    return "domestic"


def _time_bucket(close_time: datetime | None, as_of: datetime) -> str:
    if close_time is None:
        return "no_close_time"
    ct = ensure_utc(close_time)
    if ct <= as_of:
        return "past"
    if ct <= as_of + timedelta(hours=72):
        return "next_72h"
    if ct <= as_of + timedelta(days=14):
        return "next_14d"
    return "later"


def build_coverage_diagnostics(
    works: dict[str, Any], cov: CoverageLedger, as_of: datetime, *, discovery_run_id: str
) -> dict[str, Any]:
    as_of = ensure_utc(as_of)
    rows: list[dict[str, Any]] = []
    by_disp_time: dict[str, Counter] = defaultdict(Counter)
    by_comp_current: dict[str, Counter] = defaultdict(Counter)
    by_family_current: dict[str, Counter] = defaultdict(Counter)
    by_region_current: dict[str, Counter] = defaultdict(Counter)
    unknown_teams_current: Counter = Counter()
    unknown_teams_all: Counter = Counter()
    unregistered_comp_current: Counter = Counter()
    for tk, w in works.items():
        disp, reason = cov.dispositions.get(tk, (None, ""))
        if disp is None:
            continue
        m, spec = w.market, w.spec
        tb = _time_bucket(m.close_time, as_of)
        has_quote = (m.yes_ask is not None and 0 < float(m.yes_ask) < 1) or (
            m.no_ask is not None and 0 < float(m.no_ask) < 1
        )
        tradable_now = m.status.lower() == "active" and has_quote and tb != "past"
        code = spec.competition_code
        region = _region(code)
        by_disp_time[disp.value][tb] += 1
        if disp is not Disposition.PRICED and tradable_now:
            by_comp_current[code or "?"][disp.value] += 1
            by_family_current[spec.family.value][disp.value] += 1
            by_region_current[region][disp.value] += 1
            if (code and code not in COMPETITION_CODES) or (
                code and COMPETITION_CODES.get(code) is None
            ):
                unregistered_comp_current[code] += 1
        mm = _UNKNOWN_TEAM.search(reason or "")
        if mm:
            unknown_teams_all[(code or "?", mm.group(1))] += 1
            if tradable_now:
                unknown_teams_current[(code or "?", mm.group(1))] += 1
        if (
            disp is not Disposition.PRICED
            and tradable_now
            and spec.scope in (Scope.MATCH, Scope.PLAYER)
        ):
            rows.append(
                {
                    "ticker": tk,
                    "disposition": disp.value,
                    "reason": (reason or "")[:120],
                    "competition_code": code,
                    "competition_id": spec.competition_id,
                    "family": spec.family.value,
                    "event_date": spec.event_date,
                    "close_time": iso_utc(m.close_time) if m.close_time else None,
                    "time_bucket": tb,
                    "region": region,
                    "yes_ask": str(m.yes_ask),
                    "no_ask": str(m.no_ask),
                }
            )
    total = len(works)
    current_match_scope_lost = len(rows)
    return {
        "schema": "coverage_diagnostics_v1",
        "as_of": iso_utc(as_of),
        "discovery_run_id": discovery_run_id,
        "contracts_total": total,
        "by_disposition_x_time": {d: dict(c) for d, c in sorted(by_disp_time.items())},
        "current_tradable_not_priced_by_competition": {
            c: dict(v)
            for c, v in sorted(by_comp_current.items(), key=lambda kv: -sum(kv[1].values()))
        },
        "current_tradable_not_priced_by_family": {
            f: dict(v)
            for f, v in sorted(by_family_current.items(), key=lambda kv: -sum(kv[1].values()))
        },
        "current_tradable_not_priced_by_region": {r: dict(v) for r, v in by_region_current.items()},
        "current_tradable_match_scope_lost": current_match_scope_lost,
        "unknown_teams_current": [
            {"competition_code": c, "name": n, "contracts": k}
            for (c, n), k in unknown_teams_current.most_common(150)
        ],
        "unknown_teams_all": [
            {"competition_code": c, "name": n, "contracts": k}
            for (c, n), k in unknown_teams_all.most_common(60)
        ],
        "unregistered_competitions_current": dict(unregistered_comp_current.most_common()),
        "current_tradable_match_scope_lost_rows": rows[:2000],
    }
