"""Lineup upper-bound (oracle) study (remediation phase 19; audit §I2).

Question: with PERFECT knowledge of the starting XI, how much predictive value could lineups add?
Cheap and decisive: if even the oracle gains < 0.002 log loss, prospective lineup modelling cannot pay for
its operational cost and the programme stops (audit stop rule).

Data: post-hoc starting XIs of completed matches archived by `soccer espn-lineup-backfill`
(`lineups/history/<league>.jsonl`, schema `espn_lineup_snapshot_v1` with `lineup_state = post_hoc`),
joined to the ESPN results archive by `espn_event_id`. Nothing post-match beyond the XI itself is used:
the XI is known at kickoff in reality; the study only asks what it would have been worth.

Method (walk-forward within each league, chronological, no leakage):
* Baseline: `dc_laplace_v2` refitted weekly on results strictly before the match.
* Player importance: for every player, a ridge-shrunk estimate of the team's log goal-rate residual
  (attack) and conceded-rate residual (defence) when that player started, computed ONLY from matches
  strictly before the fit date (`player_ridge_lambda` grid; chosen on the first half of the window).
* Oracle adjustment: `log lam' = log lam + c * sum_{starters} imp_att - c * sum_{regulars absent} imp_att`
  (mirror for mu), with `c` fitted walk-forward on earlier matches; the XI used is the actual XI.
* Endpoints: paired 1X2 and O/U 2.5 log loss, oracle vs baseline, with a 95% bootstrap CI; by league; and
  the subset where at least one "regular" starter (started >= 60% of the team's prior matches) is absent.

Stop rule: oracle gain < 0.002 on 1X2 AND on totals => do not invest in lineup modelling yet.
This module also carries a synthetic self-test (`--synthetic`) so the estimator is validated without data.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from soccer_edge.evaluation.metrics import bootstrap_mean_ci  # noqa: E402
from soccer_edge.model.analytic import outcome_probs, score_matrix, total_over  # noqa: E402
from soccer_edge.model.strength import MatchRow  # noqa: E402
from soccer_edge.model.strength_v2 import DixonColesFitterV2  # noqa: E402

OUT = REPO / "data" / "research" / "lineup_oracle_v1.json"
STOP_THRESHOLD = 0.002


def player_importance(
    history: list[dict[str, Any]], as_of: date, *, ridge: float = 10.0, min_each: int = 3
) -> dict[str, tuple[float, float]]:
    """(attack, defence) importance per player from matches strictly before `as_of`: the WITH-minus-
    WITHOUT contrast of the team's log residuals (goals vs the goal model's expectation) when the player
    starts versus when the same team plays without them, shrunk towards 0 by an effective-sample ridge.
    A player never seen absent (or never seen starting) carries 0: their absence is unobserved, so the
    oracle cannot price it. Averaging the shared team residual over every starter (the naive estimator)
    cannot separate players and fails to recover even a large synthetic effect; the contrast does.
    history rows: {date, team, starters: list[str], goals_for, goals_against, exp_for, exp_against}."""
    by_team: dict[str, list[tuple[set[str], float, float]]] = defaultdict(list)
    for h in history:
        if h["date"] >= as_of:
            continue
        ra = float(np.log((h["goals_for"] + 0.5) / (h["exp_for"] + 0.5)))
        rd = float(-np.log((h["goals_against"] + 0.5) / (h["exp_against"] + 0.5)))
        by_team[h["team"]].append((set(h["starters"]), ra, rd))
    out: dict[str, tuple[float, float]] = {}
    for rows in by_team.values():
        players = set().union(*(r[0] for r in rows))
        ra_all = np.array([r[1] for r in rows])
        rd_all = np.array([r[2] for r in rows])
        for p in players:
            mask = np.array([p in r[0] for r in rows])
            n_with, n_without = int(mask.sum()), int((~mask).sum())
            if n_with < min_each or n_without < min_each:
                out[p] = (0.0, 0.0)
                continue
            n_eff = 1.0 / (1.0 / n_with + 1.0 / n_without)
            shrink = n_eff / (n_eff + ridge)
            out[p] = (
                float((ra_all[mask].mean() - ra_all[~mask].mean()) * shrink),
                float((rd_all[mask].mean() - rd_all[~mask].mean()) * shrink),
            )
    return out


def regulars(
    history: list[dict[str, Any]],
    team: str,
    as_of: date,
    *,
    share: float = 0.6,
    min_matches: int = 5,
) -> set[str]:
    rows = [h for h in history if h["team"] == team and h["date"] < as_of]
    if len(rows) < min_matches:
        return set()
    cnt: dict[str, int] = defaultdict(int)
    for h in rows:
        for p in h["starters"]:
            cnt[p] += 1
    return {p for p, n in cnt.items() if n / len(rows) >= share}


def oracle_adjustment(
    imp: dict[str, tuple[float, float]], starters: list[str], regs: set[str]
) -> tuple[float, float]:
    """Attack / defence log-rate shifts of this XI RELATIVE to the team's regular XI (the composition
    the fitted team strengths already average over): stand-ins who start count positively, regulars
    who are missing count negatively; regulars who start cancel out, so shared team-level residual
    components in the per-player estimates do not accumulate over the eleven starters."""
    xi = set(starters)
    ins = xi - regs
    outs = regs - xi
    att = sum(imp.get(p, (0.0, 0.0))[0] for p in ins) - sum(imp.get(p, (0.0, 0.0))[0] for p in outs)
    dfc = sum(imp.get(p, (0.0, 0.0))[1] for p in ins) - sum(imp.get(p, (0.0, 0.0))[1] for p in outs)
    return att, dfc


def ll3(p: dict[str, float], y: int) -> float:
    return -np.log(max([p["home"], p["draw"], p["away"]][y], 1e-9))


def run_study(
    matches: list[dict[str, Any]], *, refit_days: int = 7, c_grid=(0.0, 0.25, 0.5, 0.75, 1.0)
) -> dict[str, Any]:
    """matches: chronological rows {date, league, home, away, hg, ag, home_xi: list[str], away_xi: list[str]}."""
    by_lg: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in matches:
        by_lg[m["league"]].append(m)
    diffs_1x2: list[float] = []
    diffs_ou: list[float] = []
    diffs_absent: list[float] = []
    per_lg: dict[str, Any] = {}
    chosen_c: dict[str, float] = {}
    for lg, ms in by_lg.items():
        ms.sort(key=lambda m: m["date"])
        rows = [MatchRow(m["date"], m["home"], m["away"], m["hg"], m["ag"]) for m in ms]
        history: list[dict[str, Any]] = []
        post = None
        last_fit = None
        recs = []
        for i, m in enumerate(ms):
            if last_fit is None or (m["date"] - last_fit).days >= refit_days:
                fit_rows = [r for r in rows if r.date < m["date"]]
                if len(fit_rows) >= 100:
                    post = DixonColesFitterV2().fit(fit_rows, as_of=m["date"])
                    last_fit = m["date"]
                    imp = player_importance(history, m["date"])
            if post is None or m["home"] not in post.teams or m["away"] not in post.teams:
                lam = mu = None
            else:
                lam, mu = post.expected_goals(m["home"], m["away"])
            if lam is not None:
                regs_h = regulars(history, m["home"], m["date"])
                regs_a = regulars(history, m["away"], m["date"])
                ah, dh = oracle_adjustment(imp, m["home_xi"], regs_h)
                aa, da = oracle_adjustment(imp, m["away_xi"], regs_a)
                absent = bool((regs_h - set(m["home_xi"])) or (regs_a - set(m["away_xi"])))
                recs.append(
                    {
                        "i": i,
                        "lam": lam,
                        "mu": mu,
                        "shift_lam": ah - da,
                        "shift_mu": aa - dh,
                        "y": 0 if m["hg"] > m["ag"] else 1 if m["hg"] == m["ag"] else 2,
                        "over": float(m["hg"] + m["ag"] > 2.5),
                        "absent": absent,
                        "rho": float(post.mean[post.idx_rho]),
                        "date": m["date"],
                    }
                )
            # history for importance (uses this match's own outcome only for FUTURE fits)
            if lam is not None:
                history.append(
                    {
                        "date": m["date"],
                        "team": m["home"],
                        "starters": m["home_xi"],
                        "goals_for": m["hg"],
                        "goals_against": m["ag"],
                        "exp_for": lam,
                        "exp_against": mu,
                    }
                )
                history.append(
                    {
                        "date": m["date"],
                        "team": m["away"],
                        "starters": m["away_xi"],
                        "goals_for": m["ag"],
                        "goals_against": m["hg"],
                        "exp_for": mu,
                        "exp_against": lam,
                    }
                )
        if len(recs) < 200:
            per_lg[lg] = {"n": len(recs), "note": "too few scored matches"}
            continue
        # choose c on the first half chronologically, evaluate on the second half
        half = len(recs) // 2
        first, second = recs[:half], recs[half:]

        def score(rs, c):
            d1, d2 = [], []
            for r in rs:
                base = score_matrix(r["lam"], r["mu"], r["rho"])
                adj = score_matrix(
                    r["lam"] * np.exp(c * r["shift_lam"]),
                    r["mu"] * np.exp(c * r["shift_mu"]),
                    r["rho"],
                )
                pb, pa = outcome_probs(base), outcome_probs(adj)
                d1.append(ll3(pa, r["y"]) - ll3(pb, r["y"]))
                ob, oa = total_over(base, 2.5), total_over(adj, 2.5)
                d2.append(
                    -(
                        r["over"] * np.log(max(oa, 1e-9))
                        + (1 - r["over"]) * np.log(max(1 - oa, 1e-9))
                    )
                    + (
                        r["over"] * np.log(max(ob, 1e-9))
                        + (1 - r["over"]) * np.log(max(1 - ob, 1e-9))
                    )
                )
            return np.array(d1), np.array(d2)

        best_c, best = 0.0, 0.0
        for c in c_grid:
            d1, _ = score(first, c)
            if d1.mean() < best:
                best, best_c = d1.mean(), c
        chosen_c[lg] = best_c
        d1, d2 = score(second, best_c)
        absent_mask = np.array([r["absent"] for r in second])
        diffs_1x2.extend(d1.tolist())
        diffs_ou.extend(d2.tolist())
        diffs_absent.extend(d1[absent_mask].tolist())
        per_lg[lg] = {
            "n_eval": len(second),
            "c": best_c,
            "gain_1x2": float(-d1.mean()),
            "gain_ou25": float(-d2.mean()),
            "share_with_regular_absent": float(absent_mask.mean()),
        }
    out: dict[str, Any] = {
        "schema": "lineup_oracle_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "by_league": per_lg,
        "chosen_c": chosen_c,
        "stop_threshold": STOP_THRESHOLD,
    }
    if diffs_1x2:
        a = np.array(diffs_1x2)
        b = np.array(diffs_ou)
        lo, hi = bootstrap_mean_ci(-a, n_boot=1000)
        lo2, hi2 = bootstrap_mean_ci(-b, n_boot=1000)
        out["oracle_gain_1x2"] = {
            "mean": float(-a.mean()),
            "ci95": [float(lo), float(hi)],
            "n": len(a),
        }
        out["oracle_gain_ou25"] = {
            "mean": float(-b.mean()),
            "ci95": [float(lo2), float(hi2)],
            "n": len(b),
        }
        if diffs_absent:
            c_ = np.array(diffs_absent)
            lo3, hi3 = bootstrap_mean_ci(-c_, n_boot=1000)
            out["oracle_gain_1x2_regular_absent"] = {
                "mean": float(-c_.mean()),
                "ci95": [float(lo3), float(hi3)],
                "n": len(c_),
            }
        out["clears_threshold"] = bool(
            out["oracle_gain_1x2"]["mean"] >= STOP_THRESHOLD
            or out["oracle_gain_ou25"]["mean"] >= STOP_THRESHOLD
        )
        out["decision"] = (
            "design the prospective lineup model"
            if out["clears_threshold"]
            else "STOP: even perfect XI knowledge gains < 0.002 log loss; do not invest in lineup modelling yet"
        )
    else:
        out["decision"] = (
            "NOT_EVALUATED: no historical XI data (run espn-lineup-backfill + lineup-backfill.yml first)"
        )
    return out


def synthetic(
    seed: int = 0, n_teams: int = 18, seasons: int = 3, effect: float = 0.25
) -> list[dict[str, Any]]:
    """A league where one star per team lifts attack by `effect` when starting (absent 20% of the time)."""
    rng = np.random.default_rng(seed)
    teams = [f"t{i}" for i in range(n_teams)]
    att = rng.normal(0, 0.2, n_teams)
    dfc = rng.normal(0, 0.2, n_teams)
    squads = {t: [f"{t}_p{k}" for k in range(14)] for t in teams}
    out = []
    d0 = date(2022, 8, 1)
    for s in range(seasons):
        for r in range(34):
            perm = rng.permutation(n_teams)
            for i in range(0, n_teams, 2):
                h, a = perm[i], perm[i + 1]
                xi_h = list(rng.choice(squads[teams[h]][1:], 10, replace=False))
                xi_a = list(rng.choice(squads[teams[a]][1:], 10, replace=False))
                star_h = rng.random() > 0.2
                star_a = rng.random() > 0.2
                if star_h:
                    xi_h.append(squads[teams[h]][0])
                if star_a:
                    xi_a.append(squads[teams[a]][0])
                lam = 1.45 * np.exp(att[h] - dfc[a] + (effect if star_h else 0))
                mu = 1.15 * np.exp(att[a] - dfc[h] + (effect if star_a else 0))
                out.append(
                    {
                        "date": d0 + timedelta(days=365 * s + 7 * r),
                        "league": "syn",
                        "home": teams[h],
                        "away": teams[a],
                        "hg": int(rng.poisson(lam)),
                        "ag": int(rng.poisson(mu)),
                        "home_xi": xi_h,
                        "away_xi": xi_a,
                    }
                )
    return out


ESPN_LEAGUE_TO_DIVISION = {
    "eng.1": "E0",
    "esp.1": "SP1",
    "ger.1": "D1",
    "ita.1": "I1",
    "fra.1": "F1",
}


def load_archive_matches(
    archive_root: Path, matches_csv: Path | None = None, *, verbose: bool = True
) -> list[dict[str, Any]]:
    """Join `lineups/history/<league>.jsonl` post-hoc XIs with match results.

    Top-5 leagues: ESPN team ids -> canonical ids through the explicit ESPN identity map, results from
    the football-data redistribution (`data/cache/Matches.csv`, the walk-forward benchmark's source),
    matched on (home, away) and the kickoff date +-1 day. Other leagues: `results/espn/<league>.jsonl`
    by ESPN event id. Unjoined rows are counted, never guessed."""
    import json as _json

    from soccer_edge.providers.espn import EspnMap

    emap = EspnMap.load()
    out = []
    stats: dict[str, dict[str, int]] = {}
    fd_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    csv_path = matches_csv or (REPO / "data" / "cache" / "Matches.csv")
    if csv_path.exists():
        from research.wf_common import seed_registry
        from soccer_edge.providers.club_football_data import ClubFootballDataProvider

        obs = ClubFootballDataProvider(seed_registry()).load(
            divisions=tuple(ESPN_LEAGUE_TO_DIVISION.values()),
            start_date="2023-07-01",
            content=csv_path.read_bytes(),
        )
        for hm in obs.payload:
            r = hm.result
            fd_index[(hm.division, r.home_team_id, r.away_team_id, r.match_date)] = {
                "date": date.fromisoformat(r.match_date),
                "home": r.home_team_id,
                "away": r.away_team_id,
                "hg": r.home_goals,
                "ag": r.away_goals,
            }
    hist_dir = archive_root / "lineups" / "history"
    for p in sorted(hist_dir.glob("*.jsonl")) if hist_dir.exists() else []:
        league = p.stem
        st = stats.setdefault(
            league, {"rows": 0, "joined": 0, "no_result": 0, "unmapped": 0, "short_xi": 0}
        )
        results = {}
        res_path = archive_root / "results" / "espn" / f"{league}.jsonl"
        if res_path.exists():
            for ln in res_path.read_text().splitlines():
                if ln.strip():
                    r = _json.loads(ln)
                    results[r["espn_event_id"]] = r
        division = ESPN_LEAGUE_TO_DIVISION.get(league)
        for ln in p.read_text().splitlines():
            if not ln.strip():
                continue
            row = _json.loads(ln)
            st["rows"] += 1
            xi_h = [str(pl["athlete_id"]) for pl in row.get("home", []) if pl.get("starter")]
            xi_a = [str(pl["athlete_id"]) for pl in row.get("away", []) if pl.get("starter")]
            if len(xi_h) < 11 or len(xi_a) < 11:
                st["short_xi"] += 1
                continue
            rec = None
            r = results.get(str(row.get("espn_event_id")))
            if r is not None:
                rec = {
                    "date": date.fromisoformat(r["match_date"]),
                    "home": r["home_team_id"],
                    "away": r["away_team_id"],
                    "hg": r["home_goals"],
                    "ag": r["away_goals"],
                }
            elif division and fd_index:
                h = emap.teams.get(str(row.get("home_espn_id")))
                a = emap.teams.get(str(row.get("away_espn_id")))
                if h is None or a is None:
                    st["unmapped"] += 1
                    continue
                ko = row.get("kickoff_utc")
                d0 = date.fromisoformat(ko[:10]) if ko else None
                if d0 is not None:
                    for dd in (0, 1, -1):
                        cand = fd_index.get((division, h, a, (d0 + timedelta(days=dd)).isoformat()))
                        if cand is not None:
                            rec = cand
                            break
            if rec is None:
                st["no_result"] += 1
                continue
            st["joined"] += 1
            out.append({**rec, "league": league, "home_xi": xi_h, "away_xi": xi_a})
    if verbose:
        print("[oracle] join:", json.dumps(stats))
    out.sort(key=lambda m: (m["league"], m["date"]))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-dir", default=None)
    ap.add_argument(
        "--matches-csv", default=None, help="football-data redistribution CSV (top-5 results)"
    )
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument(
        "--calibrate",
        action="store_true",
        help="also record what the method recovers on synthetic leagues with a known star effect",
    )
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    matches = (
        synthetic()
        if a.synthetic
        else load_archive_matches(
            Path(a.archive_dir), Path(a.matches_csv) if a.matches_csv else None
        )
        if a.archive_dir
        else []
    )
    res = run_study(matches)
    res["input"] = "synthetic" if a.synthetic else (a.archive_dir or "none")
    res["n_matches"] = len(matches)
    if a.calibrate:
        # method calibration: the estimator's read on leagues where the truth is known (one star per
        # team worth `effect` log-attack, absent 20% of the time, heavy random rotation otherwise).
        # The study's gain on real data must be read against this: a null league costs about the
        # noise figure, a large effect recovers only part of its true value.
        res["method_calibration"] = {}
        for eff in (0.0, 0.35):
            cal = run_study(synthetic(effect=eff, seasons=4))
            res["method_calibration"][f"effect_{eff}"] = {
                "oracle_gain_1x2": cal.get("oracle_gain_1x2"),
                "chosen_c": cal.get("chosen_c"),
            }
    Path(a.out).write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(
        json.dumps(
            {
                k: res.get(k)
                for k in (
                    "n_matches",
                    "oracle_gain_1x2",
                    "oracle_gain_ou25",
                    "clears_threshold",
                    "decision",
                )
            },
            indent=1,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
