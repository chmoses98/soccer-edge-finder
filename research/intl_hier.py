"""intl_hier_v1 walk-forward benchmark (remediation phase 17; audit §E acceptance).

Protocol (fixed before looking at holdout numbers)
--------------------------------------------------
* Data: the immutable normalised CC0 international dataset (`data/international/results_v1.csv.gz`;
  FIFA members only, neutral flag, point-in-time Elo from the same archive).
* Walk-forward, monthly refit, first fit 2014-01-01; every match from the first fit onward is scored
  with the latest posterior fitted strictly before its date.
* SELECTION window: matches 2014-01-01 .. 2021-12-31. Grid: friendly weight w in {0.4, 0.6, 0.8, 1.0}
  x recency half-life in {1, 2, 3} years. Primary criterion: 3-way log loss on the selection window.
* ONE-TIME HOLDOUT: 2022-01-01 .. 2026-08-26, scored once with the chosen configuration.
* Baselines on the same matches: (a) `elo_logit` - ordinal logit on (Elo difference + home/neutral),
  thresholds and slope refitted yearly on strictly earlier matches; (b) `intl_pool_current` - the
  production configuration: club `DixonColesFitter` (dc_laplace_v1 priors, decay 0.0065/day, weight 1,
  neutral ignored), 730-day lookback, monthly refit.
* Acceptance (all must hold on the holdout): intl_hier_v1 3-way log loss < both baselines with paired
  95% CI upper bound < 0, separately for competitive matches and friendlies; mismatch calibration for
  Elo gap >= 300 (|mean predicted underdog win - realised| <= 2 pt) and no gap >= 400 match priced with
  P(underdog) > 2x the realised bin rate; neutral matches predicted with gamma = 0 and listed-home /
  listed-away expected goals on neutral matches within MC error of realised; ECE <= 0.03 per outcome;
  cross-confederation calibration reported.
* If it fails, the negative result is preserved and the production international shadows stay
  disabled/noisy (audit §E6).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import minimize

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from soccer_edge.evaluation.metrics import bootstrap_mean_ci  # noqa: E402
from soccer_edge.model.analytic import outcome_probs, score_matrix  # noqa: E402
from soccer_edge.model.intl_hier import IntlHierConfig, IntlHierFitter, IntlMatchRow  # noqa: E402
from soccer_edge.model.strength import DixonColesFitter, MatchRow  # noqa: E402
from soccer_edge.providers.international_results import read_dataset  # noqa: E402

PROTOCOL = "intl_hier_v1_protocol_v1"
FIRST_FIT = date(2014, 1, 1)
SELECTION_END = date(2021, 12, 31)
HOLDOUT_START = date(2022, 1, 1)
GRID = [(w, h) for w in (0.4, 0.6, 0.8, 1.0) for h in (1.0, 2.0, 3.0)]
OUT_DIR = REPO / "data" / "research"
CACHE = REPO / "data" / "cache" / "intl_hier"


def load_rows() -> list[IntlMatchRow]:
    return [
        IntlMatchRow(
            date.fromisoformat(r["date"]),
            r["home_id"],
            r["away_id"],
            r["home_goals"],
            r["away_goals"],
            r["neutral"],
            r["competitive"],
            r["home_conf"],
            r["away_conf"],
            r["home_elo_pre"],
            r["away_elo_pre"],
        )
        for r in read_dataset(REPO / "data" / "international")
    ]


def month_starts(first: date, last: date) -> list[date]:
    out = []
    d = date(first.year, first.month, 1)
    while d <= last:
        out.append(d)
        d = date(d.year + (d.month == 12), 1 if d.month == 12 else d.month + 1, 1)
    return out


def outcome_index(h: int, a: int) -> int:
    return 0 if h > a else 1 if h == a else 2


def walk_forward_hier(
    rows: list[IntlMatchRow], cfg: IntlHierConfig, *, verbose: bool = False
) -> dict[str, np.ndarray]:
    """Monthly MAP refits; returns per-match probabilities for every match from FIRST_FIT onward."""
    key = f"hier_w{cfg.friendly_weight}_h{cfg.half_life_years}_v{cfg.version}"
    CACHE.mkdir(parents=True, exist_ok=True)
    cpath = CACHE / f"{key}.npz"
    if cpath.exists():
        d = np.load(cpath, allow_pickle=True)
        return {k: d[k] for k in d.files}
    fitter = IntlHierFitter(cfg)
    last = max(r.date for r in rows)
    fits = month_starts(FIRST_FIT, last)
    cols: dict[str, list] = defaultdict(list)
    t0 = time.time()
    post = None
    fi = 0
    rows_sorted = sorted(rows, key=lambda r: r.date)
    for r in rows_sorted:
        if r.date < FIRST_FIT:
            continue
        while fi < len(fits) and fits[fi] <= r.date:
            post = fitter.fit(rows_sorted, as_of=fits[fi], laplace=False)
            fi += 1
            if verbose and fi % 12 == 0:
                print(f"  {key}: fit {fits[fi - 1]} ({time.time() - t0:.0f}s)")
        if post is None or r.home not in post.teams or r.away not in post.teams:
            continue
        lam, mu = post.expected_goals(r.home, r.away, neutral=r.neutral, competitive=r.competitive)
        op = outcome_probs(score_matrix(lam, mu, post.diagnostics["rho"]))
        cols["date"].append(r.date.isoformat())
        cols["home"].append(r.home)
        cols["away"].append(r.away)
        cols["y"].append(outcome_index(r.home_goals, r.away_goals))
        cols["hg"].append(r.home_goals)
        cols["ag"].append(r.away_goals)
        cols["p"].append([op["home"], op["draw"], op["away"]])
        cols["lam"].append(lam)
        cols["mu"].append(mu)
        cols["neutral"].append(int(r.neutral))
        cols["competitive"].append(int(r.competitive))
        cols["cross_conf"].append(int(r.home_conf != r.away_conf))
        cols["elo_diff"].append(r.home_elo - r.away_elo)
        cols["low_conn"].append(int(bool(post.prediction_flags(r.home, r.away))))
    table = {k: np.array(v) for k, v in cols.items()}
    np.savez_compressed(cpath, **table)
    return table


def walk_forward_pool(rows: list[IntlMatchRow], *, verbose: bool = False) -> dict[str, np.ndarray]:
    """The production international-pool configuration on the same data (audit §E baseline b)."""
    cpath = CACHE / "pool_current.npz"
    CACHE.mkdir(parents=True, exist_ok=True)
    if cpath.exists():
        d = np.load(cpath, allow_pickle=True)
        return {k: d[k] for k in d.files}
    fitter = DixonColesFitter()
    rows_sorted = sorted(rows, key=lambda r: r.date)
    mrows = [MatchRow(r.date, r.home, r.away, r.home_goals, r.away_goals) for r in rows_sorted]
    fits = month_starts(FIRST_FIT, rows_sorted[-1].date)
    cols: dict[str, list] = defaultdict(list)
    post = None
    fi = 0
    t0 = time.time()
    for r, mr in zip(rows_sorted, mrows):
        if r.date < FIRST_FIT:
            continue
        while fi < len(fits) and fits[fi] <= r.date:
            lb = fits[fi] - timedelta(days=730)
            fit_rows = [m for m in mrows if lb <= m.date < fits[fi]]
            post = fitter.fit(fit_rows, as_of=fits[fi])
            fi += 1
            if verbose and fi % 12 == 0:
                print(f"  pool: fit {fits[fi - 1]} ({time.time() - t0:.0f}s)")
        if post is None or r.home not in post.teams or r.away not in post.teams:
            continue
        lam, mu = post.expected_goals(r.home, r.away)  # neutral ignored: the production defect
        op = outcome_probs(score_matrix(lam, mu, float(post.mean[post.idx_rho])))
        cols["date"].append(r.date.isoformat())
        cols["home"].append(r.home)
        cols["away"].append(r.away)
        cols["p"].append([op["home"], op["draw"], op["away"]])
    table = {k: np.array(v) for k, v in cols.items()}
    np.savez_compressed(cpath, **table)
    return table


def elo_logit_probs(rows: list[IntlMatchRow]) -> dict[str, np.ndarray]:
    """Ordinal logit on Elo difference (+ home advantage unless neutral), thresholds refitted each
    January on strictly earlier matches since 2000."""
    rows_sorted = sorted(rows, key=lambda r: r.date)
    xs = np.array([r.home_elo - r.away_elo for r in rows_sorted]) / 400.0
    hv = np.array([0.0 if r.neutral else 1.0 for r in rows_sorted])
    ys = np.array([outcome_index(r.home_goals, r.away_goals) for r in rows_sorted])
    ds = np.array([r.date.toordinal() for r in rows_sorted])

    def probs(theta, x, h):
        b, hadv, c1, c2 = theta
        z = b * x + hadv * h
        p_away = 1 / (1 + np.exp(-(c1 - z)))
        p_notwin = 1 / (1 + np.exp(-(c2 - z)))
        p_home = 1 - p_notwin
        p_draw = np.clip(p_notwin - p_away, 1e-9, None)
        return np.column_stack([p_home, p_draw, p_away])

    def nll(theta, x, h, y):
        p = probs(theta, x, h)
        return -np.sum(np.log(np.clip(p[np.arange(len(y)), y], 1e-9, None)))

    out_p = {}
    theta = np.array([1.0, 0.3, -0.5, 0.5])
    for yr in range(FIRST_FIT.year, rows_sorted[-1].date.year + 1):
        train = (ds < date(yr, 1, 1).toordinal()) & (ds >= date(2000, 1, 1).toordinal())
        res = minimize(
            nll,
            theta,
            args=(xs[train], hv[train], ys[train]),
            method="L-BFGS-B",
            bounds=[(0, 10), (-2, 2), (-5, 5), (-5, 5)],
        )
        theta = res.x
        cur = (ds >= date(yr, 1, 1).toordinal()) & (ds < date(yr + 1, 1, 1).toordinal())
        for i in np.where(cur)[0]:
            out_p[(rows_sorted[i].date.isoformat(), rows_sorted[i].home, rows_sorted[i].away)] = (
                probs(theta, xs[i : i + 1], hv[i : i + 1])[0]
            )
    return out_p


def ll3(P: np.ndarray, y: np.ndarray) -> np.ndarray:
    return -np.log(np.clip(P[np.arange(len(y)), y], 1e-9, None))


def ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    tot = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi) if hi < 1 else (p >= lo) & (p <= hi)
        if m.any():
            tot += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(tot)


def paired(diff: np.ndarray) -> dict[str, Any]:
    lo, hi = bootstrap_mean_ci(diff, n_boot=1000)
    return {"mean": float(diff.mean()), "ci95": [float(lo), float(hi)], "n": len(diff)}


def align(
    hier: dict[str, np.ndarray], pool: dict[str, np.ndarray], elo: dict, window: tuple[date, date]
) -> dict[str, np.ndarray]:
    keyp = {
        (str(d), str(h), str(a)): i
        for i, (d, h, a) in enumerate(zip(pool["date"], pool["home"], pool["away"]))
    }
    keep, ip, pe = [], [], []
    for i, (d, h, a) in enumerate(zip(hier["date"], hier["home"], hier["away"])):
        dd = date.fromisoformat(str(d))
        if not (window[0] <= dd <= window[1]):
            continue
        k = (str(d), str(h), str(a))
        if k not in keyp or k not in elo:
            continue
        keep.append(i)
        ip.append(keyp[k])
        pe.append(elo[k])
    keep = np.array(keep, dtype=int)
    return {
        "y": hier["y"][keep],
        "p_hier": hier["p"][keep],
        "p_pool": pool["p"][np.array(ip, dtype=int)],
        "p_elo": np.array(pe),
        "competitive": hier["competitive"][keep].astype(bool),
        "neutral": hier["neutral"][keep].astype(bool),
        "cross_conf": hier["cross_conf"][keep].astype(bool),
        "elo_diff": hier["elo_diff"][keep],
        "hg": hier["hg"][keep],
        "ag": hier["ag"][keep],
        "lam": hier["lam"][keep],
        "mu": hier["mu"][keep],
        "low_conn": hier["low_conn"][keep].astype(bool),
    }


def evaluate(al: dict[str, np.ndarray]) -> dict[str, Any]:
    y = al["y"]
    res: dict[str, Any] = {"n": len(y)}
    for name in ("hier", "pool", "elo"):
        P = al[f"p_{name}"]
        res[f"ll_{name}"] = float(ll3(P, y).mean())
        res[f"ece_{name}"] = {
            k: ece(P[:, i], (y == i).astype(float)) for i, k in enumerate(("home", "draw", "away"))
        }
    res["paired_hier_minus_pool"] = paired(ll3(al["p_hier"], y) - ll3(al["p_pool"], y))
    res["paired_hier_minus_elo"] = paired(ll3(al["p_hier"], y) - ll3(al["p_elo"], y))
    for label, m in (
        ("competitive", al["competitive"]),
        ("friendly", ~al["competitive"]),
        ("neutral", al["neutral"]),
        ("cross_confederation", al["cross_conf"]),
    ):
        if m.sum() < 30:
            continue
        res[label] = {
            "n": int(m.sum()),
            "ll_hier": float(ll3(al["p_hier"][m], y[m]).mean()),
            "ll_pool": float(ll3(al["p_pool"][m], y[m]).mean()),
            "ll_elo": float(ll3(al["p_elo"][m], y[m]).mean()),
            "paired_hier_minus_pool": paired(
                ll3(al["p_hier"][m], y[m]) - ll3(al["p_pool"][m], y[m])
            ),
            "paired_hier_minus_elo": paired(ll3(al["p_hier"][m], y[m]) - ll3(al["p_elo"][m], y[m])),
        }
    # mismatch calibration: underdog = lower pre-match Elo
    gap = np.abs(al["elo_diff"])
    home_is_dog = al["elo_diff"] < 0
    p_dog = np.where(home_is_dog, al["p_hier"][:, 0], al["p_hier"][:, 2])
    dog_won = np.where(home_is_dog, y == 0, y == 2).astype(float)
    mism = {}
    for lo, hi in ((300, 400), (400, 10_000)):
        m = (gap >= lo) & (gap < hi)
        if m.sum() >= 20:
            realised = float(dog_won[m].mean())
            mism[f"elo_gap_{lo}_{hi}"] = {
                "n": int(m.sum()),
                "mean_p_underdog": float(p_dog[m].mean()),
                "realised_underdog": realised,
                "max_p_underdog": float(p_dog[m].max()),
                "n_priced_gt_2x_realised": int((p_dog[m] > 2 * max(realised, 1e-6)).sum()),
            }
    res["mismatch"] = mism
    # neutral handling: expected goals for listed home/away on neutral matches vs realised
    nm = al["neutral"]
    res["neutral_goals"] = (
        {
            "n": int(nm.sum()),
            "pred_home": float(al["lam"][nm].mean()),
            "real_home": float(al["hg"][nm].mean()),
            "pred_away": float(al["mu"][nm].mean()),
            "real_away": float(al["ag"][nm].mean()),
        }
        if nm.any()
        else None
    )
    res["low_connectivity_share"] = float(al["low_conn"].mean())
    return res


def cmd_select(a: argparse.Namespace) -> int:
    rows = load_rows()
    pool = walk_forward_pool(rows, verbose=a.verbose)
    elo = elo_logit_probs(rows)
    grid = {}
    for w, h in GRID:
        cfg = IntlHierConfig(friendly_weight=w, half_life_years=h)
        hier = walk_forward_hier(rows, cfg, verbose=a.verbose)
        al = align(hier, pool, elo, (FIRST_FIT, SELECTION_END))
        grid[f"w{w}_h{h}"] = {
            "friendly_weight": w,
            "half_life_years": h,
            **{
                k: v
                for k, v in evaluate(al).items()
                if k
                in (
                    "n",
                    "ll_hier",
                    "ll_pool",
                    "ll_elo",
                    "paired_hier_minus_pool",
                    "paired_hier_minus_elo",
                )
            },
        }
        print(
            f"  w={w} h={h}: n={grid[f'w{w}_h{h}']['n']} ll_hier={grid[f'w{w}_h{h}']['ll_hier']:.5f} pool={grid[f'w{w}_h{h}']['ll_pool']:.5f} elo={grid[f'w{w}_h{h}']['ll_elo']:.5f}"
        )
    ranked = sorted(grid, key=lambda k: grid[k]["ll_hier"])
    out = {
        "schema": "intl_hier_selection_v1",
        "protocol": PROTOCOL,
        "selection_window": [FIRST_FIT.isoformat(), SELECTION_END.isoformat()],
        "grid": grid,
        "ranking": ranked,
        "chosen": ranked[0],
        "chosen_config": {
            "friendly_weight": grid[ranked[0]]["friendly_weight"],
            "half_life_years": grid[ranked[0]]["half_life_years"],
        },
        "frozen_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "intl_hier_selection.json").write_text(json.dumps(out, indent=1) + "\n")
    print("chosen:", ranked[0])
    return 0


def cmd_holdout(a: argparse.Namespace) -> int:
    sel = json.loads((OUT_DIR / "intl_hier_selection.json").read_text())
    cfg = IntlHierConfig(**sel["chosen_config"])
    rows = load_rows()
    pool = walk_forward_pool(rows)
    elo = elo_logit_probs(rows)
    hier = walk_forward_hier(rows, cfg)
    last = max(r.date for r in rows)
    al = align(hier, pool, elo, (HOLDOUT_START, last))
    ev = evaluate(al)
    acc = {
        "beats_pool_ci_upper_lt_0": ev["paired_hier_minus_pool"]["ci95"][1] < 0,
        "beats_elo_ci_upper_lt_0": ev["paired_hier_minus_elo"]["ci95"][1] < 0,
        "beats_both_on_competitive": ev.get("competitive", {})
        .get("paired_hier_minus_pool", {})
        .get("ci95", [0, 1])[1]
        < 0
        and ev.get("competitive", {}).get("paired_hier_minus_elo", {}).get("ci95", [0, 1])[1] < 0,
        "beats_both_on_friendlies": ev.get("friendly", {})
        .get("paired_hier_minus_pool", {})
        .get("ci95", [0, 1])[1]
        < 0
        and ev.get("friendly", {}).get("paired_hier_minus_elo", {}).get("ci95", [0, 1])[1] < 0,
        "mismatch_300_calibrated_within_2pt": all(
            abs(v["mean_p_underdog"] - v["realised_underdog"]) <= 0.02
            for v in ev["mismatch"].values()
        )
        if ev["mismatch"]
        else False,
        "no_gap_ge_400_priced_gt_2x_realised": all(
            v["n_priced_gt_2x_realised"] == 0
            for k, v in ev["mismatch"].items()
            if k.startswith("elo_gap_400")
        )
        if ev["mismatch"]
        else False,
        "ece_le_0_03_each_outcome": all(v <= 0.03 for v in ev["ece_hier"].values()),
        "neutral_goals_within_0_05": (
            ev["neutral_goals"] is not None
            and abs(ev["neutral_goals"]["pred_home"] - ev["neutral_goals"]["real_home"]) <= 0.05
            and abs(ev["neutral_goals"]["pred_away"] - ev["neutral_goals"]["real_away"]) <= 0.05
        ),
    }
    acc["all_pass"] = all(acc.values())
    out = {
        "schema": "intl_hier_holdout_v1",
        "protocol": PROTOCOL,
        "chosen": sel["chosen"],
        "chosen_config": sel["chosen_config"],
        "holdout_window": [HOLDOUT_START.isoformat(), last.isoformat()],
        "evaluation": ev,
        "acceptance": acc,
        "frozen_at": datetime.now(UTC).isoformat(),
        "note": "ONE-TIME holdout; configuration chosen on 2014-2021 only",
    }
    (OUT_DIR / "intl_hier_holdout.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(
        json.dumps(
            {
                "acceptance": acc,
                "ll": {k: ev[k] for k in ("ll_hier", "ll_pool", "ll_elo")},
                "mismatch": ev["mismatch"],
                "neutral": ev["neutral_goals"],
            },
            indent=1,
            default=str,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["select", "holdout", "all"])
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd in ("select", "all"):
        cmd_select(a)
    if a.cmd in ("holdout", "all"):
        cmd_holdout(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
