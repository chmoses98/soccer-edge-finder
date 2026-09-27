"""DISCOVER EVERYTHING -> establish soccer ownership -> classify -> account.

Discovery never depends on classification. The whole series list is swept; every series whose
ownership is SOCCER or AMBIGUOUS gets a complete market sweep in each requested status. A run is
`complete` only if every sweep was complete. An incomplete run is still saved (for forensics) but
is flagged and MUST NOT be treated as a catalog: "network failure never becomes zero markets".
"""

from __future__ import annotations

import sys
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from soccer_edge.core.errors import DiscoveryIncompleteError
from soccer_edge.core.serialization import content_hash
from soccer_edge.core.time import iso_utc, utc_now
from soccer_edge.kalshi.client import KalshiPublicClient
from soccer_edge.kalshi.ownership import classify_ownership, has_soccer_wording
from soccer_edge.kalshi.schemas import Ownership, RawEvent, RawMarket, RawSeries
from soccer_edge.kalshi.taxonomy import ContractSpec, MarketFamily, classify

DEFAULT_STATUSES = ("open", "unopened")


@dataclass
class SeriesRecord:
    series: RawSeries
    ownership: Ownership
    ownership_reason: str
    market_sweeps_complete: bool = True
    event_sweep_complete: bool = True
    failures: list[str] = field(default_factory=list)
    swept: bool = True  # False = ambiguous series recorded but its markets were not enumerated


@dataclass
class DiscoveryRun:
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    base_url: str = ""
    statuses: tuple[str, ...] = DEFAULT_STATUSES
    series_sweep_complete: bool = False
    series_total: int = 0
    series_records: dict[str, SeriesRecord] = field(default_factory=dict)
    events: dict[str, RawEvent] = field(default_factory=dict)
    markets: dict[str, RawMarket] = field(default_factory=dict)
    duplicates: list[str] = field(default_factory=list)
    specs: dict[str, ContractSpec] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    request_count: int = 0
    retry_count: int = 0
    milestones_note: str = ""
    fast_skipped: int = 0  # owned series not swept in fast-capture mode (recorded, counted)

    @property
    def complete(self) -> bool:
        return (
            self.series_sweep_complete
            and not self.failures
            and all(
                r.market_sweeps_complete and r.event_sweep_complete
                for r in self.series_records.values()
            )
        )

    def owned_series(self) -> list[SeriesRecord]:
        return [
            r
            for r in self.series_records.values()
            if r.ownership in (Ownership.SOCCER, Ownership.AMBIGUOUS)
        ]

    def swept_series(self) -> list[SeriesRecord]:
        return [r for r in self.owned_series() if r.swept]

    def ambiguous_unswept(self) -> list[SeriesRecord]:
        return [r for r in self.owned_series() if not r.swept]

    def counters(self) -> dict[str, Any]:
        own = Counter(r.ownership.value for r in self.series_records.values())
        fam = Counter(s.family.value for s in self.specs.values())
        comps = Counter(s.competition_code or "?" for s in self.specs.values())
        return {
            "run_id": self.run_id,
            "complete": self.complete,
            "series_total": self.series_total,
            "series_by_ownership": dict(own),
            "series_swept": len(self.swept_series()),
            "series_ambiguous_unswept": len(
                [r for r in self.ambiguous_unswept() if "fast capture" not in r.ownership_reason]
            ),
            "series_skipped_fast_mode": self.fast_skipped,
            "series_ambiguous_unswept_tickers": sorted(
                r.series.ticker for r in self.ambiguous_unswept()
            )[:200],
            "events_discovered": len(self.events),
            "contracts_discovered": len(self.markets),
            "contracts_duplicate_seen": len(self.duplicates),
            "contracts_by_family": dict(sorted(fam.items())),
            "contracts_by_competition_code": dict(sorted(comps.items())),
            "contracts_unknown_family": fam.get(MarketFamily.UNKNOWN.value, 0),
            "failures": list(self.failures)
            + [f"{t}: {msg}" for t, r in self.series_records.items() for msg in r.failures],
            "request_count": self.request_count,
            "retry_count": self.retry_count,
            "milestones_note": self.milestones_note,
        }

    def catalog_hash(self) -> str:
        return content_hash(sorted(self.markets))

    def to_json(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "run_id": self.run_id,
            "started_at": iso_utc(self.started_at),
            "finished_at": iso_utc(self.finished_at) if self.finished_at else None,
            "base_url": self.base_url,
            "statuses": list(self.statuses),
            "complete": self.complete,
            "counters": self.counters(),
            "series": [
                {
                    "ticker": r.series.ticker,
                    "title": r.series.title,
                    "category": r.series.category,
                    "tags": list(r.series.tags),
                    "fee_type": r.series.fee_type,
                    "fee_multiplier": str(r.series.fee_multiplier)
                    if r.series.fee_multiplier is not None
                    else None,
                    "ownership": r.ownership.value,
                    "ownership_reason": r.ownership_reason,
                    "market_sweeps_complete": r.market_sweeps_complete,
                    "event_sweep_complete": r.event_sweep_complete,
                    "swept": r.swept,
                    "failures": r.failures,
                }
                for r in sorted(self.owned_series(), key=lambda r: r.series.ticker)
            ],
            "events": [e.raw for _, e in sorted(self.events.items())],
            "markets": [m.raw for _, m in sorted(self.markets.items())],
            "specs": [
                {
                    "ticker": s.ticker,
                    "family": s.family.value,
                    "scope": s.scope.value,
                    "period": s.period.value,
                    "competition_code": s.competition_code,
                    "competition_id": s.competition_id,
                    "event_date": s.event_date,
                    "team_codes": s.team_codes,
                    "side_team_code": s.side_team_code,
                    "line": str(s.line) if s.line is not None else None,
                    "player_code": s.player_code,
                    "player_name": s.player_name,
                    "k": s.k,
                    "inferred": s.inferred,
                    "rationale": s.rationale,
                }
                for _, s in sorted(self.specs.items())
            ],
        }


def discover(
    client: KalshiPublicClient,
    *,
    statuses: tuple[str, ...] = DEFAULT_STATUSES,
    include_not_soccer_series: bool = False,
    fetch_events: bool = True,
    probe_milestones: bool = True,
    sweep_series: set[str] | None = None,
    known_series: set[str] | None = None,
) -> DiscoveryRun:
    """Exhaustive by default. FAST-CAPTURE mode when both sets are given: an owned series is swept
    iff it is in `sweep_series` (had markets at the last full discovery) or NOT in `known_series`
    (new since then). Skipped series are recorded with swept=False and counted
    (`series_skipped_fast_mode`), never dropped."""
    run = DiscoveryRun(
        run_id=f"disc-{utc_now():%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}",
        started_at=utc_now(),
        base_url=client.base_url,
        statuses=statuses,
    )

    sweep = client.series(include_product_metadata=True)
    run.series_sweep_complete = sweep.complete
    if not sweep.complete:
        run.failures.append(f"series sweep incomplete: {sweep.failures}")
    run.series_total = len(sweep.items)
    for raw in sweep.items:
        try:
            s = RawSeries.from_api(raw)
        except Exception as exc:
            run.failures.append(f"series parse error: {exc}: {str(raw)[:120]}")
            continue
        own, why = classify_ownership(s)
        rec = SeriesRecord(s, own, why)
        if own is Ownership.AMBIGUOUS and not has_soccer_wording(s):
            # Fail closed at the SERIES level: retained, counted and listed in every report,
            # but its (typically American-football) markets are not enumerated. Verified cause:
            # hundreds of NFL/CFB series carry only the tag 'Football'.
            rec.swept = False
            rec.ownership_reason = why + "; not swept (no soccer wording)"
        run.series_records[s.ticker] = rec

    if sweep_series is not None and known_series is not None:
        for rec in run.owned_series():
            tk_ = rec.series.ticker
            if rec.swept and tk_ not in sweep_series and tk_ in known_series:
                rec.swept = False
                rec.ownership_reason += (
                    "; not swept (fast capture: no markets in last full discovery)"
                )
                run.fast_skipped += 1
    owned = run.swept_series()
    t_start = time.monotonic()
    print(
        f"[discover] series_total={run.series_total} owned={len(owned)} statuses={statuses}",
        file=sys.stderr,
        flush=True,
    )
    for i, rec in enumerate(owned):
        st = rec.series.ticker
        if i % 10 == 0:
            print(
                f"[discover] {i}/{len(owned)} series swept, {len(run.markets)} markets, {client.request_count} requests, {client.retry_count} retries, {time.monotonic() - t_start:.0f}s",
                file=sys.stderr,
                flush=True,
            )
        for status in statuses:
            ms = client.markets(series_ticker=st, status=status, limit=1000)
            if not ms.complete:
                rec.market_sweeps_complete = False
                rec.failures.append(f"markets status={status} incomplete: {ms.failures}")
            for raw in ms.items:
                try:
                    m = RawMarket.from_api(raw)
                except Exception as exc:
                    rec.failures.append(f"market parse error: {exc}: {str(raw)[:120]}")
                    rec.market_sweeps_complete = False
                    continue
                if m.ticker in run.markets:
                    run.duplicates.append(m.ticker)
                    continue
                if m.series_ticker is None:
                    m = m.model_copy(update={"series_ticker": st})
                run.markets[m.ticker] = m
        if fetch_events and any(mk.series_ticker == st for mk in run.markets.values()):
            # events are only needed for series that currently list markets (saves ~70k historical events)
            es = client.events(series_ticker=st, limit=200)
            if not es.complete:
                rec.event_sweep_complete = False
                rec.failures.append(f"events incomplete: {es.failures}")
            for raw in es.items:
                try:
                    e = RawEvent.from_api(raw)
                except Exception as exc:
                    rec.failures.append(f"event parse error: {exc}")
                    continue
                run.events[e.event_ticker] = e

    if probe_milestones:
        try:
            ml = client.milestones(milestone_type="soccer_tournament_multi_leg", limit=200)
            run.milestones_note = f"milestones type=soccer_tournament_multi_leg: {len(ml.items)} rows, complete={ml.complete}"
        except Exception as exc:
            run.milestones_note = f"milestones probe failed: {exc}"

    for tk, m in run.markets.items():
        run.specs[tk] = classify(m)

    run.request_count = client.request_count
    run.retry_count = client.retry_count
    run.finished_at = utc_now()
    return run


def require_complete(run: DiscoveryRun) -> DiscoveryRun:
    if not run.complete:
        raise DiscoveryIncompleteError(
            "discovery incomplete: " + "; ".join(run.counters()["failures"][:10])
        )
    return run
