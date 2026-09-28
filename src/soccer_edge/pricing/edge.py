"""Robust edge: never a point estimate alone.

Given a priced probability (with per-world probabilities) and an executable quote+fee regime:
    breakeven      = price + fee_per_contract(price)
    point_edge     = fair_mean - price              (pre-fee, probability points)
    fee_adj_edge   = fair_mean - breakeven
    p_edge_positive= P_w( p_w > breakeven )         (share of plausible worlds in which the bet is +EV)
    worst_case     = quantile_w(p_w, alpha) - breakeven
    robust         = fee_adj_edge >= min_edge AND p_edge_positive >= min_p AND worst_case > 0
    bet_up_to      = largest price with quantile_w(p_w, alpha) - breakeven(price) >= 0 (probability units)
Buying NO mirrors with q_w = 1 - p_w.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import numpy as np

from soccer_edge.kalshi.executable import ExecutableQuote
from soccer_edge.kalshi.fees import FeeRegime, breakeven_probability
from soccer_edge.pricing.pricer import PricedProbability


@dataclass(frozen=True)
class EdgeConfig:
    min_fee_adjusted_edge: float = 0.02  # probability points
    min_p_edge_positive: float = 0.80
    worst_case_quantile: float = 0.20  # 'worst reasonable case' = 20th percentile world
    interval_level: float = 0.80
    version: str = "edge_v1"


@dataclass(frozen=True)
class EdgeAssessment:
    ticker: str
    side: str  # yes | no
    price: Decimal
    breakeven: Decimal
    fair: float
    fair_low: float
    fair_high: float
    point_edge: float
    fee_adjusted_edge: float
    p_edge_positive: float
    worst_case_edge: float
    robust_positive_ev: bool
    bet_up_to_price: Decimal | None
    fee_per_contract: Decimal
    reasons: tuple[str, ...]
    config_version: str

    def to_json(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        for k in ("price", "breakeven", "bet_up_to_price", "fee_per_contract"):
            d[k] = str(d[k]) if d[k] is not None else None
        d["reasons"] = list(self.reasons)
        # accurate name for P(edge>0): the share of the model's own posterior worlds beating the price
        d["model_posterior_edge_share"] = self.p_edge_positive
        return d


def _side_probs(p: PricedProbability, side: str) -> tuple[float, float, float, np.ndarray]:
    if side == "yes":
        return p.fair_mean, p.p_low, p.p_high, p.world_probs
    return 1 - p.fair_mean, 1 - p.p_high, 1 - p.p_low, 1 - p.world_probs


def assess(
    p: PricedProbability,
    quote: ExecutableQuote,
    regime: FeeRegime,
    cfg: EdgeConfig | None = None,
    *,
    contracts: int = 1,
) -> EdgeAssessment:
    cfg = cfg or EdgeConfig()
    fair, lo, hi, pw = _side_probs(p, quote.side)
    price = quote.price
    be = breakeven_probability(price, regime, contracts=contracts)
    fee = be - price
    be_f = float(be)
    point = fair - float(price)
    fee_adj = fair - be_f
    p_pos = float((pw > be_f).mean())
    worst = float(np.quantile(pw, cfg.worst_case_quantile)) - be_f
    reasons: list[str] = []
    if not quote.is_quote:
        reasons.append("no executable quote")
    if fee_adj < cfg.min_fee_adjusted_edge:
        reasons.append(f"fee-adjusted edge {fee_adj:+.3f} < {cfg.min_fee_adjusted_edge}")
    if p_pos < cfg.min_p_edge_positive:
        reasons.append(f"P(edge>0)={p_pos:.2f} < {cfg.min_p_edge_positive}")
    if worst <= 0:
        reasons.append(f"worst-case edge {worst:+.3f} <= 0")
    robust = not reasons
    bet_up_to = _bet_up_to(pw, cfg.worst_case_quantile, regime, contracts)
    return EdgeAssessment(
        ticker=p.ticker,
        side=quote.side,
        price=price,
        breakeven=be,
        fair=fair,
        fair_low=lo,
        fair_high=hi,
        point_edge=point,
        fee_adjusted_edge=fee_adj,
        p_edge_positive=p_pos,
        worst_case_edge=worst,
        robust_positive_ev=robust,
        bet_up_to_price=bet_up_to,
        fee_per_contract=fee,
        reasons=tuple(reasons),
        config_version=cfg.version,
    )


def _bet_up_to(pw: np.ndarray, q: float, regime: FeeRegime, contracts: int) -> Decimal | None:
    """Largest cent price at which the worst-reasonable-case world still clears fees."""
    target = float(np.quantile(pw, q))
    best: Decimal | None = None
    for cents in range(1, 100):
        pr = Decimal(cents) / 100
        if float(breakeven_probability(pr, regime, contracts=contracts)) <= target:
            best = pr
        else:
            break
    return best
