"""Why does DATA_ONLY over-rate home sides when it disagrees with the market by > 10 pts?

Frozen finding (walk_forward_v1): among aligned matches with |P_data(home) - P_mkt(home)| > 0.10
the data mean P(home) is 0.458, the realised home rate 0.397 and the market mean 0.396.

Seven hypotheses, each with a pre-stated test (see docs/RESEARCH_HOME_BIAS.md):
  H1 home-advantage parameter too large / too slow to adapt
  H2 league / season heterogeneity (e.g. post-COVID 2020-21 empty stadiums)
  H3 promoted-team (thin-history) priors
  H4 opponent adjustment / strength shrinkage (under-rating away favourites)
  H5 staleness (days since refit, early season)
  H6 selection effect (regression to the mean)
  H7 schedule / rest proxies (domestic data only)
  H8 (added after H1-H7 were run) structural: no scoring intercept in the frozen fitter

Everything is chronological walk-forward exactly as ``research/walk_forward.py``; alternative
configurations are separately named candidates (``dc_laplace_v1.decay003`` ...) and the frozen
``StrengthConfig`` defaults are never edited.  Output: ``data/research/home_bias_v1.json``.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize, root

from research import wf_common as wf
from soccer_edge.core.serialization import content_hash, write_json
from soccer_edge.evaluation.metrics import (
    expected_calibration_error,
    multiclass_brier,
    multiclass_log_loss,
)
from soccer_edge.model.analytic import outcome_probs, score_matrix, total_over

OUT = wf.REPO / "data" / "research" / "home_bias_v1.json"
DISAGREE_THR = 0.10
H1_VARIANTS = (
    "dc_laplace_v1.decay003",
    "dc_laplace_v1.decay010",
    "dc_laplace_v1.gamma_sd005",
    "dc_laplace_v1.gamma_sd050",
)
H3_VARIANTS = ("dc_laplace_v1.newteam_mean000", "dc_laplace_v1.newteam_mean-030")
H4_VARIANTS = ("dc_laplace_v1.team_sd060",)
H8_VARIANTS = (
    "dc_laplace_v1.intercept",
    "dc_laplace_v1.intercept_sd060",
    "dc_laplace_v1.intercept_decay003",
)


# --------------------------------------------------------------------------------------------
# pure helpers
# --------------------------------------------------------------------------------------------
def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def fit_logistic(X: np.ndarray, y: np.ndarray, l2: float = 1e-4) -> np.ndarray:
    """Logistic regression with intercept (column of ones prepended) and a tiny ridge."""
    Xb = np.column_stack([np.ones(len(y)), X])

    def f(b):
        z = Xb @ b
        p = 1 / (1 + np.exp(-z))
        ll = -np.mean(y * np.log(np.clip(p, 1e-9, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-9, 1)))
        g = Xb.T @ (p - y) / len(y)
        return ll + 0.5 * l2 * np.sum(b[1:] ** 2), g + l2 * np.r_[0.0, b[1:]]

    return minimize(f, np.zeros(Xb.shape[1]), jac=True, method="L-BFGS-B").x


def predict_logistic(beta: np.ndarray, X: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-(np.column_stack([np.ones(len(X)), X]) @ beta)))


def market_implied_rates(
    p_mkt: np.ndarray, p_over25: float, rho: float, lam0: float = 1.4, mu0: float = 1.1
) -> tuple[float, float]:
    """Invert the DC model: find (lam, mu) reproducing the market's home-away spread and P(over
    2.5). Returns (nan, nan) if the root finder fails."""
    spread = float(p_mkt[0] - p_mkt[2])

    def g(x):
        m = score_matrix(float(np.exp(x[0])), float(np.exp(x[1])), rho)
        op = outcome_probs(m)
        return [op["home"] - op["away"] - spread, total_over(m, 2.5) - p_over25]

    sol = root(g, [np.log(lam0), np.log(mu0)], method="hybr", options={"xtol": 1e-8})
    if not sol.success:
        return float("nan"), float("nan")
    return float(np.exp(sol.x[0])), float(np.exp(sol.x[1]))


# --------------------------------------------------------------------------------------------
# bucket statistics on P(home)
# --------------------------------------------------------------------------------------------
def home_stats(T: dict, m: np.ndarray, with_ci: bool = False) -> dict:
    yh = (T["y"][m] == 0).astype(float)
    pd_, pm_ = T["p_data"][m, 0], T["p_mkt"][m, 0]
    if m.sum() == 0:
        return {"n": 0}
    out = {
        "n": int(m.sum()),
        "data_mean": round(float(pd_.mean()), 4),
        "market_mean": round(float(pm_.mean()), 4),
        "realised": round(float(yh.mean()), 4),
        "bias_data": round(float(pd_.mean() - yh.mean()), 4),
        "bias_market": round(float(pm_.mean() - yh.mean()), 4),
        "data_ll_home": round(float(wf.binary_ll(pd_, yh).mean()), 5),
        "market_ll_home": round(float(wf.binary_ll(pm_, yh).mean()), 5),
    }
    if with_ci and m.sum() > 30:
        out["paired_ll_diff_home"] = wf.paired_ci(wf.binary_ll(pd_, yh) - wf.binary_ll(pm_, yh))
    return out


def disagreement_block(T: dict, base_mask: np.ndarray, sub: np.ndarray | None = None) -> dict:
    """Stats for the |gap|>thr bucket (and the signed halves) inside base_mask & sub."""
    m = base_mask if sub is None else (base_mask & sub)
    gap = T["p_data"][:, 0] - T["p_mkt"][:, 0]
    d_abs = m & (np.abs(gap) > DISAGREE_THR)
    d_pos = m & (gap > DISAGREE_THR)
    d_neg = m & (gap < -DISAGREE_THR)
    return {
        "n_total": int(m.sum()),
        "share_in_bucket": round(float(d_abs.sum() / max(m.sum(), 1)), 4),
        "share_positive_among_bucket": round(float(d_pos.sum() / max(d_abs.sum(), 1)), 4),
        "abs": home_stats(T, d_abs),
        "data_above_market": home_stats(T, d_pos),
        "data_below_market": home_stats(T, d_neg),
        "all": home_stats(T, m),
    }


def family_metrics(T: dict, am: np.ndarray, P_data: np.ndarray) -> dict:
    y = T["y"][am]
    P_m = T["p_mkt"][am]
    lld = wf.multiclass_ll(P_data, y)
    llm = wf.multiclass_ll(P_m, y)
    return {
        "n": int(am.sum()),
        "log_loss": round(multiclass_log_loss(P_data, y), 5),
        "brier": round(multiclass_brier(P_data, y), 5),
        "ece_home": round(expected_calibration_error(P_data[:, 0], (y == 0).astype(int)), 4),
        "market_log_loss": round(multiclass_log_loss(P_m, y), 5),
        "paired_ll_diff_vs_market": wf.paired_ci(lld - llm),
    }


def variant_summary(V: dict, B: dict, am: np.ndarray) -> dict:
    """Aligned 1X2 metrics of a variant vs the frozen v1 table B and vs the market."""
    assert np.array_equal(V["date"], B["date"]) and np.array_equal(V["home"], B["home"])
    fm = family_metrics(V, am, V["p_data"][am])
    y = V["y"][am]
    fm["paired_ll_diff_vs_v1"] = wf.paired_ci(
        wf.multiclass_ll(V["p_data"][am], y) - wf.multiclass_ll(B["p_data"][am], y)
    )
    yo = (V["hg"] + V["ag"] > 2)[am].astype(float)
    fm["over25_log_loss"] = round(float(wf.binary_ll(V["p_data_o25"][am], yo).mean()), 5)
    fm["mean_gamma"] = round(float(V["gamma_mean"][am].mean()), 4)
    fm["mean_gamma_sd"] = round(float(V["gamma_sd"][am].mean()), 4)
    w, _ = wf.hybrid_weights(V)
    fm["hybrid_weight_by_season"] = w
    fm["disagreement"] = disagreement_block(V, am)
    return fm


# --------------------------------------------------------------------------------------------
# hypotheses
# --------------------------------------------------------------------------------------------
def h1_home_advantage(B: dict, am: np.ndarray, variants: dict[str, dict]) -> dict:
    """Fitted gamma vs market-implied gamma vs realised, per league-season; decay / prior variants."""
    t0 = time.time()
    # market-implied goal rates per match (needs O/U odds)
    n = len(B["y"])
    lam_m = np.full(n, np.nan)
    mu_m = np.full(n, np.nan)
    ok = ~np.isnan(B["p_mkt_o25"])
    for i in np.where(ok)[0]:
        lam_m[i], mu_m[i] = market_implied_rates(
            B["p_mkt"][i], float(B["p_mkt_o25"][i]), float(B["rho"][i]), B["lam"][i], B["mu"][i]
        )
    good = ~np.isnan(lam_m)
    rows = []
    for div in wf.DIVISIONS:
        for s in sorted(set(B["season"]), key=wf.season_start):
            m = (B["division"] == div) & (B["season"] == s)
            if m.sum() < 50:
                continue
            mg = m & good
            hg, ag = B["hg"][m], B["ag"][m]
            yh = (B["y"][m] == 0).astype(float)
            rows.append(
                {
                    "division": div,
                    "season": s,
                    "n": int(m.sum()),
                    "gamma_fit_mean": round(float(B["gamma_mean"][m].mean()), 4),
                    "gamma_fit_sd_mean": round(float(B["gamma_sd"][m].mean()), 4),
                    "gamma_fit_min_max": [
                        round(float(B["gamma_mean"][m].min()), 4),
                        round(float(B["gamma_mean"][m].max()), 4),
                    ],
                    "data_mean_log_rate_ratio": round(
                        float(np.mean(np.log(B["lam"][m] / B["mu"][m]))), 4
                    ),
                    "market_implied_mean_log_rate_ratio": round(
                        float(np.mean(np.log(lam_m[mg] / mu_m[mg]))), 4
                    ),
                    "realised_log_goal_ratio": round(float(np.log(hg.mean() / ag.mean())), 4),
                    "realised_home_goals_minus_away": round(float(hg.mean() - ag.mean()), 4),
                    "data_mean_p_home": round(float(B["p_data"][m, 0].mean()), 4),
                    "market_mean_p_home": round(float(B["p_mkt"][m, 0].mean()), 4),
                    "realised_home_rate": round(float(yh.mean()), 4),
                    "data_mean_p_away": round(float(B["p_data"][m, 2].mean()), 4),
                    "market_mean_p_away": round(float(B["p_mkt"][m, 2].mean()), 4),
                    "realised_away_rate": round(float((B["y"][m] == 2).mean()), 4),
                }
            )
    dg_mkt = np.array([r["gamma_fit_mean"] - r["market_implied_mean_log_rate_ratio"] for r in rows])
    dg_real = np.array([r["gamma_fit_mean"] - r["realised_log_goal_ratio"] for r in rows])
    dp_home = np.array([r["data_mean_p_home"] - r["realised_home_rate"] for r in rows])
    dm_home = np.array([r["market_mean_p_home"] - r["realised_home_rate"] for r in rows])
    # market-implied gamma via the market's own log-rate ratio, aggregated over aligned matches
    summary = {
        "n_league_seasons": len(rows),
        "mean_gamma_fit_minus_market_implied": round(float(dg_mkt.mean()), 4),
        "share_league_seasons_gamma_fit_above_market_by_0.05": round(
            float((dg_mkt > 0.05).mean()), 3
        ),
        "mean_gamma_fit_minus_realised": round(float(dg_real.mean()), 4),
        "mean_data_p_home_minus_realised": round(float(dp_home.mean()), 4),
        "mean_market_p_home_minus_realised": round(float(dm_home.mean()), 4),
        "aligned_overall": {
            "data_mean_p_home": round(float(B["p_data"][am, 0].mean()), 4),
            "market_mean_p_home": round(float(B["p_mkt"][am, 0].mean()), 4),
            "realised_home_rate": round(float((B["y"][am] == 0).mean()), 4),
            "data_mean_log_rate_ratio": round(
                float(np.mean(np.log(B["lam"][am] / B["mu"][am]))), 4
            ),
            "market_implied_mean_log_rate_ratio": round(
                float(np.nanmean(np.log(lam_m[am] / mu_m[am]))), 4
            ),
            "realised_log_goal_ratio": round(
                float(np.log(B["hg"][am].mean() / B["ag"][am].mean())), 4
            ),
            "mean_gamma_fit": round(float(B["gamma_mean"][am].mean()), 4),
            "market_inversion_success_rate": round(float(good[am].mean()), 4),
        },
    }
    # in the disagreement bucket: is the *home-advantage* part of the log-rate gap large?
    gap = B["p_data"][:, 0] - B["p_mkt"][:, 0]
    d_pos = am & (gap > DISAGREE_THR) & good
    d_neg = am & (gap < -DISAGREE_THR) & good
    summary["log_rate_ratio_gap_in_bucket"] = {
        "data_above_market": {
            "n": int(d_pos.sum()),
            "mean_data_log_ratio": round(float(np.log(B["lam"][d_pos] / B["mu"][d_pos]).mean()), 4),
            "mean_market_log_ratio": round(float(np.log(lam_m[d_pos] / mu_m[d_pos]).mean()), 4),
            "mean_data_lam": round(float(B["lam"][d_pos].mean()), 4),
            "mean_market_lam": round(float(lam_m[d_pos].mean()), 4),
            "mean_data_mu": round(float(B["mu"][d_pos].mean()), 4),
            "mean_market_mu": round(float(mu_m[d_pos].mean()), 4),
        },
        "data_below_market": {
            "n": int(d_neg.sum()),
            "mean_data_log_ratio": round(float(np.log(B["lam"][d_neg] / B["mu"][d_neg]).mean()), 4),
            "mean_market_log_ratio": round(float(np.log(lam_m[d_neg] / mu_m[d_neg]).mean()), 4),
            "mean_data_lam": round(float(B["lam"][d_neg].mean()), 4),
            "mean_market_lam": round(float(lam_m[d_neg].mean()), 4),
            "mean_data_mu": round(float(B["mu"][d_neg].mean()), 4),
            "mean_market_mu": round(float(mu_m[d_neg].mean()), 4),
        },
    }
    var = {k: variant_summary(variants[k], B, am) for k in H1_VARIANTS if k in variants}
    base_bias = disagreement_block(B, am)["abs"]["bias_data"]
    improving = [
        k
        for k, v in var.items()
        if v["paired_ll_diff_vs_v1"]["ci95"][1] < 0
        and v["disagreement"]["abs"]["bias_data"] < base_bias * 2 / 3
    ]
    gamma_too_large = summary["mean_gamma_fit_minus_market_implied"] > 0.05
    verdict = (
        "SUPPORTED"
        if gamma_too_large and improving
        else ("PARTIAL" if gamma_too_large or improving else "REJECTED")
    )
    return {
        "test": (
            "H1 supported if (a) the fitted home advantage exceeds the market-implied "
            "log(lam/mu) by > 0.05 on average over league-seasons AND (b) a decay or gamma-prior "
            "variant beats v1 on aligned log loss (bootstrap CI excluding 0) while cutting the "
            ">10pt-bucket bias by at least a third."
        ),
        "summary": summary,
        "per_league_season": rows,
        "variants": var,
        "variants_meeting_b": improving,
        "verdict": verdict,
        "elapsed_s": round(time.time() - t0, 1),
    }


def h2_heterogeneity(B: dict, am: np.ndarray) -> dict:
    by_league = {d: disagreement_block(B, am, B["division"] == d) for d in wf.DIVISIONS}
    seasons = sorted(set(B["season"][am]), key=wf.season_start)
    by_season = {s: disagreement_block(B, am, B["season"] == s) for s in seasons}
    cells = {}
    for d in wf.DIVISIONS:
        for s in seasons:
            blk = disagreement_block(B, am, (B["division"] == d) & (B["season"] == s))
            if blk["abs"].get("n", 0) >= 30:
                cells[f"{d}|{s}"] = {
                    "n_bucket": blk["abs"]["n"],
                    "share": blk["share_in_bucket"],
                    "bias_data": blk["abs"]["bias_data"],
                    "bias_market": blk["abs"]["bias_market"],
                    "data_ll_home": blk["abs"]["data_ll_home"],
                    "market_ll_home": blk["abs"]["market_ll_home"],
                }
    biases_league = {d: v["abs"]["bias_data"] for d, v in by_league.items()}
    biases_season = {s: v["abs"]["bias_data"] for s, v in by_season.items()}
    n_league_biased = sum(b > 0.03 for b in biases_league.values())
    n_season_biased = sum(b > 0.03 for b in biases_season.values())
    covid = by_season.get("2020-21", {}).get("abs", {})
    others = [v["abs"]["bias_data"] for s, v in by_season.items() if s != "2020-21"]
    covid_excess = (covid.get("bias_data", 0.0) - float(np.mean(others))) if others else 0.0
    broad = n_league_biased >= 4 and n_season_biased >= 5
    verdict = (
        "REJECTED (bias is broad-based)"
        if broad and covid_excess < 0.03
        else ("PARTIAL" if broad else "SUPPORTED (concentrated)")
    )
    # was gamma slow to adapt in 2020-21? gamma vs realised per league for 2019-20/2020-21/2021-22
    adapt = {}
    for d in wf.DIVISIONS:
        adapt[d] = {}
        for s in ("2019-20", "2020-21", "2021-22"):
            m = (B["division"] == d) & (B["season"] == s)
            if m.sum() < 50:
                continue
            adapt[d][s] = {
                "gamma_fit_mean": round(float(B["gamma_mean"][m].mean()), 4),
                "realised_log_goal_ratio": round(
                    float(np.log(B["hg"][m].mean() / B["ag"][m].mean())), 4
                ),
                "realised_home_rate": round(float((B["y"][m] == 0).mean()), 4),
                "data_mean_p_home": round(float(B["p_data"][m, 0].mean()), 4),
                "market_mean_p_home": round(float(B["p_mkt"][m, 0].mean()), 4),
            }
    return {
        "test": (
            "H2 supported if the >10pt-bucket bias (data mean - realised) is concentrated: fewer "
            "than 4/5 leagues or 5/7 seasons show bias > 0.03, or 2020-21 exceeds the other "
            "seasons' mean bias by > 0.03."
        ),
        "by_league": by_league,
        "by_season": by_season,
        "league_x_season_cells": cells,
        "n_leagues_bias_gt_0.03": n_league_biased,
        "n_seasons_bias_gt_0.03": n_season_biased,
        "covid_2020_21_bucket": covid,
        "covid_excess_bias_vs_other_seasons": round(float(covid_excess), 4),
        "gamma_adaptation_around_covid": adapt,
        "note": (
            "Season ids split at 1 July, so the COVID-delayed end of 2019-20 (June/July 2020, "
            "mostly empty stadiums) is labelled 2020-21 by the provider; 2020-21 therefore "
            "contains ~45 rounds and nearly all empty-stadium matches."
        ),
        "verdict": verdict,
    }


def h3_promoted(B: dict, am: np.ndarray, variants: dict[str, dict]) -> dict:
    thin = (B["eff_home"] < 8) | (B["eff_away"] < 8)
    prom = (B["promoted_home"] == 1) | (B["promoted_away"] == 1)
    gap = B["p_data"][:, 0] - B["p_mkt"][:, 0]
    d_abs = am & (np.abs(gap) > DISAGREE_THR)
    out = {
        "share_thin_history_in_aligned": round(float(thin[am].mean()), 4),
        "share_thin_history_in_bucket": round(float(thin[d_abs].mean()), 4),
        "share_promoted_in_aligned": round(float(prom[am].mean()), 4),
        "share_promoted_in_bucket": round(float(prom[d_abs].mean()), 4),
        "bucket_thin": home_stats(B, d_abs & thin),
        "bucket_not_thin": home_stats(B, d_abs & ~thin),
        "bucket_promoted": home_stats(B, d_abs & prom),
        "bucket_not_promoted": home_stats(B, d_abs & ~prom),
        "aligned_promoted_home": home_stats(B, am & (B["promoted_home"] == 1)),
        "aligned_promoted_away": home_stats(B, am & (B["promoted_away"] == 1)),
        "aligned_neither_promoted": home_stats(B, am & ~prom),
    }
    out["variants"] = {k: variant_summary(variants[k], B, am) for k in H3_VARIANTS if k in variants}
    enrich = out["share_thin_history_in_bucket"] / max(out["share_thin_history_in_aligned"], 1e-9)
    excess = out["bucket_thin"].get("bias_data", 0) - out["bucket_not_thin"].get("bias_data", 0)
    supported = enrich >= 1.5 and excess > 0.02 and out["bucket_thin"]["n"] >= 100
    out["enrichment_thin_history"] = round(float(enrich), 3)
    out["excess_bias_thin_vs_not"] = round(float(excess), 4)
    out["test"] = (
        "H3 supported if thin-history (< 8 effective matches) involvement is enriched >= 1.5x in "
        "the >10pt bucket AND the bias among those matches exceeds the rest by > 0.02; the "
        "promoted-prior variants are reported as named candidates."
    )
    out["verdict"] = "SUPPORTED" if supported else ("PARTIAL" if enrich >= 1.5 else "REJECTED")
    return out


def h4_shrinkage(B: dict, am: np.ndarray, variants: dict[str, dict]) -> dict:
    pma = B["p_mkt"][:, 2]
    edges = [0.2, 0.3, 0.4, 0.5, 0.6]
    lab = wf.bin_labels(pma, edges, "{:.1f}")
    gap = B["p_data"][:, 0] - B["p_mkt"][:, 0]
    d_abs = am & (np.abs(gap) > DISAGREE_THR)
    by_p_away = {}
    for lb in sorted(set(lab[am]), key=lambda s: (s[0] != "<", s)):
        m = am & (lab == lb)
        y = B["y"][m]
        by_p_away[lb] = {
            "n": int(m.sum()),
            "share_in_bucket": round(float((d_abs & m).sum() / m.sum()), 4),
            "share_of_bucket": round(float((d_abs & m).sum() / d_abs.sum()), 4),
            "data_mean_p_home": round(float(B["p_data"][m, 0].mean()), 4),
            "market_mean_p_home": round(float(B["p_mkt"][m, 0].mean()), 4),
            "realised_home": round(float((y == 0).mean()), 4),
            "data_mean_p_away": round(float(B["p_data"][m, 2].mean()), 4),
            "market_mean_p_away": round(float(pma[m].mean()), 4),
            "realised_away": round(float((y == 2).mean()), 4),
            "bucket": home_stats(B, d_abs & m),
        }
    # favourite calibration split by favourite side
    fav_side = np.argmax(B["p_mkt"], axis=1)
    pfav_m = B["p_mkt"].max(axis=1)
    pfav_d = B["p_data"][np.arange(len(fav_side)), fav_side]
    yfav = (B["y"] == fav_side).astype(float)
    fav_edges = [0.4, 0.5, 0.6, 0.7]
    flab = wf.bin_labels(pfav_m, fav_edges, "{:.1f}")
    fav_cal = {}
    for side, name in ((0, "home_favourite"), (2, "away_favourite")):
        fav_cal[name] = {}
        for lb in sorted(set(flab[am]), key=lambda s: (s[0] != "<", s)):
            m = am & (fav_side == side) & (flab == lb)
            if m.sum() < 50:
                continue
            fav_cal[name][lb] = {
                "n": int(m.sum()),
                "data_mean_p_fav": round(float(pfav_d[m].mean()), 4),
                "market_mean_p_fav": round(float(pfav_m[m].mean()), 4),
                "realised_fav": round(float(yfav[m].mean()), 4),
                "data_minus_realised": round(float(pfav_d[m].mean() - yfav[m].mean()), 4),
                "market_minus_realised": round(float(pfav_m[m].mean() - yfav[m].mean()), 4),
            }
    # Elo difference (away - home) as an external strength yardstick
    elo_diff = B["elo_away"] - B["elo_home"]
    e_ok = ~np.isnan(elo_diff)
    e_edges = [-200, -100, 0, 100, 200]
    elab = wf.bin_labels(np.nan_to_num(elo_diff, nan=-9999), e_edges, "{:.0f}")
    by_elo = {}
    for lb in sorted(set(elab[am & e_ok]), key=lambda s: (s[0] != "<", s)):
        m = am & e_ok & (elab == lb)
        by_elo[lb] = {
            "n": int(m.sum()),
            "share_in_bucket": round(float((d_abs & m).sum() / m.sum()), 4),
            **{k: v for k, v in home_stats(B, m).items() if k != "n"},
            "bucket": home_stats(B, d_abs & m),
        }
    out = {
        "by_market_p_away": by_p_away,
        "favourite_calibration": fav_cal,
        "by_elo_diff_away_minus_home": by_elo,
        "variants": {k: variant_summary(variants[k], B, am) for k in H4_VARIANTS if k in variants},
    }
    # tests: bias in the bucket increases with market P(away); away favourites under-rated
    bb = [
        v["bucket"].get("bias_data") for v in by_p_away.values() if v["bucket"].get("n", 0) >= 100
    ]
    monotone = len(bb) >= 3 and bb[-1] - bb[0] > 0.03
    away_fav = fav_cal.get("away_favourite", {})
    under_away_fav = [v["data_minus_realised"] for v in away_fav.values() if v["n"] >= 200]
    home_fav = fav_cal.get("home_favourite", {})
    under_home_fav = [v["data_minus_realised"] for v in home_fav.values() if v["n"] >= 200]
    away_under = bool(under_away_fav) and float(np.mean(under_away_fav)) < -0.02
    home_under = bool(under_home_fav) and float(np.mean(under_home_fav)) < -0.02
    out["bucket_bias_low_to_high_p_away"] = bb
    out["mean_data_minus_realised_away_fav"] = (
        round(float(np.mean(under_away_fav)), 4) if under_away_fav else None
    )
    out["mean_data_minus_realised_home_fav"] = (
        round(float(np.mean(under_home_fav)), 4) if under_home_fav else None
    )
    out["test"] = (
        "H4 supported if the >10pt-bucket bias grows with market P(away) by > 0.03 from the lowest "
        "to the highest bin (n >= 100 each) AND DATA_ONLY under-rates away favourites by > 0.02 "
        "on average (data P(fav) - realised); the weaker-shrinkage variant is a named candidate."
    )
    out["verdict"] = (
        "SUPPORTED"
        if monotone and away_under
        else ("PARTIAL" if monotone or away_under else "REJECTED")
    )
    out["home_favourites_also_under_rated"] = home_under
    return out


def h5_staleness(B: dict, am: np.ndarray) -> dict:
    gap = B["p_data"][:, 0] - B["p_mkt"][:, 0]
    d_abs = am & (np.abs(gap) > DISAGREE_THR)
    y = B["y"]
    lld = wf.multiclass_ll(B["p_data"], y)
    llm = wf.multiclass_ll(B["p_mkt"], y)

    def cell(m):
        return {
            "n": int(m.sum()),
            "share_in_bucket": round(float((d_abs & m).sum() / max(m.sum(), 1)), 4),
            "mean_abs_gap": round(float(np.abs(gap[m]).mean()), 4),
            "paired_ll_diff_vs_market_3way": round(float((lld[m] - llm[m]).mean()), 5),
            **{k: v for k, v in home_stats(B, m).items() if k != "n"},
            "bucket": home_stats(B, d_abs & m),
        }

    dsr = B["days_since_refit"]
    by_refit = {
        lb: cell(am & mm)
        for lb, mm in (
            ("0", dsr == 0),
            ("1", dsr == 1),
            ("2", dsr == 2),
            ("3-4", (dsr >= 3) & (dsr <= 4)),
            ("5-6", dsr >= 5),
        )
    }
    md = B["matchday"]
    by_matchday = {
        lb: cell(am & mm)
        for lb, mm in (
            ("1-5", md <= 5),
            ("6-13", (md > 5) & (md <= 13)),
            ("14-26", (md > 13) & (md <= 26)),
            ("27+", md > 26),
        )
    }
    dis = B["days_into_season"]
    by_days = {
        lb: cell(am & mm)
        for lb, mm in (
            ("<30", dis < 30),
            ("30-89", (dis >= 30) & (dis < 90)),
            ("90-179", (dis >= 90) & (dis < 180)),
            ("180+", dis >= 180),
        )
    }
    r0 = by_refit["0"]["paired_ll_diff_vs_market_3way"]
    r6 = by_refit["5-6"]["paired_ll_diff_vs_market_3way"]
    early = by_matchday["1-5"]["bucket"].get("bias_data", 0.0)
    late = by_matchday["27+"]["bucket"].get("bias_data", 0.0)
    stale_effect = r6 - r0 > 0.01
    early_effect = early - late > 0.02
    # the whole-sample tilt (data mean - realised on all aligned matches) is the baseline any
    # staleness effect has to exceed; a bucket merely showing the global tilt is not evidence
    base_bias = home_stats(B, am)["bias_data"]
    early_all = by_matchday["1-5"]["bias_data"] - base_bias
    return {
        "test": (
            "H5 supported if the paired 3-way log-loss gap vs market grows by > 0.01 from 0 to 5-6 "
            "days since refit, or the >10pt-bucket bias in matchdays 1-5 exceeds matchdays 27+ by "
            "> 0.02. (Both criteria as pre-stated; the global tilt is reported alongside as the "
            "baseline, since every bucket inherits it.)"
        ),
        "aligned_baseline_bias": round(float(base_bias), 4),
        "matchday_1_5_excess_bias_over_baseline": round(float(early_all), 4),
        "by_days_since_refit": by_refit,
        "by_matchday": by_matchday,
        "by_days_into_season": by_days,
        "refit_gap_5_6_minus_0": round(float(r6 - r0), 5),
        "early_minus_late_bucket_bias": round(float(early - late), 4),
        "verdict": (
            "SUPPORTED"
            if stale_effect and early_effect
            else ("PARTIAL" if stale_effect or early_effect else "REJECTED")
        ),
    }


def h6_selection(B: dict, am: np.ndarray) -> dict:
    """Regression to the mean: signed buckets, symmetric-noise check, walk-forward recalibration."""
    gap = B["p_data"][:, 0] - B["p_mkt"][:, 0]
    d_pos = am & (gap > DISAGREE_THR)
    d_neg = am & (gap < -DISAGREE_THR)
    yh = (B["y"] == 0).astype(float)
    starts = np.array([wf.season_start(s) for s in B["season"]])
    xd, xm = logit(B["p_data"][:, 0]), logit(B["p_mkt"][:, 0])
    p_platt = np.full(len(yh), np.nan)
    p_blend = np.full(len(yh), np.nan)
    p_shrink_mkt = np.full(len(yh), np.nan)  # market + slope on (data - market) residual
    coefs = {}
    for s0 in sorted(set(starts[am])):
        prior = starts < s0
        cur = starts == s0
        b1 = fit_logistic(xd[prior, None], yh[prior])
        b2 = fit_logistic(np.column_stack([xd[prior], xm[prior]]), yh[prior])
        b3 = fit_logistic(np.column_stack([xm[prior], xd[prior] - xm[prior]]), yh[prior])
        p_platt[cur] = predict_logistic(b1, xd[cur, None])
        p_blend[cur] = predict_logistic(b2, np.column_stack([xd[cur], xm[cur]]))
        p_shrink_mkt[cur] = predict_logistic(b3, np.column_stack([xm[cur], xd[cur] - xm[cur]]))
        coefs[f"{s0}-{str(s0 + 1)[2:]}"] = {
            "platt_data": [round(float(v), 4) for v in b1],
            "blend_data_market": [round(float(v), 4) for v in b2],
            "market_plus_residual": [round(float(v), 4) for v in b3],
        }

    def bucket(m):
        return {
            "n": int(m.sum()),
            "realised": round(float(yh[m].mean()), 4),
            "data_mean": round(float(B["p_data"][m, 0].mean()), 4),
            "market_mean": round(float(B["p_mkt"][m, 0].mean()), 4),
            "platt_data_mean": round(float(p_platt[m].mean()), 4),
            "blend_mean": round(float(p_blend[m].mean()), 4),
            "ll_data": round(float(wf.binary_ll(B["p_data"][m, 0], yh[m]).mean()), 5),
            "ll_market": round(float(wf.binary_ll(B["p_mkt"][m, 0], yh[m]).mean()), 5),
            "ll_platt_data": round(float(wf.binary_ll(p_platt[m], yh[m]).mean()), 5),
            "ll_blend": round(float(wf.binary_ll(p_blend[m], yh[m]).mean()), 5),
            "ll_market_plus_residual": round(float(wf.binary_ll(p_shrink_mkt[m], yh[m]).mean()), 5),
            "paired_blend_minus_market": wf.paired_ci(
                wf.binary_ll(p_blend[m], yh[m]) - wf.binary_ll(B["p_mkt"][m, 0], yh[m])
            ),
        }

    pos, neg, alld = bucket(d_pos), bucket(d_neg), bucket(am)
    # symmetric-noise prediction: under "data = market + noise" the realised rate equals the market
    # mean in both signed buckets and the bucket counts are equal if there is no directional tilt.
    asym = d_pos.sum() / max(d_pos.sum() + d_neg.sum(), 1)
    market_right_pos = abs(pos["realised"] - pos["market_mean"]) < 0.02
    market_right_neg = abs(neg["realised"] - neg["market_mean"]) < 0.02
    blend_no_gain = pos["paired_blend_minus_market"]["ci95"][1] > -0.0 or (
        pos["paired_blend_minus_market"]["mean"] > -0.005
    )
    verdict = (
        "SUPPORTED (market right; residual structure absent)"
        if market_right_pos and market_right_neg and blend_no_gain
        else "PARTIAL"
    )
    # residual after Platt: does recalibrated data still over-rate D+?
    residual_after_platt = pos["platt_data_mean"] - pos["realised"]
    return {
        "test": (
            "H6 supported if, in both signed >10pt buckets, |realised - market mean| < 0.02 and a "
            "walk-forward logistic blend of data and market does not beat the market in the "
            "data-above-market bucket (bootstrap CI includes 0 or gain < 0.005)."
        ),
        "data_above_market": pos,
        "data_below_market": neg,
        "aligned_all": alld,
        "share_positive_of_signed_buckets": round(float(asym), 4),
        "residual_bias_after_platt_in_positive_bucket": round(float(residual_after_platt), 4),
        "walk_forward_coefficients": coefs,
        "verdict": verdict,
    }


def h7_rest(B: dict, am: np.ndarray) -> dict:
    gap = B["p_data"][:, 0] - B["p_mkt"][:, 0]
    d_abs = am & (np.abs(gap) > DISAGREE_THR)
    rh, ra = B["rest_home"], B["rest_away"]

    def rest_bins(r):
        return (
            ("<=3", (r >= 0) & (r <= 3)),
            ("4-5", (r >= 4) & (r <= 5)),
            ("6-8", (r >= 6) & (r <= 8)),
            ("9-20", (r >= 9) & (r <= 20)),
            (">20_or_first", (r > 20) | (r < 0)),
        )

    def cell(m):
        return {
            "n": int(m.sum()),
            "share_in_bucket": round(float((d_abs & m).sum() / max(m.sum(), 1)), 4),
            **{k: v for k, v in home_stats(B, m).items() if k != "n"},
            "bucket": home_stats(B, d_abs & m),
        }

    by_home = {lb: cell(am & mm) for lb, mm in rest_bins(rh)}
    by_away = {lb: cell(am & mm) for lb, mm in rest_bins(ra)}
    both_known = (rh >= 0) & (ra >= 0) & (rh <= 20) & (ra <= 20)
    diff = rh - ra
    by_diff = {
        lb: cell(am & both_known & mm)
        for lb, mm in (
            ("<=-3", diff <= -3),
            ("-2..-1", (diff >= -2) & (diff <= -1)),
            ("0", diff == 0),
            ("1..2", (diff >= 1) & (diff <= 2)),
            (">=3", diff >= 3),
        )
    }
    # test: any rest-diff bucket (n>=300) where the realised rate departs from the data mean by
    # > 0.03 while the market is closer
    hits_raw = [
        lb
        for lb, c in by_diff.items()
        if c["n"] >= 300
        and abs(c["bias_data"]) > 0.03
        and abs(c["bias_market"]) < abs(c["bias_data"]) - 0.01
    ]
    # Refinement made after seeing the results: the pre-stated rule is satisfied by the
    # equal-rest bucket, i.e. by the whole-sample tilt that every bucket inherits. A rest effect
    # must show as *excess* bias over the aligned baseline that the market does not share.
    base_d = home_stats(B, am)["bias_data"]
    base_m = home_stats(B, am)["bias_market"]
    hits = [
        lb
        for lb, c in by_diff.items()
        if c["n"] >= 300
        and abs(c["bias_data"] - base_d) > 0.03
        and abs(c["bias_market"] - base_m) < abs(c["bias_data"] - base_d) - 0.01
    ]
    return {
        "test": (
            "Pre-stated: H7 supported if some rest-difference bucket (n >= 300) shows |data mean - "
            "realised| > 0.03 with the market at least 0.01 closer. Refined after the first run "
            "(disclosed): the same, on the bucket's EXCESS bias over the aligned-sample baseline, "
            "because the pre-stated rule is met by the equal-rest bucket through the global tilt "
            "alone. Rest is measured from domestic league matches only (cup and European "
            "fixtures are not in the dataset), so it is a noisy proxy."
        ),
        "aligned_baseline_bias": {
            "data": round(float(base_d), 4),
            "market": round(float(base_m), 4),
        },
        "by_home_rest": by_home,
        "by_away_rest": by_away,
        "by_rest_diff_home_minus_away": by_diff,
        "buckets_meeting_prestated_rule": hits_raw,
        "buckets_meeting_excess_rule": hits,
        "verdict": "SUPPORTED" if hits else "REJECTED",
    }


def h8_structural_intercept(B: dict, am: np.ndarray, variants: dict[str, dict]) -> dict:
    """Root-cause check: the frozen fitter has no scoring intercept and pins mean attack and
    defence to zero, so the away baseline is stuck near exp(0) while gamma absorbs the home
    level.  Compare model goal rates with realised goals, then test the intercept candidates."""

    def rates(T, m):
        return {
            "n": int(m.sum()),
            "mean_lam": round(float(T["lam"][m].mean()), 4),
            "realised_home_goals": round(float(T["hg"][m].mean()), 4),
            "mean_mu": round(float(T["mu"][m].mean()), 4),
            "realised_away_goals": round(float(T["ag"][m].mean()), 4),
            "mean_gamma": round(float(T["gamma_mean"][m].mean()), 4),
            "mean_intercept": (
                round(float(np.nanmean(T["intercept"][m])), 4)
                if "intercept" in T and not np.all(np.isnan(T["intercept"][m]))
                else None
            ),
            "data_mean_p_home": round(float(T["p_data"][m, 0].mean()), 4),
            "data_mean_p_away": round(float(T["p_data"][m, 2].mean()), 4),
            "realised_home_rate": round(float((T["y"][m] == 0).mean()), 4),
            "realised_away_rate": round(float((T["y"][m] == 2).mean()), 4),
            "data_mean_p_over25": round(float(T["p_data_o25"][m].mean()), 4),
            "realised_over25": round(float((T["hg"][m] + T["ag"][m] > 2).mean()), 4),
        }

    # favourite-strength profile: model rate vs realised goals for the favourite and the underdog
    pf = B["p_mkt"].max(axis=1)
    side = np.argmax(B["p_mkt"], axis=1)
    fav_prof = {}
    for lo, hi in ((0.0, 0.45), (0.45, 0.6), (0.6, 0.75), (0.75, 1.01)):
        for s, name in ((0, "home_fav"), (2, "away_fav")):
            m = am & (pf >= lo) & (pf < hi) & (side == s)
            if m.sum() < 50:
                continue
            fr = B["lam"][m] if s == 0 else B["mu"][m]
            fg = B["hg"][m] if s == 0 else B["ag"][m]
            dr = B["mu"][m] if s == 0 else B["lam"][m]
            dg = B["ag"][m] if s == 0 else B["hg"][m]
            fav_prof[f"p_fav[{lo},{hi})/{name}"] = {
                "n": int(m.sum()),
                "fav_model_rate": round(float(fr.mean()), 4),
                "fav_realised_goals": round(float(fg.mean()), 4),
                "dog_model_rate": round(float(dr.mean()), 4),
                "dog_realised_goals": round(float(dg.mean()), 4),
            }
    out = {
        "mechanism": (
            "lam = exp(att_h - def_a + gamma), mu = exp(att_a - def_h) with a soft penalty pinning "
            "mean(att) = mean(def) = 0 and no intercept: the away baseline is fixed near exp(0) "
            "(times a Jensen factor) whatever the league scoring level, and gamma (prior 0.25 +- "
            "0.15) has to carry the home scoring level instead of the home/away ratio."
        ),
        "frozen_v1_rates": {
            "aligned": rates(B, am),
            "by_league": {d: rates(B, am & (B["division"] == d)) for d in wf.DIVISIONS},
        },
        "favourite_strength_profile": fav_prof,
        "variants": {},
    }

    def fav_calibration(T):
        pfm = T["p_mkt"].max(axis=1)
        sd = np.argmax(T["p_mkt"], axis=1)
        pfd = T["p_data"][np.arange(len(sd)), sd]
        yf = (T["y"] == sd).astype(float)
        res = {}
        for s, name in ((0, "home_favourite"), (2, "away_favourite")):
            for lo, hi in ((0.0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 1.01)):
                m = am & (sd == s) & (pfm >= lo) & (pfm < hi)
                if m.sum() < 50:
                    continue
                res[f"{name}/[{lo},{hi})"] = {
                    "n": int(m.sum()),
                    "data_minus_realised": round(float(pfd[m].mean() - yf[m].mean()), 4),
                    "market_minus_realised": round(float(pfm[m].mean() - yf[m].mean()), 4),
                }
        return res

    out["favourite_calibration_frozen"] = fav_calibration(B)
    for k in H8_VARIANTS:
        if k in variants:
            v = variant_summary(variants[k], B, am)
            v["rates"] = rates(variants[k], am)
            v["favourite_calibration"] = fav_calibration(variants[k])
            out["variants"][k] = v
    base_bias = disagreement_block(B, am)["abs"]["bias_data"]
    fixed = [
        k
        for k, v in out["variants"].items()
        if v["paired_ll_diff_vs_v1"]["ci95"][1] < 0
        and v["disagreement"]["abs"]["bias_data"] < base_bias * 2 / 3
    ]
    mu_gap = (
        out["frozen_v1_rates"]["aligned"]["mean_mu"]
        - out["frozen_v1_rates"]["aligned"]["realised_away_goals"]
    )
    out["frozen_mu_minus_realised_away_goals"] = round(float(mu_gap), 4)
    out["variants_meeting_test"] = fixed
    out["test"] = (
        "H8 supported if the frozen model under-predicts away goals by > 0.05 per match on the "
        "aligned sample AND an intercept candidate beats v1 on aligned log loss (CI excluding 0) "
        "while cutting the >10pt-bucket bias by at least a third."
    )
    out["verdict"] = (
        "SUPPORTED"
        if mu_gap < -0.05 and fixed
        else ("PARTIAL" if mu_gap < -0.05 or fixed else "REJECTED")
    )
    return out


# --------------------------------------------------------------------------------------------
def reproduction(B: dict, am: np.ndarray) -> dict:
    fm = family_metrics(B, am, B["p_data"][am])
    fm["disagreement"] = disagreement_block(B, am)
    fm["frozen_v1"] = wf.frozen_v1_summary()
    return fm


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--posterior-samples", type=int, default=wf.POSTERIOR_SAMPLES)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    t0 = time.time()
    matches, extras, data_hash = wf.load_data()
    B = wf.load_or_run(
        "dc_laplace_v1",
        matches,
        extras,
        data_hash,
        keep_matrix=True,
        posterior_samples=a.posterior_samples,
    )
    names = list(H1_VARIANTS + H3_VARIANTS + H4_VARIANTS + H8_VARIANTS)
    wf.ensure_variants(names, posterior_samples=a.posterior_samples, workers=a.workers)
    variants = {
        k: wf.load_or_run(
            k, matches, extras, data_hash, keep_matrix=False, posterior_samples=a.posterior_samples
        )
        for k in names
    }
    am = wf.aligned_mask(B)
    out = {
        "protocol": wf.PROTOCOL_VERSION,
        "study": "home_bias_v1",
        "data_hash": data_hash,
        "posterior_samples": a.posterior_samples,
        "n_aligned": int(am.sum()),
        "disagreement_threshold": DISAGREE_THR,
        "reproduction_of_v1": reproduction(B, am),
        "H1_home_advantage": h1_home_advantage(B, am, variants),
        "H2_heterogeneity": h2_heterogeneity(B, am),
        "H3_promoted_priors": h3_promoted(B, am, variants),
        "H4_strength_shrinkage": h4_shrinkage(B, am, variants),
        "H5_staleness": h5_staleness(B, am),
        "H6_selection_effect": h6_selection(B, am),
        "H7_rest": h7_rest(B, am),
        "H8_structural_intercept": h8_structural_intercept(B, am, variants),
        "candidate_configs": {k: wf.strength_for(k).__dict__ for k in ["dc_laplace_v1", *names]},
    }
    out["verdicts"] = {
        k: v["verdict"] for k, v in out.items() if isinstance(v, dict) and "verdict" in v
    }
    out["elapsed_s"] = round(time.time() - t0, 1)
    out["result_hash"] = content_hash({k: v for k, v in out.items() if k != "elapsed_s"})
    write_json(Path(a.out), out)
    print(json.dumps({"verdicts": out["verdicts"], "elapsed_s": out["elapsed_s"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
