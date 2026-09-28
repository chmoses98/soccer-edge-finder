"""Walk-forward recalibration research for the uncertainty layer (protocol `recalibration_v1`).

Question
--------
The DATA_ONLY 80% posterior interval on P(home) (Dixon-Coles Laplace posterior integrated over
100 posterior samples, as in `research/walk_forward.py`) contains the de-vigged Bet365 probability
in ~93% of matches, which *looks* over-dispersed. The market is not ground truth, so this script
asks the realised outcomes first and the market second, and estimates candidate corrections
strictly walk-forward (fit on seasons < S, apply to S).

What can and cannot be learned from outcomes
-------------------------------------------
A single Bernoulli outcome cannot split the predictive variance of y into aleatoric and epistemic
parts: E[(y - p_hat)^2] = p_hat (1 - p_hat) under the model for *any* posterior width. PIT
histograms and log-loss dispersion of the per-match predictive are therefore reported but are
expected to be weakly sensitive to the posterior scale. The outcome-based test with power is a
*grouped* posterior-predictive check: a team's parameter error persists across its matches inside
a short window, so the model implies a specific covariance between the goal residuals of the same
team in consecutive matches. The cross-match moment
    sum_g sum_{i != j in g} r_i r_j   vs   k^2 * sum_g sum_{i != j in g} Cov_model(lam_i, lam_j)
identifies k (the multiplier on the posterior sd) without any assumption about aleatoric
over-dispersion (which only enters the diagonal). Because the posterior is refit weekly, the
forecast for match j has usually already learned from match i: under a correctly calibrated
Bayesian model sequential forecast errors are then *uncorrelated* (innovation whiteness), a too-wide
posterior over-reacts (negative cross products) and a too-narrow one under-reacts (positive). The
moment condition is therefore
    E[r_i r_j] = k^2 M_ij - 1{refit between i and j} M_ij,
where M is the model's covariance of the expected-goal rates at k = 1, so k^2 = (num + den_upd) /
den_all. Groups = (team, season, 28-day window), goals for and goals against, residuals de-meaned by
the league-level mean residual of *earlier* seasons.

PRE-STATED DECISION RULE (written before any number below was computed)
-----------------------------------------------------------------------
R1  Outcome-based evidence is primary: k_hat = pooled cross-term moment estimator on the scored
    seasons (2018-19 .. 2025-26), cluster bootstrap 95% CI over (league, season, team).
R2  A change from k = 1 is supported only if the 95% CI excludes 1.0 AND the per-season k_hat lies
    on the same side of 1.0 as the pooled estimate in at least 5 of the 7 aligned seasons.
R3  Among supported structures prefer the global scale; a league- or region-specific scale is
    adopted only if its walk-forward out-of-sample grouped Gaussian log score beats the global
    candidate in >= 5 of 7 seasons and overall (paired bootstrap 95% CI over groups excluding 0).
R4  The world-layer shared log-rate inflation (sigma_model 0.05, sigma_environment 0.03) is judged
    by the totals PIT variance (nominal 1/12) and totals log loss; a change is supported only if
    the current setting's PIT-variance z exceeds |2| and the alternative brings it inside |2|.
R5  The market-inside rate is reported and must move toward 80% under any adopted candidate
    (sanity), but it is not targeted and cannot by itself justify a change.
R6  Guardrail: an adopted candidate must not worsen the overall 1X2 log loss of the integrated
    predictive by more than 0.001.
If R2 fails the decision is "no change"; the outcome-based and market-implied scales are recorded
for the roadmap. Horizon-specific scales cannot be studied historically: the redistribution holds
one pre-match Bet365 snapshot per match and no lineup/time-to-kickoff information.

Run:  PYTHONPATH=src python research/recalibration.py --matches-csv data/cache/Matches.csv
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
from scipy.special import gammaln

from soccer_edge.core.serialization import content_hash, write_json
from soccer_edge.evaluation.metrics import (
    bootstrap_mean_ci,
    expected_calibration_error,
    interval_calibration,
    log_loss,
    multiclass_brier,
    multiclass_log_loss,
)
from soccer_edge.families.base import devig_proportional
from soccer_edge.identity.registry import AliasRegistry
from soccer_edge.model.strength import (
    DixonColesFitter,
    MatchRow,
    ParameterPosterior,
    StrengthConfig,
)
from soccer_edge.providers.club_football_data import ClubFootballDataProvider, HistoricalMatch

REPO = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = "recalibration_v1"
CACHE_PATH = REPO / "data" / "cache" / "recalibration_cache_v1.npz"
# worlds_v1: env and model inflation are shared by both teams -> one log-normal shift with this sd
WORLDS_V1_SIGMA_SHARED = float(np.sqrt(0.05**2 + 0.03**2))
K_GRID = tuple(round(x, 2) for x in np.arange(0.3, 1.55, 0.1))
NORMAL_80 = 1.2815515655446004


# ----------------------------------------------------------------------------------------------
# Pure functions (unit-tested without the dataset)
# ----------------------------------------------------------------------------------------------
def dc_probs_vec(
    lam: np.ndarray, mu: np.ndarray, rho: np.ndarray, max_goals: int = 10
) -> tuple[np.ndarray, np.ndarray]:
    """Vectorised Dixon-Coles score matrix -> ((n,3) [home,draw,away], (n,2*max_goals+1) total pmf).

    Matches `soccer_edge.model.analytic.score_matrix` + `outcome_probs` row by row.
    """
    lam = np.asarray(lam, float)
    mu = np.asarray(mu, float)
    rho = np.asarray(rho, float)
    i = np.arange(max_goals + 1)
    lf = gammaln(i + 1)
    ph = np.exp(-lam[:, None] + i[None, :] * np.log(lam)[:, None] - lf[None, :])
    pa = np.exp(-mu[:, None] + i[None, :] * np.log(mu)[:, None] - lf[None, :])
    m = ph[:, :, None] * pa[:, None, :]
    m[:, 0, 0] *= 1 - lam * mu * rho
    m[:, 0, 1] *= 1 + lam * rho
    m[:, 1, 0] *= 1 + mu * rho
    m[:, 1, 1] *= 1 - rho
    m = np.clip(m, 0, None)
    m /= m.sum(axis=(1, 2), keepdims=True)
    tri = np.tril(np.ones((max_goals + 1, max_goals + 1)), -1)
    home = (m * tri[None]).sum(axis=(1, 2))
    draw = np.einsum("nii->n", m)
    away = 1.0 - home - draw
    tot_idx = np.add.outer(i, i).ravel()
    S = np.zeros((len(tot_idx), 2 * max_goals + 1))
    S[np.arange(len(tot_idx)), tot_idx] = 1.0
    tot = m.reshape(len(lam), -1) @ S
    return np.stack([home, draw, away], axis=1), tot


def scaled_rates(
    base: np.ndarray, dev: np.ndarray, k: np.ndarray, shared_shift: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Apply a posterior-sd multiplier `k` (per match) to cached posterior deviations.

    base  (n,3): [log lam_mean, log mu_mean, rho_mean] at the posterior mean
    dev   (n,S,3): sampled deviations of [log lam, log mu, rho] from the mean (k = 1)
    k     (n,): multiplier on the parameter sd (log rates are linear in the parameters, so
          theta_mean + k * (theta - theta_mean) maps exactly to base + k * dev)
    shared_shift (n,S): additive log-rate shift common to both teams (world-layer inflation)
    Returns lam, mu, rho arrays of shape (n,S).
    """
    kk = k[:, None]
    loglam = base[:, 0:1] + kk * dev[:, :, 0] + shared_shift
    logmu = base[:, 1:2] + kk * dev[:, :, 1] + shared_shift
    rho = np.clip(base[:, 2:3] + kk * dev[:, :, 2], -0.3, 0.3)
    return np.exp(loglam), np.exp(logmu), rho


def randomized_pit(pmf: np.ndarray, y: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Randomised PIT for a discrete predictive: u = F(y-1) + v * p(y), v ~ U(0,1)."""
    pmf = np.asarray(pmf, float)
    pmf = pmf / pmf.sum(axis=1, keepdims=True)
    cdf = np.cumsum(pmf, axis=1)
    n = len(y)
    upper = cdf[np.arange(n), y]
    lower = upper - pmf[np.arange(n), y]
    return lower + rng.random(n) * (upper - lower)


def pit_summary(u: np.ndarray, bins: int = 10) -> dict[str, Any]:
    """Uniformity diagnostics. Variance below 1/12 (hump) = over-dispersed predictive;
    above 1/12 (U-shape) = under-dispersed. z is the variance's standardised deviation."""
    n = len(u)
    hist, _ = np.histogram(u, bins=bins, range=(0, 1))
    expected = n / bins
    chi2 = float(((hist - expected) ** 2 / expected).sum())
    var = float(np.var(u))
    # Var of the sample variance of U(0,1): (mu4 - sigma^4)/n with mu4 = 1/80, sigma^4 = 1/144
    se_var = float(np.sqrt((1 / 80 - 1 / 144) / max(n, 1)))
    srt = np.sort(u)
    ks = float(np.max(np.abs(srt - (np.arange(1, n + 1) / n)))) if n else float("nan")
    return {
        "n": int(n),
        "mean": round(float(np.mean(u)), 4) if n else None,
        "variance": round(var, 5),
        "variance_nominal": round(1 / 12, 5),
        "variance_z": round((var - 1 / 12) / se_var, 2) if n else None,
        "chi2_uniform": round(chi2, 1),
        "chi2_df": bins - 1,
        "ks": round(ks, 4),
        "hist": [round(float(h) / n, 4) for h in hist] if n else [],
    }


def logloss_dispersion(P: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Realised log-loss contributions vs what the predictive itself expects (entropy) and the
    predictive's own variance of those contributions. z = standardised excess loss."""
    P = np.clip(P, 1e-9, 1)
    P = P / P.sum(axis=1, keepdims=True)
    lp = np.log(P)
    real = -lp[np.arange(len(y)), y]
    exp_ = -(P * lp).sum(axis=1)
    var = (P * lp**2).sum(axis=1) - exp_**2
    z = float((real.sum() - exp_.sum()) / np.sqrt(var.sum()))
    return {
        "realised_mean": round(float(real.mean()), 5),
        "expected_mean": round(float(exp_.mean()), 5),
        "realised_var": round(float(real.var()), 5),
        "expected_var": round(float(var.mean()), 5),
        "z_excess_loss": round(z, 2),
    }


def standardized_disagreement(p_data: np.ndarray, p_mkt: np.ndarray, sd: np.ndarray) -> dict:
    """z = (p_data - p_market) / sd_p. Under 'market = truth' and an honest posterior, z ~ N(0,1)."""
    sd = np.maximum(sd, 1e-9)
    z = (p_data - p_mkt) / sd
    return {
        "n": len(z),
        "mean_z": round(float(z.mean()), 3),
        "sd_z": round(float(z.std()), 3),
        "rms_z": round(float(np.sqrt(np.mean(z**2))), 3),
        "share_abs_z_below_1.28": round(float((np.abs(z) < NORMAL_80).mean()), 4),
        "share_abs_z_below_2": round(float((np.abs(z) < 2).mean()), 4),
        "market_implied_k": round(
            float(np.sqrt(np.mean((p_data - p_mkt) ** 2) / np.mean(sd**2))), 3
        ),
    }


def tercile_edges(p: np.ndarray) -> tuple[float, float]:
    return float(np.quantile(p, 1 / 3)), float(np.quantile(p, 2 / 3))


def tercile_index(p: np.ndarray, edges: tuple[float, float]) -> np.ndarray:
    return np.digitize(p, [edges[0], edges[1]])


# ----------------------------------------------------------------------------------------------
# Grouped posterior-predictive check on goals (the outcome-based estimator of k)
# ----------------------------------------------------------------------------------------------
@dataclass
class Group:
    division: str
    season: str
    team: str
    kind: str  # 'for' | 'against'
    window: int
    idx: np.ndarray  # match indices (into the cache)
    goals: np.ndarray
    rates: np.ndarray  # posterior-mean expected goals for these observations
    M: np.ndarray  # (n_g, n_g) model covariance of the rates at k = 1 (delta method)
    upd: np.ndarray  # (n_g, n_g) True where a refit separates the two forecasts

    @property
    def cluster(self) -> str:
        return f"{self.division}|{self.season}|{self.team}"


def cross_moments(
    groups: list[Group], k: np.ndarray, resid_shift: np.ndarray
) -> tuple[float, float, float]:
    """Over all groups: (sum of cross residual products, sum of model cross covariances k'Mk,
    sum of model cross covariances at k = 1 over refit-separated pairs)."""
    num = 0.0
    den = 0.0
    den_upd = 0.0
    for g in groups:
        if len(g.idx) < 2:
            continue
        r = g.goals - g.rates - resid_shift[g.idx]
        kg = k[g.idx]
        num += float(r.sum() ** 2 - (r**2).sum())
        Mk = (kg[:, None] * g.M) * kg[None, :]
        den += float(Mk.sum() - np.trace(Mk))
        den_upd += float((g.M * g.upd).sum())
    return num, den, den_upd


def estimate_k(
    groups: list[Group], resid_shift: np.ndarray, k_ref: np.ndarray | None = None
) -> float:
    """Cross-term moment estimator of the posterior-sd multiplier (relative to k_ref, default 1):
    k^2 = (sum r_i r_j + sum_{refit pairs} M_ij) / sum M_ij (see module docstring)."""
    n = int(max((int(g.idx.max()) for g in groups), default=-1)) + 1
    k1 = np.ones(n) if k_ref is None else k_ref
    num, den, den_upd = cross_moments(groups, k1, resid_shift)
    if den <= 0:
        return float("nan")
    return float(np.sqrt(max(num + den_upd, 0.0) / den))


def bootstrap_k(
    groups: list[Group], resid_shift: np.ndarray, n_boot: int = 400, seed: int = 0
) -> tuple[float, float]:
    """Cluster bootstrap (league, season, team) percentile 95% CI of the k estimator."""
    rng = np.random.default_rng(seed)
    clusters = sorted({g.cluster for g in groups})
    by_cluster: dict[str, list[Group]] = defaultdict(list)
    for g in groups:
        by_cluster[g.cluster].append(g)
    n = int(max(int(g.idx.max()) for g in groups)) + 1
    k1 = np.ones(n)
    per: dict[str, tuple[float, float, float]] = {
        c: cross_moments(gs, k1, resid_shift) for c, gs in by_cluster.items()
    }
    nums = np.array([per[c][0] + per[c][2] for c in clusters])
    dens = np.array([per[c][1] for c in clusters])
    ks = []
    for _ in range(n_boot):
        w = rng.multinomial(len(clusters), np.full(len(clusters), 1 / len(clusters)))
        num, den = float((w * nums).sum()), float((w * dens).sum())
        ks.append(np.sqrt(max(num, 0) / den) if den > 0 else np.nan)
    ks = np.array(ks)
    return float(np.nanquantile(ks, 0.025)), float(np.nanquantile(ks, 0.975))


def estimate_phi(groups: list[Group], k: np.ndarray, resid_shift: np.ndarray) -> float:
    """Aleatoric over-dispersion factor on the Poisson diagonal given k (from 'for' groups, so
    each goal observation is used once)."""
    num = 0.0
    den = 0.0
    for g in groups:
        if g.kind != "for":
            continue
        r = g.goals - g.rates - resid_shift[g.idx]
        kg = k[g.idx]
        num += float((r**2).sum() - (kg**2 * np.diag(g.M)).sum())
        den += float(g.rates.sum())
    return num / den if den > 0 else float("nan")


def group_gauss_scores(
    groups: list[Group], k: np.ndarray, phi: float, resid_shift: np.ndarray
) -> np.ndarray:
    """Per-group Gaussian log score of the window residual sum under
    V = phi*sum(rates) + k'Mk - sum_{refit-separated pairs} M_ij (the learning already done by the
    weekly refit removes that part of the cross covariance whatever k is claimed).
    Only groups with >= 2 observations (the ones that carry information about k)."""
    out = []
    for g in groups:
        if len(g.idx) < 2:
            continue
        r = float((g.goals - g.rates - resid_shift[g.idx]).sum())
        kg = k[g.idx]
        A = phi * float(g.rates.sum())
        V = max(A + float(kg @ g.M @ kg) - float((g.M * g.upd).sum()), 0.25 * A)
        out.append(-0.5 * (np.log(2 * np.pi * V) + r * r / V))
    return np.array(out)


# ----------------------------------------------------------------------------------------------
# Walk-forward collection (mirrors research/walk_forward.py's scored set exactly)
# ----------------------------------------------------------------------------------------------
@dataclass
class Config:
    divisions: tuple[str, ...] = ("E0", "SP1", "D1", "I1", "F1")
    first_season_start: int = 2017  # burn-in 2017-18; scoring from 2018-19; aligned from 2019-20
    last_season_start: int = 2025
    first_aligned_season_start: int = 2019
    refit_days: int = 7
    min_team_matches: int = 5
    posterior_samples: int = 100
    interval_level: float = 0.80
    window_days: int = 28
    sigma_shared_current: float = WORLDS_V1_SIGMA_SHARED
    strength: StrengthConfig = field(default_factory=StrengthConfig)


@dataclass
class Cache:
    division: np.ndarray
    season: np.ndarray
    match_date: np.ndarray
    home: np.ndarray
    away: np.ndarray
    y: np.ndarray  # 0 home, 1 draw, 2 away
    hg: np.ndarray
    ag: np.ndarray
    base: np.ndarray  # (n,3) log lam, log mu, rho at the posterior mean
    dev: np.ndarray  # (n,S,3)
    p_mkt: np.ndarray  # (n,3) de-vigged Bet365 1X2
    odds: np.ndarray  # (n,3) Bet365 decimal odds
    p_mkt_o25: np.ndarray  # nan where absent
    post_idx: np.ndarray
    posteriors: list[ParameterPosterior] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.y)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            **{k: v for k, v in self.__dict__.items() if k != "posteriors"},
            dev32=self.dev.astype(np.float32),
        )

    @classmethod
    def load(cls, path: Path) -> Cache:
        z = np.load(path, allow_pickle=False)
        d = {k: z[k] for k in z.files if k not in ("dev", "dev32")}
        d["dev"] = z["dev32"].astype(np.float64) if "dev32" in z.files else z["dev"]
        return cls(**d, posteriors=[])


def _season_start(season: str) -> int:
    return int(season[:4])


def collect(cfg: Config, matches: list[HistoricalMatch], *, verbose: bool = True) -> Cache:
    t0 = time.time()
    cols: dict[str, list] = defaultdict(list)
    posteriors: list[ParameterPosterior] = []
    rng = np.random.default_rng(0)
    for div in cfg.divisions:
        rows = sorted([m for m in matches if m.division == div], key=lambda m: m.result.match_date)
        if not rows:
            continue
        mrows = [
            MatchRow(
                date.fromisoformat(m.result.match_date),
                m.result.home_team_id,
                m.result.away_team_id,
                m.result.home_goals,
                m.result.away_goals,
            )
            for m in rows
        ]
        dates = sorted({r.date for r in mrows})
        idx_by_date: dict[date, list[int]] = defaultdict(list)
        for i, r in enumerate(mrows):
            idx_by_date[r.date].append(i)
        post: ParameterPosterior | None = None
        L: np.ndarray | None = None
        last_fit: date | None = None
        seen: dict[str, int] = defaultdict(int)
        for d in dates:
            ids = idx_by_date[d]
            season = rows[ids[0]].result.season_id
            s0 = _season_start(season)
            if s0 < cfg.first_season_start:
                for i in ids:
                    seen[mrows[i].home] += 1
                    seen[mrows[i].away] += 1
                continue
            if s0 > cfg.last_season_start:
                break
            if last_fit is None or (d - last_fit).days >= cfg.refit_days:
                fit_rows = [r for r in mrows if r.date < d]
                if len(fit_rows) >= 100:
                    post = DixonColesFitter(cfg.strength).fit(fit_rows, as_of=d)
                    posteriors.append(post)
                    w, v = np.linalg.eigh(post.cov)
                    L = v * np.sqrt(np.clip(w, 1e-10, None))
                    last_fit = d
            for i in ids:
                hm, mr = rows[i], mrows[i]
                scored = (
                    post is not None
                    and s0 > cfg.first_season_start
                    and seen[mr.home] >= cfg.min_team_matches
                    and seen[mr.away] >= cfg.min_team_matches
                    and mr.home in post.teams
                    and mr.away in post.teams
                )
                odds = {(o.market, o.selection): o.decimal_odds for o in hm.odds}
                has_1x2 = all((("1x2", s) in odds) for s in ("home", "draw", "away"))
                if scored and has_1x2:
                    assert post is not None and L is not None
                    lam, mu = post.expected_goals(mr.home, mr.away)
                    z = rng.standard_normal((cfg.posterior_samples, len(post.mean)))
                    dth = z @ L.T  # deviations from the posterior mean
                    ia_h, id_h = post.idx_attack(mr.home), post.idx_defence(mr.home)
                    ia_a, id_a = post.idx_attack(mr.away), post.idx_defence(mr.away)
                    dev = np.stack(
                        [
                            dth[:, ia_h] - dth[:, id_a] + dth[:, post.idx_home],
                            dth[:, ia_a] - dth[:, id_h],
                            dth[:, post.idx_rho],
                        ],
                        axis=1,
                    )
                    o = np.array(
                        [odds[("1x2", "home")], odds[("1x2", "draw")], odds[("1x2", "away")]]
                    )
                    p_mkt = devig_proportional(o[None, :])[0]
                    p_o25 = np.nan
                    if ("ou", "over") in odds and ("ou", "under") in odds:
                        p_o25 = float(
                            devig_proportional(
                                np.array([[odds[("ou", "over")], odds[("ou", "under")]]])
                            )[0][0]
                        )
                    y = (
                        0
                        if mr.home_goals > mr.away_goals
                        else (1 if mr.home_goals == mr.away_goals else 2)
                    )
                    cols["division"].append(div)
                    cols["season"].append(season)
                    cols["match_date"].append(mr.date.isoformat())
                    cols["home"].append(mr.home)
                    cols["away"].append(mr.away)
                    cols["y"].append(y)
                    cols["hg"].append(mr.home_goals)
                    cols["ag"].append(mr.away_goals)
                    cols["base"].append([np.log(lam), np.log(mu), float(post.mean[post.idx_rho])])
                    cols["dev"].append(dev)
                    cols["p_mkt"].append(p_mkt)
                    cols["odds"].append(o)
                    cols["p_mkt_o25"].append(p_o25)
                    cols["post_idx"].append(len(posteriors) - 1)
                seen[mr.home] += 1
                seen[mr.away] += 1
        if verbose:
            print(
                f"{div}: {sum(1 for x in cols['division'] if x == div)} scored predictions ({time.time() - t0:.0f}s)"
            )
    return Cache(
        division=np.array(cols["division"]),
        season=np.array(cols["season"]),
        match_date=np.array(cols["match_date"]),
        home=np.array(cols["home"]),
        away=np.array(cols["away"]),
        y=np.array(cols["y"], int),
        hg=np.array(cols["hg"], int),
        ag=np.array(cols["ag"], int),
        base=np.array(cols["base"], float),
        dev=np.stack(cols["dev"]).astype(float),
        p_mkt=np.array(cols["p_mkt"], float),
        odds=np.array(cols["odds"], float),
        p_mkt_o25=np.array(cols["p_mkt_o25"], float),
        post_idx=np.array(cols["post_idx"], int),
        posteriors=posteriors,
    )


def build_groups(cache: Cache, window_days: int) -> list[Group]:
    """(team, season, window) groups of goals for / against with the delta-method covariance of
    the expected goals under the posterior in force at the group's first match."""
    n = len(cache)
    dates = np.array([date.fromisoformat(s) for s in cache.match_date])
    first_by_ds: dict[tuple[str, str], date] = {}
    for i in range(n):
        key = (str(cache.division[i]), str(cache.season[i]))
        if key not in first_by_ds or dates[i] < first_by_ds[key]:
            first_by_ds[key] = dates[i]
    members: dict[tuple, list[int]] = defaultdict(list)
    for i in range(n):
        key0 = (str(cache.division[i]), str(cache.season[i]))
        w = (dates[i] - first_by_ds[key0]).days // window_days
        members[(*key0, str(cache.home[i]), w)].append(i)
        members[(*key0, str(cache.away[i]), w)].append(i)
    lam0 = np.exp(cache.base[:, 0])
    mu0 = np.exp(cache.base[:, 1])
    groups: list[Group] = []
    for (div, season, team, w), idx in members.items():
        idx = sorted(idx, key=lambda i: (dates[i], i))
        for kind in ("for", "against"):
            goals, rates, keyrows = [], [], []
            for i in idx:
                is_home = str(cache.home[i]) == team
                opp = str(cache.away[i]) if is_home else str(cache.home[i])
                if kind == "for":
                    g = cache.hg[i] if is_home else cache.ag[i]
                    rate = lam0[i] if is_home else mu0[i]
                    keys = [(("att", team), 1.0), (("def", opp), -1.0)]
                    if is_home:
                        keys.append((("gamma",), 1.0))
                else:
                    g = cache.ag[i] if is_home else cache.hg[i]
                    rate = mu0[i] if is_home else lam0[i]
                    keys = [(("att", opp), 1.0), (("def", team), -1.0)]
                    if not is_home:
                        keys.append((("gamma",), 1.0))
                goals.append(int(g))
                rates.append(float(rate))
                keyrows.append(keys)
            M = _delta_cov(cache, idx, keyrows, np.array(rates))
            pidx = cache.post_idx[np.array(idx)]
            upd = pidx[:, None] != pidx[None, :]
            groups.append(
                Group(
                    div,
                    season,
                    team,
                    kind,
                    int(w),
                    np.array(idx),
                    np.array(goals),
                    np.array(rates),
                    M,
                    upd,
                )
            )
    return groups


def _param_index(post: ParameterPosterior, key: tuple) -> int | None:
    if key[0] == "gamma":
        return post.idx_home
    if key[1] not in post.teams:
        return None
    return post.idx_attack(key[1]) if key[0] == "att" else post.idx_defence(key[1])


def _delta_cov(cache: Cache, idx: list[int], keyrows: list[list], rates: np.ndarray) -> np.ndarray:
    """Cov of the expected-goal rates across a group's matches under the group-start posterior
    (parameter error is treated as persistent inside the window). Params missing from that
    posterior use their own match's posterior variance with zero cross-covariance."""
    base_post = cache.posteriors[cache.post_idx[idx[0]]]
    keys = sorted({k for row in keyrows for k, _ in row})
    kpos = {k: j for j, k in enumerate(keys)}
    P = len(keys)
    Sigma = np.zeros((P, P))
    present = [(k, _param_index(base_post, k)) for k in keys]
    pi = [(kpos[k], j) for k, j in present if j is not None]
    if pi:
        a = np.array([x[0] for x in pi])
        b = np.array([x[1] for x in pi])
        Sigma[np.ix_(a, a)] = base_post.cov[np.ix_(b, b)]
    for k, j in present:
        if j is None:
            for i, row in zip(idx, keyrows):
                if any(kk == k for kk, _ in row):
                    own = cache.posteriors[cache.post_idx[i]]
                    jj = _param_index(own, k)
                    Sigma[kpos[k], kpos[k]] = own.cov[jj, jj] if jj is not None else 0.0
                    break
    C = np.zeros((len(idx), P))
    for r, row in enumerate(keyrows):
        for k, coef in row:
            C[r, kpos[k]] += coef * rates[r]
    return C @ Sigma @ C.T


def residual_shift(cache: Cache, seasons_sorted: list[str]) -> np.ndarray:
    """Per-match league-level mean goal residual estimated from strictly earlier seasons (the first
    scored season uses its own mean; it is never part of the aligned evaluation)."""
    lam0, mu0 = np.exp(cache.base[:, 0]), np.exp(cache.base[:, 1])
    res_obs = np.concatenate([cache.hg - lam0, cache.ag - mu0])
    div2 = np.concatenate([cache.division, cache.division])
    sea2 = np.concatenate([cache.season, cache.season])
    out = np.zeros(len(cache))
    for div in np.unique(cache.division):
        for s in seasons_sorted:
            m = (cache.division == div) & (cache.season == s)
            if not m.any():
                continue
            prior = (div2 == div) & (np.vectorize(_season_start)(sea2) < _season_start(s))
            if prior.sum() < 100:
                prior = (div2 == div) & (sea2 == s)
            out[m] = res_obs[prior].mean()
    return out


# ----------------------------------------------------------------------------------------------
# Candidate evaluation
# ----------------------------------------------------------------------------------------------
@dataclass
class Evaluated:
    p3: np.ndarray  # (n,3) integrated predictive
    lo: np.ndarray
    hi: np.ndarray
    sd: np.ndarray  # sd of P(home) across draws
    p_o25: np.ndarray
    tot_pmf: np.ndarray  # (n,21)
    draws: np.ndarray | None = None  # (n,S,3) float32 per-draw 1X2 probabilities


def evaluate(
    cache: Cache,
    k: np.ndarray,
    sigma_shared: np.ndarray,
    *,
    level: float = 0.80,
    seed: int = 1,
    keep_draws: bool = False,
    chunk: int = 400,
) -> Evaluated:
    n, S, _ = cache.dev.shape
    rng = np.random.default_rng(seed)
    shift = rng.standard_normal((n, S)) * sigma_shared[:, None]
    p3 = np.zeros((n, 3))
    lo = np.zeros(n)
    hi = np.zeros(n)
    sd = np.zeros(n)
    p_o25 = np.zeros(n)
    tot = np.zeros((n, 21))
    draws = np.zeros((n, S, 3), np.float32) if keep_draws else None
    a = (1 - level) / 2
    for s in range(0, n, chunk):
        e = min(n, s + chunk)
        lam, mu, rho = scaled_rates(cache.base[s:e], cache.dev[s:e], k[s:e], shift[s:e])
        probs, tpmf = dc_probs_vec(lam.ravel(), mu.ravel(), rho.ravel())
        probs = probs.reshape(e - s, S, 3)
        tpmf = tpmf.reshape(e - s, S, 21)
        p3[s:e] = probs.mean(axis=1)
        ph = probs[:, :, 0]
        lo[s:e] = np.quantile(ph, a, axis=1)
        hi[s:e] = np.quantile(ph, 1 - a, axis=1)
        sd[s:e] = ph.std(axis=1)
        tm = tpmf.mean(axis=1)
        tot[s:e] = tm
        p_o25[s:e] = tm[:, 3:].sum(axis=1)
        if draws is not None:
            draws[s:e] = probs.astype(np.float32)
    return Evaluated(p3, lo, hi, sd, p_o25, tot, draws)


def _metrics(
    cache: Cache, ev: Evaluated, m: np.ndarray, *, level: float, pit_seed: int = 7
) -> dict:
    y = cache.y[m]
    P = ev.p3[m]
    yh = (y == 0).astype(int)
    pdh, pmh = P[:, 0], cache.p_mkt[m][:, 0]
    rng = np.random.default_rng(pit_seed)
    pit_1x2 = randomized_pit(P[:, ::-1], 2 - y, rng)  # ordinal: away < draw < home
    tot_y = np.clip(cache.hg[m] + cache.ag[m], 0, 20)
    pit_tot = randomized_pit(ev.tot_pmf[m], tot_y, rng)
    ic = interval_calibration(pdh, ev.lo[m], ev.hi[m], yh, level=level)
    out = {
        "n": int(m.sum()),
        "mean_width": round(float((ev.hi[m] - ev.lo[m]).mean()), 4),
        "mean_sd_p_home": round(float(ev.sd[m].mean()), 4),
        "market_inside_rate": round(float(((pmh >= ev.lo[m]) & (pmh <= ev.hi[m])).mean()), 4),
        "disagreement": standardized_disagreement(pdh, pmh, ev.sd[m]),
        "log_loss": round(multiclass_log_loss(P, y), 5),
        "brier": round(multiclass_brier(P, y), 5),
        "ece_home": round(expected_calibration_error(pdh, yh), 4),
        "logloss_dispersion": logloss_dispersion(P, y),
        "pit_1x2": pit_summary(pit_1x2),
        "pit_totals": pit_summary(pit_tot),
        "bin_coverage_weighted": round(float(ic["weighted_bin_coverage"]), 4),
    }
    mo = ~np.isnan(cache.p_mkt_o25[m])
    if mo.sum() > 100:
        yo = (tot_y[mo] > 2.5).astype(int)
        out["over25"] = {
            "n": int(mo.sum()),
            "log_loss_data": round(log_loss(ev.p_o25[m][mo], yo), 5),
            "log_loss_market": round(log_loss(cache.p_mkt_o25[m][mo], yo), 5),
            "mean_pred": round(float(ev.p_o25[m][mo].mean()), 4),
            "base_rate": round(float(yo.mean()), 4),
        }
    return out


def summarise_candidate(
    cache: Cache,
    ev: Evaluated,
    *,
    groups: list[Group],
    k: np.ndarray,
    phi_by_season: dict[str, float],
    shift: np.ndarray,
    aligned: np.ndarray,
    seasons: list[str],
    level: float,
) -> dict:
    out: dict[str, Any] = {
        "overall": _metrics(cache, ev, aligned, level=level),
        "by_season": {},
        "by_league": {},
    }
    scores_all = []
    for s in seasons:
        m = aligned & (cache.season == s)
        d = _metrics(cache, ev, m, level=level)
        gs = [g for g in groups if g.season == s]
        sc = group_gauss_scores(gs, k, phi_by_season[s], shift)
        d["group_gauss_score"] = round(float(sc.mean()), 5)
        d["n_groups"] = len(sc)
        scores_all.append(sc)
        out["by_season"][s] = d
    for div in sorted(set(cache.division[aligned])):
        m = aligned & (cache.division == div)
        out["by_league"][div] = _metrics(cache, ev, m, level=level)
    sc = np.concatenate(scores_all)
    out["overall"]["group_gauss_score"] = round(float(sc.mean()), 5)
    out["overall"]["n_groups"] = len(sc)
    out["_group_scores"] = sc
    return out


# ----------------------------------------------------------------------------------------------
# Main research flow
# ----------------------------------------------------------------------------------------------
def run(cfg: Config, cache: Cache, *, verbose: bool = True) -> dict:
    t0 = time.time()
    n = len(cache)
    seasons_all = sorted(set(cache.season), key=_season_start)
    seasons = [s for s in seasons_all if _season_start(s) >= cfg.first_aligned_season_start]
    aligned = np.isin(cache.season, seasons)
    ones = np.ones(n)
    zeros = np.zeros(n)
    sig_cur = np.full(n, cfg.sigma_shared_current)
    log = print if verbose else (lambda *a, **k: None)

    # ---- outcome-based estimator of k ----------------------------------------------------------
    groups = build_groups(cache, cfg.window_days)
    shift = residual_shift(cache, seasons_all)
    raw_shift = np.zeros(n)
    k_hat = estimate_k(groups, shift)
    k_ci = bootstrap_k(groups, shift)
    k_hat_raw = estimate_k(groups, raw_shift)
    phi_hat = estimate_phi(groups, ones * k_hat, shift)
    log(
        f"grouped estimator: k_hat={k_hat:.3f} CI95={k_ci} (raw-residual k={k_hat_raw:.3f}); phi={phi_hat:.3f} ({time.time() - t0:.0f}s)"
    )
    num_all, den_all, den_upd_all = cross_moments(groups, ones, shift)
    est: dict[str, Any] = {
        "method": "innovation cross-moment estimator on (team, season, window) goal residuals; see module docstring",
        "cross_moments": {
            "sum_cross_residual_products": round(num_all, 2),
            "sum_model_cross_cov_all_pairs": round(den_all, 2),
            "sum_model_cross_cov_refit_separated_pairs": round(den_upd_all, 2),
            "share_refit_separated": round(den_upd_all / den_all, 4) if den_all > 0 else None,
            "reading": "under k=1 the residual products should sum to -(refit-separated cross cov); more negative = over-reaction = posterior too wide",
        },
        "window_days": cfg.window_days,
        "n_groups": len(groups),
        "n_groups_ge2": int(sum(len(g.idx) >= 2 for g in groups)),
        "k_hat_pooled": round(k_hat, 4),
        "k_hat_ci95_cluster_bootstrap": [round(k_ci[0], 4), round(k_ci[1], 4)],
        "k_hat_pooled_raw_residuals": round(k_hat_raw, 4),
        "phi_hat_aleatoric_overdispersion": round(phi_hat, 4),
        "k_hat_by_season": {},
        "k_hat_by_league": {},
        "k_hat_by_window_days": {},
        "k_hat_aligned_only": None,
    }
    for s in seasons_all:
        gs = [g for g in groups if g.season == s]
        est["k_hat_by_season"][s] = round(estimate_k(gs, shift), 4)
    for div in sorted(set(cache.division)):
        gs = [g for g in groups if g.division == div]
        est["k_hat_by_league"][div] = {
            "k_hat": round(estimate_k(gs, shift), 4),
            "ci95": [round(x, 4) for x in bootstrap_k(gs, shift, n_boot=200)],
        }
    est["k_hat_aligned_only"] = round(
        estimate_k([g for g in groups if g.season in seasons], shift), 4
    )
    for wd in (14, 56):
        est["k_hat_by_window_days"][str(wd)] = round(estimate_k(build_groups(cache, wd), shift), 4)
    est["k_hat_by_window_days"][str(cfg.window_days)] = round(k_hat, 4)

    # ---- baselines and the k grid --------------------------------------------------------------
    ev_post = evaluate(cache, ones, zeros, level=cfg.interval_level)
    grid: dict[str, Any] = {}
    for sig_name, sig in (("posterior_only", zeros), ("worlds_v1_shared_inflation", sig_cur)):
        grid[sig_name] = {}
        for kv in K_GRID:
            ev = evaluate(cache, ones * kv, sig, level=cfg.interval_level)
            d = _metrics(cache, ev, aligned, level=cfg.interval_level)
            phi_k = estimate_phi(groups, ones * kv, shift)
            d["group_gauss_score_insample"] = round(
                float(group_gauss_scores(groups, ones * kv, phi_k, shift).mean()), 5
            )
            grid[sig_name][str(kv)] = {
                "mean_width": d["mean_width"],
                "market_inside_rate": d["market_inside_rate"],
                "sd_z": d["disagreement"]["sd_z"],
                "log_loss": d["log_loss"],
                "brier": d["brier"],
                "pit_1x2_variance": d["pit_1x2"]["variance"],
                "pit_totals_variance": d["pit_totals"]["variance"],
                "pit_totals_variance_z": d["pit_totals"]["variance_z"],
                "logloss_z_excess": d["logloss_dispersion"]["z_excess_loss"],
                "group_gauss_score_insample": d["group_gauss_score_insample"],
                "over25_log_loss": d.get("over25", {}).get("log_loss_data"),
            }
        log(f"grid {sig_name} done ({time.time() - t0:.0f}s)")

    # ---- market-implied scales (secondary reference, descriptive) -------------------------------
    pdh, pmh, sdh = ev_post.p3[:, 0], cache.p_mkt[:, 0], ev_post.sd
    mkt: dict[str, Any] = {
        "overall": standardized_disagreement(pdh[aligned], pmh[aligned], sdh[aligned]),
        "by_season": {
            s: standardized_disagreement(pdh[m], pmh[m], sdh[m])
            for s in seasons
            for m in [aligned & (cache.season == s)]
        },
        "by_league": {},
        "by_p_home_tercile": {},
        "note": "market-implied k = RMS(p_data - p_market) / RMS(sd_p); mixes systematic model bias with genuine parameter uncertainty and treats Bet365 as truth. Secondary reference only.",
    }
    for div in sorted(set(cache.division)):
        m = aligned & (cache.division == div)
        mkt["by_league"][div] = standardized_disagreement(pdh[m], pmh[m], sdh[m])
    edges_all = tercile_edges(pdh[aligned])
    ter_all = tercile_index(pdh, edges_all)
    for t in range(3):
        m = aligned & (ter_all == t)
        mkt["by_p_home_tercile"][f"T{t + 1}"] = {
            "p_home_range": [round(float(pdh[m].min()), 3), round(float(pdh[m].max()), 3)],
            "mean_bias_data_minus_market": round(float((pdh[m] - pmh[m]).mean()), 4),
            **standardized_disagreement(pdh[m], pmh[m], sdh[m]),
        }

    # ---- walk-forward candidates ---------------------------------------------------------------
    def prior_groups(s: str) -> list[Group]:
        return [g for g in groups if _season_start(g.season) < _season_start(s)]

    k_global_wf = np.ones(n)
    k_league_wf = np.ones(n)
    k_mkt_global = np.ones(n)
    k_mkt_tercile = np.ones(n)
    fitted: dict[str, dict[str, Any]] = {
        "global_outcome": {},
        "league_outcome": {},
        "global_market": {},
        "tercile_market": {},
    }
    for s in seasons:
        cur = cache.season == s
        pg = prior_groups(s)
        prior_m = np.vectorize(_season_start)(cache.season) < _season_start(s)
        kg = estimate_k(pg, shift)
        kg = float(np.clip(kg, 0.2, 2.0)) if np.isfinite(kg) else 1.0
        k_global_wf[cur] = kg
        fitted["global_outcome"][s] = round(kg, 4)
        fitted["league_outcome"][s] = {}
        for div in sorted(set(cache.division)):
            gl = [g for g in pg if g.division == div]
            kl = estimate_k(gl, shift) if len(gl) >= 300 else float("nan")
            kl = float(np.clip(kl, 0.2, 2.0)) if np.isfinite(kl) else kg
            k_league_wf[cur & (cache.division == div)] = kl
            fitted["league_outcome"][s][div] = round(kl, 4)
        km = standardized_disagreement(pdh[prior_m], pmh[prior_m], sdh[prior_m])["market_implied_k"]
        k_mkt_global[cur] = km
        fitted["global_market"][s] = km
        edges = tercile_edges(pdh[prior_m])
        ter_prior = tercile_index(pdh, edges)
        fitted["tercile_market"][s] = {"edges": [round(e, 4) for e in edges]}
        for t in range(3):
            mm = prior_m & (ter_prior == t)
            kt = standardized_disagreement(pdh[mm], pmh[mm], sdh[mm])["market_implied_k"]
            k_mkt_tercile[cur & (ter_prior == t)] = kt
            fitted["tercile_market"][s][f"T{t + 1}"] = kt

    candidates = {
        "current_worlds_v1": (
            ones,
            sig_cur,
            "k=1 posterior + shared log-rate inflation sd 0.058 (production proxy)",
        ),
        "posterior_only_wf_v1": (
            ones,
            zeros,
            "k=1, no world-layer inflation (walk_forward_v1 interval)",
        ),
        "global_outcome_k": (
            k_global_wf,
            sig_cur,
            "walk-forward global k from the grouped goal-residual estimator",
        ),
        "league_outcome_k": (
            k_league_wf,
            sig_cur,
            "walk-forward league-specific k (fallback to global if < 300 groups)",
        ),
        "global_market_k": (
            k_mkt_global,
            sig_cur,
            "walk-forward global k that makes RMS z = 1 vs Bet365 (market-referenced)",
        ),
        "tercile_market_k": (
            k_mkt_tercile,
            sig_cur,
            "walk-forward market-referenced k per predicted P(home) tercile",
        ),
        "fixed_k_0.6_reference": (
            ones * 0.6,
            sig_cur,
            "not walk-forward; the a-priori expectation stated in the task, for reference",
        ),
        "no_world_inflation_global_outcome_k": (
            k_global_wf,
            zeros,
            "global outcome k with sigma_model = sigma_environment = 0",
        ),
    }
    results: dict[str, Any] = {}
    scores: dict[str, np.ndarray] = {}
    for name, (kv, sig, desc) in candidates.items():
        ev = evaluate(cache, kv, sig, level=cfg.interval_level)
        phi_by_s = {}
        for s in seasons:
            pg = prior_groups(s)
            ph = estimate_phi(pg, kv, shift)
            phi_by_s[s] = float(ph) if np.isfinite(ph) and ph > 0.3 else 1.0
        d = summarise_candidate(
            cache,
            ev,
            groups=groups,
            k=kv,
            phi_by_season=phi_by_s,
            shift=shift,
            aligned=aligned,
            seasons=seasons,
            level=cfg.interval_level,
        )
        scores[name] = d.pop("_group_scores")
        d["description"] = desc
        d["mean_k_applied"] = round(float(kv[aligned].mean()), 4)
        d["phi_by_season"] = {s: round(v, 4) for s, v in phi_by_s.items()}
        results[name] = d
        log(
            f"candidate {name}: width={d['overall']['mean_width']} inside={d['overall']['market_inside_rate']} LL={d['overall']['log_loss']} gscore={d['overall']['group_gauss_score']} ({time.time() - t0:.0f}s)"
        )

    # paired comparisons of the OOS group score vs the current configuration and vs global_outcome_k
    paired: dict[str, Any] = {}
    for ref in ("current_worlds_v1", "global_outcome_k"):
        paired[ref] = {}
        for name, sc in scores.items():
            if name == ref:
                continue
            diff = sc - scores[ref]
            ci = bootstrap_mean_ci(diff, n_boot=1000)
            wins = sum(
                results[name]["by_season"][s]["group_gauss_score"]
                > results[ref]["by_season"][s]["group_gauss_score"]
                for s in seasons
            )
            paired[ref][name] = {
                "mean_diff": round(float(diff.mean()), 5),
                "ci95": [round(ci[0], 5), round(ci[1], 5)],
                "seasons_better": int(wins),
                "seasons_total": len(seasons),
            }

    decision = decide(cfg, est, results, paired, seasons, grid=grid)
    log(json.dumps(decision, indent=1))
    return {
        "protocol": PROTOCOL_VERSION,
        "config": {
            **{k: v for k, v in cfg.__dict__.items() if k != "strength"},
            "strength": cfg.strength.__dict__,
            "k_grid": list(K_GRID),
        },
        "elapsed_s": round(time.time() - t0, 1),
        "n_scored": n,
        "n_aligned": int(aligned.sum()),
        "seasons_aligned": seasons,
        "seasons_scored": seasons_all,
        "outcome_based_estimator": est,
        "market_reference": mkt,
        "k_grid_diagnostics": grid,
        "walk_forward_fitted_scales": fitted,
        "candidates": results,
        "paired_group_score_vs": paired,
        "decision": decision,
        "notes": [
            "horizon-specific scales are not studied: the historical file has one pre-match Bet365 snapshot per match and no time-to-kickoff or lineup information",
            "the interval and P(edge>0) proxy covers posterior draws + the shared log-rate inflation only; red-card hazard and game-state draws of worlds_v1 are not represented",
            "group covariances use the posterior in force at the group's first match and treat parameter error as persistent inside the window (delta method)",
            "expected goals in the residuals are the plug-in posterior-mean rates (as in walk_forward.py), not the k-integrated predictive means",
        ],
    }


def decide(
    cfg: Config,
    est: dict,
    results: dict,
    paired: dict,
    seasons: list[str],
    *,
    grid: dict | None = None,
) -> dict:
    lo, hi = est["k_hat_ci95_cluster_bootstrap"]
    k_hat = est["k_hat_pooled"]
    side = np.sign(k_hat - 1.0)
    per = [est["k_hat_by_season"][s] for s in seasons]
    same_side = sum(1 for v in per if np.isfinite(v) and np.sign(v - 1.0) == side)
    r2 = (lo > 1.0 or hi < 1.0) and same_side >= 5
    cur = results["current_worlds_v1"]["overall"]
    glob = results["global_outcome_k"]["overall"]
    r5 = abs(glob["market_inside_rate"] - 0.8) < abs(cur["market_inside_rate"] - 0.8)
    r6 = glob["log_loss"] - cur["log_loss"] <= 0.001
    out: dict[str, Any] = {
        "R2_outcome_ci_excludes_1": bool(lo > 1.0 or hi < 1.0),
        "R2_seasons_same_side": same_side,
        "R2_supported": bool(r2),
        "R5_market_inside_moves_toward_0.8": bool(r5),
        "R6_logloss_guardrail": bool(r6),
    }
    chosen = "no_change"
    if r2 and r5 and r6:
        chosen = "global_outcome_k"
        for name in ("league_outcome_k",):
            p = paired["global_outcome_k"][name]
            if p["seasons_better"] >= 5 and p["ci95"][0] > 0:
                chosen = name
    # R4: world-layer inflation judged by totals PIT variance
    cur_z = cur["pit_totals"]["variance_z"]
    alt = results["no_world_inflation_global_outcome_k"]["overall"]["pit_totals"]["variance_z"]
    out["R4_current_totals_pit_variance_z"] = cur_z
    out["R4_no_inflation_totals_pit_variance_z"] = alt
    out["R4_change_supported"] = bool(abs(cur_z) > 2 and abs(alt) <= 2)
    if grid:
        # Supplementary, NOT part of the pre-stated rule (added after the first grid was seen):
        # integrating over a correctly calibrated posterior should not worsen the log score of the
        # predictive relative to a narrower one; the k minimising walk-forward log loss is reported.
        g = grid.get("worlds_v1_shared_inflation", {})
        if g:
            best = min(g.items(), key=lambda kv: kv[1]["log_loss"])
            out["supplementary_logscore_optimal_k"] = {
                "k": float(best[0]),
                "log_loss": best[1]["log_loss"],
                "log_loss_at_k_1": g.get("1.0", {}).get("log_loss"),
                "status": "post-hoc diagnostic; not used in the decision",
            }
    out["chosen"] = chosen
    out["k_hat_pooled"] = k_hat
    out["k_hat_ci95"] = [lo, hi]
    out["market_implied_k_overall"] = results["global_market_k"]["mean_k_applied"]
    out["summary"] = (
        f"outcome-based k_hat={k_hat} (95% CI {lo}-{hi}), {same_side}/{len(seasons)} seasons on the same side of 1; "
        f"decision: {chosen}"
    )
    return out


def _strip_arrays(o: Any) -> Any:
    if isinstance(o, dict):
        return {k: _strip_arrays(v) for k, v in o.items() if not k.startswith("_")}
    if isinstance(o, list):
        return [_strip_arrays(v) for v in o]
    if isinstance(o, float) and not np.isfinite(o):
        return None
    return o


def load_matches(matches_csv: Path, divisions: tuple[str, ...], first_season: int):
    reg = AliasRegistry.from_directory(REPO / "data" / "registry")
    prov = ClubFootballDataProvider(reg)
    content = matches_csv.read_bytes()
    obs = prov.load(divisions=divisions, start_date=f"{first_season}-07-01", content=content)
    data_hash = "sha256:" + hashlib.sha256(content).hexdigest()
    return obs, data_hash


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matches-csv", default=str(REPO / "data" / "cache" / "Matches.csv"))
    ap.add_argument("--divisions", default="E0,SP1,D1,I1,F1")
    ap.add_argument("--first-season", type=int, default=2017)
    ap.add_argument("--last-season", type=int, default=2025)
    ap.add_argument("--posterior-samples", type=int, default=100)
    ap.add_argument("--out", default=str(REPO / "data" / "research" / "recalibration_v1.json"))
    ap.add_argument(
        "--cache",
        default=str(CACHE_PATH),
        help="npz cache of per-match posterior deviations (reused by pedge_eval.py)",
    )
    ap.add_argument(
        "--reuse-cache",
        action="store_true",
        help="skip the walk-forward refits if the pickled cache (npz path with .pkl) exists",
    )
    a = ap.parse_args()
    divs = tuple(a.divisions.split(","))
    cfg = Config(
        divisions=divs,
        first_season_start=a.first_season,
        last_season_start=a.last_season,
        posterior_samples=a.posterior_samples,
    )
    t0 = time.time()
    obs, data_hash = load_matches(Path(a.matches_csv), divs, a.first_season)
    print(f"loaded {len(obs.payload)} matches; data hash {data_hash}")
    pkl = Path(a.cache).with_suffix(".pkl")
    if a.reuse_cache and pkl.exists():
        cache = pickle.loads(pkl.read_bytes())
        print(f"reused {len(cache)} scored predictions from {pkl}")
    else:
        cache = collect(cfg, obs.payload)
        cache.save(Path(a.cache))
        pkl.write_bytes(pickle.dumps(cache))
        print(
            f"collected {len(cache)} scored predictions in {time.time() - t0:.0f}s; cache -> {a.cache}"
        )
    res = run(cfg, cache)
    res["data_provenance"] = {
        "source": obs.provenance.source,
        "content_hash": data_hash,
        "notes": list(obs.notes),
        "file": str(a.matches_csv),
    }
    res["collect_elapsed_s"] = round(time.time() - t0 - res["elapsed_s"], 1)
    res = _strip_arrays(res)
    res["result_hash"] = content_hash(
        {k: v for k, v in res.items() if k not in ("elapsed_s", "collect_elapsed_s")}
    )
    write_json(Path(a.out), res)
    print(f"wrote {a.out} ({res['result_hash']}) total {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
