"""Hierarchical multi-league Dixon-Coles strength model (RESEARCH_ONLY).

Status: research candidate ``data_only.multi_league_v1``. Nothing here is wired into production
pricing; ``soccer_edge.model.strength`` remains the frozen benchmark family.

Why this exists
---------------
The single-league Dixon-Coles fit identifies team strengths only *relative to the league they
play in*: shifting every team of a closed league by the same constant leaves its likelihood
unchanged. Cross-league fixtures (UEFA club competitions) and league changes (promotion /
relegation) are therefore unpriceable without an explicit statement of how strong each league
is. This model adds that statement as a latent per-league offset with an honest posterior.

Model
-----
For a match between home team i and away team j (goals x, y):

    log lambda_home = att_i - def_j + home * (1 - neutral)
    log mu_away     = att_j - def_i
    P(x, y)         = tau(x, y | lambda, mu, rho) Poisson(x | lambda) Poisson(y | mu)

with the Dixon-Coles low-score correction tau. Team effects are *absolute* (shared across every
competition and division a team plays in). The league structure enters through the prior:

    att_i ~ N(L_k(i) + m_i,  s_i^2)      def_i ~ N(L_k(i) + m_i,  s_i^2)
    L_k   ~ N(l_k, prior_sd_league^2)     (prior_sd_league = 0.30 by default, l_k = 0)

where k(i) is the league team i belongs to as of the fit date. Writing att_i = a_i + L_k(i)
with a_i the league-relative effect gives the familiar additive form

    log lambda = a_i + L(league_i) - d_j - L(league_j) + home,

i.e. L_k is the league strength on the log-goal-rate scale. The difference to a literal additive
parametrisation is deliberate: because att_i is absolute, a promoted team keeps the strength it
earned in the second division and the gap L(E0) - L(E1) is then *identified* by its results
against first-division sides. Promotion/relegation is thus cross-league evidence exactly like a
UEFA fixture, and both enter through the ordinary likelihood, nothing else.

Identifiability and uncertainty
-------------------------------
* Within a closed league the direction (att_k + c, def_k + c, L_k + c) is unidentified by the
  likelihood. It is pinned only by the N(0, prior_sd_league^2) prior, so the Laplace posterior sd of
  L_k tends to prior_sd_league for a league with no cross-play and shrinks as cross-league
  matches or transferring teams accumulate. Offset uncertainty therefore *falls out of* the
  observed information rather than being asserted.
* The global level of the L's is unidentified as well (add c to everything); a soft
  sum-to-zero on the offsets makes them read as "relative to the average modelled league" and
  ``offset_difference`` reports pairwise gaps with their own posterior sd.
* Season drift is handled by the same exponential time decay as ``StrengthConfig``.

Elo-informed prior variant
--------------------------
``fit(..., elo=...)`` accepts the latest pre-match ClubElo rating per team. With
``MultiLeagueConfig.elo_gamma`` (log-goal-rate per Elo point, to be *estimated from data* with
``fit_elo_mapping`` - not asserted) the prior means become

    m_i = gamma * (Elo_i - mean Elo of league k(i))            (thin-history teams only)
    l_k = gamma * (mean Elo of league k - mean Elo of all modelled teams)   (if elo_league_prior)

so a team's prior *total* strength att_i + def_i is 2*gamma*(Elo_i - Elo_ref) above the league
mean. Elo is a results-derived quantity, so the variant remains DATA_ONLY; it is a different
information set (a third one, per the roadmap) and is versioned separately.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from math import lgamma

import numpy as np
from scipy.optimize import minimize

from soccer_edge.core.serialization import content_hash
from soccer_edge.model.strength import _tau_and_grads

OTHER_LEAGUE = "_other"


@dataclass(frozen=True)
class LeagueMatchRow:
    """A match with league context.

    ``league`` is the domestic league the match was played in (both teams belong to it) or
    ``None`` for a cross-league fixture (UEFA), in which case each team's league is taken from
    its domestic history. ``neutral`` disables the home-advantage term (finals).
    """

    date: date
    home: str
    away: str
    home_goals: int
    away_goals: int
    league: str | None
    neutral: bool = False
    weight: float = 1.0


@dataclass(frozen=True)
class MultiLeagueConfig:
    decay_per_day: float = 0.0065  # same half-life (~107 d) as dc_laplace_v1
    window_days: int = 730  # rows older than this carry weight < 0.9%; dropped for speed
    prior_sd_attack: float = 0.35  # within-league spread of team effects
    prior_sd_defence: float = 0.35
    prior_mean_new_team: float = -0.15  # thin-history teams (first appearance) sit below league
    prior_sd_new_team: float = 0.45
    new_team_weighted_matches: float = 8.0
    prior_sd_league: float = 0.30  # sd of the league offset prior, centred on 0
    league_sum_to_zero_sd: float = 0.05  # soft constraint pinning the global level
    home_advantage_prior_mean: float = 0.25
    home_advantage_prior_sd: float = 0.15
    rho_prior_sd: float = 0.08
    max_goals: int = 10
    # Elo-informed prior (variant). gamma is log goal-rate per Elo point per side; 0 disables.
    elo_gamma: float = 0.0
    elo_league_prior: bool = False
    version: str = "multi_league_v1"


@dataclass
class MultiLeaguePosterior:
    """Gaussian (Laplace) approximation to the joint posterior over team effects and offsets."""

    teams: list[str]
    leagues: list[str]
    league_of: dict[str, str]
    mean: np.ndarray
    cov: np.ndarray
    config: MultiLeagueConfig
    fitted_through: date
    n_matches: int
    n_cross_league: int
    effective_matches: dict[str, float] = field(default_factory=dict)
    cross_play_by_league: dict[str, float] = field(default_factory=dict)
    version: str = "multi_league_v1"

    # ---- index helpers ------------------------------------------------------------------
    @property
    def n_teams(self) -> int:
        return len(self.teams)

    @property
    def n_leagues(self) -> int:
        return len(self.leagues)

    def idx_attack(self, team: str) -> int:
        return self.teams.index(team)

    def idx_defence(self, team: str) -> int:
        return self.n_teams + self.teams.index(team)

    def idx_league(self, league: str) -> int:
        return 2 * self.n_teams + self.leagues.index(league)

    @property
    def idx_home(self) -> int:
        return 2 * self.n_teams + self.n_leagues

    @property
    def idx_rho(self) -> int:
        return self.idx_home + 1

    def param_hash(self) -> str:
        return content_hash(
            {
                "teams": self.teams,
                "leagues": self.leagues,
                "mean": np.round(self.mean, 8),
                "cov_diag": np.round(np.diag(self.cov), 10),
                "config": self.config.__dict__,
                "fitted_through": self.fitted_through,
            }
        )

    # ---- summaries ----------------------------------------------------------------------
    def league_offsets(self) -> dict[str, dict[str, float]]:
        out = {}
        for lg in self.leagues:
            k = self.idx_league(lg)
            out[lg] = {
                "mean": float(self.mean[k]),
                "sd": float(np.sqrt(max(self.cov[k, k], 0.0))),
                "cross_play_weight": float(self.cross_play_by_league.get(lg, 0.0)),
            }
        return out

    def offset_difference(self, league_a: str, league_b: str) -> tuple[float, float]:
        """L_a - L_b with its posterior sd (uses the covariance, not just the diagonal)."""
        a, b = self.idx_league(league_a), self.idx_league(league_b)
        var = self.cov[a, a] + self.cov[b, b] - 2 * self.cov[a, b]
        return float(self.mean[a] - self.mean[b]), float(np.sqrt(max(var, 0.0)))

    def team_summary(self, team: str) -> dict[str, float]:
        ia, idf = self.idx_attack(team), self.idx_defence(team)
        return {
            "attack_mean": float(self.mean[ia]),
            "attack_sd": float(np.sqrt(self.cov[ia, ia])),
            "defence_mean": float(self.mean[idf]),
            "defence_sd": float(np.sqrt(self.cov[idf, idf])),
            "total_mean": float(self.mean[ia] + self.mean[idf]),
            "league": self.league_of.get(team, OTHER_LEAGUE),
            "effective_matches": float(self.effective_matches.get(team, 0.0)),
        }

    def league_table(self, league: str) -> list[tuple[str, float]]:
        rows = [
            (t, float(self.mean[self.idx_attack(t)] + self.mean[self.idx_defence(t)]))
            for t in self.teams
            if self.league_of.get(t) == league
        ]
        return sorted(rows, key=lambda r: -r[1])

    # ---- prediction ---------------------------------------------------------------------
    def expected_goals(self, home: str, away: str, *, neutral: bool = False) -> tuple[float, float]:
        m = self.mean
        gamma = 0.0 if neutral else m[self.idx_home]
        lam = float(np.exp(m[self.idx_attack(home)] - m[self.idx_defence(away)] + gamma))
        mu = float(np.exp(m[self.idx_attack(away)] - m[self.idx_defence(home)]))
        return lam, mu

    def sample(self, n: int, rng: np.random.Generator) -> np.ndarray:
        w, v = np.linalg.eigh(self.cov)
        w = np.clip(w, 1e-10, None)
        L = v * np.sqrt(w)
        z = rng.standard_normal((n, len(self.mean)))
        return self.mean + z @ L.T

    def rates_for(
        self, params: np.ndarray, home: str, away: str, *, neutral: bool = False
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        gamma = 0.0 if neutral else params[:, self.idx_home]
        lam = np.exp(params[:, self.idx_attack(home)] - params[:, self.idx_defence(away)] + gamma)
        mu = np.exp(params[:, self.idx_attack(away)] - params[:, self.idx_defence(home)])
        rho = np.clip(params[:, self.idx_rho], -0.3, 0.3)
        return lam, mu, rho

    def sample_rates(
        self, n: int, rng: np.random.Generator, home: str, away: str, *, neutral: bool = False
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Posterior draws of (lambda, mu, rho) using only the sub-covariance that matters
        (attack/defence of the two teams, home, rho): exact for these marginals and much
        cheaper than sampling the full parameter vector."""
        idx = [
            self.idx_attack(home),
            self.idx_defence(home),
            self.idx_attack(away),
            self.idx_defence(away),
            self.idx_home,
            self.idx_rho,
        ]
        mu_ = self.mean[idx]
        cov = self.cov[np.ix_(idx, idx)]
        w, v = np.linalg.eigh(0.5 * (cov + cov.T))
        L = v * np.sqrt(np.clip(w, 1e-12, None))
        z = mu_ + rng.standard_normal((n, len(idx))) @ L.T
        gamma = 0.0 if neutral else z[:, 4]
        lam = np.exp(z[:, 0] - z[:, 3] + gamma)
        mu = np.exp(z[:, 2] - z[:, 1])
        rho = np.clip(z[:, 5], -0.3, 0.3)
        return lam, mu, rho


def integrated_outcome_probs(
    lam: np.ndarray, mu: np.ndarray, rho: np.ndarray, *, max_goals: int = 10, line: float = 2.5
) -> tuple[np.ndarray, float]:
    """Average Dixon-Coles 1X2 probabilities and P(total > line) over posterior draws.

    Vectorised over draws; identical in expectation to looping ``analytic.score_matrix``.
    Returns (array [home, draw, away], p_over).
    """
    k = np.arange(max_goals + 1)
    lgk = np.array([lgamma(i + 1) for i in k])
    ph = np.exp(-lam[:, None] + k[None, :] * np.log(lam[:, None]) - lgk[None, :])
    pa = np.exp(-mu[:, None] + k[None, :] * np.log(mu[:, None]) - lgk[None, :])
    m = ph[:, :, None] * pa[:, None, :]  # (S, G, G) home x away
    m[:, 0, 0] *= 1 - lam * mu * rho
    m[:, 0, 1] *= 1 + lam * rho
    m[:, 1, 0] *= 1 + mu * rho
    m[:, 1, 1] *= 1 - rho
    m = np.clip(m, 0, None)
    m /= m.sum(axis=(1, 2), keepdims=True)
    tril = np.tril(np.ones((max_goals + 1, max_goals + 1)), -1)
    eye = np.eye(max_goals + 1)
    home = (m * tril).sum(axis=(1, 2))
    draw = (m * eye).sum(axis=(1, 2))
    away = 1 - home - draw
    over = (m * (np.add.outer(k, k) > line)).sum(axis=(1, 2))
    return np.array([home.mean(), draw.mean(), away.mean()]), float(over.mean())


def fit_elo_mapping(
    home_elo: np.ndarray,
    away_elo: np.ndarray,
    home_goals: np.ndarray,
    away_goals: np.ndarray,
) -> dict[str, float]:
    """Estimate how an Elo difference maps onto goals, from data.

    Two fits are reported: (i) OLS of the goal difference on the Elo difference (the classic
    'goals per Elo point' number); (ii) a Poisson regression of each side's goals on
    gamma * (own Elo - opponent Elo) with a home term, which is the quantity the strength model
    needs (log goal-rate per Elo point per side; the team *total* att+def moves by 2*gamma).
    """
    d = home_elo - away_elo
    gd = home_goals - away_goals
    X = np.column_stack([np.ones_like(d), d])
    beta, *_ = np.linalg.lstsq(X, gd, rcond=None)
    # Poisson regression, stacked home/away rows
    own = np.concatenate([home_goals, away_goals]).astype(float)
    dif = np.concatenate([d, -d]).astype(float)
    is_home = np.concatenate([np.ones_like(d), np.zeros_like(d)]).astype(float)

    def nll(theta: np.ndarray) -> tuple[float, np.ndarray]:
        c, h, g = theta
        eta = c + h * is_home + g * dif
        lam = np.exp(eta)
        ll = own * eta - lam
        grad = np.array(
            [np.sum(own - lam), np.sum((own - lam) * is_home), np.sum((own - lam) * dif)]
        )
        return -float(ll.sum()), -grad

    res = minimize(nll, np.array([0.3, 0.25, 0.001]), jac=True, method="L-BFGS-B")
    c, h, g = res.x
    return {
        "n": len(d),
        "ols_goal_diff_per_elo_point": float(beta[1]),
        "ols_intercept_home_gd": float(beta[0]),
        "poisson_gamma_log_rate_per_elo_point": float(g),
        "poisson_home_advantage": float(h),
        "poisson_intercept": float(c),
        "total_strength_per_elo_point": float(2 * g),
    }


class MultiLeagueFitter:
    def __init__(self, config: MultiLeagueConfig | None = None) -> None:
        self.config = config or MultiLeagueConfig()

    def fit(
        self,
        rows: list[LeagueMatchRow],
        *,
        as_of: date,
        elo: dict[str, float] | None = None,
        teams: list[str] | None = None,
    ) -> MultiLeaguePosterior:
        cfg = self.config
        rows = [
            r for r in rows if r.date < as_of and (as_of - r.date).days <= cfg.window_days
        ]  # strictly point-in-time
        if not rows:
            raise ValueError("no matches before as_of")

        # league membership: the most recent domestic league of each team as of the fit date
        last_seen: dict[str, tuple[date, str]] = {}
        for r in rows:
            if r.league is None:
                continue
            for t in (r.home, r.away):
                if t not in last_seen or r.date >= last_seen[t][0]:
                    last_seen[t] = (r.date, r.league)
        team_set = sorted(set(teams or []) | {r.home for r in rows} | {r.away for r in rows})
        league_of = {t: last_seen.get(t, (None, OTHER_LEAGUE))[1] for t in team_set}
        leagues = sorted(set(league_of.values()))
        tix = {t: i for i, t in enumerate(team_set)}
        lix = {lg: i for i, lg in enumerate(leagues)}
        n, K = len(team_set), len(leagues)
        P = 2 * n + K + 2
        team_league_idx = np.array([lix[league_of[t]] for t in team_set])

        hi = np.array([tix[r.home] for r in rows])
        ai = np.array([tix[r.away] for r in rows])
        x = np.array([min(r.home_goals, cfg.max_goals) for r in rows], dtype=float)
        y = np.array([min(r.away_goals, cfg.max_goals) for r in rows], dtype=float)
        days = np.array([(as_of - r.date).days for r in rows], dtype=float)
        w = np.exp(-cfg.decay_per_day * days) * np.array([r.weight for r in rows])
        home_on = np.array([0.0 if r.neutral else 1.0 for r in rows])
        cross = np.array([r.league is None for r in rows])

        eff = np.zeros(n)
        np.add.at(eff, hi, w)
        np.add.at(eff, ai, w)
        effective = {t: float(eff[i]) for t, i in tix.items()}
        # cross-play weight per league: decayed weight of cross-league rows + rows involving a
        # team whose league differs from the league the match was played in (promotion evidence)
        cross_by_league = np.zeros(K)
        for r_i, r in enumerate(rows):
            lh, la = team_league_idx[hi[r_i]], team_league_idx[ai[r_i]]
            if cross[r_i]:
                cross_by_league[lh] += w[r_i]
                cross_by_league[la] += w[r_i]
                continue
            lm = lix[r.league]
            for lt in (lh, la):
                if lt != lm:  # a team that has since moved league: its old rows link the two
                    cross_by_league[lt] += w[r_i]
                    cross_by_league[lm] += w[r_i]

        # ---- priors -----------------------------------------------------------------------
        # team effects: mean L_k(i) + m_i, sd s_i; thin-history teams get the wider new-team prior
        m_team = np.zeros(n)
        s_att = np.full(n, cfg.prior_sd_attack)
        s_def = np.full(n, cfg.prior_sd_defence)
        new = eff < cfg.new_team_weighted_matches
        m_team[new] = cfg.prior_mean_new_team
        s_att[new] = cfg.prior_sd_new_team
        s_def[new] = cfg.prior_sd_new_team
        l_prior = np.zeros(K)
        if elo and cfg.elo_gamma != 0.0:
            elo_vec = np.array([elo.get(t, np.nan) for t in team_set])
            have = ~np.isnan(elo_vec)
            league_mean_elo = np.full(K, np.nan)
            for k in range(K):
                sel = have & (team_league_idx == k)
                if sel.sum() >= 3:
                    league_mean_elo[k] = elo_vec[sel].mean()
            for i in range(n):
                k = team_league_idx[i]
                if new[i] and have[i] and not np.isnan(league_mean_elo[k]):
                    m_team[i] = cfg.elo_gamma * (elo_vec[i] - league_mean_elo[k])
            if cfg.elo_league_prior and have.sum() >= 3:
                overall = elo_vec[have].mean()
                for k in range(K):
                    if not np.isnan(league_mean_elo[k]):
                        l_prior[k] = cfg.elo_gamma * (league_mean_elo[k] - overall)
                l_prior -= l_prior.mean()  # keep the offsets centred (sum-to-zero prior)
        sd_L = cfg.prior_sd_league
        pm_home, psd_home = cfg.home_advantage_prior_mean, cfg.home_advantage_prior_sd
        psd_rho = cfg.rho_prior_sd
        sum0 = cfg.league_sum_to_zero_sd

        def neg_log_post(theta: np.ndarray) -> tuple[float, np.ndarray]:
            att, dfc = theta[:n], theta[n : 2 * n]
            L = theta[2 * n : 2 * n + K]
            gamma, rho = theta[2 * n + K], theta[2 * n + K + 1]
            rho = float(np.clip(rho, -0.29, 0.29))
            lam = np.exp(att[hi] - dfc[ai] + gamma * home_on)
            mu = np.exp(att[ai] - dfc[hi])
            tau, dl, dm, dr = _tau_and_grads(x, y, lam, mu, rho)
            ll = w * (np.log(tau) + x * np.log(lam) - lam + y * np.log(mu) - mu)
            g_lam = w * (dl + x / lam - 1.0) * lam
            g_mu = w * (dm + y / mu - 1.0) * mu
            grad = np.zeros(P)
            np.add.at(grad, hi, g_lam)
            np.add.at(grad, ai, g_mu)
            np.add.at(grad, n + ai, -g_lam)
            np.add.at(grad, n + hi, -g_mu)
            grad[2 * n + K] = (g_lam * home_on).sum()
            grad[2 * n + K + 1] = (w * dr).sum()
            # hierarchical prior on team effects around their league offset
            Lt = L[team_league_idx]
            ra = (att - Lt - m_team) / s_att
            rd = (dfc - Lt - m_team) / s_def
            prior = -0.5 * (np.sum(ra**2) + np.sum(rd**2))
            gp = np.zeros(P)
            gp[:n] = -ra / s_att
            gp[n : 2 * n] = -rd / s_def
            gL = np.zeros(K)
            np.add.at(gL, team_league_idx, ra / s_att + rd / s_def)
            # league offsets: N(l_prior, sd_L^2) plus soft sum-to-zero
            prior += -0.5 * np.sum(((L - l_prior) / sd_L) ** 2)
            gL += -(L - l_prior) / sd_L**2
            prior += -0.5 * (L.sum() ** 2) / sum0**2 / K
            gL += -L.sum() / sum0**2 / K
            gp[2 * n : 2 * n + K] = gL
            prior += -0.5 * ((gamma - pm_home) / psd_home) ** 2 - 0.5 * (rho / psd_rho) ** 2
            gp[2 * n + K] = -(gamma - pm_home) / psd_home**2
            gp[2 * n + K + 1] = -rho / psd_rho**2
            return -(ll.sum() + prior), -(grad + gp)

        theta0 = np.zeros(P)
        theta0[:n] = l_prior[team_league_idx] + m_team
        theta0[n : 2 * n] = l_prior[team_league_idx] + m_team
        theta0[2 * n : 2 * n + K] = l_prior
        theta0[2 * n + K] = pm_home
        res = minimize(neg_log_post, theta0, jac=True, method="L-BFGS-B", options={"maxiter": 800})
        if not res.success and res.status not in (1, 2):
            raise RuntimeError(f"multi-league fit failed: {res.message}")
        theta = res.x

        # observed information from central differences of the analytic gradient
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

        return MultiLeaguePosterior(
            teams=team_set,
            leagues=leagues,
            league_of=league_of,
            mean=theta,
            cov=cov,
            config=cfg,
            fitted_through=as_of,
            n_matches=len(rows),
            n_cross_league=int(cross.sum()),
            effective_matches=effective,
            cross_play_by_league={lg: float(cross_by_league[lix[lg]]) for lg in leagues},
            version=cfg.version,
        )


def latest_league_by_team(rows: list[LeagueMatchRow], as_of: date) -> dict[str, str]:
    """Convenience: each team's most recent domestic league strictly before ``as_of``."""
    seen: dict[str, tuple[date, str]] = {}
    for r in rows:
        if r.league is None or r.date >= as_of:
            continue
        for t in (r.home, r.away):
            if t not in seen or r.date >= seen[t][0]:
                seen[t] = (r.date, r.league)
    return {t: v[1] for t, v in seen.items()}


def rows_by_league(rows: list[LeagueMatchRow]) -> dict[str, list[LeagueMatchRow]]:
    out: dict[str, list[LeagueMatchRow]] = defaultdict(list)
    for r in rows:
        out[r.league or OTHER_LEAGUE].append(r)
    return out
