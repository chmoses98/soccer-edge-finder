"""DISCOVER EVERYTHING -> establish soccer ownership -> classify -> account.

Discovery never depends on classification. The whole series list is swept; every series whose
ownership is SOCCER or AMBIGUOUS gets a complete market sweep in each requested status. A run is
`complete` only if every sweep was complete. An incomplete run is still saved (for forensics) but
is flagged and MUST NOT be treated as a catalog: "network failure never becomes zero markets".
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from soccer_edge.core.errors import DiscoveryIncompleteError
from soccer_edge.core.serialization import content_hash
from soccer_edge.core.time import iso_utc, utc_now
from soccer_edge.kalshi.client import KalshiPublicClient
from soccer_edge.kalshi.ownership import classify_ownership
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

    def counters(self) -> dict[str, Any]:
        own = Counter(r.ownership.value for r in self.series_records.values())
        fam = Counter(s.family.value for s in self.specs.values())
        comps = Counter(s.competition_code or "?" for s in self.specs.values())
        return {
            "run_id": self.run_id,
            "complete": self.complete,
            "series_total": self.series_total,
            "series_by_ownership": dict(own),
            "series_swept": len(self.owned_series()),
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
) -> DiscoveryRun:
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
        if own is Ownership.NOT_SOCCER and not include_not_soccer_series:
            run.series_records[s.ticker] = SeriesRecord(s, own, why)
            continue
        run.series_records[s.ticker] = SeriesRecord(s, own, why)

    for rec in run.owned_series():
        st = rec.series.ticker
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
        if fetch_events:
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
