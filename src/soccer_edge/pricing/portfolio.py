"""Portfolio correlation from shared simulated worlds (research functions; staking disabled)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class PortfolioStats:
    tickers: tuple[str, ...]
    expected_profit: tuple[float, ...]
    covariance: np.ndarray
    correlation: np.ndarray
    total_expected: float
    total_sd: float
    p_total_loss: float
    max_drawdown_draw: float

    def to_json(self) -> dict[str, Any]:
        return {
            "tickers": list(self.tickers),
            "expected_profit": [round(x, 5) for x in self.expected_profit],
            "correlation": np.round(self.correlation, 3).tolist(),
            "total_expected": round(self.total_expected, 5),
            "total_sd": round(self.total_sd, 5),
            "p_total_loss": round(self.p_total_loss, 4),
            "worst_draw": round(self.max_drawdown_draw, 4),
            "staking": "DISABLED (research only)",
        }


def portfolio_stats(
    tickers: list[str], payoffs: list[np.ndarray], units: list[float] | None = None
) -> PortfolioStats:
    """payoffs: per-candidate per-draw profit vectors over the SAME draws (same fixture or joint sims)."""
    P = np.stack(payoffs)  # (k, N)
    u = np.array(units if units is not None else [1.0] * len(tickers))
    exp = P.mean(axis=1) * u
    cov = np.cov(P * u[:, None]) if len(tickers) > 1 else np.array([[float(np.var(P[0] * u[0]))]])
    sd = np.sqrt(np.diag(cov))
    corr = cov / np.outer(np.where(sd > 0, sd, 1), np.where(sd > 0, sd, 1))
    total = (P * u[:, None]).sum(axis=0)
    return PortfolioStats(
        tickers=tuple(tickers),
        expected_profit=tuple(float(x) for x in exp),
        covariance=cov,
        correlation=corr,
        total_expected=float(total.mean()),
        total_sd=float(total.std()),
        p_total_loss=float((total < 0).mean()),
        max_drawdown_draw=float(total.min()),
    )
