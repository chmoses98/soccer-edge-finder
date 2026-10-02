"""The executable Kalshi state a reprice prices against: quotes + fee regimes from one capture sweep.

Built either in-process from the DiscoveryRun a capture just produced, or from that capture's
`latest_catalog.json` (the same `DiscoveryRun.to_json()` document). `observed_at` is the sweep's START: the
oldest quote in the sweep was read then, so ages are never understated.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from soccer_edge.core.time import ensure_utc, parse_iso_utc
from soccer_edge.kalshi.fees import FeeRegime
from soccer_edge.kalshi.schemas import RawMarket


@dataclass
class MarketView:
    run_id: str
    observed_at: datetime
    finished_at: datetime | None
    complete: bool
    markets: dict[str, RawMarket]
    fee_by_series: dict[str, tuple[str | None, Decimal | None]]
    tickers_by_event: dict[str, set[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.tickers_by_event:
            idx: dict[str, set[str]] = defaultdict(set)
            for t, m in self.markets.items():
                idx[m.event_ticker].add(t)
            self.tickers_by_event = dict(idx)

    def regime(self, m: RawMarket) -> FeeRegime | None:
        """Verified fee regime of the market's series, or None (never priced without one)."""
        series = m.series_ticker or m.ticker.split("-")[0]
        fee_type, mult = self.fee_by_series.get(series, (None, None))
        if fee_type is None:
            return None
        regime = FeeRegime(fee_type, mult or Decimal(1))
        try:
            regime.verify()
        except Exception:
            return None
        return regime

    @classmethod
    def from_discovery(cls, run: Any) -> MarketView:
        return cls(
            run_id=run.run_id,
            observed_at=ensure_utc(run.started_at),
            finished_at=ensure_utc(run.finished_at) if run.finished_at else None,
            complete=bool(run.complete),
            markets=dict(run.markets),
            fee_by_series={
                t: (r.series.fee_type, r.series.fee_multiplier)
                for t, r in run.series_records.items()
            },
        )

    @classmethod
    def from_catalog_json(cls, doc: dict[str, Any]) -> MarketView:
        markets = {}
        for raw in doc.get("markets", []):
            m = RawMarket.from_api(raw)
            markets[m.ticker] = m
        fees = {
            s["ticker"]: (
                s.get("fee_type"),
                Decimal(str(s["fee_multiplier"])) if s.get("fee_multiplier") is not None else None,
            )
            for s in doc.get("series", [])
        }
        fin = doc.get("finished_at")
        return cls(
            run_id=doc.get("run_id", "?"),
            observed_at=parse_iso_utc(doc["started_at"]),
            finished_at=parse_iso_utc(fin) if fin else None,
            complete=bool(doc.get("complete")),
            markets=markets,
            fee_by_series=fees,
        )
