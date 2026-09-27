"""Kalshi fee engine (Decimal). Fails closed when the fee regime cannot be verified.

Verified mechanics (transcribed from Kalshi's July-2026 fee schedule by sibling repos and
confirmed against a live hand-recomputed probe; see docs/MARKET_PRICING.md#fees):
    raw_fee   = coefficient x fee_multiplier x contracts x P x (1 - P)
    trade fee = ceil(raw_fee, $0.000001)            # per fill
    coefficient: taker 0.07 ; maker 0.0175 (only when series fee_type == quadratic_with_maker_fees)
    fee_type   in {quadratic, quadratic_with_maker_fees}  -> anything else is UNVERIFIED (fail closed)
    fee_multiplier observed = 1 for every soccer series so far; honoured when present.
Note: two sibling repos used ceil-to-whole-cent (web-sourced); CFB measured it as 2.75x-14x too
high on small fees. We use the documented $0.000001 ceiling and record the schedule version.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

from soccer_edge.core.errors import FeeMechanicsUnverifiedError

FEE_SCHEDULE_VERSION = "kalshi_fee_schedule_2026-07_transcribed_v1"
TAKER_COEF = Decimal("0.07")
MAKER_COEF = Decimal("0.0175")
FEE_QUANTUM = Decimal("0.000001")
KNOWN_FEE_TYPES = {"quadratic": False, "quadratic_with_maker_fees": True}


@dataclass(frozen=True)
class FeeRegime:
    fee_type: str
    fee_multiplier: Decimal = Decimal(1)
    schedule_version: str = FEE_SCHEDULE_VERSION

    @property
    def maker_fees_apply(self) -> bool:
        if self.fee_type not in KNOWN_FEE_TYPES:
            raise FeeMechanicsUnverifiedError(f"unknown fee_type {self.fee_type!r}")
        return KNOWN_FEE_TYPES[self.fee_type]

    def verify(self) -> None:
        if self.fee_type not in KNOWN_FEE_TYPES:
            raise FeeMechanicsUnverifiedError(
                f"fee_type {self.fee_type!r} is not in the verified set {sorted(KNOWN_FEE_TYPES)}; refusing to price"
            )
        if self.fee_multiplier <= 0:
            raise FeeMechanicsUnverifiedError(
                f"fee_multiplier {self.fee_multiplier} is not positive"
            )


def taker_fee(price: Decimal, contracts: int, regime: FeeRegime) -> Decimal:
    """Total taker fee in dollars for `contracts` contracts bought at `price` (0..1)."""
    regime.verify()
    if not (Decimal(0) < price < Decimal(1)):
        raise ValueError(f"price must be strictly inside (0,1): {price}")
    raw = TAKER_COEF * regime.fee_multiplier * Decimal(contracts) * price * (Decimal(1) - price)
    return raw.quantize(FEE_QUANTUM, rounding=ROUND_CEILING)


def maker_fee(price: Decimal, contracts: int, regime: FeeRegime) -> Decimal:
    regime.verify()
    if not regime.maker_fees_apply:
        return Decimal(0)
    raw = MAKER_COEF * regime.fee_multiplier * Decimal(contracts) * price * (Decimal(1) - price)
    return raw.quantize(FEE_QUANTUM, rounding=ROUND_CEILING)


def fee_per_contract(
    price: Decimal, regime: FeeRegime, *, contracts: int = 1, maker: bool = False
) -> Decimal:
    """Fee per contract, as paid on a single fill of `contracts` (ceiling amortised)."""
    f = maker_fee(price, contracts, regime) if maker else taker_fee(price, contracts, regime)
    return f / Decimal(contracts)


def breakeven_probability(
    price: Decimal, regime: FeeRegime, *, contracts: int = 1, maker: bool = False
) -> Decimal:
    """Probability at which buying at `price` has zero expected profit after fees.
    Payout is $1 on YES; expected profit = p*1 - price - fee  ->  p* = price + fee_per_contract."""
    return price + fee_per_contract(price, regime, contracts=contracts, maker=maker)
