"""Market-family research (Phase 17): price several markets from the same walk-forward posterior.

For every aligned match the DATA_ONLY posterior (dc_laplace_v1, weekly refit, strictly
point-in-time) yields a posterior-averaged Dixon-Coles score matrix.  From that one object we
price:

* 1X2                       vs de-vigged Bet365 pre-match 1X2
* O/U 2.5                   vs de-vigged Bet365 Over25/Under25
* Asian handicap (home)     vs de-vigged Bet365 HandiHome/HandiAway at HandiSize, settled from
                            the score matrix with quarter/half-line push handling (quarter lines
                            are split stakes; win/push/loss probabilities are reported and
                            scoring is stake-weighted on the non-pushed part)
* BTTS                      calibration only (no market odds in the dataset)
* team totals (O0.5/1.5/2.5 for each side) calibration only

Aligned samples are per family: matches with the odds that family needs.  Per family we report
log loss / Brier for model vs market, ECE, a per-league breakdown and, for AH, the expected return
of a naive 'bet when model prob > implied + 3 pts' rule at the quoted Bet365 prices
(informational; Bet365 is not Kalshi).  Output: ``data/research/market_families_v1.json``.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from research import wf_common as wf
from soccer_edge.core.serialization import content_hash, write_json
from soccer_edge.evaluation.metrics import multiclass_brier, multiclass_log_loss

OUT = wf.REPO / "data" / "research" / "market_families_v1.json"
NAIVE_EDGE = 0.03


# --------------------------------------------------------------------------------------------
# pure helpers (unit-tested in tests/test_research_families.py)
# --------------------------------------------------------------------------------------------
def devig_two_way(o1: float, o2: float) -> float:
    """Proportional de-vig of a two-way market; returns the fair probability of side 1."""
    a, b = 1.0 / o1, 1.0 / o2
    return a / (a + b)


def snap_quarter(size: float) -> float:
    """football-data.co.uk stores quarter lines rounded to one decimal (-0.3 == -0.25,
    -0.8 == -0.75); snap to the nearest quarter goal."""
    return float(np.round(size * 4.0) / 4.0)


def split_line(size: float) -> list[float]:
    """A quarter line is two half-stakes on the neighbouring half/whole lines."""
    q = snap_quarter(size)
    if round(abs(q) * 4) % 2 == 1:  # x.25 or x.75
        return [q - 0.25, q + 0.25]
    return [q]


def _settle_diff(adj: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    win = adj > 1e-9
    push = np.abs(adj) <= 1e-9
    loss = adj < -1e-9
    return win, push, loss


def ah_settle_score(hg: int, ag: int, size: float) -> tuple[float, float, float]:
    """Stake fractions (win, push, loss) for a HOME bet at handicap `size` (added to home goals)."""
    lines = split_line(size)
    w = p = lo = 0.0
    for h in lines:
        win, push, loss = _settle_diff(np.array([hg - ag + h]))
        w += float(win[0]) / len(lines)
        p += float(push[0]) / len(lines)
        lo += float(loss[0]) / len(lines)
    return w, p, lo


def ah_probs(mat: np.ndarray, size: float) -> tuple[float, float, float]:
    """(P(win), P(push), P(loss)) of a HOME bet at handicap `size` from a score matrix
    P(home=i, away=j); quarter lines are split stakes so the three sum to one."""
    g = mat.shape[0]
    diff = np.subtract.outer(np.arange(g), np.arange(g)).astype(float)
    lines = split_line(size)
    w = p = lo = 0.0
    for h in lines:
        win, push, loss = _settle_diff(diff + h)
        w += float(mat[win].sum()) / len(lines)
        p += float(mat[push].sum()) / len(lines)
        lo += float(mat[loss].sum()) / len(lines)
    return w, p, lo


def btts_prob(mat: np.ndarray) -> float:
    return float(1.0 - mat[0, :].sum() - mat[:, 0].sum() + mat[0, 0])


def team_total_over(mat: np.ndarray, side: str, line: float) -> float:
    marg = mat.sum(axis=1) if side == "home" else mat.sum(axis=0)
    return float(marg[np.arange(mat.shape[0]) > line].sum())


def weighted_ll(p: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    return float(np.sum(w * wf.binary_ll(p, y)) / np.sum(w))


def weighted_brier(p: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    return float(np.sum(w * (p - y) ** 2) / np.sum(w))


def paired_ci_weighted(diff: np.ndarray, w: np.ndarray, n_boot: int = 1000, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    n = len(diff)
    idx = rng.integers(0, n, size=(n_boot, n))
    wsum = w[idx].sum(axis=1)
    keep = wsum > 0  # a resample of only pushed stakes carries no information
    means = (w[idx] * diff[idx]).sum(axis=1)[keep] / wsum[keep]
    return {
        "mean": round(float(np.sum(w * diff) / np.sum(w)), 5),
        "ci95": [
            round(float(np.quantile(means, 0.025)), 5),
            round(float(np.quantile(means, 0.975)), 5),
        ],
    }


def reliability_table(p: np.ndarray, y: np.ndarray, bins: int = 10) -> list[dict]:
    edges = np.linspace(0, 1, bins + 1)
    rows = []
    for i in range(bins):
        m = (p >= edges[i]) & ((p < edges[i + 1]) if i < bins - 1 else (p <= edges[i + 1]))
        if m.sum() == 0:
            continue
        rows.append(
            {
                "lo": round(float(edges[i]), 2),
                "n": int(m.sum()),
                "mean_pred": round(float(p[m].mean()), 4),
                "mean_obs": round(float(y[m].mean()), 4),
            }
        )
    return rows


def prior_season_rate(B: dict, flag: np.ndarray) -> np.ndarray:
    """Walk-forward baseline: for each row, the realised rate of `flag` in the same league over
    all *earlier* seasons of scored predictions (never the current season)."""
    out = np.full(len(flag), np.nan)
    starts = np.array([wf.season_start(s) for s in B["season"]])
    for d in set(B["division"]):
        for s0 in set(starts):
            m = (B["division"] == d) & (starts == s0)
            prior = (B["division"] == d) & (starts < s0)
            if prior.sum() >= 100:
                out[m] = flag[prior].mean()
    return out


# --------------------------------------------------------------------------------------------
# families
# --------------------------------------------------------------------------------------------
def binary_family(p_model, p_mkt, y, *, mask, divs, seasons, n_boot) -> dict:
    """Model vs market on a binary target, overall and per league."""

    def block(m):
        pm, pk, yy = p_model[m], p_mkt[m], y[m]
        ld, lm = wf.binary_ll(pm, yy), wf.binary_ll(pk, yy)
        return {
            "n": int(m.sum()),
            "model": {
                "log_loss": round(float(ld.mean()), 5),
                "brier": round(float(((pm - yy) ** 2).mean()), 5),
                "ece": round(wf.ece(pm, yy), 4),
                "mean_pred": round(float(pm.mean()), 4),
            },
            "market": {
                "log_loss": round(float(lm.mean()), 5),
                "brier": round(float(((pk - yy) ** 2).mean()), 5),
                "ece": round(wf.ece(pk, yy), 4),
                "mean_pred": round(float(pk.mean()), 4),
            },
            "base_rate": round(float(yy.mean()), 4),
            "paired_ll_diff_model_minus_market": wf.paired_ci(ld - lm, n_boot=n_boot),
            **wf.season_consistency(ld - lm, seasons[m]),
        }

    out = block(mask)
    out["by_league"] = {d: block(mask & (divs == d)) for d in wf.DIVISIONS}
    return out


def calibration_family(p_model, y, base, *, mask, divs, n_boot) -> dict:
    def block(m, with_rel=False):
        pm, yy, bb = p_model[m], y[m], base[m]
        ok = ~np.isnan(bb)
        r = {
            "n": int(m.sum()),
            "model": {
                "log_loss": round(float(wf.binary_ll(pm, yy).mean()), 5),
                "brier": round(float(((pm - yy) ** 2).mean()), 5),
                "ece": round(wf.ece(pm, yy), 4),
                "mean_pred": round(float(pm.mean()), 4),
            },
            "prior_season_base_rate_baseline": {
                "n": int(ok.sum()),
                "log_loss": round(float(wf.binary_ll(bb[ok], yy[ok]).mean()), 5),
                "brier": round(float(((bb[ok] - yy[ok]) ** 2).mean()), 5),
            },
            "base_rate": round(float(yy.mean()), 4),
        }
        if ok.sum() > 30:
            r["paired_ll_diff_model_minus_baseline"] = wf.paired_ci(
                wf.binary_ll(pm[ok], yy[ok]) - wf.binary_ll(bb[ok], yy[ok]), n_boot=n_boot
            )
        if with_rel:
            r["reliability"] = reliability_table(pm, yy)
        return r

    out = block(mask, with_rel=True)
    out["by_league"] = {d: block(mask & (divs == d)) for d in wf.DIVISIONS}
    return out


def asian_handicap_family(B: dict, am: np.ndarray, n_boot: int) -> dict:
    size, oh, oa = B["ah_size"], B["ah_home"], B["ah_away"]
    ok = am & ~np.isnan(size) & ~np.isnan(oh) & ~np.isnan(oa) & (oh > 1.0) & (oa > 1.0)
    idx = np.where(ok)[0]
    n = len(idx)
    pw = np.zeros(n)
    pp = np.zeros(n)
    pl = np.zeros(n)
    rw = np.zeros(n)
    rp = np.zeros(n)
    rl = np.zeros(n)
    for k, i in enumerate(idx):
        pw[k], pp[k], pl[k] = ah_probs(B["mat"][i].astype(float), float(size[i]))
        rw[k], rp[k], rl[k] = ah_settle_score(int(B["hg"][i]), int(B["ag"][i]), float(size[i]))
    p_model = pw / (pw + pl)  # conditional on the stake not being pushed
    p_mkt = np.array([devig_two_way(float(oh[i]), float(oa[i])) for i in idx])
    w = rw + rl  # stake fraction that was actually decided
    yv = np.where(w > 0, rw / np.where(w > 0, w, 1), 0.0)
    divs, seasons = B["division"][idx], B["season"][idx]
    snapped = np.array([snap_quarter(float(s)) for s in size[idx]])
    quarter = np.array([len(split_line(float(s))) == 2 for s in size[idx]])

    def block(m):
        if m.sum() == 0:
            return {"n": 0}
        ld = wf.binary_ll(p_model[m], yv[m])
        lm = wf.binary_ll(p_mkt[m], yv[m])
        return {
            "n": int(m.sum()),
            "decided_stake_share": round(float(w[m].mean()), 4),
            "model": {
                "log_loss": round(weighted_ll(p_model[m], yv[m], w[m]), 5),
                "brier": round(weighted_brier(p_model[m], yv[m], w[m]), 5),
                "ece": round(wf.ece(p_model[m], yv[m], w=w[m]), 4),
                "mean_p_home_cond": round(float(p_model[m].mean()), 4),
                "mean_p_win": round(float(pw[m].mean()), 4),
                "mean_p_push": round(float(pp[m].mean()), 4),
                "mean_p_loss": round(float(pl[m].mean()), 4),
            },
            "market": {
                "log_loss": round(weighted_ll(p_mkt[m], yv[m], w[m]), 5),
                "brier": round(weighted_brier(p_mkt[m], yv[m], w[m]), 5),
                "ece": round(wf.ece(p_mkt[m], yv[m], w=w[m]), 4),
                "mean_p_home_cond": round(float(p_mkt[m].mean()), 4),
                "mean_overround": round(float((1 / oh[idx][m] + 1 / oa[idx][m]).mean()), 4),
            },
            "realised": {
                "home_cover_rate_cond": round(float(np.sum(w[m] * yv[m]) / np.sum(w[m])), 4),
                "win_stake": round(float(rw[m].mean()), 4),
                "push_stake": round(float(rp[m].mean()), 4),
                "loss_stake": round(float(rl[m].mean()), 4),
            },
            "paired_ll_diff_model_minus_market": paired_ci_weighted(ld - lm, w[m], n_boot=n_boot),
            **wf.season_consistency(w[m] * (ld - lm), seasons[m]),
        }

    out = {
        "definition": (
            "HOME bet at Bet365 HandiSize (added to home goals). Quarter lines split the stake "
            "over the two neighbouring lines. Model/market probabilities are P(win | not pushed); "
            "log loss / Brier / ECE are weighted by the decided stake fraction."
        ),
        "n_aligned_with_ah_odds": n,
        "share_quarter_lines": round(float(quarter.mean()), 4),
        "line_distribution": {
            str(k): int(v) for k, v in zip(*np.unique(snapped, return_counts=True))
        },
        "overall": block(np.ones(n, bool)),
        "by_league": {d: block(divs == d) for d in wf.DIVISIONS},
        "by_line_type": {
            "whole_or_half": block(~quarter),
            "quarter": block(quarter),
        },
        "by_abs_line": {
            "0": block(np.abs(snapped) < 0.01),
            "0.25-0.5": block((np.abs(snapped) >= 0.24) & (np.abs(snapped) <= 0.51)),
            "0.75-1.0": block((np.abs(snapped) >= 0.74) & (np.abs(snapped) <= 1.01)),
            ">=1.25": block(np.abs(snapped) >= 1.24),
        },
    }
    # naive betting rule at quoted prices (informational)
    ohh, oaa = oh[idx], oa[idx]
    bets = {}
    for edge in (0.03, 0.05, 0.10):
        bh = p_model > 1 / ohh + edge
        ba = (1 - p_model) > 1 / oaa + edge
        pnl_h = rw * (ohh - 1) - rl
        pnl_a = rl * (oaa - 1) - rw
        ev_h = pw * (ohh - 1) - pl
        ev_a = pl * (oaa - 1) - pw
        bets[f"edge>{edge}"] = {
            "home": {
                "n_bets": int(bh.sum()),
                "roi": round(float(pnl_h[bh].mean()), 4) if bh.sum() else None,
                "model_expected_roi": round(float(ev_h[bh].mean()), 4) if bh.sum() else None,
            },
            "away": {
                "n_bets": int(ba.sum()),
                "roi": round(float(pnl_a[ba].mean()), 4) if ba.sum() else None,
                "model_expected_roi": round(float(ev_a[ba].mean()), 4) if ba.sum() else None,
            },
            "both": {
                "n_bets": int(bh.sum() + ba.sum()),
                "roi": round(float(np.concatenate([pnl_h[bh], pnl_a[ba]]).mean()), 4)
                if (bh.sum() + ba.sum())
                else None,
            },
        }
    out["naive_betting_at_bet365"] = bets
    return out


def run(B: dict, *, n_boot: int = 1000) -> dict:
    t0 = time.time()
    am = wf.aligned_mask(B)
    divs, seasons, y = B["division"], B["season"], B["y"]
    out: dict = {
        "protocol": wf.PROTOCOL_VERSION,
        "study": "market_families_v1",
        "n_aligned": int(am.sum()),
    }
    # 1X2 (3-way)
    ll3d, ll3m = wf.multiclass_ll(B["p_data"], y), wf.multiclass_ll(B["p_mkt"], y)

    def b1x2(m):
        return {
            "n": int(m.sum()),
            "model": {
                "log_loss": round(multiclass_log_loss(B["p_data"][m], y[m]), 5),
                "brier": round(multiclass_brier(B["p_data"][m], y[m]), 5),
                "ece_home": round(wf.ece(B["p_data"][m, 0], (y[m] == 0).astype(float)), 4),
                "ece_draw": round(wf.ece(B["p_data"][m, 1], (y[m] == 1).astype(float)), 4),
                "ece_away": round(wf.ece(B["p_data"][m, 2], (y[m] == 2).astype(float)), 4),
            },
            "market": {
                "log_loss": round(multiclass_log_loss(B["p_mkt"][m], y[m]), 5),
                "brier": round(multiclass_brier(B["p_mkt"][m], y[m]), 5),
                "ece_home": round(wf.ece(B["p_mkt"][m, 0], (y[m] == 0).astype(float)), 4),
                "ece_draw": round(wf.ece(B["p_mkt"][m, 1], (y[m] == 1).astype(float)), 4),
                "ece_away": round(wf.ece(B["p_mkt"][m, 2], (y[m] == 2).astype(float)), 4),
            },
            "paired_ll_diff_model_minus_market": wf.paired_ci(ll3d[m] - ll3m[m], n_boot=n_boot),
            **wf.season_consistency(ll3d[m] - ll3m[m], seasons[m]),
        }

    out["1x2"] = {**b1x2(am), "by_league": {d: b1x2(am & (divs == d)) for d in wf.DIVISIONS}}
    # O/U 2.5
    tot = B["hg"] + B["ag"]
    ok_ou = am & ~np.isnan(B["p_mkt_o25"])
    out["over_under_2.5"] = binary_family(
        B["p_data_o25"],
        np.nan_to_num(B["p_mkt_o25"], nan=0.5),
        (tot > 2.5).astype(float),
        mask=ok_ou,
        divs=divs,
        seasons=seasons,
        n_boot=n_boot,
    )
    # matrix-derived O/U 2.5 (cross-check that the cached matrix reproduces the per-sample mean)
    mats = B["mat"].astype(float)
    g = mats.shape[1]
    tot_idx = np.add.outer(np.arange(g), np.arange(g))
    p_o25_mat = mats[:, tot_idx > 2.5].sum(axis=1)
    out["over_under_2.5"]["matrix_vs_sample_mean_max_abs_diff"] = round(
        float(np.abs(p_o25_mat[am] - B["p_data_o25"][am]).max()), 6
    )
    # Asian handicap
    out["asian_handicap"] = asian_handicap_family(B, am, n_boot)
    # BTTS (calibration only)
    p_btts = 1.0 - mats[:, 0, :].sum(axis=1) - mats[:, :, 0].sum(axis=1) + mats[:, 0, 0]
    y_btts = ((B["hg"] > 0) & (B["ag"] > 0)).astype(float)
    out["btts"] = {
        "note": "no BTTS odds in the dataset: model calibration vs realised only",
        **calibration_family(
            p_btts, y_btts, prior_season_rate(B, y_btts), mask=am, divs=divs, n_boot=n_boot
        ),
    }
    # team totals (calibration only)
    home_marg = mats.sum(axis=2)
    away_marg = mats.sum(axis=1)
    out["team_totals"] = {"note": "no team-total odds in the dataset: calibration only"}
    for side, marg, goals in (("home", home_marg, B["hg"]), ("away", away_marg, B["ag"])):
        for line in (0.5, 1.5, 2.5):
            p = marg[:, np.arange(g) > line].sum(axis=1)
            yy = (goals > line).astype(float)
            out["team_totals"][f"{side}_over_{line}"] = calibration_family(
                p, yy, prior_season_rate(B, yy), mask=am, divs=divs, n_boot=n_boot
            )
    # compact table for the report
    out["summary_table"] = {
        "1x2": {
            "n": out["1x2"]["n"],
            "model_log_loss": out["1x2"]["model"]["log_loss"],
            "market_log_loss": out["1x2"]["market"]["log_loss"],
            "paired_diff": out["1x2"]["paired_ll_diff_model_minus_market"],
        },
        "over_under_2.5": {
            "n": out["over_under_2.5"]["n"],
            "model_log_loss": out["over_under_2.5"]["model"]["log_loss"],
            "market_log_loss": out["over_under_2.5"]["market"]["log_loss"],
            "paired_diff": out["over_under_2.5"]["paired_ll_diff_model_minus_market"],
        },
        "asian_handicap": {
            "n": out["asian_handicap"]["overall"]["n"],
            "model_log_loss": out["asian_handicap"]["overall"]["model"]["log_loss"],
            "market_log_loss": out["asian_handicap"]["overall"]["market"]["log_loss"],
            "paired_diff": out["asian_handicap"]["overall"]["paired_ll_diff_model_minus_market"],
        },
        "btts": {
            "n": out["btts"]["n"],
            "model_log_loss": out["btts"]["model"]["log_loss"],
            "baseline_log_loss": out["btts"]["prior_season_base_rate_baseline"]["log_loss"],
            "ece": out["btts"]["model"]["ece"],
        },
        "team_totals": {
            k: {
                "n": v["n"],
                "model_log_loss": v["model"]["log_loss"],
                "baseline_log_loss": v["prior_season_base_rate_baseline"]["log_loss"],
                "ece": v["model"]["ece"],
                "mean_pred": v["model"]["mean_pred"],
                "base_rate": v["base_rate"],
            }
            for k, v in out["team_totals"].items()
            if k != "note"
        },
    }
    out["elapsed_s"] = round(time.time() - t0, 1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--posterior-samples", type=int, default=wf.POSTERIOR_SAMPLES)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    matches, extras, data_hash = wf.load_data()
    B = wf.load_or_run(
        "dc_laplace_v1",
        matches,
        extras,
        data_hash,
        keep_matrix=True,
        posterior_samples=a.posterior_samples,
    )
    res = run(B, n_boot=a.n_boot)
    res["data_hash"] = data_hash
    res["posterior_samples"] = a.posterior_samples
    res["result_hash"] = content_hash({k: v for k, v in res.items() if k != "elapsed_s"})
    write_json(Path(a.out), res)
    print(json.dumps({"summary": res["summary_table"], "elapsed_s": res["elapsed_s"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
