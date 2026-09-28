"""Prospective market capture: what was executable, when, under which fee regime."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from soccer_edge.core.serialization import content_hash
from soccer_edge.core.time import iso_utc
from soccer_edge.kalshi.schemas import RawMarket, RawSeries


class Horizon(str, Enum):
    T_24H = "T-24h"
    T_12H = "T-12h"
    T_6H = "T-6h"
    T_2H = "T-2h"
    T_90M = "T-90m"
    T_60M = "T-60m"
    T_30M = "T-30m"
    LINEUP = "lineup"
    T_15M = "T-15m"
    T_10M = "T-10m"
    CLOSE = "close"
    ADHOC = "adhoc"


HORIZON_MINUTES: dict[Horizon, int] = {
    Horizon.T_24H: 1440,
    Horizon.T_12H: 720,
    Horizon.T_6H: 360,
    Horizon.T_2H: 120,
    Horizon.T_90M: 90,
    Horizon.T_60M: 60,
    Horizon.T_30M: 30,
    Horizon.T_15M: 15,
    Horizon.T_10M: 10,
    Horizon.CLOSE: 0,
}


def label_horizon(minutes_to_kickoff: float) -> Horizon:
    """Nearest *not-yet-passed* decision horizon: the LARGEST horizon whose minutes <= the time left.
    Examples: 2,964 minutes out -> 'T-24h'; 40 minutes out -> 'T-30m'; inside 10 minutes -> 'close'.

    PRODUCTION NOTE (2026-09-28): the first version iterated all horizons without stopping and
    labelled everything 'T-10m'. Archived snapshots from 2026-09-27 carry that wrong label; their
    `minutes_to_kickoff` is correct, so consumers must recompute with this function."""
    if minutes_to_kickoff <= 0:
        return Horizon.CLOSE
    for m, h in sorted(((m, h) for h, m in HORIZON_MINUTES.items() if m > 0), reverse=True):
        if minutes_to_kickoff >= m:
            return h
    return Horizon.CLOSE


class MarketSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ticker: str
    event_ticker: str
    series_ticker: str
    captured_at: datetime
    status: str
    yes_bid: Decimal | None
    yes_ask: Decimal | None
    no_bid: Decimal | None
    no_ask: Decimal | None
    yes_bid_size: Decimal | None = None
    yes_ask_size: Decimal | None = None
    no_bid_size: Decimal | None = None
    no_ask_size: Decimal | None = None
    last_price: Decimal | None = None
    volume: Decimal | None = None
    open_interest: Decimal | None = None
    close_time: datetime | None = None
    expected_expiration_time: datetime | None = None
    fee_type: str | None = None
    fee_multiplier: Decimal | None = None
    rules_primary_hash: str | None = Field(
        default=None, description="hash of rules text; full text lives in the catalog"
    )
    price_unit: str = Field(
        default="dollars", description="always 'dollars' (0..1); producers must declare it"
    )
    horizon: Horizon = Horizon.ADHOC
    minutes_to_kickoff: float | None = None
    orderbook: dict[str, Any] | None = None

    @classmethod
    def from_market(
        cls,
        m: RawMarket,
        series: RawSeries | None,
        captured_at: datetime,
        *,
        minutes_to_kickoff: float | None = None,
        orderbook: dict[str, Any] | None = None,
    ) -> MarketSnapshot:
        return cls(
            ticker=m.ticker,
            event_ticker=m.event_ticker,
            series_ticker=m.series_ticker or (series.ticker if series else m.ticker.split("-")[0]),
            captured_at=captured_at,
            status=m.status,
            yes_bid=m.yes_bid,
            yes_ask=m.yes_ask,
            no_bid=m.no_bid,
            no_ask=m.no_ask,
            yes_bid_size=m.yes_bid_size,
            yes_ask_size=m.yes_ask_size,
            no_bid_size=m.no_bid_size,
            no_ask_size=m.no_ask_size,
            last_price=m.last_price,
            volume=m.volume,
            open_interest=m.open_interest,
            close_time=m.close_time,
            expected_expiration_time=m.expected_expiration_time,
            fee_type=series.fee_type if series else None,
            fee_multiplier=series.fee_multiplier if series else None,
            rules_primary_hash=content_hash(m.rules_primary) if m.rules_primary else None,
            horizon=label_horizon(minutes_to_kickoff)
            if minutes_to_kickoff is not None
            else Horizon.ADHOC,
            minutes_to_kickoff=minutes_to_kickoff,
            orderbook=orderbook,
        )

    def quote_fingerprint(self) -> str:
        """Change-suppression key: identical fingerprints need not be stored twice."""
        return content_hash(
            {
                "t": self.ticker,
                "s": self.status,
                "yb": self.yes_bid,
                "ya": self.yes_ask,
                "nb": self.no_bid,
                "na": self.no_ask,
                "ybs": self.yes_bid_size,
                "yas": self.yes_ask_size,
                "nbs": self.no_bid_size,
                "nas": self.no_ask_size,
            }
        )


class SnapshotBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    batch_id: str
    discovery_run_id: str
    discovery_complete: bool
    captured_at: datetime
    snapshots: tuple[MarketSnapshot, ...]
    fee_schedule_version: str

    def to_records(self) -> list[dict[str, Any]]:
        return [
            {
                **s.model_dump(mode="json"),
                "batch_id": self.batch_id,
                "discovery_run_id": self.discovery_run_id,
                "captured_at": iso_utc(s.captured_at),
            }
            for s in self.snapshots
        ]
