"""Typed views over raw Kalshi payloads. Raw dicts are preserved verbatim alongside."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from soccer_edge.core.time import parse_iso_utc


class Ownership(str, Enum):
    SOCCER = "soccer"
    NOT_SOCCER = "not_soccer"
    AMBIGUOUS = "ambiguous"  # e.g. bare 'Football' tag; retained and dispositioned, never dropped


class RawSeries(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    ticker: str
    title: str = ""
    category: str = ""
    tags: tuple[str, ...] = ()
    frequency: str | None = None
    fee_type: str | None = None
    fee_multiplier: Decimal | None = None
    settlement_sources: tuple[dict[str, Any], ...] = ()

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> RawSeries:
        fm = d.get("fee_multiplier")
        return cls(
            ticker=d["ticker"],
            title=d.get("title") or "",
            category=d.get("category") or "",
            tags=tuple(d.get("tags") or ()),
            frequency=d.get("frequency"),
            fee_type=d.get("fee_type"),
            fee_multiplier=Decimal(str(fm)) if fm is not None else None,
            settlement_sources=tuple(d.get("settlement_sources") or ()),
        )


class RawEvent(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    event_ticker: str
    series_ticker: str
    title: str = ""
    sub_title: str = ""
    category: str = ""
    strike_date: datetime | None = None
    mutually_exclusive: bool | None = None
    competition: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> RawEvent:
        sd = d.get("strike_date")
        return cls(
            event_ticker=d["event_ticker"],
            series_ticker=d.get("series_ticker") or d["event_ticker"].split("-")[0],
            title=d.get("title") or "",
            sub_title=d.get("sub_title") or "",
            category=d.get("category") or "",
            strike_date=parse_iso_utc(sd) if sd else None,
            mutually_exclusive=d.get("mutually_exclusive"),
            competition=d.get("competition"),
            raw=d,
        )


def _dollars(d: dict[str, Any], key: str) -> Decimal | None:
    """Prefer *_dollars strings; fall back to legacy integer cents."""
    v = d.get(f"{key}_dollars")
    if v not in (None, ""):
        return Decimal(str(v))
    v = d.get(key)
    if v in (None, ""):
        return None
    return (Decimal(int(v)) / 100).quantize(Decimal("0.0001"))


def _fp(d: dict[str, Any], key: str) -> Decimal | None:
    v = d.get(f"{key}_fp")
    if v not in (None, ""):
        return Decimal(str(v))
    v = d.get(key)
    return Decimal(int(v)) if v not in (None, "") else None


class RawMarket(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    ticker: str
    event_ticker: str
    series_ticker: str | None = None
    title: str = ""
    subtitle: str = ""
    yes_sub_title: str = ""
    no_sub_title: str = ""
    status: str = ""
    result: str = ""
    market_type: str = ""
    strike_type: str | None = None
    floor_strike: Decimal | None = None
    cap_strike: Decimal | None = None
    open_time: datetime | None = None
    close_time: datetime | None = None
    expiration_time: datetime | None = None
    expected_expiration_time: datetime | None = None
    yes_bid: Decimal | None = None
    yes_ask: Decimal | None = None
    no_bid: Decimal | None = None
    no_ask: Decimal | None = None
    last_price: Decimal | None = None
    yes_bid_size: Decimal | None = None
    yes_ask_size: Decimal | None = None
    no_bid_size: Decimal | None = None
    no_ask_size: Decimal | None = None
    volume: Decimal | None = None
    open_interest: Decimal | None = None
    liquidity: Decimal | None = None
    rules_primary: str = ""
    rules_secondary: str = ""
    can_close_early: bool | None = None
    settlement_value: Decimal | None = None
    settlement_ts: datetime | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> RawMarket:
        def ts(k: str) -> datetime | None:
            v = d.get(k)
            return parse_iso_utc(v) if v else None

        def dec(k: str) -> Decimal | None:
            v = d.get(k)
            return Decimal(str(v)) if v not in (None, "") else None

        return cls(
            ticker=d["ticker"],
            event_ticker=d.get("event_ticker") or "",
            series_ticker=d.get("series_ticker"),
            title=d.get("title") or "",
            subtitle=d.get("subtitle") or "",
            yes_sub_title=d.get("yes_sub_title") or "",
            no_sub_title=d.get("no_sub_title") or "",
            status=d.get("status") or "",
            result=d.get("result") or "",
            market_type=d.get("market_type") or "",
            strike_type=d.get("strike_type"),
            floor_strike=dec("floor_strike"),
            cap_strike=dec("cap_strike"),
            open_time=ts("open_time"),
            close_time=ts("close_time"),
            expiration_time=ts("expiration_time"),
            expected_expiration_time=ts("expected_expiration_time"),
            yes_bid=_dollars(d, "yes_bid"),
            yes_ask=_dollars(d, "yes_ask"),
            no_bid=_dollars(d, "no_bid"),
            no_ask=_dollars(d, "no_ask"),
            last_price=_dollars(d, "last_price"),
            yes_bid_size=_fp(d, "yes_bid_size"),
            yes_ask_size=_fp(d, "yes_ask_size"),
            no_bid_size=_fp(d, "no_bid_size"),
            no_ask_size=_fp(d, "no_ask_size"),
            volume=_fp(d, "volume"),
            open_interest=_fp(d, "open_interest"),
            liquidity=_dollars(d, "liquidity"),
            rules_primary=d.get("rules_primary") or "",
            rules_secondary=d.get("rules_secondary") or "",
            can_close_early=d.get("can_close_early"),
            settlement_value=_dollars(d, "settlement_value"),
            settlement_ts=ts("settlement_ts"),
            raw=d,
        )
