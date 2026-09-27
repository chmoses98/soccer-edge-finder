"""Fair probability with uncertainty from the nested (worlds x draws) structure.

p_w  = mean over draws in world w of the YES indicator           (aleatoric integrated out)
fair = mean_w p_w                                                  (parameter/model integrated out)
interval = quantiles of p_w (parameter+model uncertainty) widened by Monte-Carlo error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from soccer_edge.pricing.semantics import Semantics
from soccer_edge.sim.outcome import JointOutcome


@dataclass(frozen=True)
class PricedProbability:
    ticker: str
    fair_mean: float
    fair_median: float
    p_low: float  # lower bound of `interval_level` interval
    p_high: float
    interval_level: float
    param_sd: float  # sd of p_w across worlds
    mc_se: float  # Monte-Carlo standard error of fair_mean
    n_worlds: int
    n_draws: int
    effective_draws: int
    world_probs: np.ndarray = field(repr=False, compare=False)
    description: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "fair_probability_mean": round(self.fair_mean, 6),
            "fair_probability_median": round(self.fair_median, 6),
            "fair_probability_low": round(self.p_low, 6),
            "fair_probability_high": round(self.p_high, 6),
            "interval_level": self.interval_level,
            "parameter_sd": round(self.param_sd, 6),
            "mc_standard_error": round(self.mc_se, 6),
            "n_worlds": self.n_worlds,
            "n_draws": self.n_draws,
            "effective_draws": self.effective_draws,
            "description": self.description,
        }


def world_means(indicator: np.ndarray, out: JointOutcome) -> np.ndarray:
    sums = np.bincount(out.world_index, weights=indicator.astype(float), minlength=out.n_worlds)
    counts = np.bincount(out.world_index, minlength=out.n_worlds)
    return sums / np.maximum(counts, 1)


def price(sem: Semantics, out: JointOutcome, *, interval_level: float = 0.80) -> PricedProbability:
    ind = sem.settle(out)
    pw = world_means(ind, out)
    fair = float(pw.mean())
    lo_q, hi_q = (1 - interval_level) / 2, 1 - (1 - interval_level) / 2
    lo, hi = float(np.quantile(pw, lo_q)), float(np.quantile(pw, hi_q))
    # MC error of the overall mean: binomial approx across all draws plus between-world variance
    n = out.n
    mc_se = float(np.sqrt(max(fair * (1 - fair), 1e-12) / n))
    z = 1.2816 if interval_level == 0.80 else 1.96
    lo = max(0.0, lo - z * mc_se)
    hi = min(1.0, hi + z * mc_se)
    return PricedProbability(
        ticker=sem.ticker,
        fair_mean=fair,
        fair_median=float(np.median(pw)),
        p_low=lo,
        p_high=hi,
        interval_level=interval_level,
        param_sd=float(pw.std()),
        mc_se=mc_se,
        n_worlds=out.n_worlds,
        n_draws=n,
        effective_draws=int(n),
        world_probs=pw,
        description=sem.description,
    )
