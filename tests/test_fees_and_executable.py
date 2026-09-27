from __future__ import annotations

from decimal import Decimal

import pytest

from soccer_edge.core.errors import FeeMechanicsUnverifiedError
from soccer_edge.kalshi.executable import top_of_book, walk_book
from soccer_edge.kalshi.fees import (
    FeeRegime,
    breakeven_probability,
    fee_per_contract,
    maker_fee,
    taker_fee,
)
from soccer_edge.kalshi.schemas import RawMarket


def test_taker_fee_formula_and_rounding():
    r = FeeRegime("quadratic")
    # 0.07 * 1 * 0.5 * 0.5 = 0.0175 exactly
    assert taker_fee(Decimal("0.50"), 1, r) == Decimal("0.017500")
    # 0.07 * 10 * 0.47 * 0.53 = 0.174370
    assert taker_fee(Decimal("0.47"), 10, r) == Decimal("0.174370")
    # ceiling to $0.000001, never to the cent
    assert taker_fee(Decimal("0.03"), 1, r) == Decimal("0.002037")


def test_maker_fee_only_when_series_says_so():
    assert maker_fee(Decimal("0.5"), 1, FeeRegime("quadratic")) == 0
    assert maker_fee(Decimal("0.5"), 1, FeeRegime("quadratic_with_maker_fees")) == Decimal(
        "0.004375"
    )


def test_unknown_fee_type_fails_closed():
    with pytest.raises(FeeMechanicsUnverifiedError):
        taker_fee(Decimal("0.5"), 1, FeeRegime("linear_mystery"))


def test_breakeven_exceeds_price():
    r = FeeRegime("quadratic")
    be = breakeven_probability(Decimal("0.60"), r)
    assert be == Decimal("0.60") + fee_per_contract(Decimal("0.60"), r)
    assert be > Decimal("0.60")


def test_fee_multiplier_honoured():
    assert taker_fee(Decimal("0.5"), 1, FeeRegime("quadratic", Decimal(2))) == Decimal("0.035000")


def test_executable_is_ask_never_mid():
    m = RawMarket.from_api(
        {
            "ticker": "T-1-1",
            "event_ticker": "T-1",
            "yes_bid_dollars": "0.40",
            "yes_ask_dollars": "0.46",
            "no_bid_dollars": "0.54",
            "no_ask_dollars": "0.60",
            "yes_ask_size_fp": "10",
            "no_ask_size_fp": "5",
        }
    )
    assert top_of_book(m, "yes").price == Decimal("0.46")
    assert top_of_book(m, "no").price == Decimal("0.60")


def test_zero_size_or_degenerate_book_is_not_a_quote():
    m = RawMarket.from_api(
        {
            "ticker": "T-1-1",
            "event_ticker": "T-1",
            "yes_ask_dollars": "0.99",
            "yes_ask_size_fp": "0",
            "no_ask_dollars": "1.00",
        }
    )
    assert not top_of_book(m, "yes").is_quote
    assert not top_of_book(m, "no").is_quote


def test_book_walk_vwap():
    ob = {
        "orderbook_fp": {
            "yes_dollars": [["0.40", "100"]],
            "no_dollars": [["0.50", "10"], ["0.55", "20"]],
        }
    }
    q = walk_book("T", ob, "yes", 25)
    # best NO bid 0.55 -> YES ask 0.45 for 20, then 0.50 for 5
    assert q.price == Decimal("0.45")
    assert q.filled_size == 25
    assert q.vwap_for_size == (Decimal("0.45") * 20 + Decimal("0.50") * 5) / 25
