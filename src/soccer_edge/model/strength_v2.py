"""dc_laplace_v2: Dixon-Coles MAP + Laplace posterior with a scoring intercept (remediation phase 12;
audit §D). A NEW model family; `dc_laplace_v1` (`model/strength.py`) is untouched.

    log lam_ij = kappa + a_i - d_j + gamma * (1 - neutral_ij)        log mu_ij = kappa + a_j - d_i
    sum _i a_i = sum _i d_i = 0   (hard: the fit runs in the (n-1)-dimensional centred space)
    kappa ~ N(log(weighted mean away goals of the training rows), 0.3^2)     (data-centred, weak)
    a_i, d_i ~ N(0, s^2)  (thin-history teams: N(-0.15, 0.45^2))      gamma ~ N(0.20, 0.10^2)     rho ~ N(0, 0.08^2)
    recency: e^(-xi * days)   (v1 framework; xi and s are the pre-registered grid, chosen on 2019-24)

Why the intercept fixes the away-level defect: with sum a = sum d = 0 enforced and no kappa, the away baseline is
exp(0) = 1.0 whatever the league, and gamma has to carry the *home level* instead of the home/away ratio
(audit §D, B3). kappa carries the league level; gamma is then a ratio; mu is no longer pinned.

The posterior is exposed in the full parameter space (attack n, defence n, gamma, rho, kappa; P = 2n + 3) so every
consumer that uses `idx_attack/idx_defence/idx_home/idx_rho`, `mean`, `cov`, `sample`, `rates_for`
(world generator, walk-forward loop, sim cache) works unchanged; `cov` is the reduced Laplace covariance
mapped through the centring Jacobian (rank 2(n-1)+3), and `sample` draws in the reduced space.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
from scipy.optimize import minimize

from soccer_edge.core.serialization import canonical_json
from soccer_edge.core.temporal import assert_no_future_dates
from soccer_edge.model.strength import MatchRow, _tau_and_grads

MODEL_VERSION_V2 = "dc_laplace_v2"


@dataclass(frozen=True)
class StrengthConfigV2:
    decay_per_day: float = 0.0065
    prior_sd_team: float = 0.35
    prior_mean_new_team: float = -0.15
    prior_sd_new_team: float = 0.45
    new_team_weighted_matches: float = 8.0
    home_advantage_prior_mean: float = 0.20
    home_advantage_prior_sd: float = 0.10
    rho_prior_sd: float = 0.08
    intercept_prior_sd: float = 0.30
    max_goals: int = 10
    version: str = MODEL_VERSION_V2


@dataclass
class ParameterPosteriorV2:
    teams: list[str]
    mean: np.ndarray  # full space (P = 2n + 3)
    cov: np.ndarray  # full space, rank-deficient by the two centring constraints
    reduced_mean: np.ndarray
    reduced_cov: np.ndarray
    jacobian: np.ndarray  # full = jacobian @ reduced
    config: StrengthConfigV2
    fitted_through: date
    n_matches: int
    effective_matches: dict[str, float]
    intercept_prior_mean: float
    log_likelihood: float = 0.0
    version: str = MODEL_VERSION_V2
    diagnostics: dict[str, Any] = field(default_factory=dict)

    # ---- layout (identical to v1 for the shared indices; kappa is the last parameter)
    @property
    def n_teams(self) -> int:
        return len(self.teams)

    def idx_attack(self, team: str) -> int:
        return self.teams.index(team)

    def idx_defence(self, team: str) -> int:
        return self.n_teams + self.teams.index(team)

    @property
    def idx_home(self) -> int:
        return 2 * self.n_teams

    @property
    def idx_rho(self) -> int:
        return 2 * self.n_teams + 1

    @property
    def idx_intercept(self) -> int:
        return 2 * self.n_teams + 2

    def param_hash(self) -> str:
        body = {
            "teams": self.teams,
            "mean": np.round(self.mean, 8).tolist(),
            "cov_diag": np.round(np.diag(self.cov), 10).tolist(),
            "config": self.config.__dict__,
            "fitted_through": self.fitted_through.isoformat(),
        }
        return "sha256:" + hashlib.sha256(canonical_json(body).encode()).hexdigest()

    def expected_goals(self, home: str, away: str, *, neutral: bool = False) -> tuple[float, float]:
        m = self.mean
        gamma = 0.0 if neutral else m[self.idx_home]
        k = m[self.idx_intercept]
        lam = float(np.exp(k + m[self.idx_attack(home)] - m[self.idx_defence(away)] + gamma))
        mu = float(np.exp(k + m[self.idx_attack(away)] - m[self.idx_defence(home)]))
        return lam, mu

    def sample(self, n: int, rng: np.random.Generator) -> np.ndarray:
        """Draw `n` full-space parameter vectors from the Laplace posterior (reduced-space Gaussian)."""
        vals, vecs = np.linalg.eigh(self.reduced_cov)
        vals = np.clip(vals, 1e-10, None)
        z = rng.standard_normal((n, len(self.reduced_mean)))
        red = self.reduced_mean + (z * np.sqrt(vals)) @ vecs.T
        return red @ self.jacobian.T

    def rates_for(
        self, params: np.ndarray, home: str, away: str, *, neutral: bool = False
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        gamma = 0.0 if neutral else params[:, self.idx_home]
        k = params[:, self.idx_intercept]
        lam = np.exp(
            k + params[:, self.idx_attack(home)] - params[:, self.idx_defence(away)] + gamma
        )
        mu = np.exp(k + params[:, self.idx_attack(away)] - params[:, self.idx_defence(home)])
        rho = np.clip(params[:, self.idx_rho], -0.3, 0.3)
        return lam, mu, rho


def _centring_jacobian(n: int) -> np.ndarray:
    """Map reduced [a_1..a_{n-1}, d_1..d_{n-1}, gamma, rho, kappa] to full [a_1..a_n, d_1..d_n, gamma, rho, kappa]."""
    P_red = 2 * (n - 1) + 3
    P = 2 * n + 3
    J = np.zeros((P, P_red))
    for i in range(n - 1):
        J[i, i] = 1.0
        J[n - 1, i] = -1.0  # a_n = -sum  a_i
        J[n + i, (n - 1) + i] = 1.0
        J[2 * n - 1, (n - 1) + i] = -1.0  # d_n = -sum  d_i
    J[2 * n, P_red - 3] = 1.0
    J[2 * n + 1, P_red - 2] = 1.0
    J[2 * n + 2, P_red - 1] = 1.0
    return J


class DixonColesFitterV2:
    def __init__(self, config: StrengthConfigV2 | None = None) -> None:
        self.config = config or StrengthConfigV2()

    def fit(
        self,
        rows: list[MatchRow],
        *,
        as_of: date,
        teams: list[str] | None = None,
        strict_point_in_time: bool = False,
        fix_intercept: float | None = None,
    ) -> ParameterPosteriorV2:
        """MAP + Laplace. `fix_intercept` pins kappa (used for the likelihood-ratio test of the intercept)."""
        cfg = self.config
        if strict_point_in_time:
            assert_no_future_dates((r.date for r in rows), as_of, "results")
        rows = [r for r in rows if r.date < as_of]
        if not rows:
            raise ValueError("no matches before as_of")
        team_set = sorted(set(teams or []) | {r.home for r in rows} | {r.away for r in rows})
        tix = {t: i for i, t in enumerate(team_set)}
        n = len(team_set)
        if n < 2:
            raise ValueError("need at least two teams")
        J = _centring_jacobian(n)
        P_red = J.shape[1]

        hi = np.array([tix[r.home] for r in rows])
        ai = np.array([tix[r.away] for r in rows])
        neutral = np.array([bool(getattr(r, "neutral", False)) for r in rows], dtype=float)
        x = np.array([min(r.home_goals, cfg.max_goals) for r in rows], dtype=float)
        y = np.array([min(r.away_goals, cfg.max_goals) for r in rows], dtype=float)
        days = np.array([(as_of - r.date).days for r in rows], dtype=float)
        w = np.exp(-cfg.decay_per_day * days) * np.array([r.weight for r in rows])

        eff = np.zeros(n)
        np.add.at(eff, hi, w)
        np.add.at(eff, ai, w)
        effective = {t: float(eff[i]) for t, i in tix.items()}

        # priors in the FULL space (per-team), applied through the Jacobian
        P = 2 * n + 3
        pm = np.zeros(P)
        psd = np.zeros(P)
        for t, i in tix.items():
            new = eff[i] < cfg.new_team_weighted_matches
            pm[i] = cfg.prior_mean_new_team if new else 0.0
            pm[n + i] = cfg.prior_mean_new_team if new else 0.0
            psd[i] = cfg.prior_sd_new_team if new else cfg.prior_sd_team
            psd[n + i] = cfg.prior_sd_new_team if new else cfg.prior_sd_team
        pm[2 * n] = cfg.home_advantage_prior_mean
        psd[2 * n] = cfg.home_advantage_prior_sd
        pm[2 * n + 1] = 0.0
        psd[2 * n + 1] = cfg.rho_prior_sd
        # data-centred intercept prior: the (weighted) mean away-goal level of the training rows
        away_level = float(np.sum(w * y) / max(np.sum(w), 1e-9))
        k0 = float(np.log(max(away_level, 0.2)))
        pm[2 * n + 2] = k0
        psd[2 * n + 2] = cfg.intercept_prior_sd
        ik = 2 * n + 2

        def unpack(theta_red: np.ndarray) -> np.ndarray:
            full = J @ theta_red
            if fix_intercept is not None:
                full[ik] = fix_intercept
            return full

        def neg_log_post(theta_red: np.ndarray) -> tuple[float, np.ndarray]:
            th = unpack(theta_red)
            att, dfc, gamma, rho, kap = th[:n], th[n : 2 * n], th[2 * n], th[2 * n + 1], th[ik]
            rho = float(np.clip(rho, -0.29, 0.29))
            lam = np.exp(kap + att[hi] - dfc[ai] + gamma * (1.0 - neutral))
            mu = np.exp(kap + att[ai] - dfc[hi])
            tau, dl, dm, dr = _tau_and_grads(x, y, lam, mu, rho)
            ll = w * (np.log(tau) + x * np.log(lam) - lam + y * np.log(mu) - mu)
            g_lam = w * (dl + x / lam - 1.0) * lam
            g_mu = w * (dm + y / mu - 1.0) * mu
            grad = np.zeros(P)
            np.add.at(grad, hi, g_lam)
            np.add.at(grad, ai, g_mu)
            np.add.at(grad, n + ai, -g_lam)
            np.add.at(grad, n + hi, -g_mu)
            grad[2 * n] = float(np.sum(g_lam * (1.0 - neutral)))
            grad[2 * n + 1] = float((w * dr).sum())
            grad[ik] = float(g_lam.sum() + g_mu.sum())
            prior = -0.5 * np.sum(((th - pm) / psd) ** 2)
            grad_prior = -(th - pm) / psd**2
            if fix_intercept is not None:
                grad[ik] = 0.0
                grad_prior[ik] = 0.0
            g_full = grad + grad_prior
            return -(ll.sum() + prior), -(J.T @ g_full)

        theta0 = np.zeros(P_red)
        theta0[-3] = cfg.home_advantage_prior_mean
        theta0[-1] = k0
        res = minimize(neg_log_post, theta0, jac=True, method="L-BFGS-B", options={"maxiter": 800})
        if not res.success and res.status not in (1, 2):
            raise RuntimeError(f"dc_laplace_v2 fit failed: {res.message}")
        theta_red = res.x
        eps = 1e-4
        H = np.zeros((P_red, P_red))
        for j in range(P_red):
            e = np.zeros(P_red)
            e[j] = eps
            H[:, j] = (neg_log_post(theta_red + e)[1] - neg_log_post(theta_red - e)[1]) / (2 * eps)
        H = 0.5 * (H + H.T) + np.eye(P_red) * 1e-6
        try:
            cov_red = np.linalg.inv(H)
        except np.linalg.LinAlgError:
            cov_red = np.linalg.pinv(H)
        cov_red = 0.5 * (cov_red + cov_red.T)
        if fix_intercept is not None:
            cov_red[-1, :] = 0.0
            cov_red[:, -1] = 0.0
        full_mean = unpack(theta_red)
        full_cov = J @ cov_red @ J.T
        # log-likelihood at the MAP (for the intercept likelihood-ratio diagnostic)
        th = full_mean
        att, dfc, gamma, rho, kap = th[:n], th[n : 2 * n], th[2 * n], th[2 * n + 1], th[ik]
        lam = np.exp(kap + att[hi] - dfc[ai] + gamma * (1.0 - neutral))
        mu = np.exp(kap + att[ai] - dfc[hi])
        tau, *_ = _tau_and_grads(x, y, lam, mu, float(np.clip(rho, -0.29, 0.29)))
        ll_map = float(np.sum(w * (np.log(tau) + x * np.log(lam) - lam + y * np.log(mu) - mu)))
        return ParameterPosteriorV2(
            teams=team_set,
            mean=full_mean,
            cov=full_cov,
            reduced_mean=theta_red,
            reduced_cov=cov_red,
            jacobian=J,
            config=cfg,
            fitted_through=as_of,
            n_matches=len(rows),
            effective_matches=effective,
            intercept_prior_mean=k0,
            log_likelihood=ll_map,
            version=cfg.version,
            diagnostics={
                "weighted_away_level": away_level,
                "fitted_intercept": float(full_mean[ik]),
                "fitted_gamma": float(full_mean[2 * n]),
                "fitted_rho": float(full_mean[2 * n + 1]),
                "n_neutral_rows": int(neutral.sum()),
                "optimizer_status": int(res.status),
            },
        )
