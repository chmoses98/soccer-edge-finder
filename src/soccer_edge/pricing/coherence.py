"""Coherence audit across contracts priced from the same joint distribution.

Because every contract is settled on the same realisations, these hold *by construction*;
the audit exists to catch semantics bugs (wrong side, wrong period) loudly.
"""

from __future__ import annotations

from collections import defaultdict

from soccer_edge.core.errors import CoherenceError
from soccer_edge.kalshi.taxonomy import MarketFamily, Period
from soccer_edge.pricing.pricer import PricedProbability
from soccer_edge.pricing.semantics import Semantics

TOL = 1e-9
MEAN_INTERVAL_TOL = 0.01  # skewed world distributions: mean may exceed p90 by a hair; see audit()


def audit(priced: list[tuple[Semantics, PricedProbability]], *, tol: float = TOL) -> list[str]:
    problems: list[str] = []
    ladders: dict[tuple, list[tuple[float, float, str]]] = defaultdict(list)
    results: dict[tuple, dict[str, float]] = defaultdict(dict)
    for sem, p in priced:
        if not (0.0 <= p.fair_mean <= 1.0):
            problems.append(f"{p.ticker}: probability out of bounds {p.fair_mean}")
        # The mean of a skewed per-world distribution can legitimately sit outside the central 80%
        # interval (e.g. 90% of worlds at 0, 10% at 0.001 -> mean 1e-4 > p90 = 0). Only a material
        # excursion (> MEAN_INTERVAL_TOL probability points) indicates a pricing bug.
        if not (p.p_low - MEAN_INTERVAL_TOL <= p.fair_mean <= p.p_high + MEAN_INTERVAL_TOL):
            problems.append(f"{p.ticker}: mean outside interval")
        if (
            sem.family
            in (
                MarketFamily.TOTAL_GOALS,
                MarketFamily.TEAM_TOTAL,
                MarketFamily.HANDICAP,
                MarketFamily.FIRST_HALF_TOTAL,
            )
            and sem.line is not None
        ):
            ladders[(sem.family, sem.period, sem.side)].append(
                (float(sem.line), p.fair_mean, p.ticker)
            )
        if (
            sem.family in (MarketFamily.MATCH_RESULT_3WAY, MarketFamily.FIRST_HALF_RESULT)
            and sem.side
        ):
            results[(sem.family, sem.period)][sem.side] = p.fair_mean
    for key, rows in ladders.items():
        rows.sort()
        for (l1, p1, t1), (l2, p2, t2) in zip(rows, rows[1:]):
            if l2 > l1 and p2 > p1 + tol:
                problems.append(
                    f"ladder not monotone: {t1} (>{l1}) {p1:.4f} < {t2} (>{l2}) {p2:.4f} for {key[0].value}"
                )
    for key, sides in results.items():
        if set(sides) == {"home", "draw", "away"}:
            s = sum(sides.values())
            if abs(s - 1.0) > 1e-6:
                problems.append(f"3-way legs sum to {s:.6f} for {key[0].value}/{key[1].value}")
    return problems


def assert_coherent(priced: list[tuple[Semantics, PricedProbability]]) -> None:
    problems = audit(priced)
    if problems:
        raise CoherenceError("; ".join(problems[:10]))


__all__ = ["Period", "assert_coherent", "audit"]
