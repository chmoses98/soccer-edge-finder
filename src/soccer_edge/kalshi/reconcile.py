"""Phase 23 — proof that a fast (intraday) capture is complete relative to the last full discovery.

Fast capture (`soccer capture --fast`) enumerates markets only for series that carried markets in
the last committed full discovery, plus any series new since then. That relaxation is only safe if
(a) no skipped series actually had markets in the full run and (b) every full-run market that the
fast run did not see is explained by a market lifecycle event (it closed / expired) or by a status
the fast run did not request. `reconcile_fast_vs_full` checks exactly that and reports COUNTS.

Accepted input shapes (both sides are the JSON documents already written by the CLI):
    catalog  — `DiscoveryRun.to_json()` (latest_catalog.json from `discover` or `capture`):
               has `series` (with `swept`) and `markets` (raw dicts)         -> market evidence
    index    — data/catalog/latest_index.json: `series`, `series_with_markets`, `market_count`,
               no market tickers                                             -> series evidence
    status   — a capture's STATUS.json: counters only                        -> insufficient
The report says which evidence level it reached. Anything weaker than series-level evidence fails
closed (`complete_relative_to_full=False`); a proof cannot be built from totals alone.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from soccer_edge.core.time import iso_utc, parse_iso_utc, utc_now

SCHEMA = "discovery_reconcile_v1"
FAST_SKIP_MARKER = "fast capture"
CLOSED_STATUSES = frozenset(
    {"closed", "settled", "determined", "finalized", "expired", "canceled", "cancelled"}
)
# Kalshi list filter value -> market `status` values it returns
STATUS_FILTER_TO_MARKET_STATUS: dict[str, frozenset[str]] = {
    "open": frozenset({"open", "active"}),
    "unopened": frozenset({"unopened", "initialized"}),
    "closed": frozenset({"closed"}),
    "settled": frozenset({"settled", "determined", "finalized"}),
}
_LIST_CAP = 50


def series_of(market: dict[str, Any]) -> str:
    """Same rule the committed index uses for `series_with_markets`."""
    return market.get("series_ticker") or str(market.get("ticker", "")).split("-")[0]


@dataclass
class Side:
    kind: str  # catalog | index | status
    run_id: str | None
    timestamp: datetime | None
    statuses_requested: tuple[str, ...]
    complete: bool
    series_known: set[str] = field(default_factory=set)
    series_swept: set[str] = field(default_factory=set)
    series_skipped_fast: set[str] = field(default_factory=set)
    series_unswept_other: set[str] = field(default_factory=set)
    series_with_markets: set[str] = field(default_factory=set)
    markets: dict[str, dict[str, Any]] | None = None  # ticker -> raw market (None if unavailable)
    market_count: int = 0

    def describe(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "run_id": self.run_id,
            "timestamp": iso_utc(self.timestamp) if self.timestamp else None,
            "statuses_requested": list(self.statuses_requested),
            "complete": self.complete,
            "series_known": len(self.series_known),
            "series_swept": len(self.series_swept),
            "series_skipped_fast_mode": len(self.series_skipped_fast),
            "series_unswept_other": len(self.series_unswept_other),
            "series_with_markets": len(self.series_with_markets),
            "market_count": self.market_count,
            "markets_available": self.markets is not None,
        }


def _ts(doc: dict[str, Any], *keys: str) -> datetime | None:
    for k in keys:
        v = doc.get(k)
        if v:
            try:
                return parse_iso_utc(str(v))
            except ValueError:
                continue
    return None


def _statuses(doc: dict[str, Any]) -> tuple[str, ...]:
    st = doc.get("statuses")
    if isinstance(st, list) and st:
        return tuple(str(s) for s in st)
    return ("open", "unopened")  # DEFAULT_STATUSES; catalogs always record theirs explicitly


def normalise(doc: dict[str, Any]) -> Side:
    """Classify the document shape and extract the sets the proof needs."""
    counters = doc.get("counters") or {}
    if "markets" in doc and isinstance(doc.get("markets"), list):
        kind = "catalog"
    elif "series_with_markets" in doc:
        kind = "index"
    else:
        kind = "status"
    side = Side(
        kind=kind,
        run_id=doc.get("run_id") or counters.get("run_id") or doc.get("batch_id"),
        timestamp=_ts(doc, "finished_at", "captured_at", "started_at"),
        statuses_requested=_statuses(doc),
        complete=bool(
            doc.get("complete", doc.get("discovery_complete", counters.get("complete", True)))
        ),
    )
    for s in doc.get("series") or []:
        tk = s.get("ticker")
        if not tk:
            continue
        side.series_known.add(tk)
        reason = str(s.get("ownership_reason") or "")
        swept = s.get("swept")
        if swept is None:
            swept = "not swept" not in reason
        if swept:
            side.series_swept.add(tk)
        elif FAST_SKIP_MARKER in reason:
            side.series_skipped_fast.add(tk)
        else:
            side.series_unswept_other.add(tk)
    if kind == "catalog":
        side.markets = {}
        for m in doc["markets"]:
            tk = m.get("ticker")
            if tk:
                side.markets[tk] = m
        side.market_count = len(side.markets)
        side.series_with_markets = {series_of(m) for m in side.markets.values()}
    elif kind == "index":
        side.series_with_markets = set(doc.get("series_with_markets") or [])
        side.market_count = int(
            doc.get("market_count") or counters.get("contracts_discovered") or 0
        )
    else:
        side.market_count = int(
            doc.get("contracts_discovered") or counters.get("contracts_discovered") or 0
        )
    return side


def _closed_between_runs(m: dict[str, Any], cutoff: datetime | None) -> bool:
    if str(m.get("status") or "").lower() in CLOSED_STATUSES:
        return True
    if cutoff is None:
        return False
    for k in ("close_time", "expected_expiration_time", "expiration_time"):
        v = m.get(k)
        if v:
            try:
                if parse_iso_utc(str(v)) <= cutoff:
                    return True
            except ValueError:
                continue
    return False


def reconcile_fast_vs_full(
    fast_run_counters_or_index: dict[str, Any], full_index: dict[str, Any]
) -> dict[str, Any]:
    """Counts-only reconciliation of one fast-capture run against the full discovery it relied on."""
    fast = normalise(fast_run_counters_or_index)
    full = normalise(full_index)
    violations: list[dict[str, Any]] = []

    # ---- series level -------------------------------------------------------------------
    skipped_with_markets = sorted(fast.series_skipped_fast & full.series_with_markets)
    new_in_fast = sorted(fast.series_swept - full.series_known)
    vanished = sorted((full.series_swept | full.series_with_markets) - fast.series_known)
    swept_by_full_not_fast = sorted(
        (full.series_with_markets & fast.series_known)
        - fast.series_swept
        - fast.series_skipped_fast
    )
    if skipped_with_markets:
        violations.append(
            {
                "kind": "fast_mode_missed",
                "series": len(skipped_with_markets),
                "series_tickers": skipped_with_markets[:_LIST_CAP],
                "detail": "fast mode skipped series that carried markets in the full discovery",
            }
        )
    if swept_by_full_not_fast:
        violations.append(
            {
                "kind": "series_not_swept_by_fast",
                "series": len(swept_by_full_not_fast),
                "series_tickers": swept_by_full_not_fast[:_LIST_CAP],
                "detail": "series had markets in full and is known to fast but fast neither swept nor fast-skipped it",
            }
        )

    # ---- market level -------------------------------------------------------------------
    evidence = (
        "market"
        if (fast.markets is not None and full.markets is not None)
        else ("series" if fast.kind != "status" and full.kind != "status" else "insufficient")
    )
    fast_allowed_status: set[str] = set()
    for s in fast.statuses_requested:
        fast_allowed_status |= STATUS_FILTER_TO_MARKET_STATUS.get(s, frozenset({s}))
    breakdown = Counter()
    unexplained_by_series: Counter = Counter()
    in_both = in_fast_not_full = 0
    if evidence == "market":
        assert fast.markets is not None and full.markets is not None
        for tk, m in full.markets.items():
            if tk in fast.markets:
                in_both += 1
                continue
            s_tk = series_of(m)
            if s_tk in fast.series_skipped_fast:
                breakdown["in_skipped_series"] += 1
            elif _closed_between_runs(m, fast.timestamp):
                breakdown["closed_between_runs"] += 1
            elif (
                fast_allowed_status
                and str(m.get("status") or "").lower() not in fast_allowed_status
            ):
                breakdown["status_not_requested"] += 1
            else:
                breakdown["unexplained"] += 1
                unexplained_by_series[s_tk] += 1
        in_fast_not_full = sum(1 for tk in fast.markets if tk not in full.markets)
        if breakdown["in_skipped_series"]:
            # already a fast_mode_missed series violation; attach the market count to it
            for v in violations:
                if v["kind"] == "fast_mode_missed":
                    v["markets"] = breakdown["in_skipped_series"]
            if not any(v["kind"] == "fast_mode_missed" for v in violations):
                violations.append(
                    {
                        "kind": "fast_mode_missed",
                        "series": 0,
                        "markets": breakdown["in_skipped_series"],
                        "detail": "markets in full belong to series the fast run skipped",
                    }
                )
        if breakdown["unexplained"]:
            violations.append(
                {
                    "kind": "unexplained_missing_markets",
                    "markets": breakdown["unexplained"],
                    "series": len(unexplained_by_series),
                    "detail": "open markets in full absent from fast without a lifecycle or status explanation",
                }
            )
    elif evidence == "insufficient":
        violations.append(
            {
                "kind": "insufficient_evidence",
                "detail": "a STATUS.json carries counters only; pass the run's latest_catalog.json (or the committed index for the full side)",
            }
        )
    if not fast.complete:
        violations.append(
            {
                "kind": "fast_discovery_incomplete",
                "detail": "fast run flagged its own discovery incomplete",
            }
        )
    if not full.complete:
        violations.append(
            {
                "kind": "full_discovery_incomplete",
                "detail": "full discovery flagged incomplete; not a valid baseline",
            }
        )

    complete = not violations
    return {
        "schema": SCHEMA,
        "generated_at": iso_utc(utc_now()),
        "evidence_level": evidence,
        "fast": fast.describe(),
        "full": full.describe(),
        "series": {
            "swept_fast": len(fast.series_swept),
            "swept_full": len(full.series_swept),
            "swept_both": len(fast.series_swept & full.series_swept),
            "with_markets_full": len(full.series_with_markets),
            "with_markets_fast": len(fast.series_with_markets),
            "skipped_by_fast": len(fast.series_skipped_fast),
            "skipped_by_fast_with_markets_in_full": len(skipped_with_markets),
            "skipped_by_fast_with_markets_in_full_tickers": skipped_with_markets[:_LIST_CAP],
            "with_markets_full_not_swept_by_fast": len(swept_by_full_not_fast),
            "new_in_fast": len(new_in_fast),
            "in_full_not_known_to_fast": len(vanished),
        },
        "markets": {
            "full_total": full.market_count,
            "fast_total": fast.market_count,
            "in_both": in_both if evidence == "market" else None,
            "in_full_not_fast": (sum(breakdown.values()) if evidence == "market" else None),
            "in_fast_not_full": in_fast_not_full if evidence == "market" else None,
            "full_not_fast_breakdown": {
                "in_skipped_series": breakdown.get("in_skipped_series", 0),
                "closed_between_runs": breakdown.get("closed_between_runs", 0),
                "status_not_requested": breakdown.get("status_not_requested", 0),
                "unexplained": breakdown.get("unexplained", 0),
            },
            "unexplained_by_series": dict(
                sorted(unexplained_by_series.items(), key=lambda kv: (-kv[1], kv[0]))[:_LIST_CAP]
            ),
        },
        "violations": violations,
        "complete_relative_to_full": complete,
    }
