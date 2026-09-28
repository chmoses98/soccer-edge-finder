"""Systematic model-vs-market disagreement study (Phase 16).

Question: is there *any* subgroup of matches in which DATA_ONLY (dc_laplace_v1) is reliably
better than the de-vigged Bet365 pre-match price?  Targets: P(home), P(draw), P(away) and
O/U 2.5.  Buckets: disagreement size and sign, league, market-favourite size (terciles of
P(fav)), favourite side, promoted / thin-history involvement, season stage (matchday terciles),
team-strength uncertainty (Laplace sd of log(lam/mu), terciles) and scoring environment
(lam+mu terciles).

Per cell: n, market log loss, data log loss, realised rate vs both means, bootstrap 95% CI on the
paired per-match log-loss difference (data - market; negative = data better), and the number of
scored seasons in which data beat the market inside the cell.  A cell is called "informative"
only if n >= 200, the CI excludes 0 in favour of the data model, and the data model wins in at
least 4 of the 7 scored seasons.  Pre-registered expectation: no informative subgroup.

Walk-forward protocol and aligned sample: exactly ``research/walk_forward.py`` (via
``research/wf_common.py``).  Output: ``data/research/disagreement_v1.json``.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from research import wf_common as wf
from soccer_edge.core.serialization import content_hash, write_json

OUT = wf.REPO / "data" / "research" / "disagreement_v1.json"
MIN_CELL_N = 200
MIN_SEASONS_CONSISTENT = 4
GAP_EDGES = [-0.15, -0.10, -0.05, 0.05, 0.10, 0.15]


def targets(B: dict) -> dict[str, dict[str, np.ndarray]]:
    """Binary targets: predicted probabilities (data, market) and outcomes; plus a validity mask."""
    n = len(B["y"])
    tot = B["hg"] + B["ag"]
    ok_ou = ~np.isnan(B["p_mkt_o25"])
    return {
        "home": {
            "p_data": B["p_data"][:, 0],
            "p_mkt": B["p_mkt"][:, 0],
            "y": (B["y"] == 0).astype(float),
            "ok": np.ones(n, bool),
        },
        "draw": {
            "p_data": B["p_data"][:, 1],
            "p_mkt": B["p_mkt"][:, 1],
            "y": (B["y"] == 1).astype(float),
            "ok": np.ones(n, bool),
        },
        "away": {
            "p_data": B["p_data"][:, 2],
            "p_mkt": B["p_mkt"][:, 2],
            "y": (B["y"] == 2).astype(float),
            "ok": np.ones(n, bool),
        },
        "over25": {
            "p_data": B["p_data_o25"],
            "p_mkt": np.nan_to_num(B["p_mkt_o25"], nan=0.5),
            "y": (tot > 2.5).astype(float),
            "ok": ok_ou,
        },
    }


def bucket_families(B: dict, am: np.ndarray) -> dict[str, tuple[np.ndarray, dict]]:
    """Name -> (label array over all rows, metadata such as cut points)."""
    fams: dict[str, tuple[np.ndarray, dict]] = {}
    fams["league"] = (B["division"].astype(str), {})
    pfav = B["p_mkt"].max(axis=1)
    lab, cuts = wf.tercile_labels(pfav[am])
    full = np.full(len(pfav), "", dtype=object)
    full[am] = lab
    fams["market_favourite_size"] = (full.astype(str), {"tercile_cuts_p_fav": cuts})
    side = np.where(np.argmax(B["p_mkt"], axis=1) == 0, "home_favourite", "away_favourite")
    fams["favourite_side"] = (side.astype(str), {})
    prom = (B["promoted_home"] == 1) | (B["promoted_away"] == 1)
    fams["promoted_involved"] = (np.where(prom, "promoted", "not_promoted").astype(str), {})
    thin = (B["eff_home"] < 8) | (B["eff_away"] < 8)
    fams["thin_history_involved"] = (
        np.where(thin, "thin_history", "established").astype(str),
        {"definition": "either team < 8 effective (decayed) matches at fit time"},
    )
    lab, cuts = wf.tercile_labels(B["matchday"][am], ("early", "mid", "late"))
    full = np.full(len(pfav), "", dtype=object)
    full[am] = lab
    fams["season_stage"] = (full.astype(str), {"tercile_cuts_matchday": cuts})
    lab, cuts = wf.tercile_labels(B["sd_logdiff"][am])
    full = np.full(len(pfav), "", dtype=object)
    full[am] = lab
    fams["strength_uncertainty"] = (
        full.astype(str),
        {"tercile_cuts_sd_logdiff": cuts, "definition": "Laplace sd of log(lam) - log(mu)"},
    )
    lab, cuts = wf.tercile_labels((B["lam"] + B["mu"])[am])
    full = np.full(len(pfav), "", dtype=object)
    full[am] = lab
    fams["scoring_environment"] = (full.astype(str), {"tercile_cuts_lam_plus_mu": cuts})
    return fams


def cell_stats(t: dict[str, np.ndarray], seasons: np.ndarray, m: np.ndarray, n_boot: int) -> dict:
    pd_, pm_, y = t["p_data"][m], t["p_mkt"][m], t["y"][m]
    ld, lm = wf.binary_ll(pd_, y), wf.binary_ll(pm_, y)
    diff = ld - lm
    out = {
        "n": int(m.sum()),
        "market_log_loss": round(float(lm.mean()), 5),
        "data_log_loss": round(float(ld.mean()), 5),
        "realised_rate": round(float(y.mean()), 4),
        "data_mean": round(float(pd_.mean()), 4),
        "market_mean": round(float(pm_.mean()), 4),
        "market_brier": round(float(((pm_ - y) ** 2).mean()), 5),
        "data_brier": round(float(((pd_ - y) ** 2).mean()), 5),
    }
    if m.sum() >= 30:
        out["paired_ll_diff_data_minus_market"] = wf.paired_ci(diff, n_boot=n_boot)
        out.update(wf.season_consistency(diff, seasons[m]))
        ci = out["paired_ll_diff_data_minus_market"]["ci95"]
        out["informative_for_data"] = bool(
            m.sum() >= MIN_CELL_N
            and ci[1] < 0
            and out["seasons_data_better"] >= MIN_SEASONS_CONSISTENT
        )
        out["market_reliably_better"] = bool(
            m.sum() >= MIN_CELL_N
            and ci[0] > 0
            and (out["seasons_evaluated"] - out["seasons_data_better"]) >= MIN_SEASONS_CONSISTENT
        )
    return out


def run(B: dict, *, n_boot: int = 1000) -> dict:
    t0 = time.time()
    am = wf.aligned_mask(B)
    seasons = B["season"]
    T = targets(B)
    fams = bucket_families(B, am)
    y3 = B["y"]
    ll3d = wf.multiclass_ll(B["p_data"], y3)
    ll3m = wf.multiclass_ll(B["p_mkt"], y3)
    out: dict = {
        "protocol": wf.PROTOCOL_VERSION,
        "study": "disagreement_v1",
        "n_aligned": int(am.sum()),
        "rules": {
            "min_cell_n": MIN_CELL_N,
            "min_seasons_data_better": MIN_SEASONS_CONSISTENT,
            "ci": "bootstrap 95% on mean paired per-match log-loss difference (data - market)",
            "informative": "n >= 200 AND CI upper < 0 AND data better in >= 4 scored seasons",
        },
        "overall": {},
        "by_disagreement": {},
        "by_bucket": {},
        "informative_cells": [],
        "market_reliably_better_cells": [],
        "n_cells_tested": 0,
    }
    for name, t in T.items():
        base = am & t["ok"]
        out["overall"][name] = cell_stats(t, seasons, base, n_boot)
    out["overall"]["1x2_3way"] = {
        "n": int(am.sum()),
        "data_log_loss": round(float(ll3d[am].mean()), 5),
        "market_log_loss": round(float(ll3m[am].mean()), 5),
        "paired_ll_diff_data_minus_market": wf.paired_ci(ll3d[am] - ll3m[am], n_boot=n_boot),
    }
    n_cells = 0
    # 1. disagreement size and sign per target
    for name, t in T.items():
        base = am & t["ok"]
        gap = t["p_data"] - t["p_mkt"]
        lab = wf.bin_labels(gap, GAP_EDGES)
        out["by_disagreement"][name] = {}
        for lb in sorted(set(lab[base]), key=lambda s: float(s.strip("<>=[").split(",")[0])):
            m = base & (lab == lb)
            if m.sum() < 30:
                continue
            cs = cell_stats(t, seasons, m, n_boot)
            out["by_disagreement"][name][lb] = cs
            n_cells += 1
            _collect(out, f"disagreement/{name}/{lb}", cs)
    # 2. the other bucket families, all four targets each (+ 3-way 1X2 paired diff)
    for fam, (lab, meta) in fams.items():
        out["by_bucket"][fam] = {"meta": meta, "cells": {}}
        for lb in sorted(set(lab[am])):
            if lb == "":
                continue
            cell: dict = {}
            m3 = am & (lab == lb)
            cell["1x2_3way"] = {
                "n": int(m3.sum()),
                "data_log_loss": round(float(ll3d[m3].mean()), 5),
                "market_log_loss": round(float(ll3m[m3].mean()), 5),
                "paired_ll_diff_data_minus_market": wf.paired_ci(
                    ll3d[m3] - ll3m[m3], n_boot=n_boot
                ),
                **wf.season_consistency(ll3d[m3] - ll3m[m3], seasons[m3]),
            }
            for name, t in T.items():
                m = am & t["ok"] & (lab == lb)
                if m.sum() < 30:
                    continue
                cs = cell_stats(t, seasons, m, n_boot)
                cell[name] = cs
                n_cells += 1
                _collect(out, f"{fam}/{lb}/{name}", cs)
            out["by_bucket"][fam]["cells"][lb] = cell
    out["n_cells_tested"] = n_cells
    out["expected_false_positives_at_5pct"] = round(0.05 * n_cells, 1)
    out["conclusion"] = (
        "no informative subgroup"
        if not out["informative_cells"]
        else f"{len(out['informative_cells'])} informative cell(s) - inspect before believing"
    )
    out["elapsed_s"] = round(time.time() - t0, 1)
    return out


def _collect(out: dict, key: str, cs: dict) -> None:
    if cs.get("informative_for_data"):
        out["informative_cells"].append(
            {
                "cell": key,
                **{
                    k: cs[k]
                    for k in ("n", "paired_ll_diff_data_minus_market", "seasons_data_better")
                },
            }
        )
    if cs.get("market_reliably_better"):
        out["market_reliably_better_cells"].append(
            {"cell": key, "n": cs["n"], "diff": cs["paired_ll_diff_data_minus_market"]["mean"]}
        )


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
    res["frozen_v1"] = wf.frozen_v1_summary()
    res["result_hash"] = content_hash({k: v for k, v in res.items() if k != "elapsed_s"})
    write_json(Path(a.out), res)
    print(
        json.dumps(
            {
                "overall": res["overall"],
                "informative_cells": res["informative_cells"],
                "n_market_reliably_better": len(res["market_reliably_better_cells"]),
                "n_cells_tested": res["n_cells_tested"],
                "conclusion": res["conclusion"],
                "elapsed_s": res["elapsed_s"],
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
