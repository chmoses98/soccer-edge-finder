"""Research candidate: Dixon-Coles with a global scoring intercept (``dc_laplace_v1.intercept``).

Diagnosis (docs/RESEARCH_HOME_BIAS.md): ``soccer_edge.model.strength.DixonColesFitter`` has no
intercept.  Its soft identifiability penalty pins mean attack and mean defence to zero, so the
away scoring baseline is fixed near exp(0) whatever the league's real level (~1.27 away goals),
while the home-advantage term gamma absorbs the *home* scoring level (prior 0.25 +- 0.15).  The
result is a systematic under-prediction of away goals, hence too much P(home) and too little
P(away) and P(over).

This file is a copy of the frozen fitter with one extra parameter ``kappa`` (log scoring level):

    lam = exp(kappa + att_h - def_a + gamma),   mu = exp(kappa + att_a - def_h)

Nothing in ``src/`` is modified; the frozen family and its defaults are untouched.
"""

from __future__ import annotations

from datetime import date

import numpy as np
from scipy.optimize import minimize

from soccer_edge.model.strength import (
    DixonColesFitter,
    MatchRow,
    ParameterPosterior,
    StrengthConfig,
    _tau_and_grads,
)

INTERCEPT_PRIOR_MEAN = 0.15  # log(1.16): weak, roughly the league away-goal level
INTERCEPT_PRIOR_SD = 0.50


class InterceptPosterior(ParameterPosterior):
    @property
    def idx_intercept(self) -> int:
        return 2 * self.n_teams + 2

    def expected_goals(self, home: str, away: str, *, neutral: bool = False) -> tuple[float, float]:
        m = self.mean
        gamma = 0.0 if neutral else m[self.idx_home]
        k = m[self.idx_intercept]
        lam = float(np.exp(k + m[self.idx_attack(home)] - m[self.idx_defence(away)] + gamma))
        mu = float(np.exp(k + m[self.idx_attack(away)] - m[self.idx_defence(home)]))
        return lam, mu

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


class InterceptDixonColesFitter(DixonColesFitter):
    def fit(
        self, rows: list[MatchRow], *, as_of: date, teams: list[str] | None = None
    ) -> InterceptPosterior:
        cfg: StrengthConfig = self.config
        rows = [r for r in rows if r.date < as_of]
        if not rows:
            raise ValueError("no matches before as_of")
        team_set = sorted(set(teams or []) | {r.home for r in rows} | {r.away for r in rows})
        tix = {t: i for i, t in enumerate(team_set)}
        n = len(team_set)
        P = 2 * n + 3
        ik = 2 * n + 2

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
        pm[ik] = INTERCEPT_PRIOR_MEAN
        psd[ik] = INTERCEPT_PRIOR_SD

        def neg_log_post(theta: np.ndarray) -> tuple[float, np.ndarray]:
            att, dfc, gamma, rho, kap = (
                theta[:n],
                theta[n : 2 * n],
                theta[2 * n],
                theta[2 * n + 1],
                theta[ik],
            )
            rho = float(np.clip(rho, -0.29, 0.29))
            lam = np.exp(kap + att[hi] - dfc[ai] + gamma)
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
            grad[2 * n] = g_lam.sum()
            grad[2 * n + 1] = (w * dr).sum()
            grad[ik] = g_lam.sum() + g_mu.sum()
            prior = -0.5 * np.sum(((theta - pm) / psd) ** 2)
            grad_prior = -(theta - pm) / psd**2
            prior += -0.5 * (att.sum() ** 2 + dfc.sum() ** 2) / (0.05**2) / n
            grad_prior[:n] += -att.sum() / (0.05**2) / n
            grad_prior[n : 2 * n] += -dfc.sum() / (0.05**2) / n
            return -(ll.sum() + prior), -(grad + grad_prior)

        res = minimize(
            neg_log_post, pm.copy(), jac=True, method="L-BFGS-B", options={"maxiter": 500}
        )
        if not res.success and res.status not in (1, 2):
            raise RuntimeError(f"Dixon-Coles (intercept) fit failed: {res.message}")
        theta = res.x
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
        return InterceptPosterior(
            teams=team_set,
            mean=theta,
            cov=cov,
            config=cfg,
            fitted_through=as_of,
            n_matches=len(rows),
            effective_matches=effective,
            version=cfg.version,
        )
