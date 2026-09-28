"""Shared walk-forward machinery for the home-bias, disagreement and market-family studies.

This module re-implements the *exact* protocol of ``research/walk_forward.py`` (pre-registered as
``walk_forward_v1``): chronological only, DATA_ONLY refit weekly on matches strictly before the
match date, burn-in season 2017-18, hybrid warm-up 2018-19, aligned scoring 2019-20 .. 2025-26,
divisions E0/SP1/D1/I1/F1, posterior integration with the same ``numpy`` RNG draw order.  What it
adds is *bookkeeping*: per match it records the posterior-averaged Dixon-Coles score matrix and
the covariates the hypothesis tests need (fitted home advantage and its sd, effective matches per
team, the Laplace sd of the log-rate difference, days since refit, rest days, matchday, ClubElo,
Asian-handicap odds).  Everything is cached once under ``data/cache/research/`` (git-ignored) and
reused by the three studies.

Nothing in ``src/`` is modified; alternative strength configurations are built with
``dataclasses.replace`` and reported under their own candidate names.
"""

from __future__ import annotations

import csv
import dataclasses
import hashlib
import io
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
from scipy.stats import poisson

from soccer_edge.core.serialization import content_hash
from soccer_edge.evaluation.metrics import bootstrap_mean_ci
from soccer_edge.families.base import blend_logit, devig_proportional, fit_blend_weight
from soccer_edge.identity.registry import AliasRegistry
from soccer_edge.model.strength import DixonColesFitter, MatchRow, StrengthConfig
from soccer_edge.providers.club_football_data import ClubFootballDataProvider, HistoricalMatch

REPO = Path(__file__).resolve().parents[1]
MATCHES_CSV = REPO / "data" / "cache" / "Matches.csv"
CACHE_DIR = REPO / "data" / "cache" / "research"
PROTOCOL_VERSION = "walk_forward_v1"
DIVISIONS: tuple[str, ...] = ("E0", "SP1", "D1", "I1", "F1")
FIRST_SEASON_START = 2017  # burn-in
LAST_SEASON_START = 2025
REFIT_DAYS = 7
MIN_TEAM_MATCHES = 5
MIN_PRIOR_FOR_HYBRID = 500
POSTERIOR_SAMPLES = 100
INTERVAL_LEVEL = 0.80
MAX_GOALS = 10
FROZEN_V1_JSON = REPO / "data" / "research" / "walk_forward_v1.json"

# Named candidate configurations (never edit StrengthConfig defaults; these are *variants*).
VARIANTS: dict[str, dict] = {
    "dc_laplace_v1": {},
    "dc_laplace_v1.decay003": {"decay_per_day": 0.003},
    "dc_laplace_v1.decay010": {"decay_per_day": 0.010},
    "dc_laplace_v1.gamma_sd005": {"home_advantage_prior_sd": 0.05},
    "dc_laplace_v1.gamma_sd050": {"home_advantage_prior_sd": 0.50},
    "dc_laplace_v1.newteam_mean000": {
        "prior_mean_new_team_attack": 0.0,
        "prior_mean_new_team_defence": 0.0,
    },
    "dc_laplace_v1.newteam_mean-030": {
        "prior_mean_new_team_attack": -0.30,
        "prior_mean_new_team_defence": -0.30,
    },
    "dc_laplace_v1.team_sd060": {"prior_sd_attack": 0.60, "prior_sd_defence": 0.60},
    # structural candidate: same priors, plus a global log scoring intercept (research/dc_intercept.py)
    "dc_laplace_v1.intercept": {"_fitter": "intercept"},
    "dc_laplace_v1.intercept_sd060": {
        "_fitter": "intercept",
        "prior_sd_attack": 0.60,
        "prior_sd_defence": 0.60,
    },
    "dc_laplace_v1.intercept_decay003": {"_fitter": "intercept", "decay_per_day": 0.003},
}


def strength_for(variant: str) -> StrengthConfig:
    over = {k: v for k, v in VARIANTS[variant].items() if not k.startswith("_")}
    return dataclasses.replace(StrengthConfig(), **over, version=variant)


def fitter_for(variant: str) -> DixonColesFitter:
    if VARIANTS.get(variant, {}).get("_fitter") == "intercept":
        from research.dc_intercept import InterceptDixonColesFitter

        return InterceptDixonColesFitter(strength_for(variant))
    return DixonColesFitter(strength_for(variant))


def season_start(season: str) -> int:
    return int(season[:4])


# --------------------------------------------------------------------------------------------
# data loading (provider rows + the raw CSV columns the provider drops, aligned by row order)
# --------------------------------------------------------------------------------------------
@dataclass
class RawExtra:
    home_name: str
    away_name: str
    ah_size: float
    ah_home: float
    ah_away: float
    hg: int
    ag: int


def _f(v: str) -> float:
    return float(v) if v not in ("", None) else float("nan")


def seed_registry() -> AliasRegistry:
    """The canonical registry as used by walk_forward_v1: ``data/registry/seed.json`` only.

    ``AliasRegistry.from_directory`` would also ingest any other ``*.json`` dropped into the
    directory later (other research tracks add mapping files there), which could change team-id
    resolution and break reproducibility of the frozen protocol.
    """
    import json

    reg = AliasRegistry()
    payload = json.loads((REPO / "data" / "registry" / "seed.json").read_text(encoding="utf-8"))
    from soccer_edge.identity.models import Competition, Team

    for c in payload.get("competitions", []):
        reg.add_competition(Competition(**c))
    for t in payload.get("teams", []):
        reg.add_team(Team(**t))
    return reg


def load_data(
    divisions: tuple[str, ...] = DIVISIONS, csv_path: Path = MATCHES_CSV
) -> tuple[list[HistoricalMatch], list[RawExtra], str]:
    """Load provider rows for the study window plus the raw AH columns, row-aligned.

    The provider keeps CSV rows in file order after filtering on division / date / FT scores; we
    replay the same filter on the raw CSV and assert the alignment on goals and dates.
    """
    content = csv_path.read_bytes()
    data_hash = "sha256:" + hashlib.sha256(content).hexdigest()
    reg = seed_registry()
    obs = ClubFootballDataProvider(reg).load(
        divisions=divisions, start_date=f"{FIRST_SEASON_START}-07-01", content=content
    )
    matches = obs.payload
    wanted = set(divisions)
    extras: list[RawExtra] = []
    for r in csv.DictReader(io.StringIO(content.decode("utf-8"))):
        if r["Division"] not in wanted or r["MatchDate"] < f"{FIRST_SEASON_START}-07-01":
            continue
        if r["FTHome"] == "" or r["FTAway"] == "":
            continue
        extras.append(
            RawExtra(
                r["HomeTeam"],
                r["AwayTeam"],
                _f(r["HandiSize"]),
                _f(r["HandiHome"]),
                _f(r["HandiAway"]),
                int(float(r["FTHome"])),
                int(float(r["FTAway"])),
            )
        )
    if len(extras) != len(matches):
        raise RuntimeError(f"raw/provider row mismatch: {len(extras)} vs {len(matches)}")
    for m, e in zip(matches, extras, strict=True):
        if m.result.home_goals != e.hg or m.result.away_goals != e.ag:
            raise RuntimeError("raw/provider alignment failure")
    return matches, extras, data_hash


# --------------------------------------------------------------------------------------------
# vectorised Dixon-Coles score matrices (identical per sample to model.analytic.score_matrix)
# --------------------------------------------------------------------------------------------
def score_matrices(
    lams: np.ndarray, mus: np.ndarray, rhos: np.ndarray, max_goals: int = MAX_GOALS
) -> np.ndarray:
    """(S,) rates -> (S, G+1, G+1) renormalised DC score matrices."""
    i = np.arange(max_goals + 1)
    ph = poisson.pmf(i[None, :], lams[:, None])
    pa = poisson.pmf(i[None, :], mus[:, None])
    m = ph[:, :, None] * pa[:, None, :]
    m[:, 0, 0] *= 1 - lams * mus * rhos
    m[:, 0, 1] *= 1 + lams * rhos
    m[:, 1, 0] *= 1 + mus * rhos
    m[:, 1, 1] *= 1 - rhos
    m = np.clip(m, 0, None)
    return m / m.sum(axis=(1, 2), keepdims=True)


def outcome_probs_batch(m: np.ndarray) -> np.ndarray:
    """(S, G, G) -> (S, 3) [home, draw, away]."""
    g = m.shape[-1]
    ii, jj = np.meshgrid(np.arange(g), np.arange(g), indexing="ij")
    home = m[:, ii > jj].sum(axis=1)
    draw = m[:, ii == jj].sum(axis=1)
    away = m[:, ii < jj].sum(axis=1)
    return np.stack([home, draw, away], axis=1)


def total_over_matrix(m: np.ndarray, line: float) -> float:
    g = m.shape[0]
    idx = np.add.outer(np.arange(g), np.arange(g))
    return float(m[idx > line].sum())


# --------------------------------------------------------------------------------------------
# the walk-forward loop
# --------------------------------------------------------------------------------------------
def run_walk_forward(
    matches: list[HistoricalMatch],
    extras: list[RawExtra],
    strength: StrengthConfig,
    *,
    keep_matrix: bool,
    posterior_samples: int = POSTERIOR_SAMPLES,
    divisions: tuple[str, ...] = DIVISIONS,
    seed: int = 0,
    verbose: bool = True,
) -> dict[str, np.ndarray]:
    """Return a column table (dict of arrays) with one row per scored prediction.

    Row order and RNG draw order are identical to ``research/walk_forward.run`` so the frozen v1
    numbers reproduce (up to float summation order in the vectorised score matrix).
    """
    t0 = time.time()
    rng = np.random.default_rng(seed)
    cols: dict[str, list] = defaultdict(list)
    for div in divisions:
        order = sorted(
            [i for i, m in enumerate(matches) if m.division == div],
            key=lambda i: matches[i].result.match_date,
        )
        if not order:
            continue
        rows = [matches[i] for i in order]
        ext = [extras[i] for i in order]
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
        post = None
        last_fit: date | None = None
        seen: dict[str, int] = defaultdict(int)
        last_played: dict[str, date] = {}
        season_games: dict[tuple[str, str], int] = defaultdict(int)
        teams_by_season: dict[str, set[str]] = defaultdict(set)
        season_first_date: dict[str, date] = {}
        for d in dates:
            ids = idx_by_date[d]
            season = rows[ids[0]].result.season_id
            s0 = season_start(season)
            season_first_date.setdefault(season, d)
            if s0 > LAST_SEASON_START:
                break
            if s0 >= FIRST_SEASON_START:
                fit_rows = [r for r in mrows if r.date < d]
                if (last_fit is None or (d - last_fit).days >= REFIT_DAYS) and len(fit_rows) >= 100:
                    post = fitter_for(strength.version).fit(fit_rows, as_of=d)
                    last_fit = d
            prev_season = f"{s0 - 1}-{str(s0)[2:]}"
            for i in ids:
                hm, mr, ex = rows[i], mrows[i], ext[i]
                scored = (
                    post is not None
                    and s0 > FIRST_SEASON_START
                    and seen[mr.home] >= MIN_TEAM_MATCHES
                    and seen[mr.away] >= MIN_TEAM_MATCHES
                    and mr.home in post.teams
                    and mr.away in post.teams
                )
                odds = {(o.market, o.selection): o.decimal_odds for o in hm.odds}
                has_1x2 = all((("1x2", s) in odds) for s in ("home", "draw", "away"))
                if scored and has_1x2:
                    assert post is not None and last_fit is not None
                    lam, mu = post.expected_goals(mr.home, mr.away)
                    params = post.sample(posterior_samples, rng)
                    lams, mus, rhos = post.rates_for(params, mr.home, mr.away)
                    mats = score_matrices(lams, mus, rhos, strength.max_goals)
                    op = outcome_probs_batch(mats)
                    p_data = op.mean(axis=0)
                    mat = mats.mean(axis=0)
                    ph = op[:, 0]
                    lo = float(np.quantile(ph, (1 - INTERVAL_LEVEL) / 2))
                    hi = float(np.quantile(ph, 1 - (1 - INTERVAL_LEVEL) / 2))
                    p_data_o25 = float(np.mean([total_over_matrix(m, 2.5) for m in mats]))
                    p_mkt = devig_proportional(
                        np.array(
                            [[odds[("1x2", "home")], odds[("1x2", "draw")], odds[("1x2", "away")]]]
                        )
                    )[0]
                    if ("ou", "over") in odds and ("ou", "under") in odds:
                        oo, ou = odds[("ou", "over")], odds[("ou", "under")]
                        p_mkt_o25 = float(devig_proportional(np.array([[oo, ou]]))[0][0])
                    else:
                        oo = ou = p_mkt_o25 = float("nan")
                    # Laplace sd of the log-rate difference log(lam) - log(mu)
                    P = len(post.mean)
                    v = np.zeros(P)
                    v[post.idx_attack(mr.home)] += 1
                    v[post.idx_defence(mr.away)] -= 1
                    v[post.idx_home] += 1
                    v[post.idx_attack(mr.away)] -= 1
                    v[post.idx_defence(mr.home)] += 1
                    sd_logdiff = float(np.sqrt(max(v @ post.cov @ v, 0.0)))
                    vs = np.zeros(P)
                    vs[post.idx_attack(mr.home)] += 1
                    vs[post.idx_defence(mr.away)] -= 1
                    vs[post.idx_home] += 1
                    vs[post.idx_attack(mr.away)] += 1
                    vs[post.idx_defence(mr.home)] -= 1
                    ik = getattr(post, "idx_intercept", None)
                    if ik is not None:
                        vs[ik] += 2
                    sd_logsum = float(np.sqrt(max(vs @ post.cov @ vs, 0.0)))
                    y = (
                        0
                        if mr.home_goals > mr.away_goals
                        else (1 if mr.home_goals == mr.away_goals else 2)
                    )
                    cols["division"].append(div)
                    cols["season"].append(season)
                    cols["date"].append(mr.date.isoformat())
                    cols["home"].append(mr.home)
                    cols["away"].append(mr.away)
                    cols["home_name"].append(ex.home_name)
                    cols["away_name"].append(ex.away_name)
                    cols["y"].append(y)
                    cols["hg"].append(mr.home_goals)
                    cols["ag"].append(mr.away_goals)
                    cols["p_data"].append(p_data)
                    cols["p_mkt"].append(p_mkt)
                    cols["p_data_o25"].append(p_data_o25)
                    cols["p_mkt_o25"].append(p_mkt_o25)
                    cols["p_home_lo"].append(lo)
                    cols["p_home_hi"].append(hi)
                    if keep_matrix:
                        cols["mat"].append(mat.astype(np.float32))
                    cols["lam"].append(lam)
                    cols["mu"].append(mu)
                    cols["rho"].append(float(post.mean[post.idx_rho]))
                    cols["gamma_mean"].append(float(post.mean[post.idx_home]))
                    cols["gamma_sd"].append(float(np.sqrt(post.cov[post.idx_home, post.idx_home])))
                    cols["intercept"].append(
                        float(post.mean[ik]) if ik is not None else float("nan")
                    )
                    cols["fit_date"].append(last_fit.isoformat())
                    cols["days_since_refit"].append((d - last_fit).days)
                    cols["eff_home"].append(post.effective_matches.get(mr.home, 0.0))
                    cols["eff_away"].append(post.effective_matches.get(mr.away, 0.0))
                    cols["sd_logdiff"].append(sd_logdiff)
                    cols["sd_logsum"].append(sd_logsum)
                    cols["seen_home"].append(seen[mr.home])
                    cols["seen_away"].append(seen[mr.away])
                    cols["odds_1x2"].append(
                        [odds[("1x2", "home")], odds[("1x2", "draw")], odds[("1x2", "away")]]
                    )
                    cols["odds_ou"].append([oo, ou])
                    cols["ah_size"].append(ex.ah_size)
                    cols["ah_home"].append(ex.ah_home)
                    cols["ah_away"].append(ex.ah_away)
                    cols["elo_home"].append(hm.home_elo if hm.home_elo is not None else np.nan)
                    cols["elo_away"].append(hm.away_elo if hm.away_elo is not None else np.nan)
                    rh = (d - last_played[mr.home]).days if mr.home in last_played else -1
                    ra = (d - last_played[mr.away]).days if mr.away in last_played else -1
                    cols["rest_home"].append(rh)
                    cols["rest_away"].append(ra)
                    gh = season_games[(season, mr.home)]
                    ga = season_games[(season, mr.away)]
                    cols["matchday"].append(1 + 0.5 * (gh + ga))
                    cols["days_into_season"].append((d - season_first_date[season]).days)
                    cols["promoted_home"].append(int(mr.home not in teams_by_season[prev_season]))
                    cols["promoted_away"].append(int(mr.away not in teams_by_season[prev_season]))
                seen[mr.home] += 1
                seen[mr.away] += 1
                last_played[mr.home] = d
                last_played[mr.away] = d
                season_games[(season, mr.home)] += 1
                season_games[(season, mr.away)] += 1
                teams_by_season[season].add(mr.home)
                teams_by_season[season].add(mr.away)
        if verbose:
            n_div = sum(1 for x in cols["division"] if x == div)
            print(f"  {strength.version} {div}: {n_div} scored ({time.time() - t0:.0f}s)")
    table = {k: np.array(v) for k, v in cols.items()}
    table["_elapsed_s"] = np.array(time.time() - t0)
    return table


# --------------------------------------------------------------------------------------------
# alignment + hybrid (walk-forward blend weight fitted on strictly earlier seasons)
# --------------------------------------------------------------------------------------------
def aligned_mask(table: dict[str, np.ndarray]) -> np.ndarray:
    """Matches in seasons with >= MIN_PRIOR_FOR_HYBRID earlier predictions (hybrid warm-up
    excluded), exactly as ``walk_forward.summarise`` defines the aligned sample."""
    seasons = sorted(set(table["season"]), key=season_start)
    starts = np.array([season_start(s) for s in table["season"]])
    mask = np.zeros(len(starts), dtype=bool)
    for s in seasons:
        s0 = season_start(s)
        if int((starts < s0).sum()) >= MIN_PRIOR_FOR_HYBRID:
            mask |= starts == s0
    return mask


def hybrid_weights(table: dict[str, np.ndarray]) -> tuple[dict[str, float | None], np.ndarray]:
    seasons = sorted(set(table["season"]), key=season_start)
    starts = np.array([season_start(s) for s in table["season"]])
    P_hyb = np.full_like(table["p_data"], np.nan)
    w_by_season: dict[str, float | None] = {}
    for s in seasons:
        s0 = season_start(s)
        prior = starts < s0
        cur = starts == s0
        if int(prior.sum()) < MIN_PRIOR_FOR_HYBRID:
            w_by_season[s] = None
            continue
        w = fit_blend_weight(table["p_data"][prior], table["p_mkt"][prior], table["y"][prior])
        w_by_season[s] = w
        P_hyb[cur] = blend_logit(table["p_data"][cur], table["p_mkt"][cur], w)
    return w_by_season, P_hyb


# --------------------------------------------------------------------------------------------
# caching
# --------------------------------------------------------------------------------------------
def cache_key(variant: str, data_hash: str, posterior_samples: int, keep_matrix: bool) -> str:
    return content_hash(
        {
            "protocol": PROTOCOL_VERSION,
            "variant": variant,
            "strength": strength_for(variant).__dict__,
            "data_hash": data_hash,
            "posterior_samples": posterior_samples,
            "keep_matrix": keep_matrix,
            "divisions": DIVISIONS,
            "code_version": 4,
        }
    ).split(":")[1][:16]


def load_or_run(
    variant: str,
    matches: list[HistoricalMatch],
    extras: list[RawExtra],
    data_hash: str,
    *,
    keep_matrix: bool,
    posterior_samples: int = POSTERIOR_SAMPLES,
    verbose: bool = True,
) -> dict[str, np.ndarray]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = cache_key(variant, data_hash, posterior_samples, keep_matrix)
    path = CACHE_DIR / f"wf_{variant}_{key}.npz"
    if path.exists():
        with np.load(path, allow_pickle=False) as z:
            table = {k: z[k] for k in z.files}
        table["_from_cache"] = np.array(True)
        return table
    if verbose:
        print(f"running walk-forward for {variant} ...")
    table = run_walk_forward(
        matches,
        extras,
        strength_for(variant),
        keep_matrix=keep_matrix,
        posterior_samples=posterior_samples,
        verbose=verbose,
    )
    np.savez_compressed(path, **table)
    table["_from_cache"] = np.array(False)
    return table


def _variant_worker(args: tuple) -> str:
    variant, posterior_samples = args
    matches, extras, data_hash = load_data()
    load_or_run(
        variant,
        matches,
        extras,
        data_hash,
        keep_matrix=False,
        posterior_samples=posterior_samples,
        verbose=True,
    )
    return variant


def ensure_variants(
    variants: list[str], *, posterior_samples: int = POSTERIOR_SAMPLES, workers: int = 4
) -> None:
    """Run missing variant walk-forwards in parallel processes (each sequential internally)."""
    import multiprocessing as mp

    _, _, data_hash = load_data()
    todo = [
        v
        for v in variants
        if not (
            CACHE_DIR / f"wf_{v}_{cache_key(v, data_hash, posterior_samples, False)}.npz"
        ).exists()
    ]
    if not todo:
        return
    with mp.get_context("spawn").Pool(min(workers, len(todo))) as pool:
        for v in pool.imap_unordered(_variant_worker, [(v, posterior_samples) for v in todo]):
            print(f"variant done: {v}")


# --------------------------------------------------------------------------------------------
# metrics helpers shared by the studies
# --------------------------------------------------------------------------------------------
EPS = 1e-6


def binary_ll(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def multiclass_ll(P: np.ndarray, y: np.ndarray) -> np.ndarray:
    P = np.clip(P, EPS, 1)
    P = P / P.sum(axis=1, keepdims=True)
    return -np.log(P[np.arange(len(y)), y])


def ece(p: np.ndarray, y: np.ndarray, bins: int = 10, w: np.ndarray | None = None) -> float:
    w = np.ones_like(p) if w is None else w
    edges = np.linspace(0, 1, bins + 1)
    tot = w.sum()
    out = 0.0
    for i in range(bins):
        m = (p >= edges[i]) & ((p < edges[i + 1]) if i < bins - 1 else (p <= edges[i + 1]))
        if w[m].sum() == 0:
            continue
        mp_ = np.average(p[m], weights=w[m])
        mo = np.average(y[m], weights=w[m])
        out += w[m].sum() / tot * abs(mp_ - mo)
    return float(out)


def paired_ci(diff: np.ndarray, n_boot: int = 1000) -> dict:
    lo, hi = bootstrap_mean_ci(diff, n_boot=n_boot)
    return {"mean": round(float(diff.mean()), 5), "ci95": [round(lo, 5), round(hi, 5)]}


def tercile_labels(
    x: np.ndarray, names: tuple[str, str, str] = ("low", "mid", "high")
) -> tuple[np.ndarray, list[float]]:
    """Assign terciles by empirical quantiles (ties go to the lower bucket). Returns labels and
    the two cut points."""
    q1, q2 = np.quantile(x, [1 / 3, 2 / 3])
    lab = np.where(x <= q1, names[0], np.where(x <= q2, names[1], names[2]))
    return lab, [float(q1), float(q2)]


def bin_labels(x: np.ndarray, edges: list[float], fmt: str = "{:+.2f}") -> np.ndarray:
    """Label x by half-open bins [e_i, e_{i+1}) with open-ended tails; edges ascending."""
    out = np.empty(len(x), dtype=object)
    lo_name = f"<{fmt.format(edges[0])}"
    hi_name = f">={fmt.format(edges[-1])}"
    out[x < edges[0]] = lo_name
    out[x >= edges[-1]] = hi_name
    for a, b in zip(edges[:-1], edges[1:]):
        out[(x >= a) & (x < b)] = f"[{fmt.format(a)},{fmt.format(b)})"
    return out.astype(str)


def season_consistency(
    diff: np.ndarray, seasons: np.ndarray, min_n: int = 20
) -> dict[str, int | list[str]]:
    """How many scored seasons show data better (mean paired diff < 0) inside a cell."""
    better: list[str] = []
    worse: list[str] = []
    for s in sorted(set(seasons), key=season_start):
        m = seasons == s
        if m.sum() < min_n:
            continue
        (better if diff[m].mean() < 0 else worse).append(s)
    return {
        "seasons_data_better": len(better),
        "seasons_evaluated": len(better) + len(worse),
        "better_list": better,
    }


def frozen_v1_summary() -> dict:
    import json

    if not FROZEN_V1_JSON.exists():
        return {}
    d = json.loads(FROZEN_V1_JSON.read_text())
    return {
        "result_hash": d.get("result_hash"),
        "n_aligned_scored": d.get("n_aligned_scored"),
        "overall": d.get("overall"),
        "disagreement": d.get("disagreement"),
        "over25": d.get("over25"),
        "paired_logloss_diff_ci95": d.get("paired_logloss_diff_ci95"),
    }
