"""Decimal helpers for prices and money. Prices are in *probability units* (0..1) or cents (0..100)."""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ONE = Decimal(1)
ZERO = Decimal(0)


def D(value: int | float | str | Decimal) -> Decimal:  # noqa: N802 - conventional short name
    """Construct a Decimal safely (floats go through repr to avoid binary noise)."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(repr(value))
    return Decimal(value)


def cents_to_prob(cents: int | Decimal) -> Decimal:
    """Kalshi integer cents (1..99) -> probability-unit price (0.01..0.99)."""
    return (D(cents) / 100).quantize(CENT)


def prob_to_cents(prob: Decimal) -> int:
    return int((prob * 100).to_integral_value(rounding=ROUND_HALF_UP))


def quantize_cent(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def ceil_cent(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_CEILING)
