"""intl_hier_v1: hierarchical international Dixon-Coles (remediation phase 17; audit §E).

Why: the production "international pool" is the club fitter on ~1,000 ESPN results with club priors, a
107-day half-life, friendlies at full weight, neutral venues dropped and a sum-to-zero over ~200 nations,
so a minnow shrinks toward the *average national team* (San Marino 25% to beat Albania). The shrinkage
target was wrong, not its strength. Here every effect is a parameter with a prior and a likelihood:

    log lam = kappa + a_h - d_a + gamma_T * home_h        log mu = kappa + a_a - d_h + gamma_T * home_a
    a_i = A_conf(i) + beta_a * e_i(t) + alpha_i           d_i = D_conf(i) + beta_d * e_i(t) + delta_i

* e_i(t): standardised point-in-time Elo computed from the same archive (never an external snapshot);
* A_c, D_c ~ N(0, 0.30^2) with a soft sum-to-zero over confederations (identified only by
  cross-confederation matches; the prior carries the rest);
* alpha_i, delta_i ~ N(0, s_T^2), s_T = 0.20, inflated x1.5 for teams with < 10 weighted matches
  (sparse teams shrink toward A_conf + beta * Elo: the right centre);
* gamma_T by match type T in {competitive, friendly}; home_x = 1 only when x plays at home and the venue
  is not neutral; friendlies enter the likelihood with a FITTED weight w_friendly (tempering; chosen by
  walk-forward on the selection window, never a heuristic); recency half-life in years (grid);
* rho ~ N(0, 0.08^2) (Dixon-Coles low-score correction).

No minnow penalty and no rank override exist anywhere in this file.

Connectivity: per fit, the match graph of the weighted window is analysed. A team outside the giant
component, or with fewer than 10 weighted matches, is LOW_CONNECTIVITY for every prediction; a team with
< 3 distinct cross-confederation opponents in the last 4 years is LOW_CONNECTIVITY for cross-confederation
predictions only. `prediction_flags(home, away)` gives the reasons for a fixture; flagged fixtures must
never surface as shadows.

Uncertainty: MAP + Laplace when `laplace=True` (the observed information by finite differences of the
analytic gradient, ~500 parameters); the walk-forward research fits use `laplace=False` (MAP only, the
outcome probabilities barely move under posterior averaging) and the production fit uses the full
posterior so sparse teams carry wider intervals automatically.
"""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
from scipy.optimize import minimize

from soccer_edge.core.serialization import canonical_json
from soccer_edge.core.temporal import assert_no_future_dates
from soccer_edge.model.strength import _tau_and_grads

MODEL_VERSION = "intl_hier_v1"


@dataclass(frozen=True)
class IntlMatchRow:
    date: date
    home: str
    away: str
    home_goals: int
    away_goals: int
    neutral: bool
    competitive: bool
    home_conf: str
    away_conf: str
    home_elo: float  # point-in-time Elo BEFORE the match
    away_elo: float


@dataclass(frozen=True)
class IntlHierConfig:
    half_life_years: float = 2.0
    friendly_weight: float = 0.6
    prior_sd_conf: float = 0.30
    prior_sd_team: float = 0.20
    sparse_team_weighted_matches: float = 10.0
    sparse_inflation: float = 1.5
    prior_sd_elo_slope: float = 1.0
    home_advantage_prior_mean: float = 0.20
    home_advantage_prior_sd: float = 0.10
    intercept_prior_sd: float = 0.30
    rho_prior_sd: float = 0.08
    lookback_years: float = 8.0
    max_goals: int = 10
    low_connectivity_min_cross_conf_opponents: int = 3
    low_connectivity_window_years: float = 4.0
    version: str = MODEL_VERSION


@dataclass
class IntlHierPosterior:
    teams: list[str]
    confs: list[str]
    mean: np.ndarray
    cov: np.ndarray | None
    config: IntlHierConfig
    fitted_through: date
    n_matches: int
    effective_matches: dict[str, float]
    team_conf: dict[str, str]
    team_elo_std: dict[str, float]  # standardised latest Elo per team at fit time
    elo_mean: float
    elo_sd: float
    low_connectivity: dict[str, str]  # team -> reason
    log_likelihood: float = 0.0
    version: str = MODEL_VERSION
    diagnostics: dict[str, Any] = field(default_factory=dict)

    # layout: alpha(n), delta(n), A(C), D(C), beta_a, beta_d, gamma_comp, gamma_friendly, rho, kappa
    @property
    def n_teams(self) -> int:
        return len(self.teams)

    @property
    def n_confs(self) -> int:
        return len(self.confs)

    def idx_alpha(self, t: str) -> int:
        return self.teams.index(t)

    def idx_delta(self, t: str) -> int:
        return self.n_teams + self.teams.index(t)

    def idx_conf_attack(self, c: str) -> int:
        return 2 * self.n_teams + self.confs.index(c)

    def idx_conf_defence(self, c: str) -> int:
        return 2 * self.n_teams + self.n_confs + self.confs.index(c)

    @property
    def idx_beta_a(self) -> int:
        return 2 * self.n_teams + 2 * self.n_confs

    @property
    def idx_beta_d(self) -> int:
        return self.idx_beta_a + 1

    @property
    def idx_gamma_comp(self) -> int:
        return self.idx_beta_a + 2

    @property
    def idx_gamma_friendly(self) -> int:
        return self.idx_beta_a + 3

    @property
    def idx_rho(self) -> int:
        return self.idx_beta_a + 4

    @property
    def idx_intercept(self) -> int:
        return self.idx_beta_a + 5

    @property
    def idx_home(self) -> int:  # world-generator compatibility (competitive home advantage)
        return self.idx_gamma_comp

    def prediction_flags(self, home: str, away: str) -> list[str]:
        """LOW_CONNECTIVITY reasons that apply to THIS fixture (empty = the prediction may be used).
        Confederation level offsets are identified only by cross-confederation matches, so the
        cross-confederation-opponent rule applies to cross-confederation fixtures; sparse history and
        isolation from the giant component apply to every fixture."""
        out: list[str] = []
        cross = self.team_conf.get(home) != self.team_conf.get(away)
        for t in (home, away):
            if t not in self.teams:
                out.append(f"{t}:unknown_team")
                continue
            if self.effective_matches.get(t, 0.0) < self.config.sparse_team_weighted_matches:
                out.append(f"{t}:sparse_history")
            reason = self.low_connectivity.get(t)
            if reason is None:
                continue
            if reason.startswith("cross_conf_only:"):
                if cross:
                    out.append(f"{t}:{reason.split(':', 1)[1]}")
            else:
                out.append(f"{t}:{reason}")
        return out

    def param_hash(self) -> str:
        body = {
            "teams": self.teams,
            "mean": np.round(self.mean, 8).tolist(),
            "cfg": self.config.__dict__,
            "d": self.fitted_through.isoformat(),
        }
        return "sha256:" + hashlib.sha256(canonical_json(body).encode()).hexdigest()

    def _strength(self, params: np.ndarray, team: str) -> tuple[np.ndarray, np.ndarray]:
        c = self.team_conf.get(team)
        e = self.team_elo_std.get(team, 0.0)
        if c is None or team not in self.teams:
            # unknown team: prior centre of an unknown confederation is zero, Elo unknown -> 0
            a = np.zeros(params.shape[0])
            d = np.zeros(params.shape[0])
            return a, d
        a = (
            params[:, self.idx_conf_attack(c)]
            + params[:, self.idx_beta_a] * e
            + params[:, self.idx_alpha(team)]
        )
        d = (
            params[:, self.idx_conf_defence(c)]
            + params[:, self.idx_beta_d] * e
            + params[:, self.idx_delta(team)]
        )
        return a, d

    def rates_for(
        self,
        params: np.ndarray,
        home: str,
        away: str,
        *,
        neutral: bool = False,
        competitive: bool = True,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        ah, dh = self._strength(params, home)
        aa, da = self._strength(params, away)
        g = params[:, self.idx_gamma_comp if competitive else self.idx_gamma_friendly]
        k = params[:, self.idx_intercept]
        lam = np.exp(k + ah - da + (0.0 if neutral else g))
        mu = np.exp(k + aa - dh)
        rho = np.clip(params[:, self.idx_rho], -0.3, 0.3)
        return lam, mu, rho

    def expected_goals(
        self, home: str, away: str, *, neutral: bool = False, competitive: bool = True
    ) -> tuple[float, float]:
        lam, mu, _ = self.rates_for(
            self.mean[None, :], home, away, neutral=neutral, competitive=competitive
        )
        return float(lam[0]), float(mu[0])

    def sample(self, n: int, rng: np.random.Generator) -> np.ndarray:
        if self.cov is None:
            return np.repeat(self.mean[None, :], n, axis=0)
        vals, vecs = np.linalg.eigh(self.cov)
        vals = np.clip(vals, 1e-10, None)
        z = rng.standard_normal((n, len(self.mean)))
        return self.mean + (z * np.sqrt(vals)) @ vecs.T


def connectivity_flags(
    rows: list[IntlMatchRow],
    teams: list[str],
    team_conf: dict[str, str],
    cfg: IntlHierConfig,
    as_of: date,
) -> dict[str, str]:
    """LOW_CONNECTIVITY: outside the giant component of the lookback match graph, or fewer than N distinct
    cross-confederation opponents in the last `low_connectivity_window_years`."""
    adj: dict[str, set[str]] = defaultdict(set)
    cross: dict[str, set[str]] = defaultdict(set)
    win_start = date.fromordinal(
        as_of.toordinal() - int(365.25 * cfg.low_connectivity_window_years)
    )
    for r in rows:
        adj[r.home].add(r.away)
        adj[r.away].add(r.home)
        if r.date >= win_start and team_conf.get(r.home) != team_conf.get(r.away):
            cross[r.home].add(r.away)
            cross[r.away].add(r.home)
    # giant component
    seen: set[str] = set()
    best: set[str] = set()
    for t in teams:
        if t in seen or t not in adj:
            continue
        comp = set()
        stack = [t]
        while stack:
            u = stack.pop()
            if u in comp:
                continue
            comp.add(u)
            stack.extend(adj[u] - comp)
        seen |= comp
        if len(comp) > len(best):
            best = comp
    flags: dict[str, str] = {}
    for t in teams:
        if t not in best:
            flags[t] = "outside_giant_component"
        elif len(cross.get(t, ())) < cfg.low_connectivity_min_cross_conf_opponents:
            flags[t] = (
                "cross_conf_only:cross_confederation_opponents"
                f"<{cfg.low_connectivity_min_cross_conf_opponents}"
            )
    return flags


class IntlHierFitter:
    def __init__(self, config: IntlHierConfig | None = None) -> None:
        self.config = config or IntlHierConfig()

    def fit(
        self,
        rows: list[IntlMatchRow],
        *,
        as_of: date,
        teams: list[str] | None = None,
        laplace: bool = False,
        strict_point_in_time: bool = False,
    ) -> IntlHierPosterior:
        cfg = self.config
        if strict_point_in_time:
            assert_no_future_dates((r.date for r in rows), as_of, "results")
        lb = date.fromordinal(as_of.toordinal() - int(365.25 * cfg.lookback_years))
        rows = [r for r in rows if lb <= r.date < as_of]
        if len(rows) < 50:
            raise ValueError(f"too few matches to fit ({len(rows)})")
        team_conf: dict[str, str] = {}
        latest_elo: dict[str, tuple[date, float]] = {}
        for r in rows:
            team_conf[r.home] = r.home_conf
            team_conf[r.away] = r.away_conf
            for t, e in ((r.home, r.home_elo), (r.away, r.away_elo)):
                if t not in latest_elo or r.date >= latest_elo[t][0]:
                    latest_elo[t] = (r.date, e)
        team_set = sorted(set(teams or []) | set(team_conf))
        for t in team_set:
            team_conf.setdefault(t, "UNKNOWN")
        confs = sorted(set(team_conf.values()))
        n, C = len(team_set), len(confs)
        tix = {t: i for i, t in enumerate(team_set)}
        cix = {c: i for i, c in enumerate(confs)}
        P = 2 * n + 2 * C + 6
        ib_a, ib_d, ig_c, ig_f, ir, ik = (2 * n + 2 * C + j for j in range(6))

        hi = np.array([tix[r.home] for r in rows])
        ai = np.array([tix[r.away] for r in rows])
        hc = np.array([cix[team_conf[r.home]] for r in rows])
        ac = np.array([cix[team_conf[r.away]] for r in rows])
        x = np.array([min(r.home_goals, cfg.max_goals) for r in rows], dtype=float)
        y = np.array([min(r.away_goals, cfg.max_goals) for r in rows], dtype=float)
        neutral = np.array([r.neutral for r in rows], dtype=float)
        comp = np.array([r.competitive for r in rows], dtype=float)
        # standardised Elo per match side (point-in-time), standardisation from the fit rows
        all_elo = np.concatenate([[r.home_elo for r in rows], [r.away_elo for r in rows]])
        e_mean, e_sd = float(all_elo.mean()), float(all_elo.std() or 1.0)
        eh = (np.array([r.home_elo for r in rows]) - e_mean) / e_sd
        ea = (np.array([r.away_elo for r in rows]) - e_mean) / e_sd
        days = np.array([(as_of - r.date).days for r in rows], dtype=float)
        decay = math.log(2) / (365.25 * cfg.half_life_years)
        w = np.exp(-decay * days) * np.where(comp > 0, 1.0, cfg.friendly_weight)

        eff = np.zeros(n)
        np.add.at(eff, hi, w)
        np.add.at(eff, ai, w)
        effective = {t: float(eff[i]) for t, i in tix.items()}

        pm = np.zeros(P)
        psd = np.zeros(P)
        for t, i in tix.items():
            sd_t = cfg.prior_sd_team * (
                cfg.sparse_inflation if eff[i] < cfg.sparse_team_weighted_matches else 1.0
            )
            psd[i] = sd_t
            psd[n + i] = sd_t
        psd[2 * n : 2 * n + 2 * C] = cfg.prior_sd_conf
        psd[ib_a] = psd[ib_d] = cfg.prior_sd_elo_slope
        pm[ig_c] = pm[ig_f] = cfg.home_advantage_prior_mean
        psd[ig_c] = psd[ig_f] = cfg.home_advantage_prior_sd
        psd[ir] = cfg.rho_prior_sd
        away_level = float(np.sum(w * y) / max(np.sum(w), 1e-9))
        k0 = math.log(max(away_level, 0.2))
        pm[ik] = k0
        psd[ik] = cfg.intercept_prior_sd
        conf_pen = 1.0 / (0.05**2) / max(C, 1)

        def neg_log_post(theta: np.ndarray) -> tuple[float, np.ndarray]:
            al, de = theta[:n], theta[n : 2 * n]
            A, D = theta[2 * n : 2 * n + C], theta[2 * n + C : 2 * n + 2 * C]
            ba, bd, gc, gf, rho, kap = (
                theta[ib_a],
                theta[ib_d],
                theta[ig_c],
                theta[ig_f],
                theta[ir],
                theta[ik],
            )
            rho = float(np.clip(rho, -0.29, 0.29))
            a_h = A[hc] + ba * eh + al[hi]
            d_h = D[hc] + bd * eh + de[hi]
            a_a = A[ac] + ba * ea + al[ai]
            d_a = D[ac] + bd * ea + de[ai]
            g = np.where(comp > 0, gc, gf) * (1.0 - neutral)
            lam = np.exp(kap + a_h - d_a + g)
            mu = np.exp(kap + a_a - d_h)
            tau, dl, dm, dr = _tau_and_grads(x, y, lam, mu, rho)
            ll = w * (np.log(tau) + x * np.log(lam) - lam + y * np.log(mu) - mu)
            g_lam = w * (dl + x / lam - 1.0) * lam
            g_mu = w * (dm + y / mu - 1.0) * mu
            grad = np.zeros(P)
            np.add.at(grad, hi, g_lam)  # alpha_h via a_h
            np.add.at(grad, ai, g_mu)  # alpha_a via a_a
            np.add.at(grad, n + ai, -g_lam)  # delta_a via d_a
            np.add.at(grad, n + hi, -g_mu)  # delta_h via d_h
            np.add.at(grad, 2 * n + hc, g_lam)  # A_conf(home)
            np.add.at(grad, 2 * n + ac, g_mu)  # A_conf(away)
            np.add.at(grad, 2 * n + C + ac, -g_lam)  # D_conf(away)
            np.add.at(grad, 2 * n + C + hc, -g_mu)  # D_conf(home)
            grad[ib_a] = float(np.sum(g_lam * eh + g_mu * ea))
            grad[ib_d] = float(np.sum(-g_lam * ea - g_mu * eh))
            grad[ig_c] = float(np.sum(g_lam * comp * (1.0 - neutral)))
            grad[ig_f] = float(np.sum(g_lam * (1.0 - comp) * (1.0 - neutral)))
            grad[ir] = float((w * dr).sum())
            grad[ik] = float(g_lam.sum() + g_mu.sum())
            prior = -0.5 * np.sum(((theta - pm) / psd) ** 2)
            grad_prior = -(theta - pm) / psd**2
            # soft sum-to-zero on confederation offsets (global level lives in kappa)
            prior += -0.5 * (A.sum() ** 2 + D.sum() ** 2) * conf_pen
            grad_prior[2 * n : 2 * n + C] += -A.sum() * conf_pen
            grad_prior[2 * n + C : 2 * n + 2 * C] += -D.sum() * conf_pen
            return -(ll.sum() + prior), -(grad + grad_prior)

        theta0 = pm.copy()
        res = minimize(neg_log_post, theta0, jac=True, method="L-BFGS-B", options={"maxiter": 1000})
        if not res.success and res.status not in (1, 2):
            raise RuntimeError(f"intl_hier_v1 fit failed: {res.message}")
        theta = res.x
        cov = None
        if laplace:
            eps = 1e-4
            H = np.zeros((P, P))
            for j in range(P):
                e = np.zeros(P)
                e[j] = eps
                H[:, j] = (neg_log_post(theta + e)[1] - neg_log_post(theta - e)[1]) / (2 * eps)
            H = 0.5 * (H + H.T) + np.eye(P) * 1e-6
            try:
                cov = np.linalg.inv(H)
            except np.linalg.LinAlgError:
                cov = np.linalg.pinv(H)
            cov = 0.5 * (cov + cov.T)
        team_elo_std = {
            t: (latest_elo[t][1] - e_mean) / e_sd if t in latest_elo else 0.0 for t in team_set
        }
        flags = connectivity_flags(rows, team_set, team_conf, cfg, as_of)
        ll_map = -neg_log_post(theta)[0]
        return IntlHierPosterior(
            teams=team_set,
            confs=confs,
            mean=theta,
            cov=cov,
            config=cfg,
            fitted_through=as_of,
            n_matches=len(rows),
            effective_matches=effective,
            team_conf=team_conf,
            team_elo_std=team_elo_std,
            elo_mean=e_mean,
            elo_sd=e_sd,
            low_connectivity=flags,
            log_likelihood=float(ll_map),
            version=cfg.version,
            diagnostics={
                "kappa": float(theta[ik]),
                "gamma_competitive": float(theta[ig_c]),
                "gamma_friendly": float(theta[ig_f]),
                "beta_attack": float(theta[ib_a]),
                "beta_defence": float(theta[ib_d]),
                "rho": float(theta[ir]),
                "conf_attack": {c: float(theta[2 * n + i]) for c, i in cix.items()},
                "conf_defence": {c: float(theta[2 * n + C + i]) for c, i in cix.items()},
                "n_low_connectivity": len(flags),
                "optimizer_status": int(res.status),
                "n_rows": len(rows),
            },
        )
