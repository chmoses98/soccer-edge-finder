"""Analytic Dixon-Coles score matrix. Exact for static markets; used as the benchmark
and as a cross-check for the dynamic simulator."""

from __future__ import annotations

import numpy as np
from scipy.stats import poisson


def score_matrix(lam: float, mu: float, rho: float = 0.0, max_goals: int = 10) -> np.ndarray:
    """P(home=i, away=j) for i,j in 0..max_goals (renormalised to sum to one)."""
    i = np.arange(max_goals + 1)
    ph = poisson.pmf(i, lam)
    pa = poisson.pmf(i, mu)
    m = np.outer(ph, pa)
    m[0, 0] *= 1 - lam * mu * rho
    m[0, 1] *= 1 + lam * rho
    m[1, 0] *= 1 + mu * rho
    m[1, 1] *= 1 - rho
    m = np.clip(m, 0, None)
    return m / m.sum()


def outcome_probs(m: np.ndarray) -> dict[str, float]:
    home = float(np.tril(m, -1).sum())
    draw = float(np.trace(m))
    away = float(np.triu(m, 1).sum())
    return {"home": home, "draw": draw, "away": away}


def total_over(m: np.ndarray, line: float) -> float:
    n = m.shape[0]
    idx = np.add.outer(np.arange(n), np.arange(n))
    return float(m[idx > line].sum())
