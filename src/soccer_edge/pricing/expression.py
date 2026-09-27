"""Best market expression: from many +EV contracts on one fixture to the few that express a thesis.

Algorithm (documented in docs/MARKET_EXPRESSION.md):
1. Group candidate (contract, side) pairs by fixture.
2. Build the payoff matrix from the SAME joint outcomes: payoff_i(draw) = 1[YES_i] - price (or NO).
3. Correlation between candidates = corr of payoff vectors across draws -> correlation groups
   (single-linkage at |rho| >= threshold).
4. Dominance: A dominates B if same group and A's worst-case edge >= B's and fee-adjusted edge >= B's
   and P(edge>0) >= B's (with at least one strict); remove B and log the reason.
5. Within a group keep the best expression by (worst-case edge, fee-adjusted edge, liquidity).
6. Output ranked expressions with correlation group ids; no top-N truncation by raw edge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from soccer_edge.pricing.edge import EdgeAssessment


@dataclass
class Candidate:
    fixture_id: str
    assessment: EdgeAssessment
    payoff: np.ndarray  # per-draw profit if bought 1 contract at the executable price
    liquidity: float = 0.0
    thesis: str = ""


@dataclass
class ExpressionResult:
    kept: list[Candidate]
    removed: list[tuple[Candidate, str]]
    groups: dict[str, int]  # ticker|side -> correlation group id
    correlation: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "kept": [
                {
                    "ticker": c.assessment.ticker,
                    "side": c.assessment.side,
                    "group": self.groups[_key(c)],
                    "thesis": c.thesis,
                }
                for c in self.kept
            ],
            "removed": [
                {"ticker": c.assessment.ticker, "side": c.assessment.side, "reason": r}
                for c, r in self.removed
            ],
        }


def _key(c: Candidate) -> str:
    return f"{c.assessment.ticker}|{c.assessment.side}"


def payoff_vector(indicator: np.ndarray, side: str, price: float, fee: float) -> np.ndarray:
    win = indicator if side == "yes" else ~indicator
    return win.astype(float) - price - fee


def reduce_expressions(cands: list[Candidate], *, corr_threshold: float = 0.6) -> ExpressionResult:
    kept: list[Candidate] = []
    removed: list[tuple[Candidate, str]] = []
    groups: dict[str, int] = {}
    corr_out: dict[str, dict[str, float]] = {}
    by_fx: dict[str, list[Candidate]] = {}
    for c in cands:
        by_fx.setdefault(c.fixture_id, []).append(c)
    gid = 0
    for fx_cands in by_fx.values():
        n = len(fx_cands)
        if n == 1:
            groups[_key(fx_cands[0])] = gid
            kept.append(fx_cands[0])
            gid += 1
            continue
        P = np.stack([c.payoff for c in fx_cands])
        C = np.corrcoef(P)
        C = np.nan_to_num(C, nan=0.0)
        # single-linkage components
        parent = list(range(n))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i in range(n):
            for j in range(i + 1, n):
                if abs(C[i, j]) >= corr_threshold:
                    parent[find(i)] = find(j)
        comp: dict[int, list[int]] = {}
        for i in range(n):
            comp.setdefault(find(i), []).append(i)
        for members in comp.values():
            for i in members:
                groups[_key(fx_cands[i])] = gid
                corr_out[_key(fx_cands[i])] = {
                    _key(fx_cands[j]): round(float(C[i, j]), 3) for j in members if j != i
                }
            # dominance + best expression
            ranked = sorted(
                members,
                key=lambda i: (
                    fx_cands[i].assessment.worst_case_edge,
                    fx_cands[i].assessment.fee_adjusted_edge,
                    fx_cands[i].liquidity,
                ),
                reverse=True,
            )
            best = fx_cands[ranked[0]]
            kept.append(best)
            for i in ranked[1:]:
                c = fx_cands[i]
                a, b = best.assessment, c.assessment
                if C[ranked[0], i] < 0:
                    # negatively correlated but same fixture: opposite sides of the same view -> keep only best
                    removed.append(
                        (
                            c,
                            f"opposes {a.ticker}/{a.side} in the same fixture (corr {C[ranked[0], i]:+.2f})",
                        )
                    )
                elif (
                    a.worst_case_edge >= b.worst_case_edge
                    and a.fee_adjusted_edge >= b.fee_adjusted_edge
                    and a.p_edge_positive >= b.p_edge_positive
                ):
                    removed.append(
                        (c, f"dominated by {a.ticker}/{a.side} (corr {C[ranked[0], i]:+.2f})")
                    )
                else:
                    removed.append(
                        (
                            c,
                            f"redundant with {a.ticker}/{a.side} (corr {C[ranked[0], i]:+.2f}); best expression kept",
                        )
                    )
            gid += 1
    kept.sort(
        key=lambda c: (c.assessment.worst_case_edge, c.assessment.fee_adjusted_edge), reverse=True
    )
    return ExpressionResult(kept=kept, removed=removed, groups=groups, correlation=corr_out)
