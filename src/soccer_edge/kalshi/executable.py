"""Executable price extraction. Never the midpoint.

Buy YES -> pay yes_ask ; buy NO -> pay no_ask (Kalshi publishes no_ask = 1 - yes_bid; verified
identical on 15,444/15,444 live contracts by a sibling repo). Zero-size $0/$1 books are not quotes.
When an order book is available we walk resting bids on the opposite side to get a VWAP for size.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from soccer_edge.kalshi.schemas import RawMarket


@dataclass(frozen=True)
class ExecutableQuote:
    ticker: str
    side: str  # "yes" | "no"
    price: Decimal  # dollars per contract, (0,1)
    size: Decimal | None  # contracts available at top of book, if known
    source: str  # "top_of_book" | "book_walk" | "none"
    vwap_for_size: Decimal | None = None
    filled_size: Decimal | None = None

    @property
    def is_quote(self) -> bool:
        return self.source != "none" and Decimal(0) < self.price < Decimal(1)


def top_of_book(market: RawMarket, side: str) -> ExecutableQuote:
    if side == "yes":
        price, size = market.yes_ask, market.yes_ask_size
    elif side == "no":
        # Kalshi does not return no_ask_size; the NO ask is (1 - yes_bid), so its depth is the YES bid size
        price = market.no_ask
        size = market.no_ask_size if market.no_ask_size is not None else market.yes_bid_size
    else:
        raise ValueError(side)
    if price is None or not (Decimal(0) < price < Decimal(1)):
        return ExecutableQuote(market.ticker, side, price or Decimal(0), size, "none")
    if size is not None and size <= 0:
        return ExecutableQuote(market.ticker, side, price, size, "none")
    return ExecutableQuote(market.ticker, side, price, size, "top_of_book")


def walk_book(ticker: str, orderbook: dict[str, Any], side: str, size: int) -> ExecutableQuote:
    """Buying `side` consumes resting bids on the OTHER side: price paid = 1 - opposite_bid.
    Kalshi orderbook_fp lists [price_dollars, size_fp] ascending; best bid is last."""
    book = orderbook.get("orderbook_fp") or orderbook.get("orderbook") or {}
    key = "no" if side == "yes" else "yes"
    levels = book.get(f"{key}_dollars") or book.get(key) or []
    parsed: list[tuple[Decimal, Decimal]] = []
    for lvl in levels:
        p, s = lvl[0], lvl[1]
        p = Decimal(str(p)) if isinstance(p, str) or isinstance(p, float) else Decimal(int(p)) / 100
        parsed.append((p, Decimal(str(s))))
    parsed.sort(key=lambda x: x[0], reverse=True)  # best (highest) opposite bid first
    remaining = Decimal(size)
    cost = Decimal(0)
    filled = Decimal(0)
    for bid, avail in parsed:
        take = min(avail, remaining)
        if take <= 0:
            continue
        cost += take * (Decimal(1) - bid)
        filled += take
        remaining -= take
        if remaining <= 0:
            break
    if filled == 0:
        return ExecutableQuote(ticker, side, Decimal(0), Decimal(0), "none")
    best = Decimal(1) - parsed[0][0]
    return ExecutableQuote(
        ticker,
        side,
        best,
        parsed[0][1],
        "book_walk",
        vwap_for_size=cost / filled,
        filled_size=filled,
    )
