"""Point-in-time rest / congestion / calendar features and a residual-information test.

Question: do schedule-context features carry information that the de-vigged Bet365 pre-match
1X2 (MARKET_ONLY) or the Dixon-Coles posterior (DATA_ONLY) do not already price?

Features (all computed from matches strictly before the match date, domestic league matches of
the same division only - cups and UEFA fixtures are NOT in the CSV, so "days since last match"
is an UPPER bound on rest and the congestion counts are LOWER bounds):
* rest_home, rest_away  : days since the team's previous league match (capped at 30; a team's
                          first match of a season carries the cap and the early-season flag)
* rest_diff             : rest_home - rest_away
* n7/n14/n28 (each side): league matches in the prior 7 / 14 / 28 days, and home - away diffs
* early_season          : the match is within the team's first 5 league matches of the season
* post_break            : the division had no match in the previous > 10 days and this is not the
                          season's first round (approximates international breaks; winter breaks
                          are flagged too, which is documented rather than filtered)

Test: walk-forward multinomial logistic regression, fitted on scored seasons < S and evaluated
on S (S = 2020-21 .. 2025-26; 2019-20 is training-only). Baseline = the reference forecast's own
logits (market or DATA_ONLY), which recalibrates it; each feature block is added on top. Log-loss
improvement is reported with a paired bootstrap CI over matches. Inputs are the aligned
per-match predictions written by research/multi_league.py (data/research/multi_league_v1_predictions.csv).
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

import numpy as np

from research.multi_league import (
    CSV_PATH,
    LEAGUE_COUNTRY,
    PRED_CSV,
    TOP5,
    TeamIds,
    fit_multinomial,
    load_registry,
    predict_multinomial,
)
from soccer_edge.core.serialization import content_hash, write_json
from soccer_edge.evaluation.metrics import bootstrap_mean_ci
from soccer_edge.providers.club_football_data import season_id_for

REPO = Path(__file__).resolve().parents[1]
OUT_JSON = REPO / "data" / "research" / "context_features_v1.json"
PROTOCOL_VERSION = "context_features_v1"
REST_CAP = 30
FEATURE_START = date(2015, 7, 1)
BLOCKS = {
    "rest": ["rest_home", "rest_away", "rest_diff"],
    "congestion": ["n7_home", "n7_away", "n14_home", "n14_away", "n28_home", "n28_away", "n7_diff", "n28_diff"],
    "calendar": ["early_home", "early_away", "post_break"],
}  # fmt: skip
BLOCKS["all"] = BLOCKS["rest"] + BLOCKS["congestion"] + BLOCKS["calendar"]


def build_features() -> dict[str, dict[str, float]]:
    reg = load_registry()
    ids = TeamIds(reg)
    rows = []
    with CSV_PATH.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            div = r["Division"]
            if div not in TOP5 or r["FTHome"] == "" or r["MatchDate"] < FEATURE_START.isoformat():
                continue
            cc = LEAGUE_COUNTRY[div]
            rows.append(
                (
                    date.fromisoformat(r["MatchDate"]),
                    div,
                    ids.get(r["HomeTeam"], cc),
                    ids.get(r["AwayTeam"], cc),
                )
            )
    rows.sort()
    past: dict[str, deque] = defaultdict(deque)  # team -> dates of past league matches
    season_count: dict[tuple[str, str], int] = defaultdict(int)
    div_last: dict[str, date] = {}
    div_season_first: dict[tuple[str, str], date] = {}
    feats: dict[str, dict[str, float]] = {}
    # group by (div, date) so same-day matches see the same division state
    by_dd: dict[tuple[str, date], list] = defaultdict(list)
    for d, div, h, a in rows:
        by_dd[(div, d)].append((h, a))
    for div, d in sorted(by_dd, key=lambda k: (k[1], k[0])):
        season = season_id_for(div, d.isoformat())
        first = div_season_first.setdefault((div, season), d)
        gap = (d - div_last[div]).days if div in div_last else None
        post_break = 1.0 if (gap is not None and gap > 10 and d != first) else 0.0
        for h, a in by_dd[(div, d)]:

            def side(t: str) -> dict[str, float]:
                q = past[t]
                rest = (d - q[-1]).days if q else REST_CAP
                rest = min(rest, REST_CAP)
                n7 = sum(1 for x in q if 0 < (d - x).days <= 7)
                n14 = sum(1 for x in q if 0 < (d - x).days <= 14)
                n28 = sum(1 for x in q if 0 < (d - x).days <= 28)
                early = 1.0 if season_count[(t, season)] < 5 else 0.0
                return {"rest": float(rest), "n7": n7, "n14": n14, "n28": n28, "early": early}

            sh, sa = side(h), side(a)
            feats[f"{div}|{d.isoformat()}|{h}|{a}"] = {
                "rest_home": sh["rest"],
                "rest_away": sa["rest"],
                "rest_diff": sh["rest"] - sa["rest"],
                "n7_home": sh["n7"],
                "n7_away": sa["n7"],
                "n14_home": sh["n14"],
                "n14_away": sa["n14"],
                "n28_home": sh["n28"],
                "n28_away": sa["n28"],
                "n7_diff": sh["n7"] - sa["n7"],
                "n28_diff": sh["n28"] - sa["n28"],
                "early_home": sh["early"],
                "early_away": sa["early"],
                "post_break": post_break,
            }
        for h, a in by_dd[(div, d)]:
            for t in (h, a):
                past[t].append(d)
                while past[t] and (d - past[t][0]).days > 60:
                    past[t].popleft()
                season_count[(t, season)] += 1
        div_last[div] = d
    return feats


def load_predictions(path: Path) -> list[dict]:
    out = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append(r)
    return out


def _logit_feats(p: np.ndarray) -> np.ndarray:
    lp = np.log(np.clip(p, 1e-6, 1))
    return np.column_stack([lp[:, 0] - lp[:, 2], lp[:, 1] - lp[:, 2]])


def residual_test(
    preds: list[dict], feats: dict[str, dict[str, float]], ref: str, seasons: list[str]
) -> dict:
    """ref in {'mkt', 'dc', 'core'}: which forecast's logits form the baseline."""
    keys = [r["key"] for r in preds if r["key"] in feats]
    rows = [r for r in preds if r["key"] in feats]
    y = np.array([int(r["y"]) for r in rows])
    seas = np.array([r["season"] for r in rows])
    P_ref = np.array(
        [[float(r[f"{ref}_h"]), float(r[f"{ref}_d"]), float(r[f"{ref}_a"])] for r in rows]
    )
    F = {name: np.array([feats[k][name] for k in keys]) for name in BLOCKS["all"]}
    base_logits = _logit_feats(P_ref)
    out: dict = {
        "reference": ref,
        "n_total": len(rows),
        "by_block": {},
        "raw_reference_logloss": None,
    }
    ll_raw_all, ll_base_all = [], []
    per_match: dict[str, list[np.ndarray]] = {b: [] for b in BLOCKS}
    per_match_base: list[np.ndarray] = []
    coef_last: dict[str, dict[str, float]] = {}
    for s in seasons:
        tr = np.array([int(x[:4]) < int(s[:4]) for x in seas])
        te = seas == s
        if tr.sum() < 500 or te.sum() == 0:
            continue
        X0_tr = np.column_stack([np.ones(tr.sum()), base_logits[tr]])
        X0_te = np.column_stack([np.ones(te.sum()), base_logits[te]])
        W0 = fit_multinomial(X0_tr, y[tr])
        P0 = predict_multinomial(W0, X0_te)
        l_base = -np.log(np.clip(P0[np.arange(te.sum()), y[te]], 1e-9, 1))
        l_raw = -np.log(np.clip(P_ref[te][np.arange(te.sum()), y[te]], 1e-9, 1))
        ll_raw_all.append(l_raw)
        ll_base_all.append(l_base)
        per_match_base.append(l_base)
        for b, names in BLOCKS.items():
            Xf_tr = np.column_stack([F[n][tr] for n in names]).astype(float)
            Xf_te = np.column_stack([F[n][te] for n in names]).astype(float)
            mu, sd = Xf_tr.mean(axis=0), Xf_tr.std(axis=0) + 1e-9
            Xb_tr = np.column_stack([X0_tr, (Xf_tr - mu) / sd])
            Xb_te = np.column_stack([X0_te, (Xf_te - mu) / sd])
            Wb = fit_multinomial(Xb_tr, y[tr])
            Pb = predict_multinomial(Wb, Xb_te)
            per_match[b].append(-np.log(np.clip(Pb[np.arange(te.sum()), y[te]], 1e-9, 1)))
            if s == seasons[-1]:
                coef_last[b] = {
                    f"{n}:{c}": round(float(Wb[3 + i, j]), 4)
                    for i, n in enumerate(names)
                    for j, c in enumerate(("home", "draw"))
                }
    l_raw = np.concatenate(ll_raw_all)
    l_base = np.concatenate(ll_base_all)
    out["n_scored"] = len(l_base)
    out["raw_reference_logloss"] = round(float(l_raw.mean()), 5)
    out["recalibrated_reference_logloss"] = round(float(l_base.mean()), 5)
    for b in BLOCKS:
        lb = np.concatenate(per_match[b])
        diff = l_base - lb  # positive = block improves on the recalibrated reference
        ci = bootstrap_mean_ci(diff, n_boot=2000)
        diff_raw = l_raw - lb
        ci_raw = bootstrap_mean_ci(diff_raw, n_boot=2000)
        out["by_block"][b] = {
            "log_loss": round(float(lb.mean()), 5),
            "improvement_vs_recalibrated_ref": round(float(diff.mean()), 5),
            "ci95": [round(ci[0], 5), round(ci[1], 5)],
            "improvement_vs_raw_ref": round(float(diff_raw.mean()), 5),
            "ci95_vs_raw": [round(ci_raw[0], 5), round(ci_raw[1], 5)],
            "significant_at_95": bool(ci[0] > 0),
            "coefficients_last_season_standardised": coef_last.get(b, {}),
        }
    return out


def rest_buckets(preds: list[dict], feats: dict[str, dict[str, float]]) -> dict:
    """Descriptive: realised home rate vs market P(home) by rest-difference bucket."""
    edges = [(-99, -3), (-2, -1), (0, 0), (1, 2), (3, 99)]
    out = {}
    rows = [r for r in preds if r["key"] in feats]
    rd = np.array([feats[r["key"]]["rest_diff"] for r in rows])
    yh = np.array([int(r["y"]) == 0 for r in rows]).astype(float)
    pm = np.array([float(r["p_mkt_h"]) for r in rows])
    pdc = np.array([float(r["dc_h"]) for r in rows])
    for lo, hi in edges:
        m = (rd >= lo) & (rd <= hi)
        if m.sum() < 50:
            continue
        out[f"rest_diff {lo}..{hi}"] = {
            "n": int(m.sum()),
            "realised_home_rate": round(float(yh[m].mean()), 4),
            "market_p_home": round(float(pm[m].mean()), 4),
            "dc_p_home": round(float(pdc[m].mean()), 4),
            "market_residual": round(float((yh[m] - pm[m]).mean()), 4),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", default=str(PRED_CSV))
    ap.add_argument("--out", default=str(OUT_JSON))
    a = ap.parse_args()
    t0 = time.time()
    feats = build_features()
    preds = load_predictions(Path(a.preds))
    seasons = sorted({r["season"] for r in preds}, key=lambda s: int(s[:4]))
    missing = [r["key"] for r in preds if r["key"] not in feats]
    refs = ["mkt", "dc"] + (["core"] if "core_h" in preds[0] else [])
    res = {
        "protocol": PROTOCOL_VERSION,
        "status": "RESEARCH_ONLY",
        "inputs": {
            "predictions_csv": str(Path(a.preds).relative_to(REPO)),
            "n_predictions": len(preds),
            "n_without_features": len(missing),
            "seasons_in_sample": seasons,
            "seasons_scored": [s for s in seasons if int(s[:4]) >= 2020],
        },
        "feature_definitions": {
            "note": "domestic league matches only; cups/UEFA absent from the CSV -> rest is an upper bound, congestion a lower bound",
            "blocks": BLOCKS,
        },
        "feature_summary": {
            n: {
                "mean": round(
                    float(np.mean([feats[r["key"]][n] for r in preds if r["key"] in feats])), 3
                ),
                "sd": round(
                    float(np.std([feats[r["key"]][n] for r in preds if r["key"] in feats])), 3
                ),
            }
            for n in BLOCKS["all"]
        },
        "rest_diff_buckets": rest_buckets(preds, feats),
        "residual_tests": {ref: residual_test(preds, feats, ref, seasons) for ref in refs},
    }
    res["elapsed_s"] = round(time.time() - t0, 1)
    res["result_hash"] = content_hash({k: v for k, v in res.items() if k != "elapsed_s"})
    write_json(Path(a.out), res)
    print(
        json.dumps(
            {
                k: {
                    "raw": v["raw_reference_logloss"],
                    "recal": v["recalibrated_reference_logloss"],
                    **{
                        b: (x["improvement_vs_recalibrated_ref"], x["ci95"])
                        for b, x in v["by_block"].items()
                    },
                }
                for k, v in res["residual_tests"].items()
            },
            indent=1,
        )
    )
    print(json.dumps(res["rest_diff_buckets"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
