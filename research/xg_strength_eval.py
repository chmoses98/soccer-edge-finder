"""xg_strength_v1 walk-forward evaluation (remediation phase 20; audit section J).

Family: `dc_laplace_v2` whose team strengths are fitted on a JOINT likelihood, Poisson goals plus a
quasi-Poisson xG pseudo-likelihood with weight omega:

    ll(match) = [y log lam - lam] + omega * [xg log lam - lam]      (per side, DC low-score term on goals only)

which the v2 fitter sees as two rows per match: the goal row (weight 1, Dixon-Coles correction on) and
the xG row (fractional targets, weight omega, correction off). omega = 0 is the goal-only benchmark.

Pre-registered protocol (written before any number was seen):
  * data: `data/research/xg_history_v1.csv.gz` (FiveThirtyEight SPI, CC-BY 4.0; top-5, 2016-17..2022-23)
  * burn-in 2016-17; SELECTION 2017-18..2020-21; ONE-TIME HOLDOUT 2021-22..2022-23
  * walk-forward per division, refit every 7 days on that division's history, prediction from the
    posterior mean (plug-in Dixon-Coles score matrix; identical treatment for every omega)
  * omega grid {0.25, 0.5, 0.75}; chosen = lowest 1X2 log loss on the selection window
  * holdout decision: PASS if the paired 1X2 log-loss gain of the chosen omega over omega = 0 has a
    95 % bootstrap CI above zero AND a mean gain >= 0.003 (the audit's detectable effect), else FAIL.
    Totals (O/U 2.5) log loss is reported, not decided on.
  * the holdout is used once; a changed family needs new data.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from soccer_edge.evaluation.metrics import bootstrap_mean_ci  # noqa: E402
from soccer_edge.model.analytic import outcome_probs, score_matrix, total_over  # noqa: E402
from soccer_edge.model.strength import MatchRow  # noqa: E402
from soccer_edge.model.strength_v2 import DixonColesFitterV2, StrengthConfigV2  # noqa: E402

DATA = REPO / "data" / "research" / "xg_history_v1.csv.gz"
OUT = REPO / "data" / "research" / "xg_strength_v1.json"
OMEGA_GRID = (0.25, 0.5, 0.75)
BURN_IN = ("2016",)
SELECTION = ("2017", "2018", "2019", "2020")
HOLDOUT = ("2021", "2022")
MIN_GAIN = 0.003
REFIT_DAYS = 7


def load_history(path: Path = DATA) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        out.append(
            {
                "division": r["division"],
                "date": date.fromisoformat(r["date"]),
                "home": r["home"],
                "away": r["away"],
                "hg": int(r["home_goals"]),
                "ag": int(r["away_goals"]),
                "hxg": float(r["home_xg"]),
                "axg": float(r["away_xg"]),
                "season": r["season"],
            }
        )
    out.sort(key=lambda m: (m["division"], m["date"]))
    return out


def fit_rows(matches: list[dict[str, Any]], omega: float) -> list[MatchRow]:
    rows = []
    for m in matches:
        rows.append(MatchRow(m["date"], m["home"], m["away"], m["hg"], m["ag"]))
        if omega > 0:
            rows.append(
                MatchRow(
                    m["date"],
                    m["home"],
                    m["away"],
                    m["hxg"],
                    m["axg"],
                    weight=omega,
                    dc_correction=False,
                )
            )
    return rows


def walk_forward(
    division: str, matches: list[dict[str, Any]], omega: float, seasons: tuple[str, ...]
) -> dict[str, Any]:
    """Score every match of `seasons` in `division` with weekly refits on all earlier matches."""
    ms = [m for m in matches if m["division"] == division]
    cfg = StrengthConfigV2()
    fitter = DixonColesFitterV2(cfg)
    post = None
    last_fit: date | None = None
    recs = []
    for m in ms:
        if m["season"] not in seasons:
            continue
        if last_fit is None or (m["date"] - last_fit).days >= REFIT_DAYS:
            hist = [h for h in ms if h["date"] < m["date"]]
            if len(hist) >= 100:
                post = fitter.fit(fit_rows(hist, omega), as_of=m["date"])
                last_fit = m["date"]
        if post is None or m["home"] not in post.teams or m["away"] not in post.teams:
            continue
        lam, mu = post.expected_goals(m["home"], m["away"])
        rho = float(post.mean[post.idx_rho])
        mat = score_matrix(lam, mu, rho)
        p = outcome_probs(mat)
        y = 0 if m["hg"] > m["ag"] else 1 if m["hg"] == m["ag"] else 2
        p3 = [p["home"], p["draw"], p["away"]]
        over = total_over(mat, 2.5)
        yo = float(m["hg"] + m["ag"] > 2.5)
        recs.append(
            {
                "division": division,
                "season": m["season"],
                "date": m["date"].isoformat(),
                "ll_1x2": float(-np.log(max(p3[y], 1e-9))),
                "ll_ou25": float(
                    -(yo * np.log(max(over, 1e-9)) + (1 - yo) * np.log(max(1 - over, 1e-9)))
                ),
                "p_home": float(p3[0]),
                "y": y,
            }
        )
    return {"division": division, "omega": omega, "seasons": list(seasons), "records": recs}


def _job(args):
    division, matches, omega, seasons = args
    return walk_forward(division, matches, omega, seasons)


def run_grid(
    matches: list[dict[str, Any]], omegas: tuple[float, ...], seasons: tuple[str, ...], workers: int
) -> dict[float, list[dict[str, Any]]]:
    divisions = sorted({m["division"] for m in matches})
    jobs = [(d, matches, o, seasons) for o in omegas for d in divisions]
    out: dict[float, list[dict[str, Any]]] = {o: [] for o in omegas}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(_job, jobs):
            out[res["omega"]].extend(res["records"])
    for o in omegas:
        out[o].sort(key=lambda r: (r["division"], r["date"]))
    return out


def paired(a: list[dict[str, Any]], b: list[dict[str, Any]], key: str) -> dict[str, Any]:
    """Mean of (b - a) log loss per matched record (same division+date+order); negative = b better."""
    ka = {(r["division"], r["date"], i): r for i, r in enumerate(a)}
    kb = {(r["division"], r["date"], i): r for i, r in enumerate(b)}
    common = sorted(set(ka) & set(kb))
    d = np.array([kb[k][key] - ka[k][key] for k in common])
    lo, hi = bootstrap_mean_ci(d, n_boot=2000) if len(d) else (float("nan"), float("nan"))
    return {
        "n": len(d),
        "mean": float(d.mean()) if len(d) else None,
        "ci95": [float(lo), float(hi)],
    }


def summarise(recs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(recs),
        "ll_1x2": float(np.mean([r["ll_1x2"] for r in recs])) if recs else None,
        "ll_ou25": float(np.mean([r["ll_ou25"] for r in recs])) if recs else None,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--divisions", default=None, help="comma-separated subset (smoke tests)")
    a = ap.parse_args(argv)
    matches = load_history(Path(a.data))
    if a.divisions:
        keep = set(a.divisions.split(","))
        matches = [m for m in matches if m["division"] in keep]
    t0 = datetime.now(UTC)
    sel = run_grid(matches, (0.0, *OMEGA_GRID), SELECTION, a.workers)
    sel_summary = {str(o): summarise(r) for o, r in sel.items()}
    ranking = sorted(OMEGA_GRID, key=lambda o: sel_summary[str(o)]["ll_1x2"] or 9)
    chosen = ranking[0]
    sel_paired = {str(o): paired(sel[0.0], sel[o], "ll_1x2") for o in OMEGA_GRID}
    hold = run_grid(matches, (0.0, chosen), HOLDOUT, a.workers)
    gain = paired(hold[0.0], hold[chosen], "ll_1x2")
    gain_ou = paired(hold[0.0], hold[chosen], "ll_ou25")
    passed = bool(
        gain["n"] > 0
        and gain["ci95"][1] < 0
        and gain["mean"] is not None
        and -gain["mean"] >= MIN_GAIN
    )
    by_div = {}
    for d in sorted({r["division"] for r in hold[0.0]}):
        a0 = [r for r in hold[0.0] if r["division"] == d]
        a1 = [r for r in hold[chosen] if r["division"] == d]
        by_div[d] = {"n": len(a0), "paired_1x2": paired(a0, a1, "ll_1x2")}
    res = {
        "schema": "xg_strength_v1_eval_v1",
        "generated_at": t0.isoformat(),
        "protocol": {
            "family": "xg_strength_v1 = dc_laplace_v2 + omega * quasi-Poisson xG pseudo-likelihood",
            "burn_in": list(BURN_IN),
            "selection": list(SELECTION),
            "holdout": list(HOLDOUT),
            "omega_grid": list(OMEGA_GRID),
            "refit_days": REFIT_DAYS,
            "prediction": "posterior-mean plug-in Dixon-Coles score matrix (same for every omega)",
            "decision": f"PASS if holdout paired 1X2 log-loss gain CI95 excludes 0 and mean gain >= {MIN_GAIN}",
        },
        "n_matches": len(matches),
        "selection": {
            "summary": sel_summary,
            "paired_vs_goal_only": sel_paired,
            "ranking": ranking,
        },
        "chosen_omega": chosen,
        "holdout": {
            "goal_only": summarise(hold[0.0]),
            "xg": summarise(hold[chosen]),
            "paired_gain_1x2": {
                **gain,
                "gain_mean": -gain["mean"] if gain["mean"] is not None else None,
            },
            "paired_gain_ou25": gain_ou,
            "by_division": by_div,
        },
        "acceptance": {"pass": passed, "min_gain": MIN_GAIN},
        "xg_strength_v1_status": "PASSED_HOLDOUT" if passed else "FAILED_HOLDOUT",
        "elapsed_s": (datetime.now(UTC) - t0).total_seconds(),
        "note": "ONE-TIME holdout; omega chosen on the selection window only",
    }
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("chosen_omega", "acceptance", "xg_strength_v1_status")}))
    print(json.dumps(res["holdout"]["paired_gain_1x2"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
