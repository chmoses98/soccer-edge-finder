"""Structural model error per market family (remediation phase 15; audit section F, item 2c).

sigma_struct(family) is the walk-forward dispersion of (model - reference) that the parameter posterior
cannot see: the sd of `logit(p_model) - logit(p_reference)` over scored walk-forward predictions, by
season (each season is out of sample for the model that priced it) and pooled. It is a property of a
strength-model variant, so it is computed for every walk-forward cache in `data/cache/research/`
(`research/wf_common.py` tables: `p_data`, `p_mkt` de-vigged Bet365 1X2; `p_data_o25`, `p_mkt_o25`).

Only families with a historical reference can be estimated: `match_result_3way` (1X2) and
`total_goals` at the 2.5 line. Every other family is `NOT_ESTIMATED` and edge_v2 keeps its default.
The term is used ONLY by edge_v2 (`sigma_edge^2 = sigma_devig^2 + sigma_stale^2 + w^2 sigma_struct^2`)
and today w_family = 0 for every family, so it changes no selection; it is recorded so that the
uncertainty that would decide bets is estimated rather than invented.

Bet365 is a retail reference, not a sharp close; the numbers are therefore an UPPER bound on the
model-vs-sharp dispersion (retail noise adds to it), which is the conservative direction for edge_v2.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

CACHE_DIR = REPO / "data" / "cache" / "research"
OUT = REPO / "data" / "research" / "sigma_struct_v1.json"
EPS = 1e-4


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def family_dispersion(
    p_model: np.ndarray, p_ref: np.ndarray, seasons: np.ndarray
) -> dict[str, Any]:
    """Dispersion of model minus reference, in logit units and in probability points, by season and
    pooled. Inputs are 1-d (one column of a family) with NaN where the reference is absent."""
    ok = np.isfinite(p_model) & np.isfinite(p_ref)
    pm, pr, se = p_model[ok], p_ref[ok], seasons[ok]
    if len(pm) < 50:
        return {"n": len(pm), "status": "INSUFFICIENT"}
    d_logit = logit(pm) - logit(pr)
    d_pts = pm - pr
    by_season = {}
    for s in sorted(set(se.tolist())):
        m = se == s
        if m.sum() >= 50:
            by_season[str(s)] = {
                "n": int(m.sum()),
                "sd_logit": float(d_logit[m].std(ddof=1)),
                "sd_points": float(d_pts[m].std(ddof=1)),
                "mean_logit": float(d_logit[m].mean()),
            }
    sds = [v["sd_logit"] for v in by_season.values()]
    return {
        "n": len(pm),
        "status": "ESTIMATED",
        "sd_logit_pooled": float(d_logit.std(ddof=1)),
        "sd_points_pooled": float(d_pts.std(ddof=1)),
        "mean_logit_pooled": float(d_logit.mean()),
        "sd_logit_season_median": float(np.median(sds)) if sds else None,
        "sd_logit_season_max": float(max(sds)) if sds else None,
        "by_season": by_season,
    }


def from_table(table: dict[str, np.ndarray]) -> dict[str, Any]:
    seasons = table["season"]
    p_data, p_mkt = table["p_data"], table["p_mkt"]
    out: dict[str, Any] = {}
    sides = {}
    for j, side in enumerate(("home", "draw", "away")):
        sides[side] = family_dispersion(p_data[:, j], p_mkt[:, j], seasons)
    # the family-level figure is the pooled dispersion over the three sides (a contract is one side)
    pm_all = np.concatenate([p_data[:, j] for j in range(3)])
    pr_all = np.concatenate([p_mkt[:, j] for j in range(3)])
    se_all = np.concatenate([seasons] * 3)
    out["match_result_3way"] = {"sides": sides, **family_dispersion(pm_all, pr_all, se_all)}
    out["total_goals"] = {
        "line": "2.5",
        **family_dispersion(table["p_data_o25"], table["p_mkt_o25"], seasons),
    }
    return out


def edge_v2_points(fams: dict[str, Any]) -> dict[str, float]:
    """The per-family value edge_v2 consumes (probability points): the season-max logit sd converted at
    the pooled points/logit ratio, i.e. the conservative end of the walk-forward range."""
    out = {}
    for fam, v in fams.items():
        if v.get("status") != "ESTIMATED":
            continue
        ratio = v["sd_points_pooled"] / max(v["sd_logit_pooled"], 1e-9)
        out[fam] = round(float((v["sd_logit_season_max"] or v["sd_logit_pooled"]) * ratio), 4)
    return out


def variant_name(path: Path) -> str:
    stem = path.stem[len("wf_") :]
    return stem.rsplit("_", 1)[0]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default=str(CACHE_DIR))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    res: dict[str, Any] = {
        "schema": "sigma_struct_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "reference": "Bet365 de-vigged (proportional), football-data.co.uk; retail, so an UPPER bound",
        "units": "sd_logit = sd of logit(p_model) - logit(p_ref); sd_points = sd of p_model - p_ref",
        "not_estimated_families": [
            "match_winner_2way",
            "draw_no_bet",
            "handicap",
            "btts",
            "exact_score",
            "first_half_*",
            "second_half_*",
            "player_goals",
            "first_to_score",
        ],
        "variants": {},
    }
    for path in sorted(Path(a.cache_dir).glob("wf_*.npz")):
        z = np.load(path, allow_pickle=True)
        if "p_mkt" not in z.files:
            continue
        table = {k: z[k] for k in ("season", "p_data", "p_mkt", "p_data_o25", "p_mkt_o25")}
        fams = from_table(table)
        res["variants"][variant_name(path)] = {
            "cache": path.name,
            "n_rows": len(table["season"]),
            "families": fams,
            "edge_v2_sigma_struct_points": edge_v2_points(fams),
        }
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    for name, v in res["variants"].items():
        print(name, json.dumps(v["edge_v2_sigma_struct_points"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
