"""dc_laplace_v2 + world_sim_v2: pre-registered selection, ONE-TIME holdout, acceptance tests, and the
re-run of the frozen benchmark across model families and engines (remediation phases 12-14; audit §D,
§P8-9, phase 14).

Protocol (fixed before any holdout number was looked at)
--------------------------------------------------------
* Data / sample: `research/wf_common` walk-forward (E0, SP1, D1, I1, F1; weekly refit; Bet365 pre-match
  odds as the market), aligned sample rule of walk_forward_v1.
* DESIGN / TRAIN seasons: 2019-20 .. 2023-24 (`select`). The grid is decay xi in {0.0065, 0.004, 0.003}
  x team prior sd s in {0.35, 0.50, 0.60} (9 variants). Primary criterion: 1X2 log loss on the design
  seasons; tie-break: O/U 2.5 log loss. Nothing else is tuned.
* ONE-TIME HOLDOUT: 2024-25 + 2025-26 (`holdout`), scored once with the chosen configuration. This file
  writes the result; re-running does not change the choice (it is read from the selection file).
* Acceptance (all on the holdout; fail closed): away level error <= 2%, home level error <= 2% (mean
  predicted / mean realised goals, per league and pooled); home ECE <= 0.020; paired 1X2 log-loss gain
  over v1 with 95% CI upper bound < 0; Brier; O/U 2.5 log loss; market-relative gap reported with CI
  (no requirement to beat the market); hybrid weight reported. Likelihood-ratio statistic of the
  intercept per league-season on the design seasons (>= 6.63 in >= 90% of fits).
* Engines (`engines`): on a stratified subsample of the aligned holdout+design matches, price 1X2 /
  O2.5 / BTTS / expected goals through (a) the analytic per-world Dixon-Coles matrix, (b) the production
  world_sim_v1 path (worlds_v1 + minute_engine_v1), (c) world_sim_v2, for both posteriors; report the
  absolute reconciliation gaps to (a). This is the first historical evidence for the production path.

Outputs: data/research/dc_v2_selection.json, data/research/dc_v2_holdout.json,
data/research/world_sim_benchmark.json. Losing variants are kept in the files.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from research.wf_common import (  # noqa: E402
    V2_GRID,
    aligned_mask,
    binary_ll,
    ece,
    fitter_for,
    hybrid_weights,
    load_data,
    load_or_run,
    multiclass_ll,
    paired_ci,
    season_start,
    strength_for,
)

PROTOCOL = "dc_v2_protocol_v1"
DESIGN_SEASONS = (2019, 2020, 2021, 2022, 2023)
HOLDOUT_SEASONS = (2024, 2025)
BASE_V1 = "dc_laplace_v1"
OUT_SEL = REPO / "data" / "research" / "dc_v2_selection.json"
OUT_HOLD = REPO / "data" / "research" / "dc_v2_holdout.json"
OUT_ENG = REPO / "data" / "research" / "world_sim_benchmark.json"


def _starts(table: dict[str, np.ndarray]) -> np.ndarray:
    return np.array([season_start(s) for s in table["season"]])


def _mask(table: dict[str, np.ndarray], seasons: tuple[int, ...]) -> np.ndarray:
    return aligned_mask(table) & np.isin(_starts(table), seasons)


def _metrics(table: dict[str, np.ndarray], m: np.ndarray) -> dict[str, Any]:
    P = table["p_data"][m]
    y = table["y"][m]
    hg, ag = table["hg"][m], table["ag"][m]
    over = ((hg + ag) > 2.5).astype(float)
    out = {
        "n": int(m.sum()),
        "ll_1x2": float(multiclass_ll(P, y).mean()),
        "ll_1x2_market": float(multiclass_ll(table["p_mkt"][m], y).mean()),
        "ll_ou25": float(binary_ll(table["p_data_o25"][m], over).mean()),
        "ll_ou25_market": float(binary_ll(table["p_mkt_o25"][m], over).mean()),
        "brier_1x2": float(np.mean(np.sum((P - np.eye(3)[y]) ** 2, axis=1))),
        "ece_home": float(ece(P[:, 0], (y == 0).astype(float))),
        "ece_draw": float(ece(P[:, 1], (y == 1).astype(float))),
        "ece_away": float(ece(P[:, 2], (y == 2).astype(float))),
        "home_level_ratio": float(table["lam"][m].mean() / hg.mean()),
        "away_level_ratio": float(table["mu"][m].mean() / ag.mean()),
        "mean_p_home": float(P[:, 0].mean()),
        "realised_home": float((y == 0).mean()),
        "mean_p_over25": float(table["p_data_o25"][m].mean()),
        "realised_over25": float(over.mean()),
    }
    by_league = {}
    for lg in sorted(set(table["division"][m].tolist())):
        mm = m & (table["division"] == lg)
        by_league[lg] = {
            "n": int(mm.sum()),
            "home_level_ratio": float(table["lam"][mm].mean() / table["hg"][mm].mean()),
            "away_level_ratio": float(table["mu"][mm].mean() / table["ag"][mm].mean()),
            "ll_1x2": float(multiclass_ll(table["p_data"][mm], table["y"][mm]).mean()),
        }
    out["by_league"] = by_league
    # >10-point disagreement bucket bias (audit §D acceptance 4)
    gap = table["p_data"][m][:, 0] - table["p_mkt"][m][:, 0]
    big = np.abs(gap) > 0.10
    out["disagreement_gt10pt"] = {
        "n": int(big.sum()),
        "bias_data_minus_realised": float((P[big, 0] - (y[big] == 0)).mean())
        if big.any()
        else None,
    }
    return out


def _paired(table_a, table_b, m):
    """Paired per-match differences (a - b) on the same rows; both tables share row order."""
    d1 = multiclass_ll(table_a["p_data"][m], table_a["y"][m]) - multiclass_ll(
        table_b["p_data"][m], table_b["y"][m]
    )
    over = ((table_a["hg"][m] + table_a["ag"][m]) > 2.5).astype(float)
    d2 = binary_ll(table_a["p_data_o25"][m], over) - binary_ll(table_b["p_data_o25"][m], over)
    return {"ll_1x2_diff": paired_ci(d1), "ll_ou25_diff": paired_ci(d2)}


def _same_rows(a, b) -> bool:
    return (
        len(a["date"]) == len(b["date"])
        and np.array_equal(a["home"], b["home"])
        and np.array_equal(a["date"].astype(str), b["date"].astype(str))
    )


def cmd_select(a: argparse.Namespace) -> int:
    matches, extras, data_hash = load_data()
    base = load_or_run(BASE_V1, matches, extras, data_hash, keep_matrix=False, verbose=False)
    m = _mask(base, DESIGN_SEASONS)
    rows = {}
    for v in V2_GRID:
        t = load_or_run(v, matches, extras, data_hash, keep_matrix=False, verbose=a.verbose)
        assert _same_rows(base, t), f"row misalignment for {v}"
        met = _metrics(t, m)
        met["paired_vs_v1"] = _paired(t, base, m)
        rows[v] = met
    base_met = _metrics(base, m)
    ranked = sorted(rows, key=lambda v: (rows[v]["ll_1x2"], rows[v]["ll_ou25"]))
    chosen = ranked[0]
    out = {
        "schema": "dc_v2_selection_v1",
        "protocol": PROTOCOL,
        "design_seasons": [f"{s}-{str(s + 1)[2:]}" for s in DESIGN_SEASONS],
        "criterion": "min 1X2 log loss on the design seasons; tie-break O/U 2.5 log loss",
        "data_hash": data_hash,
        "n_design": int(m.sum()),
        "v1": base_met,
        "grid": rows,
        "ranking": ranked,
        "chosen": chosen,
        "chosen_config": {k: v for k, v in strength_for(chosen).__dict__.items()},
        "frozen_at": datetime.now(UTC).isoformat(),
    }
    OUT_SEL.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print("chosen:", chosen, "1X2 LL", rows[chosen]["ll_1x2"], "v1", base_met["ll_1x2"])
    return 0


def _lr_intercept(matches, chosen: str) -> dict[str, Any]:
    """Likelihood-ratio statistic of the intercept per league-season on the design seasons."""
    from soccer_edge.model.strength import MatchRow

    by_ls: dict[tuple[str, str], list[MatchRow]] = defaultdict(list)
    for hm in matches:
        s0 = season_start(hm.result.season_id)
        if s0 in DESIGN_SEASONS:
            by_ls[(hm.division, hm.result.season_id)].append(
                MatchRow(
                    date.fromisoformat(hm.result.match_date),
                    hm.result.home_team_id,
                    hm.result.away_team_id,
                    hm.result.home_goals,
                    hm.result.away_goals,
                )
            )
    fitter = fitter_for(chosen)
    stats = {}
    for (div, season), rows in sorted(by_ls.items()):
        as_of = max(r.date for r in rows)
        as_of = date.fromordinal(as_of.toordinal() + 1)
        free = fitter.fit(rows, as_of=as_of)
        fixed = fitter.fit(rows, as_of=as_of, fix_intercept=0.0)
        stats[f"{div}|{season}"] = {
            "lr": 2 * (free.log_likelihood - fixed.log_likelihood),
            "kappa": free.diagnostics["fitted_intercept"],
            "gamma": free.diagnostics["fitted_gamma"],
            "n": len(rows),
        }
    n_sig = sum(1 for v in stats.values() if v["lr"] >= 6.63)
    return {
        "per_league_season": stats,
        "share_lr_ge_6_63": n_sig / max(len(stats), 1),
        "n_fits": len(stats),
        "passes": (n_sig / max(len(stats), 1)) >= 0.90,
    }


def cmd_holdout(a: argparse.Namespace) -> int:
    sel = json.loads(OUT_SEL.read_text())
    chosen = sel["chosen"]
    matches, extras, data_hash = load_data()
    base = load_or_run(BASE_V1, matches, extras, data_hash, keep_matrix=False, verbose=False)
    t = load_or_run(chosen, matches, extras, data_hash, keep_matrix=False, verbose=a.verbose)
    assert _same_rows(base, t)
    m = _mask(base, HOLDOUT_SEASONS)
    v2 = _metrics(t, m)
    v1 = _metrics(base, m)
    paired = _paired(t, base, m)
    mk = {
        "gap_1x2_vs_market": paired_ci(
            multiclass_ll(t["p_data"][m], t["y"][m]) - multiclass_ll(t["p_mkt"][m], t["y"][m])
        ),
        "gap_1x2_vs_market_v1": paired_ci(
            multiclass_ll(base["p_data"][m], base["y"][m])
            - multiclass_ll(base["p_mkt"][m], base["y"][m])
        ),
    }
    w2, P_hyb2 = hybrid_weights(t)
    w1, P_hyb1 = hybrid_weights(base)
    hyb = {
        "v2_weight_by_season": w2,
        "v1_weight_by_season": w1,
        "ll_hybrid_v2_holdout": float(multiclass_ll(P_hyb2[m], t["y"][m]).mean()),
        "ll_hybrid_v1_holdout": float(multiclass_ll(P_hyb1[m], base["y"][m]).mean()),
    }
    lr = _lr_intercept(matches, chosen)
    acceptance = {
        "away_level_error_le_2pct": abs(v2["away_level_ratio"] - 1) <= 0.02,
        "home_level_error_le_2pct": abs(v2["home_level_ratio"] - 1) <= 0.02,
        "away_level_error_le_2pct_every_league": all(
            abs(v["away_level_ratio"] - 1) <= 0.02 for v in v2["by_league"].values()
        ),
        "home_level_error_le_2pct_every_league": all(
            abs(v["home_level_ratio"] - 1) <= 0.02 for v in v2["by_league"].values()
        ),
        "home_ece_le_0_020": v2["ece_home"] <= 0.020,
        "ll_1x2_better_than_v1_ci_upper_lt_0": paired["ll_1x2_diff"]["ci95"][1] < 0,
        "ll_ou25_better_than_v1_ci_upper_lt_0": paired["ll_ou25_diff"]["ci95"][1] < 0,
        "disagreement_gt10pt_bias_le_0_02": (
            v2["disagreement_gt10pt"]["bias_data_minus_realised"] is None
            or abs(v2["disagreement_gt10pt"]["bias_data_minus_realised"]) <= 0.02
        ),
        "intercept_lr_ge_6_63_in_90pct": lr["passes"],
    }
    acceptance["all_pass"] = all(acceptance.values())
    out = {
        "schema": "dc_v2_holdout_v1",
        "protocol": PROTOCOL,
        "chosen": chosen,
        "chosen_config": sel["chosen_config"],
        "holdout_seasons": [f"{s}-{str(s + 1)[2:]}" for s in HOLDOUT_SEASONS],
        "data_hash": data_hash,
        "n_holdout": int(m.sum()),
        "v2": v2,
        "v1": v1,
        "paired_v2_minus_v1": paired,
        "market": mk,
        "hybrid": hyb,
        "intercept_lr": {k: v for k, v in lr.items() if k != "per_league_season"},
        "acceptance": acceptance,
        "frozen_at": datetime.now(UTC).isoformat(),
        "note": "ONE-TIME holdout: the configuration was chosen on 2019-24 only; this file is not to be regenerated with a different choice",
    }
    OUT_HOLD.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(
        json.dumps(
            {
                "acceptance": acceptance,
                "v2_ll_1x2": v2["ll_1x2"],
                "v1_ll_1x2": v1["ll_1x2"],
                "market": v2["ll_1x2_market"],
                "away_ratio": v2["away_level_ratio"],
                "home_ratio": v2["home_level_ratio"],
                "ece_home": v2["ece_home"],
            },
            indent=1,
        )
    )
    return 0


def cmd_engines(a: argparse.Namespace) -> int:
    """Engine reconciliation on a stratified subsample: analytic vs world_sim_v1 vs world_sim_v2."""
    from soccer_edge.model.analytic import outcome_probs, total_over
    from soccer_edge.model.context import MatchContext
    from soccer_edge.model.strength import MatchRow
    from soccer_edge.model.worlds import WorldConfig, WorldGenerator
    from soccer_edge.sim.engine import SimConfig, simulate
    from soccer_edge.sim.engine_v2 import SimConfigV2, score_matrices, simulate_v2

    sel = json.loads(OUT_SEL.read_text()) if OUT_SEL.exists() else None
    chosen = sel["chosen"] if sel else "dc_laplace_v2.d0065_s035"
    matches, extras, data_hash = load_data()
    base = load_or_run(BASE_V1, matches, extras, data_hash, keep_matrix=False, verbose=False)
    m = _mask(base, DESIGN_SEASONS + HOLDOUT_SEASONS)
    idx = np.where(m)[0]
    rng = np.random.default_rng(0)
    pick = np.sort(rng.choice(idx, size=min(a.n_sample, len(idx)), replace=False))
    by_div: dict[str, list] = defaultdict(list)
    for hm in matches:
        by_div[hm.division].append(hm)
    rows_by_div = {
        d: sorted(
            (
                MatchRow(
                    date.fromisoformat(hm.result.match_date),
                    hm.result.home_team_id,
                    hm.result.away_team_id,
                    hm.result.home_goals,
                    hm.result.away_goals,
                )
                for hm in hms
            ),
            key=lambda r: r.date,
        )
        for d, hms in by_div.items()
    }
    fitters = {"v1": fitter_for(BASE_V1), "v2": fitter_for(chosen)}
    fit_cache: dict[tuple[str, str, str], Any] = {}
    results = {k: defaultdict(list) for k in ("v1", "v2")}
    t0 = time.time()
    for n_done, i in enumerate(pick):
        div = str(base["division"][i])
        d = base["date"][i]
        d = d if isinstance(d, date) else date.fromisoformat(str(d)[:10])
        fit_date = base["fit_date"][i]
        fit_date = (
            fit_date if isinstance(fit_date, date) else date.fromisoformat(str(fit_date)[:10])
        )
        home, away = str(base["home"][i]), str(base["away"][i])
        hg, ag = int(base["hg"][i]), int(base["ag"][i])
        for key, fitter in fitters.items():
            ck = (key, div, fit_date.isoformat())
            if ck not in fit_cache:
                fit_rows = [r for r in rows_by_div[div] if r.date < fit_date]
                fit_cache[ck] = fitter.fit(fit_rows, as_of=fit_date)
            post = fit_cache[ck]
            ctx = MatchContext("fx", div, home, away, datetime(d.year, d.month, d.day, tzinfo=UTC))
            wrng = np.random.default_rng(int(i))
            worlds = WorldGenerator(post, WorldConfig()).generate(ctx, a.n_worlds, wrng)
            mats = score_matrices(worlds.lam_home, worlds.mu_away, worlds.rho)
            mean_mat = mats.mean(axis=0)
            an = outcome_probs(mean_mat)
            an_o25 = total_over(mean_mat, 2.5)
            an_btts = float(mean_mat[1:, 1:].sum())
            an_eh = float((np.arange(11)[:, None] * mean_mat).sum())
            an_ea = float((np.arange(11)[None, :] * mean_mat).sum())
            o1 = simulate(
                worlds,
                ctx,
                SimConfig(draws_per_world=a.draws, allocate_player_goals=False),
                seed=int(i) + 1,
            )
            o2 = simulate_v2(
                worlds,
                ctx,
                SimConfigV2(draws_per_world=a.draws, allocate_player_goals=False),
                seed=int(i) + 2,
            )
            for name, o in (("sim_v1", o1), ("sim_v2", o2)):
                r = results[key]
                r[f"{name}_draw_gap"].append(float((o.home_ft == o.away_ft).mean() - an["draw"]))
                r[f"{name}_home_gap"].append(float((o.home_ft > o.away_ft).mean() - an["home"]))
                r[f"{name}_o25_gap"].append(float(((o.home_ft + o.away_ft) > 2.5).mean() - an_o25))
                r[f"{name}_btts_gap"].append(
                    float(((o.home_ft > 0) & (o.away_ft > 0)).mean() - an_btts)
                )
                r[f"{name}_eh_ratio"].append(float(o.home_ft.mean() / an_eh))
                r[f"{name}_ea_ratio"].append(float(o.away_ft.mean() / an_ea))
                r[f"{name}_ll_1x2"].append(
                    float(
                        -np.log(
                            max(
                                [
                                    (o.home_ft > o.away_ft).mean(),
                                    (o.home_ft == o.away_ft).mean(),
                                    (o.away_ft > o.home_ft).mean(),
                                ][0 if hg > ag else 1 if hg == ag else 2],
                                1e-6,
                            )
                        )
                    )
                )
            r = results[key]
            r["analytic_ll_1x2"].append(
                float(
                    -np.log(
                        max(
                            an[["home", "draw", "away"][0 if hg > ag else 1 if hg == ag else 2]],
                            1e-6,
                        )
                    )
                )
            )
            r["lam"].append(float(worlds.lam_home.mean()))
            r["mu"].append(float(worlds.mu_away.mean()))
            r["hg"].append(hg)
            r["ag"].append(ag)
        if a.verbose and n_done % 100 == 0:
            print(f"  {n_done}/{len(pick)} ({time.time() - t0:.0f}s)")

    def summ(r: dict) -> dict:
        out = {}
        for k, v in r.items():
            arr = np.array(v, dtype=float)
            if k.endswith("_gap"):
                out[k] = {
                    "mean": float(arr.mean()),
                    "mean_abs": float(np.abs(arr).mean()),
                    "p95_abs": float(np.percentile(np.abs(arr), 95)),
                }
            elif k.endswith("_ratio"):
                out[k] = {"mean": float(arr.mean())}
            elif k.endswith("_ll_1x2"):
                out[k] = float(arr.mean())
        out["mean_lambda_over_realised_home"] = float(np.mean(r["lam"]) / np.mean(r["hg"]))
        out["mean_mu_over_realised_away"] = float(np.mean(r["mu"]) / np.mean(r["ag"]))
        out["n"] = len(r["hg"])
        return out

    out = {
        "schema": "world_sim_benchmark_v1",
        "protocol": PROTOCOL,
        "subsample": {
            "n": len(pick),
            "seed": 0,
            "n_worlds": a.n_worlds,
            "draws_per_world": a.draws,
        },
        "posteriors": {"v1": BASE_V1, "v2": chosen},
        "by_posterior": {k: summ(r) for k, r in results.items()},
        "audit_regression_points": _regression_points(),
        "frozen_at": datetime.now(UTC).isoformat(),
    }
    OUT_ENG.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(
        json.dumps(
            {
                k: {
                    kk: vv
                    for kk, vv in v.items()
                    if "draw_gap" in kk or "eh_ratio" in kk or "ll_1x2" in kk
                }
                for k, v in out["by_posterior"].items()
            },
            indent=1,
        )
    )
    return 0


def _regression_points() -> list[dict[str, Any]]:
    from soccer_edge.model.analytic import outcome_probs, score_matrix, total_over
    from soccer_edge.model.context import MatchContext
    from soccer_edge.model.worlds import WorldConfig, WorldSet
    from soccer_edge.sim.engine import SimConfig, simulate
    from soccer_edge.sim.engine_v2 import SimConfigV2, simulate_v2

    pts = []
    for lam, mu in ((2.30, 0.80), (1.52, 1.13), (1.00, 1.90)):
        W = 1000
        ws = WorldSet(
            W,
            np.full(W, lam),
            np.full(W, mu),
            np.full(W, -0.10),
            np.zeros(W),
            np.zeros(W),
            np.ones(W),
            np.ones(W),
            config=WorldConfig(),
        )
        ctx = MatchContext("f", "c", "H", "A", datetime(2026, 1, 1, tzinfo=UTC))
        m = score_matrix(lam, mu, -0.10)
        an = outcome_probs(m)
        o1 = simulate(ws, ctx, SimConfig(draws_per_world=200, allocate_player_goals=False), seed=5)
        o2 = simulate_v2(
            ws, ctx, SimConfigV2(draws_per_world=200, allocate_player_goals=False), seed=5
        )

        def s(o):
            return {
                "draw": float((o.home_ft == o.away_ft).mean()),
                "home": float((o.home_ft > o.away_ft).mean()),
                "o25": float(((o.home_ft + o.away_ft) > 2.5).mean()),
                "btts": float(((o.home_ft > 0) & (o.away_ft > 0)).mean()),
                "e_home": float(o.home_ft.mean()),
                "e_away": float(o.away_ft.mean()),
            }

        pts.append(
            {
                "lambda": lam,
                "mu": mu,
                "rho": -0.10,
                "analytic": {
                    **an,
                    "o25": total_over(m, 2.5),
                    "btts": float(m[1:, 1:].sum()),
                    "e_home": lam,
                    "e_away": mu,
                },
                "world_sim_v1_production_worlds": s(o1),
                "world_sim_v2": s(o2),
            }
        )
    return pts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["select", "holdout", "engines", "all"])
    ap.add_argument("--n-sample", type=int, default=1500)
    ap.add_argument("--n-worlds", type=int, default=200)
    ap.add_argument("--draws", type=int, default=50)
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd in ("select", "all"):
        cmd_select(a)
    if a.cmd in ("holdout", "all"):
        cmd_holdout(a)
    if a.cmd in ("engines", "all"):
        cmd_engines(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
