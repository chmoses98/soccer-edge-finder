"""Price-time expression research over the script layer: same-thesis detection and a transparent robust ranking.

Neither output changes the production selection policy, authority or any action; they are presentation and
research fields that sit next to them.

Same thesis. A candidate side re-expresses another's match thesis when their payoffs are strongly correlated under
the model's joint distribution. The joint is exact and cheap at reprice time: the board stores the mean
full-time score grid, and the world-independent timing kernel (kernel.cell_kernel) extends it to
(h, a, h1, a1, first scorer), where every supported contract is an indicator (cells.cell_indicator). Groups are
formed in rank order: a side joins the first group whose best expression it tracks with phi >= 0.5, else it leads a
new group (leader grouping; single linkage chained 16-17 weakly related sides on the first live board). A group's
anchor script is the script with the
largest summed positive edge contribution across its members - the "match thesis" the group expresses.

Robust ranking (lexicographic, no composite score):
    1. survivability label: VERY_ROBUST < ROBUST < MIXED < FRAGILE < SCRIPT_DEPENDENT
    2. robust worst-case (q0.20 world) edge > 0 first
    3. edge_ex_top_script, descending (value that survives losing the best script)
    4. overall fee-adjusted edge, descending
The best expression of a thesis group is its top-ranked member.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from soccer_edge.gamescript.cells import ADVANCE, CellSpec, ScriptUnsupported, cell_indicator
from soccer_edge.gamescript.kernel import cell_kernel
from soccer_edge.gamescript.taxonomy import SCRIPT_IDS

EXPRESSION_VERSION = "script_expressions_v1"
SAME_THESIS_PHI = 0.5
LABEL_RANK = {
    "VERY_ROBUST": 0,
    "ROBUST": 1,
    "MIXED": 2,
    "FRAGILE": 3,
    "SCRIPT_DEPENDENT": 4,
    "NO_EDGE": 9,
}
RANK_BASIS = (
    "survivability label (VERY_ROBUST > ROBUST > MIXED > FRAGILE > SCRIPT_DEPENDENT), then worst-case "
    "(q0.20) edge > 0, then edge_ex_top_script, then overall fee-adjusted edge; research presentation only"
)


def rank_key(row: dict[str, Any]) -> tuple:
    sr = row["script_robustness"]
    wc = row.get("worst_case_edge")
    return (
        LABEL_RANK.get(sr["label"], 9),
        0 if (wc is not None and wc > 0) else 1,
        -(sr.get("edge_ex_top_script") or -9.0),
        -(sr.get("overall_edge") or -9.0),
        row["key"],
    )


class JointSpace:
    """Exact mean joint over (h, a, h1, a1, first) for one fixture, rebuilt from board fields only."""

    def __init__(
        self,
        score_grid: list[list[float]],
        first_half_share: float,
        *,
        requires_winner: bool,
        advance_table: list[list[float | None]] | None = None,
    ) -> None:
        grid = np.asarray(score_grid, dtype=float)
        grid = grid / grid.sum()
        self.p_cell = grid[:, :, None, None, None] * cell_kernel(float(first_half_share))
        self.requires_winner = requires_winner
        self.adv = (
            None
            if advance_table is None
            else np.nan_to_num(np.asarray(advance_table, dtype=float))[:, :, None, None, None]
        )

    def indicator(self, spec: CellSpec, side: str) -> np.ndarray:
        ind = cell_indicator(spec, requires_winner=self.requires_winner)
        if isinstance(ind, str) and ind == ADVANCE:
            if self.adv is None:
                raise ScriptUnsupported("advance table missing")
            a = self.adv if spec.side == "home" else 1.0 - self.adv
            ind = np.broadcast_to(a, self.p_cell.shape)
        return ind if side == "yes" else 1.0 - ind

    def correlation_matrix(self, inds: list[np.ndarray]) -> np.ndarray:
        if not inds:
            return np.zeros((0, 0))
        w = self.p_cell.reshape(-1)
        X = np.stack([i.reshape(-1) for i in inds])  # (n, cells)
        p = X @ w
        Pab = (X * w) @ X.T
        np.fill_diagonal(Pab, p)
        cov = Pab - np.outer(p, p)
        sd = np.sqrt(np.clip(p * (1 - p), 1e-12, None))
        return cov / np.outer(sd, sd)


def thesis_groups(
    rows: list[dict[str, Any]], space: JointSpace | None, *, fixture_id: str
) -> tuple[list[dict[str, Any]], dict[str, dict[str, float]]]:
    """Group candidate sides (rows carry key, spec, side, script_robustness, shares) by payoff correlation."""
    n = len(rows)
    if n == 0:
        return [], {}
    inds: list[np.ndarray | None] = []
    for r in rows:
        try:
            inds.append(space.indicator(r["spec"], r["side"]) if space is not None else None)
        except ScriptUnsupported:
            inds.append(None)
    ok = [i for i in range(n) if inds[i] is not None]
    phi = np.eye(n)
    if space is not None and ok:
        sub = space.correlation_matrix([inds[i] for i in ok])  # type: ignore[misc]
        for a, i in enumerate(ok):
            for b, j in enumerate(ok):
                phi[i, j] = sub[a, b]
    # leader grouping in rank order: a side joins the first group whose BEST expression it tracks
    # (phi >= SAME_THESIS_PHI); otherwise it leads a new group. Every member is therefore a correlated
    # re-expression of its group's best side (single linkage would chain weakly related sides together).
    order = sorted(range(n), key=lambda i: rank_key(rows[i]))
    leaders: list[int] = []
    members_of: dict[int, list[int]] = {}
    for i in order:
        lead = next((ld for ld in leaders if phi[i, ld] >= SAME_THESIS_PHI), None)
        if lead is None:
            leaders.append(i)
            members_of[i] = [i]
        else:
            members_of[lead].append(i)
    groups: list[dict[str, Any]] = []
    correlated: dict[str, dict[str, float]] = {}
    ordered = [members_of[ld] for ld in leaders]
    for gi, members in enumerate(ordered, start=1):
        members = sorted(members, key=lambda i: rank_key(rows[i]))
        contrib = np.zeros(len(SCRIPT_IDS))
        for i in members:
            sr = rows[i]["script_robustness"]
            for s, e in enumerate(sr["conditional_edges"]):
                if e is not None and e > 0:
                    contrib[s] += rows[i]["shares"][s] * e
        anchor = SCRIPT_IDS[int(np.argmax(contrib))] if contrib.sum() > 0 else None
        gid = f"{fixture_id}#thesis{gi}"
        for i in members:
            rows[i]["thesis_group"] = gid
            correlated[rows[i]["key"]] = {
                rows[j]["key"]: round(float(phi[i, j]), 3)
                for j in range(n)
                if j != i and abs(phi[i, j]) >= 0.3
            }
        groups.append(
            {
                "thesis_group": gid,
                "anchor_script": anchor,
                "members": [rows[i]["key"] for i in members],
                "best_expression": rows[members[0]]["key"],
                "size": len(members),
            }
        )
    return groups, correlated
