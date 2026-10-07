"""Model-time script layer: script shares, P(contract | script) for every supported contract, and per-script
outcome / temporal profiles - all exact sums over (world, h, a, h1, a1, first scorer).

Inputs are the model's own per-world Dixon-Coles score matrices (the matrices world_sim_v2 draws full-time scores
from and the analytic pricer sums) plus the engine's first-half share. Nothing here reads a market price.

Definitions (w = world, S = script, M = contract YES event):
    P_w(S)        = sum_{h,a} mats[w,h,a] * T[h,a,S]                        T = P(S | h, a) from the kernel
    P_w(M and S)  = sum_{h,a,h1,a1,f} mats[w,h,a] * kernel[h,a,h1,a1,f] * 1_M * 1[S(h,a,f) = S]
    share(S)      = mean_w P_w(S)                                           (simulation_share)
    P(M | S)      = sum_w P_w(M and S) / sum_w P_w(S)                      (ratio of means)
    P(M)          = sum_S share(S) * P(M | S)                               (exact decomposition)
The conditional interval is the weighted (by P_w(S)) quantile of P_w(M and S) / P_w(S): the posterior over worlds
given that the match follows script S.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from soccer_edge.gamescript.cells import (
    ADVANCE,
    CellSpec,
    ScriptUnsupported,
    advance_home_prob,
    cell_indicator,
)
from soccer_edge.gamescript.kernel import (
    MAX_GOALS,
    TEMPORAL_FIELDS,
    cell_kernel,
    script_given_score,
    script_onehot,
    temporal_kernel,
)
from soccer_edge.gamescript.taxonomy import (
    MATERIAL_SHARE_MIN,
    MATERIAL_SHARE_RULE,
    SCRIPT_IDS,
    SCRIPTS,
    TAXONOMY_VERSION,
    K,
)

SCRIPT_LAYER_VERSION = "soccer_script_layer_v1"
DECIMALS = 5


def _r(x: float | None, d: int = DECIMALS) -> float | None:
    if x is None or not np.isfinite(x):
        return None
    return round(float(x), d)


def weighted_quantiles(
    values: np.ndarray, weights: np.ndarray, qs: tuple[float, ...]
) -> list[float | None]:
    w = np.asarray(weights, dtype=float)
    if w.sum() <= 0:
        return [None for _ in qs]
    order = np.argsort(values)
    v = np.asarray(values)[order]
    cw = np.cumsum(w[order])
    cw = cw / cw[-1]
    return [float(v[min(np.searchsorted(cw, q, side="left"), len(v) - 1)]) for q in qs]


class ScriptLayer:
    """Per-fixture exact script computation over the model's worlds."""

    def __init__(
        self,
        mats: np.ndarray,
        *,
        first_half_share: float,
        lam: np.ndarray | None = None,
        mu: np.ndarray | None = None,
        requires_winner: bool = False,
        knockout: dict[str, Any] | None = None,
        interval_level: float = 0.80,
    ) -> None:
        if mats.ndim != 3 or mats.shape[1] != MAX_GOALS + 1:
            raise ValueError(f"score matrices must be (W, {MAX_GOALS + 1}, {MAX_GOALS + 1})")
        self.mats = mats
        self.W = mats.shape[0]
        self.s = float(first_half_share)
        self.kernel = cell_kernel(self.s)
        self.onehot = script_onehot()
        self.T = script_given_score(self.s)
        self.requires_winner = bool(requires_winner)
        self.interval_level = interval_level
        self.lo_q = (1 - interval_level) / 2
        self.hi_q = 1 - self.lo_q
        self.pw_s = mats.reshape(self.W, -1) @ self.T.reshape(-1, self.T.shape[-1])  # (W, K)
        self.share = self.pw_s.mean(axis=0)
        self.mean_grid = mats.mean(axis=0)
        # P(h, a, h1, a1, f) at the mean (the kernel is world-independent)
        self.p_cell = self.mean_grid[:, :, None, None, None] * self.kernel
        self.adv: np.ndarray | None = None
        if self.requires_winner:
            if lam is None or mu is None:
                raise ValueError("knockout script layer needs the world rates")
            self.adv = advance_home_prob(lam, mu, **(knockout or {}))

    # ---------------------------------------------------------------------------------------- contracts
    def joint_by_world(self, spec: CellSpec) -> np.ndarray:
        """P_w(M and S), shape (W, K)."""
        ind = cell_indicator(spec, requires_winner=self.requires_winner)
        if isinstance(ind, str) and ind == ADVANCE:
            assert self.adv is not None
            a = self.adv if spec.side == "home" else 1.0 - self.adv
            return (self.mats * a).reshape(self.W, -1) @ self.T.reshape(-1, self.T.shape[-1])
        kf = (self.kernel * ind).sum(axis=(2, 3))  # P(M, first | h, a)
        g = np.einsum("haf,hafs->has", kf, self.onehot)
        return self.mats.reshape(self.W, -1) @ g.reshape(-1, g.shape[-1])

    def contract(self, spec: CellSpec) -> dict[str, Any]:
        """Compact board block: overall exact p, per-script conditional p and interval (canonical order)."""
        j = self.joint_by_world(spec)
        p_overall = float(j.sum(axis=1).mean())
        num = j.sum(axis=0)
        den = self.pw_s.sum(axis=0)
        cond = np.where(den > 0, num / np.maximum(den, 1e-300), np.nan)
        lo, hi = [], []
        for s in range(K):
            w = self.pw_s[:, s]
            if w.sum() <= 0:
                lo.append(None)
                hi.append(None)
                continue
            r = np.where(w > 0, j[:, s] / np.maximum(w, 1e-300), 0.0)
            ql, qh = weighted_quantiles(r, w, (self.lo_q, self.hi_q))
            lo.append(_r(ql, 4))
            hi.append(_r(qh, 4))
        return {
            "p": _r(p_overall, 6),
            "sp": [_r(c) for c in cond],
            "lo": lo,
            "hi": hi,
        }

    def contracts(
        self, specs: dict[str, CellSpec]
    ) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
        out: dict[str, dict[str, Any]] = {}
        gaps: dict[str, str] = {}
        for tk, spec in specs.items():
            try:
                out[tk] = self.contract(spec)
            except ScriptUnsupported as exc:
                gaps[tk] = str(exc)[:160]
        return out, gaps

    # ----------------------------------------------------------------------------------------- profiles
    def _cond_mean(self, f: np.ndarray, s: int | None) -> float | None:
        """E[f | S] at the mean cell distribution; f broadcastable to the cell grid."""
        w = self.p_cell if s is None else self.p_cell * self._script_mask(s)
        tot = w.sum()
        if tot <= 0:
            return None
        return float((w * f).sum() / tot)

    _mask_cache: dict[int, np.ndarray] = {}

    def _script_mask(self, s: int) -> np.ndarray:
        if s not in self._mask_cache:
            self._mask_cache[s] = np.broadcast_to(
                self.onehot[:, :, None, None, :, s], self.kernel.shape
            )
        return self._mask_cache[s]

    def profile(self, s: int | None) -> dict[str, Any]:
        from soccer_edge.gamescript.cells import grids

        H, A, H1, A1, F = grids()
        w = self.p_cell if s is None else self.p_cell * self._script_mask(s)
        tot = float(w.sum())

        def m(f: Any) -> float | None:
            return _r(float((w * f).sum() / tot), 4) if tot > 0 else None

        ht_res = np.where(H1 > A1, 0, np.where(H1 == A1, 1, 2))
        ft_res = np.where(H > A, 0, np.where(H == A, 1, 2))
        lab = ("H", "D", "A")
        htft = {
            f"{lab[i]}/{lab[j]}": m((ht_res == i) & (ft_res == j))
            for i in range(3)
            for j in range(3)
        }
        prof: dict[str, Any] = {
            "p_home_win": m(H > A),
            "p_draw": m(H == A),
            "p_away_win": m(A > H),
            "exp_home_goals": m(H),
            "exp_away_goals": m(A),
            "p_btts": m((H > 0) & (A > 0)),
            "p_over_1_5": m(H + A > 1.5),
            "p_over_2_5": m(H + A > 2.5),
            "p_over_3_5": m(H + A > 3.5),
            "p_home_clean_sheet": m(A == 0),
            "p_away_clean_sheet": m(H == 0),
            "p_home_1plus": m(H >= 1),
            "p_home_2plus": m(H >= 2),
            "p_home_3plus": m(H >= 3),
            "p_away_1plus": m(A >= 1),
            "p_away_2plus": m(A >= 2),
            "p_away_3plus": m(A >= 3),
            "p_home_scores_first": m(F == 1),
            "p_away_scores_first": m(F == 2),
            "p_no_goal": m(H + A == 0),
            "p_level_at_half_time": m(H1 == A1),
            "ht_ft": htft,
            "typical_scores": self._typical_scores(s),
        }
        if self.requires_winner and self.adv is not None:
            prof["p_extra_time"] = m(H == A)
            prof["p_home_advances"] = _r(self._advance_given(s), 4)
        return prof

    def _advance_given(self, s: int | None) -> float | None:
        assert self.adv is not None
        t = self.T if s is None else self.T[:, :, s : s + 1]
        num = np.einsum("wha,wha,has->", self.mats, self.adv, t)
        den = np.einsum("wha,has->", self.mats, t)
        return float(num / den) if den > 0 else None

    def _typical_scores(self, s: int | None, n: int = 3) -> list[dict[str, Any]]:
        grid = self.mean_grid * (self.T[:, :, s] if s is not None else 1.0)
        tot = grid.sum()
        if tot <= 0:
            return []
        flat = np.argsort(grid, axis=None)[::-1][:n]
        g1 = grid.shape[0]
        return [
            {"score": f"{i // g1}-{i % g1}", "p": _r(grid.flat[i] / tot, 4)}
            for i in flat
            if grid.flat[i] > 0
        ]

    def temporal(self, s: int | None) -> dict[str, Any]:
        tk = temporal_kernel(self.s)
        pf = self.p_cell.sum(axis=(2, 3))  # (h, a, f)
        w = pf if s is None else pf * self.onehot[..., s]
        out: dict[str, Any] = {}
        for i, name in enumerate(TEMPORAL_FIELDS):
            v = tk[..., i]
            ok = np.isfinite(v) & (w > 0)
            tot = w[ok].sum()
            out[name] = _r(float((w[ok] * v[ok]).sum() / tot), 3) if tot > 0 else None
        return out

    # --------------------------------------------------------------------------------------- the block
    def fixture_block(self) -> dict[str, Any]:
        lo = np.quantile(self.pw_s, self.lo_q, axis=0)
        hi = np.quantile(self.pw_s, self.hi_q, axis=0)
        order = np.argsort(-self.share, kind="stable")
        block: dict[str, Any] = {
            "taxonomy_version": TAXONOMY_VERSION,
            "layer_version": SCRIPT_LAYER_VERSION,
            "scripts": list(SCRIPT_IDS),
            "shares": [_r(x) for x in self.share],
            "share_low": [_r(x, 4) for x in lo],
            "share_high": [_r(x, 4) for x in hi],
            "interval_level": self.interval_level,
            "primary": SCRIPT_IDS[int(order[0])],
            "secondary": SCRIPT_IDS[int(order[1])],
            "material_rule": MATERIAL_SHARE_RULE,
            "material_min_share": round(MATERIAL_SHARE_MIN, 6),
            "material": [
                SCRIPT_IDS[i] for i in range(K) if self.share[i] >= MATERIAL_SHARE_MIN - 1e-12
            ],
            "profiles": {SCRIPT_IDS[s]: self.profile(s) for s in range(K)},
            "overall_profile": self.profile(None),
            "temporal": {SCRIPT_IDS[s]: self.temporal(s) for s in range(K)},
            "score_grid": [[_r(x, 6) for x in row] for row in self.mean_grid],
            "first_half_share": self.s,
            "n_worlds": self.W,
            "method": (
                "exact: per-world Dixon-Coles score matrices x the world_sim_v2 timing kernel "
                "(half-time split ~ binomial(first_half_share), first scorer exchangeable); no Monte Carlo"
            ),
            "evidence": {
                "taxonomy": "DESCRIPTIVE_MODEL_DERIVED",
                "shares": "SIMULATION_DERIVED",
                "conditional_probabilities": "MODEL_DERIVED",
                "temporal_profile": "MODEL_DERIVED_TIMING_ASSUMPTION (no game-state dynamics in world_sim_v2)",
                "tactical_interpretation": "UNAVAILABLE",
            },
            "not_modelled": [
                "red cards (world_sim_v2 drops red-card dynamics)",
                "game-state effects on scoring rates (not fitted)",
            ],
        }
        if self.requires_winner and self.adv is not None:
            g1 = self.mean_grid.shape[0]
            num = np.einsum("wha,wha->ha", self.mats, self.adv)
            den = self.mats.sum(axis=0)
            block["advance_home_given_score"] = [
                [_r(num[i, j] / den[i, j], 6) if den[i, j] > 0 else None for j in range(g1)]
                for i in range(g1)
            ]
        return block


def script_definitions() -> list[dict[str, Any]]:
    return [
        {
            "script_id": s.script_id,
            "title": s.title,
            "definition": s.definition,
            "lean": s.lean,
            "tempo": s.tempo,
        }
        for s in SCRIPTS
    ]
