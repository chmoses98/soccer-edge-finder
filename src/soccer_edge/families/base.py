"""Model-family interface and registry.

DATA_ONLY  : independent soccer model (Dixon-Coles posterior + world simulator).
MARKET_ONLY: de-vigged reference prices at the prediction timestamp (benchmark / prior).
HYBRID     : logit-space blend of DATA_ONLY and MARKET_ONLY with a weight fitted ONLY on
             information available before the prediction timestamp (walk-forward).

Every family exposes `probabilities(...)` for the 1X2 core outcome and, where possible, a full
score distribution. Families are versioned and hashed; frozen baselines live in config/.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class FamilyKind(str, Enum):
    DATA_ONLY = "DATA_ONLY"
    MARKET_ONLY = "MARKET_ONLY"
    HYBRID = "HYBRID"


@dataclass(frozen=True)
class FamilySpec:
    family_id: str  # e.g. 'data_only.dc_laplace_v1'
    kind: FamilyKind
    version: str
    description: str
    frozen_hash: str | None = None  # set when a baseline is frozen in config/frozen_baselines.json


def devig_proportional(odds: np.ndarray) -> np.ndarray:
    """Decimal odds (k outcomes) -> probabilities by proportional (multiplicative) de-vig."""
    inv = 1.0 / odds
    return inv / inv.sum(axis=-1, keepdims=True)


def devig_power(odds: np.ndarray, tol: float = 1e-10) -> np.ndarray:
    """Power method de-vig (Shin-like favourite-longshot correction): find k with sum (1/o)^k = 1."""
    inv = 1.0 / odds
    out = np.empty_like(inv)
    for i in range(inv.shape[0]):
        lo, hi = 0.5, 2.0
        for _ in range(100):
            k = 0.5 * (lo + hi)
            s = np.sum(inv[i] ** k)
            if abs(s - 1) < tol:
                break
            if s > 1:
                lo = k
            else:
                hi = k
        out[i] = inv[i] ** k
        out[i] /= out[i].sum()
    return out


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def blend_logit(p_data: np.ndarray, p_market: np.ndarray, w_market: float) -> np.ndarray:
    """Multiclass logit blend: softmax(w*log p_m + (1-w)*log p_d)."""
    lp = w_market * np.log(np.clip(p_market, 1e-9, 1)) + (1 - w_market) * np.log(
        np.clip(p_data, 1e-9, 1)
    )
    lp -= lp.max(axis=-1, keepdims=True)
    e = np.exp(lp)
    return e / e.sum(axis=-1, keepdims=True)


def fit_blend_weight(
    p_data: np.ndarray, p_market: np.ndarray, y_idx: np.ndarray, grid: np.ndarray | None = None
) -> float:
    """Choose w minimising multiclass log loss on PAST outcomes only (caller guarantees chronology)."""
    grid = grid if grid is not None else np.linspace(0, 1, 21)
    best_w, best = 0.0, np.inf
    for w in grid:
        P = blend_logit(p_data, p_market, float(w))
        ll = -np.mean(np.log(np.clip(P[np.arange(len(y_idx)), y_idx], 1e-9, 1)))
        if ll < best:
            best, best_w = ll, float(w)
    return best_w


FAMILIES: dict[str, FamilySpec] = {
    "data_only.dc_laplace_v1": FamilySpec(
        "data_only.dc_laplace_v1",
        FamilyKind.DATA_ONLY,
        "1",
        "Dixon-Coles MAP + Laplace posterior, analytic score matrix",
    ),
    "data_only.world_sim_v1": FamilySpec(
        "data_only.world_sim_v1",
        FamilyKind.DATA_ONLY,
        "1",
        "DC posterior worlds + minute-level dynamic simulator",
    ),
    "market_only.bet365_prematch_v1": FamilySpec(
        "market_only.bet365_prematch_v1",
        FamilyKind.MARKET_ONLY,
        "1",
        "Proportional de-vig of Bet365 pre-match 1X2 (not closing)",
    ),
    "market_only.kalshi_mid_v1": FamilySpec(
        "market_only.kalshi_mid_v1",
        FamilyKind.MARKET_ONLY,
        "1",
        "Kalshi YES mid-price, normalised across mutually exclusive legs",
    ),
    "hybrid.logit_blend_v1": FamilySpec(
        "hybrid.logit_blend_v1",
        FamilyKind.HYBRID,
        "1",
        "Walk-forward logit blend of data_only and market_only",
    ),
}
