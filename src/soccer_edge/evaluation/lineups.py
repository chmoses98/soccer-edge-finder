"""Lineup capture reliability report (remediation phase 18; audit §I).

For every fixture with lineup capture attempts in the archive (`lineups/<day>/<league>.jsonl`):
scheduled kickoff, number of capture attempts, when a starting XI was first observed (`published`),
lead time in seconds (kickoff - first XI observation), whether that first observation happened before
kickoff, competition (ESPN league slug), source. Publishes the lead-time distribution and the share of
fixtures with a pre-kickoff XI at >= 20 min (the audit's target: >= 90 % of priced fixtures).

A lineup captured after kickoff is never usable for pregame pricing; it is counted as `post_hoc` here
and the pipeline's lineup context ignores it (audit fix S4).
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from soccer_edge.core.time import parse_iso_utc


def _dt(v: str | None) -> datetime | None:
    if not v:
        return None
    try:
        return parse_iso_utc(v)
    except ValueError:
        return datetime.fromisoformat(v)


def lineup_rows(archive_root: Path, *, include_backfill: bool = False) -> list[dict[str, Any]]:
    """Prospective capture attempts only by default: `lineups/history/` holds post-hoc backfilled XIs
    (`backfill: true`, fetched long after kickoff for the oracle study); counting those as capture
    attempts would report a lead time the capture pipeline never achieved."""
    out: list[dict[str, Any]] = []
    for p in sorted((archive_root / "lineups").glob("*/*.jsonl")):
        if p.parent.name == "history" and not include_backfill:
            continue
        with p.open(encoding="utf-8") as fh:
            for ln in fh:
                if ln.strip():
                    row = json.loads(ln)
                    if row.get("backfill") and not include_backfill:
                        continue
                    out.append(row)
    return out


def lead_time_report(rows: list[dict[str, Any]], *, as_of: datetime) -> dict[str, Any]:
    by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r.get("schema") != "espn_lineup_snapshot_v1":
            continue
        by_event[str(r.get("espn_event_id"))].append(r)
    fixtures = []
    for eid, rs in by_event.items():
        rs.sort(key=lambda r: r.get("captured_at") or "")
        ko = _dt(rs[0].get("kickoff_utc"))
        attempts = len(rs)
        published = [r for r in rs if r.get("published")]
        first_pub = _dt(published[0]["captured_at"]) if published else None
        lead = (ko - first_pub).total_seconds() if (ko and first_pub) else None
        fixtures.append(
            {
                "espn_event_id": eid,
                "competition": rs[0].get("league"),
                "source": rs[0].get("provider"),
                "scheduled_kickoff_utc": rs[0].get("kickoff_utc"),
                "capture_attempts": attempts,
                "xi_first_observed_at": published[0]["captured_at"] if published else None,
                "lead_time_seconds": lead,
                "observed_before_kickoff": (lead is not None and lead > 0),
                "final_state": rs[-1].get("lineup_state"),
                "kickoff_passed": bool(ko and ko < as_of),
            }
        )
    passed = [f for f in fixtures if f["kickoff_passed"]]
    leads = np.array([f["lead_time_seconds"] for f in passed if f["lead_time_seconds"] is not None])
    pre = leads[leads > 0] if leads.size else leads

    def q(x, p):
        return float(np.percentile(x, p)) if x.size else None

    by_comp: dict[str, dict[str, Any]] = {}
    for comp in sorted({f["competition"] for f in passed if f["competition"]}):
        fs = [f for f in passed if f["competition"] == comp]
        ls = np.array([f["lead_time_seconds"] for f in fs if f["lead_time_seconds"] is not None])
        by_comp[comp] = {
            "fixtures": len(fs),
            "with_pre_kickoff_xi": int((ls > 0).sum()) if ls.size else 0,
            "with_xi_ge_20min": int((ls >= 1200).sum()) if ls.size else 0,
            "median_lead_minutes": (q(ls[ls > 0], 50) / 60) if ls.size and (ls > 0).any() else None,
        }
    return {
        "schema": "lineup_lead_time_v1",
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "fixtures_tracked": len(fixtures),
        "fixtures_kickoff_passed": len(passed),
        "with_any_xi": int(sum(1 for f in passed if f["xi_first_observed_at"])),
        "with_pre_kickoff_xi": int((leads > 0).sum()) if leads.size else 0,
        "with_xi_ge_20min_before_kickoff": int((leads >= 1200).sum()) if leads.size else 0,
        "share_pre_kickoff_xi": (float((leads > 0).sum() / len(passed)) if passed else None),
        "share_xi_ge_20min": (float((leads >= 1200).sum() / len(passed)) if passed else None),
        "lead_time_minutes": {
            "n": int(pre.size),
            "min": (float(pre.min()) / 60) if pre.size else None,
            "p10": (q(pre, 10) / 60) if pre.size else None,
            "median": (q(pre, 50) / 60) if pre.size else None,
            "p90": (q(pre, 90) / 60) if pre.size else None,
            "max": (float(pre.max()) / 60) if pre.size else None,
        },
        "post_kickoff_first_xi": int((leads <= 0).sum()) if leads.size else 0,
        "capture_attempts_per_fixture_median": float(
            np.median([f["capture_attempts"] for f in fixtures])
        )
        if fixtures
        else None,
        "by_competition": by_comp,
        "fixtures": fixtures[:500],
        "target": "audit §I1: >= 90% of priced fixtures with a confirmed XI captured >= 20 min before kickoff",
    }
