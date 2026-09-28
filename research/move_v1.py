"""move_v1: does DATA_ONLY predict the direction of SHARP market movement from open to close?
(remediation phase 11; audit §H1 — the only mechanism by which a model that loses to the close on final
prediction quality could still earn closing-line value.)

Pre-registered protocol
-----------------------
Data: football-data.co.uk direct season CSVs (opening Pinnacle `PSH/PSD/PSA`, closing `PSCH/PSCD/PSCA`;
Bet365 `B365*`/`B365C*` as the secondary book; O/U 2.5 `P>2.5`/`PC>2.5`), seasons 2019-20 onward for
E0/SP1/D1/I1/F1, joined by (division, date, home, away) to the frozen walk-forward v1 table
(`research/wf_common`, variant `dc_laplace_v1`), whose `p_data` is the model's 1X2 probability from a
posterior refitted weekly on results strictly before the match date — the "hypothetical valid early
horizon". The opening quote is posted days earlier, so the model can hold up to `days_since_refit` more
result days than the open; the study also reports the subset with `days_since_refit >= 3`.

Per family f (1X2 selections home/draw/away; O/U 2.5 over), chronological, all seasons pooled and per
season, with matches as the unit and match-date cluster bootstrap for intervals:

    y = logit(p_close) - logit(p_open)
    x = logit(p_model) - logit(p_open)
    y = alpha + beta * x + eps                      OLS; beta 95% CI by cluster bootstrap (by date)
    directional accuracy = P( sign(p_model - p_open) == sign(p_close - p_open) | close moved )
    rank correlation     = Spearman(x, y)
    magnitude buckets    = mean close move in the model's direction by |p_model - p_open| bucket
    calibration          = log loss of p_open, p_close, p_model against outcomes (paired, CI)

Decision rule (pre-registered): DATA_ONLY "predicts movement" for a family only if beta's 95% lower
bound > 0 pooled AND beta > 0 in at least 5 of the 7 seasons AND directional accuracy's lower bound
> 0.5. Anything else is a preserved negative result. No subgroup mining beyond league x family.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

PROTOCOL_VERSION = "move_v1"
DIVISIONS = ("E0", "SP1", "D1", "I1", "F1")
SEASONS = ("1920", "2021", "2122", "2223", "2324", "2425", "2526")
FD_BASE = "https://www.football-data.co.uk/mmz4281"
OUT_JSON = REPO / "data" / "research" / "move_v1.json"
ODDS_DIR = REPO / "data" / "cache" / "football_data"
BUCKETS = ((0.0, 0.02), (0.02, 0.05), (0.05, 0.10), (0.10, 1.0))


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def devig_power(odds: np.ndarray) -> np.ndarray:
    """Power de-vig for one market: find k with sum (1/o)^k = 1 (rows independently)."""
    inv = 1.0 / odds
    out = np.empty_like(inv)
    for i, row in enumerate(inv):
        lo, hi = 0.5, 3.0
        for _ in range(60):
            k = 0.5 * (lo + hi)
            s = np.sum(row**k)
            if s > 1:
                lo = k
            else:
                hi = k
        k = 0.5 * (lo + hi)
        out[i] = row**k / np.sum(row**k)
    return out


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _fd_date(s: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            from datetime import datetime

            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


@dataclass
class OddsRow:
    division: str
    date: date
    home: str
    away: str
    open_1x2: tuple[float, float, float] | None
    close_1x2: tuple[float, float, float] | None
    open_b365: tuple[float, float, float] | None
    close_b365: tuple[float, float, float] | None
    open_ou: tuple[float, float] | None
    close_ou: tuple[float, float] | None


def _trip(r: dict[str, str], cols: tuple[str, str, str]) -> tuple[float, float, float] | None:
    try:
        v = tuple(float(r[c]) for c in cols)
    except (KeyError, ValueError, TypeError):
        return None
    return v if all(x > 1.0 for x in v) else None


def _pair(r: dict[str, str], cols: tuple[str, str]) -> tuple[float, float] | None:
    try:
        v = tuple(float(r[c]) for c in cols)
    except (KeyError, ValueError, TypeError):
        return None
    return v if all(x > 1.0 for x in v) else None


def load_odds(odds_dir: Path = ODDS_DIR) -> list[OddsRow]:
    rows: list[OddsRow] = []
    for season in SEASONS:
        for div in DIVISIONS:
            p = odds_dir / season / f"{div}.csv"
            if not p.exists():
                continue
            with p.open(encoding="utf-8-sig", errors="replace") as fh:
                for r in csv.DictReader(fh):
                    d = _fd_date(r.get("Date", ""))
                    if d is None or not r.get("HomeTeam"):
                        continue
                    rows.append(
                        OddsRow(
                            div,
                            d,
                            r["HomeTeam"],
                            r["AwayTeam"],
                            _trip(r, ("PSH", "PSD", "PSA")),
                            _trip(r, ("PSCH", "PSCD", "PSCA")),
                            _trip(r, ("B365H", "B365D", "B365A")),
                            _trip(r, ("B365CH", "B365CD", "B365CA")),
                            _pair(r, ("P>2.5", "P<2.5")),
                            _pair(r, ("PC>2.5", "PC<2.5")),
                        )
                    )
    return rows


def join(table: dict[str, np.ndarray], odds: list[OddsRow]) -> dict[str, Any]:
    """Align the walk-forward table rows with odds rows by (division, date, normalised team names)."""
    idx: dict[tuple[str, date, str, str], OddsRow] = {}
    for o in odds:
        idx[(o.division, o.date, _norm(o.home), _norm(o.away))] = o
    keep = []
    matched: list[OddsRow] = []
    for i in range(len(table["date"])):
        d = table["date"][i]
        d = d if isinstance(d, date) else date.fromisoformat(str(d)[:10])
        key = (
            str(table["division"][i]),
            d,
            _norm(str(table["home_name"][i])),
            _norm(str(table["away_name"][i])),
        )
        o = idx.get(key)
        if o is None or o.open_1x2 is None or o.close_1x2 is None:
            continue
        keep.append(i)
        matched.append(o)
    return {"rows": np.array(keep, dtype=int), "odds": matched}


def ols_beta(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    x1 = np.column_stack([np.ones_like(x), x])
    coef, *_ = np.linalg.lstsq(x1, y, rcond=None)
    return float(coef[0]), float(coef[1])


def cluster_bootstrap(  # noqa: PLR0917
    stat, x: np.ndarray, y: np.ndarray, clusters: np.ndarray, n_boot: int = 500, seed: int = 0
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    uniq = np.unique(clusters)
    by = {c: np.where(clusters == c)[0] for c in uniq}
    vals = []
    for _ in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        ix = np.concatenate([by[c] for c in pick])
        vals.append(stat(x[ix], y[ix]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    if rx.std() == 0 or ry.std() == 0:
        return 0.0
    return float(np.corrcoef(rx, ry)[0, 1])


def binary_ll(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def analyse_family(  # noqa: PLR0917
    p_open: np.ndarray,
    p_close: np.ndarray,
    p_model: np.ndarray,
    y: np.ndarray,
    clusters: np.ndarray,
    seasons: np.ndarray,
    leagues: np.ndarray,
    *,
    n_boot: int = 500,
) -> dict[str, Any]:
    """All arrays are per selection (binary outcome y for that selection)."""
    xs = logit(p_model) - logit(p_open)
    ys = logit(p_close) - logit(p_open)
    alpha, beta = ols_beta(xs, ys)
    b_lo, b_hi = cluster_bootstrap(lambda a, b: ols_beta(a, b)[1], xs, ys, clusters, n_boot=n_boot)
    moved = p_close != p_open
    agree = np.sign(p_model - p_open) == np.sign(p_close - p_open)
    dir_acc = float(agree[moved].mean()) if moved.any() else float("nan")
    da_lo, da_hi = cluster_bootstrap(
        lambda a, b: (
            float((np.sign(a) == np.sign(b))[b != 0].mean()) if (b != 0).any() else float("nan")
        ),
        p_model - p_open,
        p_close - p_open,
        clusters,
        n_boot=n_boot,
    )
    rho = spearman(xs, ys)
    by_season = {}
    for s in sorted(set(seasons.tolist())):
        m = seasons == s
        if m.sum() < 50:
            continue
        a, b = ols_beta(xs[m], ys[m])
        mv = moved & m
        by_season[str(s)] = {
            "n": int(m.sum()),
            "beta": b,
            "directional_accuracy": float(agree[mv].mean()) if mv.any() else None,
            "ll_open": binary_ll(p_open[m], y[m]),
            "ll_close": binary_ll(p_close[m], y[m]),
            "ll_model": binary_ll(p_model[m], y[m]),
        }
    by_league = {}
    for lg in sorted(set(leagues.tolist())):
        m = leagues == lg
        if m.sum() < 50:
            continue
        a, b = ols_beta(xs[m], ys[m])
        mv = moved & m
        by_league[str(lg)] = {
            "n": int(m.sum()),
            "beta": b,
            "directional_accuracy": float(agree[mv].mean()) if mv.any() else None,
        }
    buckets = []
    gap = np.abs(p_model - p_open)
    sign_model = np.sign(p_model - p_open)
    for lo, hi in BUCKETS:
        m = (gap >= lo) & (gap < hi) & (sign_model != 0)
        if m.sum() < 30:
            buckets.append(
                {"bucket": [lo, hi], "n": int(m.sum()), "mean_close_move_in_model_direction": None}
            )
            continue
        mv_dir = (p_close[m] - p_open[m]) * sign_model[m]
        buckets.append(
            {
                "bucket": [lo, hi],
                "n": int(m.sum()),
                "mean_close_move_in_model_direction": float(mv_dir.mean()),
                "share_close_moved_with_model": float((mv_dir > 0).mean()),
                "share_close_moved_against_model": float((mv_dir < 0).mean()),
                "ll_open": binary_ll(p_open[m], y[m]),
                "ll_close": binary_ll(p_close[m], y[m]),
                "ll_model": binary_ll(p_model[m], y[m]),
            }
        )
    seasons_pos = sum(1 for v in by_season.values() if v["beta"] > 0)
    verdict = bool(b_lo > 0 and seasons_pos >= min(5, max(1, len(by_season))) and da_lo > 0.5)
    return {
        "n_selections": len(xs),
        "n_matches": len(np.unique(clusters)),
        "alpha": alpha,
        "beta": beta,
        "beta_ci95": [b_lo, b_hi],
        "directional_accuracy": dir_acc,
        "directional_accuracy_ci95": [da_lo, da_hi],
        "share_close_moved": float(moved.mean()),
        "spearman": rho,
        "ll_open": binary_ll(p_open, y),
        "ll_close": binary_ll(p_close, y),
        "ll_model": binary_ll(p_model, y),
        "by_season": by_season,
        "seasons_with_positive_beta": seasons_pos,
        "by_league": by_league,
        "magnitude_buckets": buckets,
        "predicts_movement": verdict,
    }


def run_study(
    table: dict[str, np.ndarray],
    odds: list[OddsRow],
    *,
    n_boot: int = 500,
    min_days_since_refit: int = 0,
) -> dict[str, Any]:
    j = join(table, odds)
    rows, od = j["rows"], j["odds"]
    if len(rows) == 0:
        return {"error": "no aligned rows", "n_table": len(table["date"])}
    dsr = (
        np.asarray(table["days_since_refit"])[rows]
        if "days_since_refit" in table
        else np.zeros(len(rows))
    )
    keep = dsr >= min_days_since_refit
    rows, od = rows[keep], [o for o, k in zip(od, keep) if k]
    p_model = np.asarray(table["p_data"])[rows]  # (n,3) home/draw/away
    y3 = np.asarray(table["y"])[rows]
    seasons = np.asarray(table["season"])[rows]
    leagues = np.asarray(table["division"])[rows]
    dates = np.array([o.date.toordinal() for o in od])
    match_id = np.arange(len(rows))
    p_open = devig_power(np.array([o.open_1x2 for o in od]))
    p_close = devig_power(np.array([o.close_1x2 for o in od]))
    out: dict[str, Any] = {
        "schema": "move_v1_result",
        "protocol": PROTOCOL_VERSION,
        "min_days_since_refit": min_days_since_refit,
        "n_matches_aligned": len(rows),
        "families": {},
    }
    # 1X2 pooled over the three selections (one row per selection; clusters = match date)
    sel_y = np.concatenate([(y3 == k).astype(float) for k in range(3)])
    out["families"]["match_result_3way"] = analyse_family(
        np.concatenate([p_open[:, k] for k in range(3)]),
        np.concatenate([p_close[:, k] for k in range(3)]),
        np.concatenate([p_model[:, k] for k in range(3)]),
        sel_y,
        np.concatenate([dates] * 3),
        np.concatenate([seasons] * 3),
        np.concatenate([leagues] * 3),
        n_boot=n_boot,
    )
    for k, name in enumerate(("home", "draw", "away")):
        out["families"][f"match_result_3way.{name}"] = analyse_family(
            p_open[:, k],
            p_close[:, k],
            p_model[:, k],
            (y3 == k).astype(float),
            dates,
            seasons,
            leagues,
            n_boot=n_boot,
        )
    # O/U 2.5 where both open and close exist
    if "p_data_o25" in table:
        has = np.array([o.open_ou is not None and o.close_ou is not None for o in od])
        if has.sum() >= 100:
            po = devig_power(np.array([o.open_ou for o, h in zip(od, has) if h]))[:, 0]
            pc = devig_power(np.array([o.close_ou for o, h in zip(od, has) if h]))[:, 0]
            pm = np.asarray(table["p_data_o25"])[rows][has]
            hg, ag = np.asarray(table["hg"])[rows][has], np.asarray(table["ag"])[rows][has]
            out["families"]["total_goals_2.5"] = analyse_family(
                po,
                pc,
                pm,
                ((hg + ag) > 2.5).astype(float),
                dates[has],
                seasons[has],
                leagues[has],
                n_boot=n_boot,
            )
    out["verdict"] = {
        f: v["predicts_movement"] for f, v in out["families"].items() if isinstance(v, dict)
    }
    out["any_family_predicts_movement"] = any(out["verdict"].values())
    _ = match_id
    return out


def fetch_odds(odds_dir: Path = ODDS_DIR) -> dict[str, Any]:
    """Download the direct season CSVs (runner-side; blocked from some egress)."""
    import urllib.request

    got, failed = [], []
    for season in SEASONS:
        for div in DIVISIONS:
            url = f"{FD_BASE}/{season}/{div}.csv"
            dst = odds_dir / season / f"{div}.csv"
            if dst.exists():
                got.append(str(dst))
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    dst.write_bytes(r.read())
                got.append(str(dst))
            except Exception as exc:
                failed.append(f"{url}: {str(exc)[:80]}")
    return {"downloaded": len(got), "failed": failed}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--fetch", action="store_true", help="download the football-data.co.uk CSVs first"
    )
    ap.add_argument("--odds-dir", default=str(ODDS_DIR))
    ap.add_argument("--variant", default="dc_laplace_v1")
    ap.add_argument("--out", default=str(OUT_JSON))
    ap.add_argument("--n-boot", type=int, default=500)
    a = ap.parse_args(argv)
    if a.fetch:
        print(json.dumps(fetch_odds(Path(a.odds_dir))))
    from research.wf_common import load_data, load_or_run

    matches, extras, data_hash = load_data()
    table = load_or_run(a.variant, matches, extras, data_hash, keep_matrix=False)
    odds = load_odds(Path(a.odds_dir))
    print(f"odds rows: {len(odds)}; table rows: {len(table['date'])}")
    result = run_study(table, odds, n_boot=a.n_boot)
    result["robustness_days_since_refit_ge_3"] = run_study(
        table, odds, n_boot=max(100, a.n_boot // 5), min_days_since_refit=3
    )
    result["variant"] = a.variant
    result["data_hash"] = data_hash
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(result, indent=1, default=str) + "\n")
    fam = result.get("families", {})
    for f, v in fam.items():
        if isinstance(v, dict) and "beta" in v:
            print(
                f"{f}: n={v['n_selections']} beta={v['beta']:+.3f} CI={v['beta_ci95']} dir_acc={v['directional_accuracy']:.3f} predicts={v['predicts_movement']}"
            )
    print("any_family_predicts_movement:", result.get("any_family_predicts_movement"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
