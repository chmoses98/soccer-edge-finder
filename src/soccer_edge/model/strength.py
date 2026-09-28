"""Dixon-Coles team-strength model with time decay and a Gaussian (Laplace) posterior.

Why this shape
--------------
* Baseline family for benchmarking (PART 7). Not assumed to be the production winner.
* Fitted as a *penalised* likelihood (MAP) with per-team Gaussian priors, so sparse teams
  (promoted, new to the window) shrink toward a prior mean and carry wider uncertainty.
* The posterior covariance is the inverse observed information at the MAP (Laplace
  approximation). That gives parameter uncertainty that is *evidence based*: it widens
  automatically when a team has few weighted matches and narrows as data accrue.

Parameters (all on the log scale)
---------------------------------
attack_i, defence_i for each team, home_advantage (gamma), rho (Dixon-Coles low-score term).
lambda_home = exp(attack_h - defence_a + gamma), mu_away = exp(attack_a - defence_h).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
from scipy.optimize import minimize

from soccer_edge.core.serialization import content_hash
from soccer_edge.core.temporal import assert_no_future_dates


@dataclass(frozen=True)
class MatchRow:
    date: date
    home: str
    away: str
    home_goals: int
    away_goals: int
    weight: float = 1.0  # extra multiplicative weight (e.g., competition strength, neutral site)


@dataclass(frozen=True)
class StrengthConfig:
    decay_per_day: float = 0.0065  # Dixon-Coles style; half-life ~107 days
    prior_sd_attack: float = 0.35
    prior_sd_defence: float = 0.35
    prior_mean_new_team_attack: float = (
        -0.15
    )  # promoted teams are, on average, weaker than the pool
    prior_mean_new_team_defence: float = -0.15
    prior_sd_new_team: float = 0.45  # wider prior for teams with little history in the window
    new_team_weighted_matches: float = (
        8.0  # below this effective-sample size use the new-team prior
    )
    home_advantage_prior_mean: float = 0.25
    home_advantage_prior_sd: float = 0.15
    rho_prior_sd: float = 0.08
    max_goals: int = 10
    version: str = "dc_laplace_v1"


@dataclass
class ParameterPosterior:
    """Gaussian approximation to the posterior over model parameters."""

    teams: list[str]
    mean: np.ndarray  # shape (P,)
    cov: np.ndarray  # shape (P, P)
    config: StrengthConfig
    fitted_through: date
    n_matches: int
    effective_matches: dict[str, float] = field(default_factory=dict)
    version: str = "dc_laplace_v1"

    # index helpers ---------------------------------------------------------------------
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

    def param_hash(self) -> str:
        return content_hash(
            {
                "teams": self.teams,
                "mean": np.round(self.mean, 8),
                "cov_diag": np.round(np.diag(self.cov), 10),
                "config": self.config.__dict__,
                "fitted_through": self.fitted_through,
            }
        )

    def team_summary(self, team: str) -> dict[str, float]:
        ia, idf = self.idx_attack(team), self.idx_defence(team)
        return {
            "attack_mean": float(self.mean[ia]),
            "attack_sd": float(np.sqrt(self.cov[ia, ia])),
            "defence_mean": float(self.mean[idf]),
            "defence_sd": float(np.sqrt(self.cov[idf, idf])),
            "effective_matches": float(self.effective_matches.get(team, 0.0)),
        }

    def expected_goals(self, home: str, away: str, *, neutral: bool = False) -> tuple[float, float]:
        m = self.mean
        gamma = 0.0 if neutral else m[self.idx_home]
        lam = float(np.exp(m[self.idx_attack(home)] - m[self.idx_defence(away)] + gamma))
        mu = float(np.exp(m[self.idx_attack(away)] - m[self.idx_defence(home)]))
        return lam, mu

    def sample(self, n: int, rng: np.random.Generator) -> np.ndarray:
        """Draw n parameter vectors from the Gaussian posterior. Shape (n, P)."""
        # cov may be slightly non-PSD numerically; use eigen clipping.
        w, v = np.linalg.eigh(self.cov)
        w = np.clip(w, 1e-10, None)
        L = v * np.sqrt(w)
        z = rng.standard_normal((n, len(self.mean)))
        return self.mean + z @ L.T

    def rates_for(
        self, params: np.ndarray, home: str, away: str, *, neutral: bool = False
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Given sampled params (n, P) return (lambda_home, mu_away, rho) arrays of shape (n,)."""
        gamma = 0.0 if neutral else params[:, self.idx_home]
        lam = np.exp(params[:, self.idx_attack(home)] - params[:, self.idx_defence(away)] + gamma)
        mu = np.exp(params[:, self.idx_attack(away)] - params[:, self.idx_defence(home)])
        rho = np.clip(params[:, self.idx_rho], -0.3, 0.3)
        return lam, mu, rho


def _tau_and_grads(x: np.ndarray, y: np.ndarray, lam: np.ndarray, mu: np.ndarray, rho: float):
    """Dixon-Coles tau and d log tau / d(lam, mu, rho). Vectorised over matches."""
    tau = np.ones_like(lam)
    dl = np.zeros_like(lam)
    dm = np.zeros_like(lam)
    dr = np.zeros_like(lam)
    m00 = (x == 0) & (y == 0)
    m01 = (x == 0) & (y == 1)
    m10 = (x == 1) & (y == 0)
    m11 = (x == 1) & (y == 1)
    tau[m00] = 1 - lam[m00] * mu[m00] * rho
    tau[m01] = 1 + lam[m01] * rho
    tau[m10] = 1 + mu[m10] * rho
    tau[m11] = 1 - rho
    tau = np.clip(tau, 1e-6, None)
    dl[m00] = -mu[m00] * rho / tau[m00]
    dm[m00] = -lam[m00] * rho / tau[m00]
    dr[m00] = -lam[m00] * mu[m00] / tau[m00]
    dl[m01] = rho / tau[m01]
    dr[m01] = lam[m01] / tau[m01]
    dm[m10] = rho / tau[m10]
    dr[m10] = mu[m10] / tau[m10]
    dr[m11] = -1.0 / tau[m11]
    return tau, dl, dm, dr


class DixonColesFitter:
    def __init__(self, config: StrengthConfig | None = None) -> None:
        self.config = config or StrengthConfig()

    def fit(
        self,
        rows: list[MatchRow],
        *,
        as_of: date,
        teams: list[str] | None = None,
        strict_point_in_time: bool = False,
    ) -> ParameterPosterior:
        cfg = self.config
        if strict_point_in_time:
            # fail closed instead of silently dropping: a caller that hands the fitter a result dated on or
            # after the decision date has a leak upstream (docs/TEMPORAL_INTEGRITY.md)
            assert_no_future_dates((r.date for r in rows), as_of, "results")
        rows = [r for r in rows if r.date < as_of]  # strictly point-in-time
        if not rows:
            raise ValueError("no matches before as_of")
        team_set = sorted(set(teams or []) | {r.home for r in rows} | {r.away for r in rows})
        tix = {t: i for i, t in enumerate(team_set)}
        n = len(team_set)
        P = 2 * n + 2

        hi = np.array([tix[r.home] for r in rows])
        ai = np.array([tix[r.away] for r in rows])
        x = np.array([min(r.home_goals, cfg.max_goals) for r in rows], dtype=float)
        y = np.array([min(r.away_goals, cfg.max_goals) for r in rows], dtype=float)
        days = np.array([(as_of - r.date).days for r in rows], dtype=float)
        w = np.exp(-cfg.decay_per_day * days) * np.array([r.weight for r in rows])

        eff = np.zeros(n)
        np.add.at(eff, hi, w)
        np.add.at(eff, ai, w)
        effective = {t: float(eff[i]) for t, i in tix.items()}

        # priors: per-team mean/sd, with a wider, weaker prior for teams with thin history
        pm = np.zeros(P)
        psd = np.zeros(P)
        for t, i in tix.items():
            new = eff[i] < cfg.new_team_weighted_matches
            pm[i] = cfg.prior_mean_new_team_attack if new else 0.0
            pm[n + i] = cfg.prior_mean_new_team_defence if new else 0.0
            psd[i] = cfg.prior_sd_new_team if new else cfg.prior_sd_attack
            psd[n + i] = cfg.prior_sd_new_team if new else cfg.prior_sd_defence
        pm[2 * n] = cfg.home_advantage_prior_mean
        psd[2 * n] = cfg.home_advantage_prior_sd
        pm[2 * n + 1] = 0.0
        psd[2 * n + 1] = cfg.rho_prior_sd

        def neg_log_post(theta: np.ndarray) -> tuple[float, np.ndarray]:
            att, dfc, gamma, rho = theta[:n], theta[n : 2 * n], theta[2 * n], theta[2 * n + 1]
            rho = float(np.clip(rho, -0.29, 0.29))
            lam = np.exp(att[hi] - dfc[ai] + gamma)
            mu = np.exp(att[ai] - dfc[hi])
            tau, dl, dm, dr = _tau_and_grads(x, y, lam, mu, rho)
            ll = w * (np.log(tau) + x * np.log(lam) - lam + y * np.log(mu) - mu)
            # gradient wrt lam, mu (then chain through exp)
            g_lam = w * (dl + x / lam - 1.0) * lam
            g_mu = w * (dm + y / mu - 1.0) * mu
            grad = np.zeros(P)
            np.add.at(grad, hi, g_lam)  # d/d att_h
            np.add.at(grad, ai, g_mu)  # d/d att_a
            np.add.at(grad, n + ai, -g_lam)  # d/d def_a
            np.add.at(grad, n + hi, -g_mu)  # d/d def_h
            grad[2 * n] = g_lam.sum()
            grad[2 * n + 1] = (w * dr).sum()
            # gaussian prior
            prior = -0.5 * np.sum(((theta - pm) / psd) ** 2)
            grad_prior = -(theta - pm) / psd**2
            # soft identifiability: mean attack = 0 and mean defence = 0 (very mild)
            prior += -0.5 * (att.sum() ** 2 + dfc.sum() ** 2) / (0.05**2) / n
            grad_prior[:n] += -att.sum() / (0.05**2) / n
            grad_prior[n : 2 * n] += -dfc.sum() / (0.05**2) / n
            return -(ll.sum() + prior), -(grad + grad_prior)

        theta0 = pm.copy()
        res = minimize(neg_log_post, theta0, jac=True, method="L-BFGS-B", options={"maxiter": 500})
        if not res.success and res.status not in (
            1,
            2,
        ):  # allow precision-loss / maxiter with sane values
            raise RuntimeError(f"Dixon-Coles fit failed: {res.message}")
        theta = res.x

        # observed information via central differences of the analytic gradient
        eps = 1e-4
        H = np.zeros((P, P))
        for j in range(P):
            e = np.zeros(P)
            e[j] = eps
            gp = neg_log_post(theta + e)[1]
            gm = neg_log_post(theta - e)[1]
            H[:, j] = (gp - gm) / (2 * eps)
        H = 0.5 * (H + H.T)
        # regularise then invert
        H += np.eye(P) * 1e-6
        try:
            cov = np.linalg.inv(H)
        except np.linalg.LinAlgError:
            cov = np.linalg.pinv(H)
        cov = 0.5 * (cov + cov.T)

        return ParameterPosterior(
            teams=team_set,
            mean=theta,
            cov=cov,
            config=cfg,
            fitted_through=as_of,
            n_matches=len(rows),
            effective_matches=effective,
            version=cfg.version,
        )
