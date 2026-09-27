"""Pure evaluation functions. Inputs are numpy arrays; no I/O."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

EPS = 1e-6


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def log_loss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, EPS, 1 - EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def multiclass_log_loss(P: np.ndarray, y_idx: np.ndarray) -> float:
    P = np.clip(P, EPS, 1)
    P = P / P.sum(axis=1, keepdims=True)
    return float(-np.mean(np.log(P[np.arange(len(y_idx)), y_idx])))


def multiclass_brier(P: np.ndarray, y_idx: np.ndarray) -> float:
    Y = np.zeros_like(P)
    Y[np.arange(len(y_idx)), y_idx] = 1
    return float(np.mean(np.sum((P - Y) ** 2, axis=1)))


@dataclass(frozen=True)
class ReliabilityBin:
    lo: float
    hi: float
    n: int
    mean_pred: float
    mean_obs: float


def reliability(p: np.ndarray, y: np.ndarray, bins: int = 10) -> list[ReliabilityBin]:
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for i in range(bins):
        m = (p >= edges[i]) & (p < edges[i + 1] if i < bins - 1 else p <= edges[i + 1])
        if m.sum() == 0:
            out.append(
                ReliabilityBin(float(edges[i]), float(edges[i + 1]), 0, float("nan"), float("nan"))
            )
        else:
            out.append(
                ReliabilityBin(
                    float(edges[i]),
                    float(edges[i + 1]),
                    int(m.sum()),
                    float(p[m].mean()),
                    float(y[m].mean()),
                )
            )
    return out


def expected_calibration_error(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    rel = reliability(p, y, bins)
    n = len(p)
    return float(sum(b.n / n * abs(b.mean_pred - b.mean_obs) for b in rel if b.n > 0))


def sharpness(p: np.ndarray) -> float:
    return float(np.mean(np.abs(p - 0.5)))


def interval_coverage(lo: np.ndarray, hi: np.ndarray, y_rate: np.ndarray) -> float:
    """Share of cases whose realised frequency falls inside [lo, hi]. For binary outcomes,
    use grouped realised rates (see `interval_calibration`)."""
    return float(np.mean((y_rate >= lo) & (y_rate <= hi)))


def interval_calibration(
    p: np.ndarray, lo: np.ndarray, hi: np.ndarray, y: np.ndarray, *, level: float, bins: int = 10
) -> dict[str, Any]:
    """Are our credible intervals honest? Group by predicted probability, compare the bin's
    realised rate with the *average* interval in that bin. Also PIT-like check: share of y
    'consistent' with interval via binomial tail. Returns diagnostics, not a verdict."""
    rel = reliability(p, y, bins)
    edges = np.linspace(0, 1, bins + 1)
    inside = 0
    total = 0
    rows = []
    for i, b in enumerate(rel):
        if b.n == 0:
            continue
        m = (p >= edges[i]) & (p < edges[i + 1] if i < bins - 1 else p <= edges[i + 1])
        blo, bhi = float(lo[m].mean()), float(hi[m].mean())
        ok = blo <= b.mean_obs <= bhi
        inside += int(ok) * b.n
        total += b.n
        rows.append(
            {
                "bin": i,
                "n": b.n,
                "mean_pred": round(b.mean_pred, 4),
                "mean_obs": round(b.mean_obs, 4),
                "mean_lo": round(blo, 4),
                "mean_hi": round(bhi, 4),
                "obs_inside": ok,
            }
        )
    width = float(np.mean(hi - lo))
    return {
        "level": level,
        "weighted_bin_coverage": (inside / total) if total else float("nan"),
        "mean_width": width,
        "bins": rows,
    }


def clv_points(
    entry_price: np.ndarray, closing_price: np.ndarray, side_is_yes: np.ndarray
) -> np.ndarray:
    """Closing-line value in probability points, POSITIVE_IS_GOOD: for YES, close - entry;
    for NO, entry - close (prices in YES units)."""
    return np.where(side_is_yes, closing_price - entry_price, entry_price - closing_price)


def realised_ev(price: np.ndarray, fee: np.ndarray, won: np.ndarray) -> np.ndarray:
    return won.astype(float) - price - fee


def bootstrap_mean_ci(
    x: np.ndarray, n_boot: int = 2000, level: float = 0.95, seed: int = 0
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    if len(x) == 0:
        return float("nan"), float("nan")
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    means = x[idx].mean(axis=1)
    a = (1 - level) / 2
    return float(np.quantile(means, a)), float(np.quantile(means, 1 - a))
