"""Point-in-time walk-forward evaluation: DATA_ONLY vs MARKET_ONLY vs HYBRID vs baselines.

Protocol (pre-registered in docs/CALIBRATION.md#walk-forward):
* Chronological only. For each league and each match date D, the DATA_ONLY posterior is refit on
  matches with date < D (refit cadence: every `refit_days`; between refits the last posterior is
  used, which only makes DATA_ONLY *staler*, never leaky).
* MARKET_ONLY = de-vigged Bet365 pre-match 1X2 / O-U 2.5 for the same match (not closing).
* HYBRID = logit blend; the weight for season S is fitted on predictions from seasons < S only.
* Baselines: league base rates (prior seasons only) and a home-advantage-only model.
* Aligned sample: matches where every family has a prediction (odds present, teams seen >= 5 times).
* The first evaluated season is preceded by one burn-in season that is never scored.
* Negative results are reported as-is.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np

from soccer_edge.core.serialization import content_hash, write_json
from soccer_edge.evaluation.metrics import (
    bootstrap_mean_ci,
    brier,
    expected_calibration_error,
    interval_calibration,
    log_loss,
    multiclass_brier,
    multiclass_log_loss,
)
from soccer_edge.families.base import blend_logit, devig_proportional, fit_blend_weight
from soccer_edge.identity.registry import AliasRegistry
from soccer_edge.model.analytic import outcome_probs, score_matrix, total_over
from soccer_edge.model.strength import DixonColesFitter, MatchRow, StrengthConfig
from soccer_edge.providers.club_football_data import ClubFootballDataProvider, HistoricalMatch

REPO = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = "walk_forward_v1"


@dataclass
class Pred:
    division: str
    season: str
    match_date: str
    y: int  # 0 home, 1 draw, 2 away
    total: int
    p_data: np.ndarray
    p_mkt: np.ndarray
    p_base: np.ndarray
    p_home_only: np.ndarray
    p_data_o25: float
    p_mkt_o25: float | None
    p_home_lo: float
    p_home_hi: float
    lam: float
    mu: float
    mkt_odds_home: float


@dataclass
class Config:
    divisions: tuple[str, ...] = ("E0", "SP1", "D1", "I1", "F1")
    first_season_start: int = 2017  # burn-in season 2017-18; scoring starts 2018-19
    last_season_start: int = 2025
    refit_days: int = 7
    min_team_matches: int = 5
    posterior_samples: int = 200
    interval_level: float = 0.80
    min_prior_for_hybrid: int = (
        500  # hybrid weight needs this many earlier predictions; earlier seasons are hybrid warm-up
    )
    strength: StrengthConfig = field(default_factory=StrengthConfig)


def _season_start(season: str) -> int:
    return int(season[:4])


def run(cfg: Config, matches: list[HistoricalMatch], *, verbose: bool = True) -> dict:
    t0 = time.time()
    preds: list[Pred] = []
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
        post = None
        last_fit: date | None = None
        seen: dict[str, int] = defaultdict(int)
        idx_by_date: dict[date, list[int]] = defaultdict(list)
        for i, r in enumerate(mrows):
            idx_by_date[r.date].append(i)
        # season-level priors for baselines
        season_counts: dict[str, np.ndarray] = defaultdict(lambda: np.zeros(3))
        season_hadv: dict[str, list[float]] = defaultdict(list)
        for d in dates:
            ids = idx_by_date[d]
            season = rows[ids[0]].result.season_id
            s0 = _season_start(season)
            if s0 < cfg.first_season_start:
                for i in ids:
                    _bump(seen, season_counts, season_hadv, rows[i], mrows[i])
                continue
            if s0 > cfg.last_season_start:
                break
            fit_rows = [r for r in mrows if r.date < d]
            if last_fit is None or (d - last_fit).days >= cfg.refit_days:
                if len(fit_rows) >= 100:
                    post = DixonColesFitter(cfg.strength).fit(fit_rows, as_of=d)
                    last_fit = d
            prior_seasons = [s for s in season_counts if _season_start(s) < s0]
            base = sum((season_counts[s] for s in prior_seasons), np.zeros(3))
            p_base = (base + 1) / (base.sum() + 3)
            hadv = (
                np.mean([x for s in prior_seasons for x in season_hadv[s]])
                if prior_seasons
                else 0.3
            )
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
                    lam, mu = post.expected_goals(mr.home, mr.away)
                    rho = float(post.mean[post.idx_rho])
                    # integrate over the posterior (parameter uncertainty) instead of plugging in the mean
                    params = post.sample(cfg.posterior_samples, rng)
                    lams, mus, rhos = post.rates_for(params, mr.home, mr.away)
                    ph = np.zeros(cfg.posterior_samples)
                    acc = np.zeros(3)
                    o25 = 0.0
                    for k in range(cfg.posterior_samples):
                        m = score_matrix(float(lams[k]), float(mus[k]), float(rhos[k]))
                        op = outcome_probs(m)
                        ph[k] = op["home"]
                        acc += np.array([op["home"], op["draw"], op["away"]])
                        o25 += total_over(m, 2.5)
                    p_data = acc / cfg.posterior_samples
                    p_data_o25 = o25 / cfg.posterior_samples
                    lo, hi = (
                        np.quantile(ph, (1 - cfg.interval_level) / 2),
                        np.quantile(ph, 1 - (1 - cfg.interval_level) / 2),
                    )
                    p_mkt = devig_proportional(
                        np.array(
                            [[odds[("1x2", "home")], odds[("1x2", "draw")], odds[("1x2", "away")]]]
                        )
                    )[0]
                    p_mkt_o25 = None
                    if ("ou", "over") in odds and ("ou", "under") in odds:
                        p_mkt_o25 = float(
                            devig_proportional(
                                np.array([[odds[("ou", "over")], odds[("ou", "under")]]])
                            )[0][0]
                        )
                    # home-advantage-only: league-average goals with home adv
                    lam_b = float(np.exp(np.log(max(base.sum(), 1) and 1.35) + hadv / 2))
                    mu_b = float(np.exp(np.log(1.35) - hadv / 2))
                    opb = outcome_probs(score_matrix(lam_b, mu_b, rho))
                    y = (
                        0
                        if mr.home_goals > mr.away_goals
                        else (1 if mr.home_goals == mr.away_goals else 2)
                    )
                    preds.append(
                        Pred(
                            div,
                            season,
                            mr.date.isoformat(),
                            y,
                            mr.home_goals + mr.away_goals,
                            p_data,
                            p_mkt,
                            p_base.copy(),
                            np.array([opb["home"], opb["draw"], opb["away"]]),
                            p_data_o25,
                            p_mkt_o25,
                            float(lo),
                            float(hi),
                            lam,
                            mu,
                            odds[("1x2", "home")],
                        )
                    )
                _bump(seen, season_counts, season_hadv, hm, mr)
        if verbose:
            print(
                f"{div}: {sum(1 for p in preds if p.division == div)} scored predictions ({time.time() - t0:.0f}s)"
            )
    return summarise(cfg, preds, time.time() - t0)


def _bump(seen, season_counts, season_hadv, hm: HistoricalMatch, mr: MatchRow) -> None:
    seen[mr.home] += 1
    seen[mr.away] += 1
    y = 0 if mr.home_goals > mr.away_goals else (1 if mr.home_goals == mr.away_goals else 2)
    season_counts[hm.result.season_id][y] += 1
    season_hadv[hm.result.season_id].append(np.log((mr.home_goals + 0.5) / (mr.away_goals + 0.5)))


def _metrics3(P: np.ndarray, y: np.ndarray) -> dict:
    return {
        "log_loss": round(multiclass_log_loss(P, y), 5),
        "brier": round(multiclass_brier(P, y), 5),
        "ece_home": round(expected_calibration_error(P[:, 0], (y == 0).astype(int)), 4),
        "n": len(y),
    }


def summarise(cfg: Config, preds: list[Pred], elapsed: float) -> dict:
    if not preds:
        return {"error": "no predictions"}
    seasons = sorted({p.season for p in preds}, key=_season_start)
    # HYBRID weights: fitted on strictly earlier seasons
    w_by_season: dict[str, float | None] = {}
    P_hyb = np.zeros((len(preds), 3))
    for s in seasons:
        prior = [i for i, p in enumerate(preds) if _season_start(p.season) < _season_start(s)]
        cur = [i for i, p in enumerate(preds) if p.season == s]
        if len(prior) < cfg.min_prior_for_hybrid:
            w_by_season[s] = None
            for i in cur:
                P_hyb[i] = np.nan
            continue
        w = fit_blend_weight(
            np.stack([preds[i].p_data for i in prior]),
            np.stack([preds[i].p_mkt for i in prior]),
            np.array([preds[i].y for i in prior]),
        )
        w_by_season[s] = w
        for i in cur:
            P_hyb[i] = blend_logit(preds[i].p_data[None, :], preds[i].p_mkt[None, :], w)[0]
    aligned = [i for i in range(len(preds)) if not np.isnan(P_hyb[i, 0])]
    if not aligned:
        return {
            "error": "no aligned predictions (need more seasons for the hybrid warm-up)",
            "n_predictions_total": len(preds),
        }
    y = np.array([preds[i].y for i in aligned])
    fam = {
        "data_only.dc_laplace_v1": np.stack([preds[i].p_data for i in aligned]),
        "market_only.bet365_prematch_v1": np.stack([preds[i].p_mkt for i in aligned]),
        "hybrid.logit_blend_v1": P_hyb[aligned],
        "baseline.league_base_rates": np.stack([preds[i].p_base for i in aligned]),
        "baseline.home_advantage_only": np.stack([preds[i].p_home_only for i in aligned]),
    }
    out: dict = {
        "protocol": PROTOCOL_VERSION,
        "config": {
            **{k: v for k, v in cfg.__dict__.items() if k != "strength"},
            "strength": cfg.strength.__dict__,
        },
        "elapsed_s": round(elapsed, 1),
        "n_predictions_total": len(preds),
        "n_aligned_scored": len(aligned),
        "seasons_scored": [s for s in seasons if w_by_season.get(s) is not None],
        "hybrid_weight_by_season": w_by_season,
        "overall": {k: _metrics3(P, y) for k, P in fam.items()},
        "by_league": {},
        "by_season": {},
        "over25": {},
        "disagreement": {},
        "interval_calibration_p_home": {},
        "paired_logloss_diff_ci95": {},
        "naive_betting_vs_bet365": {},
    }
    divs = np.array([preds[i].division for i in aligned])
    seas = np.array([preds[i].season for i in aligned])
    for d in sorted(set(divs)):
        m = divs == d
        out["by_league"][d] = {k: _metrics3(P[m], y[m]) for k, P in fam.items()}
    for s in sorted(set(seas), key=_season_start):
        m = seas == s
        out["by_season"][s] = {k: _metrics3(P[m], y[m]) for k, P in fam.items()}
    # O/U 2.5
    io = [i for i in aligned if preds[i].p_mkt_o25 is not None]
    if io:
        yo = np.array([preds[i].total > 2.5 for i in io]).astype(int)
        pd_ = np.array([preds[i].p_data_o25 for i in io])
        pm_ = np.array([preds[i].p_mkt_o25 for i in io])
        out["over25"] = {
            "n": len(io),
            "data_only": {
                "log_loss": round(log_loss(pd_, yo), 5),
                "brier": round(brier(pd_, yo), 5),
                "ece": round(expected_calibration_error(pd_, yo), 4),
                "mean_pred": round(float(pd_.mean()), 4),
                "base_rate": round(float(yo.mean()), 4),
            },
            "market_only": {
                "log_loss": round(log_loss(pm_, yo), 5),
                "brier": round(brier(pm_, yo), 5),
                "ece": round(expected_calibration_error(pm_, yo), 4),
                "mean_pred": round(float(pm_.mean()), 4),
            },
        }
    # disagreement: who is right when the model and the market differ by > 0.10 on P(home)
    pdh = fam["data_only.dc_laplace_v1"][:, 0]
    pmh = fam["market_only.bet365_prematch_v1"][:, 0]
    yh = (y == 0).astype(int)
    for thr in (0.05, 0.10, 0.15):
        m = np.abs(pdh - pmh) > thr
        if m.sum() > 30:
            out["disagreement"][f">{thr}"] = {
                "n": int(m.sum()),
                "data_logloss": round(log_loss(pdh[m], yh[m]), 5),
                "market_logloss": round(log_loss(pmh[m], yh[m]), 5),
                "realised_home_rate": round(float(yh[m].mean()), 4),
                "data_mean": round(float(pdh[m].mean()), 4),
                "market_mean": round(float(pmh[m].mean()), 4),
            }
    # interval calibration of the posterior 80% interval on P(home)
    lo = np.array([preds[i].p_home_lo for i in aligned])
    hi = np.array([preds[i].p_home_hi for i in aligned])
    out["interval_calibration_p_home"] = interval_calibration(
        pdh, lo, hi, yh, level=cfg.interval_level
    )
    # Market-as-oracle: how often does the de-vigged market probability fall inside our interval?
    # If the market is close to the truth, an honest 80% interval should contain it ~80% of the
    # time; much higher means our intervals are too wide, much lower too narrow.
    inside = (pmh >= lo) & (pmh <= hi)
    ic = out["interval_calibration_p_home"]
    ic["market_inside_interval_rate"] = round(float(inside.mean()), 4)
    ic["mean_abs_data_minus_market"] = round(float(np.abs(pdh - pmh).mean()), 4)
    for w in (0.05, 0.10, 0.15):
        ic[f"share_market_within_{w}"] = round(float((np.abs(pdh - pmh) <= w).mean()), 4)
    # paired differences vs market (bootstrap CI on mean per-match log-loss difference)
    lm = -np.log(np.clip(fam["market_only.bet365_prematch_v1"][np.arange(len(y)), y], 1e-9, 1))
    for k, P in fam.items():
        if k.startswith("market_only"):
            continue
        lk = -np.log(np.clip(P[np.arange(len(y)), y], 1e-9, 1))
        diff = lk - lm
        ci = bootstrap_mean_ci(diff, n_boot=1000)
        out["paired_logloss_diff_ci95"][k] = {
            "mean_diff_vs_market": round(float(diff.mean()), 5),
            "ci95": [round(ci[0], 5), round(ci[1], 5)],
            "interpretation": "positive = worse than market",
        }
    # naive betting sanity check at Bet365 prices (informational; Bet365 != Kalshi)
    oh = np.array([preds[i].mkt_odds_home for i in aligned])
    for edge in (0.03, 0.05, 0.10):
        bet = pdh - 1 / oh > edge
        if bet.sum() > 20:
            pnl = np.where(yh[bet] == 1, oh[bet] - 1, -1.0)
            out["naive_betting_vs_bet365"][f"home_edge>{edge}"] = {
                "n_bets": int(bet.sum()),
                "roi": round(float(pnl.mean()), 4),
                "hit_rate": round(float(yh[bet].mean()), 4),
            }
    out["result_hash"] = content_hash({k: v for k, v in out.items() if k not in ("elapsed_s",)})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--matches-csv", default=None, help="local Matches.csv (else fetched from GitHub raw)"
    )
    ap.add_argument("--divisions", default="E0,SP1,D1,I1,F1")
    ap.add_argument("--first-season", type=int, default=2017)
    ap.add_argument("--last-season", type=int, default=2025)
    ap.add_argument("--posterior-samples", type=int, default=200)
    ap.add_argument("--out", default=str(REPO / "data" / "research" / "walk_forward_v1.json"))
    a = ap.parse_args()
    reg = AliasRegistry.from_directory(REPO / "data" / "registry")
    prov = ClubFootballDataProvider(reg)
    content = Path(a.matches_csv).read_bytes() if a.matches_csv else None
    divs = tuple(a.divisions.split(","))
    obs = prov.load(divisions=divs, start_date=f"{a.first_season}-07-01", content=content)
    print(
        f"loaded {len(obs.payload)} matches; flags={[f.value for f in obs.flags]}; notes={obs.notes}"
    )
    cfg = Config(
        divisions=divs,
        first_season_start=a.first_season,
        last_season_start=a.last_season,
        posterior_samples=a.posterior_samples,
    )
    res = run(cfg, obs.payload)
    res["data_provenance"] = {
        "source": obs.provenance.source,
        "content_hash": obs.provenance.content_hash,
        "observed_at": obs.provenance.observed_at.isoformat(),
        "notes": list(obs.notes),
    }
    write_json(Path(a.out), res)
    print(
        json.dumps(
            {
                "overall": res["overall"],
                "hybrid_w": res["hybrid_weight_by_season"],
                "over25": res.get("over25"),
                "disagreement": res.get("disagreement"),
                "interval": {
                    k: v for k, v in res["interval_calibration_p_home"].items() if k != "bins"
                },
                "paired": res["paired_logloss_diff_ci95"],
                "naive": res["naive_betting_vs_bet365"],
            },
            indent=1,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
