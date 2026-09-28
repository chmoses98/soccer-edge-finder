"""Evaluation infrastructure for `probability_edge_positive` (P(edge > 0)).

Two parts:

1. A pure function library for archived records (`prediction_record_v1` from
   `soccer_edge.run.pipeline._contract_record`, joined with `settlement_record_v1` from
   `soccer_edge.run.settle`): candidates are binned by the reported p_edge_positive and each bin
   reports n, mean fee-adjusted edge, realised fee-adjusted return per contract (settled only),
   CLV vs the captured close, and the share beating the reference-market probability.

2. A historical proxy study (`proxy` sub-command): the walk-forward DATA_ONLY posterior draws
   (cached by `research/recalibration.py`) against de-vigged Bet365 pre-match 1X2 as the 'market'.
   For every (match, side) the analogue of p_edge_positive is
       P_posterior( p_side > price + fee ),   price = de-vigged market probability,
       fee = 0.07 * price * (1 - price)        (Kalshi quadratic taker fee, multiplier 1)
   and realised returns are computed both at that fee-adjusted de-vigged price and at the actual
   Bet365 decimal odds (vig included). Bet365 is a sharp book; returns are expected to be negative
   overall and are reported as they are. The question is only whether higher p_edge_positive
   buckets are *relatively* better (higher realised return, higher hit rate).

What p_edge_positive is and is not
----------------------------------
It is the share of posterior worlds in which the model's own probability clears the breakeven.
It is NOT the probability that the contract wins, and it is not the probability that the bet is
+EV against the truth: it carries no term for the model's systematic bias relative to the market,
and it inherits any mis-scaling of the posterior width (a too-wide posterior makes it too timid,
a too-narrow one too bold). See docs/PEDGE_CALIBRATION.md for the label recommendation.

Run:
  PYTHONPATH=src python research/pedge_eval.py proxy
  PYTHONPATH=src python research/pedge_eval.py records --predictions <jsonl...> --settlements <jsonl...>
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from soccer_edge.core.serialization import content_hash, read_jsonl, write_json

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:  # allow `python research/pedge_eval.py` with only PYTHONPATH=src
    sys.path.insert(0, str(REPO))
PROTOCOL_VERSION = "pedge_proxy_v1"
FEE_COEF = 0.07
PEDGE_EDGES = (0.0, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0 + 1e-9)
PEDGE_LABELS = ("<0.6", "0.6-0.7", "0.7-0.8", "0.8-0.9", "0.9-0.95", ">=0.95")
SIDES = ("home", "draw", "away")


# ----------------------------------------------------------------------------------------------
# Pure functions
# ----------------------------------------------------------------------------------------------
def quadratic_fee(price: np.ndarray | float, coef: float = FEE_COEF) -> np.ndarray | float:
    """Kalshi quadratic taker fee per contract (dollars) at `price` in (0,1)."""
    return coef * price * (1.0 - price)


def breakeven(price: np.ndarray | float, coef: float = FEE_COEF) -> np.ndarray | float:
    return price + quadratic_fee(price, coef)


def p_edge_positive(draws: np.ndarray, be: np.ndarray) -> np.ndarray:
    """Share of posterior draws (n,S) strictly above the breakeven (n,)."""
    return (draws > np.asarray(be)[:, None]).mean(axis=1)


def bin_index(p: np.ndarray | float) -> np.ndarray:
    """Bucket index into PEDGE_LABELS for p in [0,1]."""
    return np.clip(np.digitize(np.asarray(p, float), PEDGE_EDGES[1:-1]), 0, len(PEDGE_LABELS) - 1)


def _mean(xs: list[float]) -> float | None:
    return round(float(np.mean(xs)), 5) if xs else None


def bucket_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per p_edge_positive bucket: n, mean claimed fee-adjusted edge, realised return, hit rate,
    CLV and share beating the reference. Rows carry the keys produced by `rows_from_records` or
    `proxy_rows`; unsettled rows (realised None) count in n only."""
    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        buckets[int(bin_index(r["p_edge_positive"]))].append(r)
    out = []
    for b, label in enumerate(PEDGE_LABELS):
        rs = buckets.get(b, [])
        settled = [r for r in rs if r.get("realised") is not None]
        clv = [r["clv"] for r in rs if r.get("clv") is not None]
        beat = [r["beat_reference"] for r in rs if r.get("beat_reference") is not None]
        alt = [r["realised_alt"] for r in settled if r.get("realised_alt") is not None]
        entry = {
            "bucket": label,
            "n": len(rs),
            "mean_p_edge_positive": _mean([r["p_edge_positive"] for r in rs]),
            "mean_fee_adjusted_edge": _mean([r["fee_adjusted_edge"] for r in rs]),
            "n_settled": len(settled),
            "mean_realised_return": _mean([r["realised"] for r in settled]),
            "hit_rate": _mean([float(r["won"]) for r in settled]),
            "mean_price": _mean([r["price"] for r in rs]),
            "mean_clv": _mean(clv),
            "n_clv": len(clv),
            "share_beating_reference": _mean(beat),
        }
        if alt:
            entry["mean_realised_return_alt"] = _mean(alt)
        if settled:
            se = float(np.std([r["realised"] for r in settled]) / np.sqrt(len(settled)))
            entry["realised_return_se"] = round(se, 5)
        out.append(entry)
    return out


def monotonicity(table: list[dict[str, Any]], key: str = "mean_realised_return") -> dict[str, Any]:
    """Spearman rank correlation between bucket order and a bucket statistic (buckets with data)."""
    xs = [
        i
        for i, t in enumerate(table)
        if t.get(key) is not None and t.get("n_settled", t.get("n", 0)) >= 30
    ]
    ys = [table[i][key] for i in xs]
    if len(xs) < 3:
        return {"spearman": None, "n_buckets": len(xs)}
    rx = np.argsort(np.argsort(xs))
    ry = np.argsort(np.argsort(ys))
    rho = float(np.corrcoef(rx, ry)[0, 1])
    return {"spearman": round(rho, 3), "n_buckets": len(xs), "values": [round(v, 5) for v in ys]}


def _f(v: Any) -> float | None:
    if v in (None, "", "None"):
        return None
    return float(v)


def rows_from_records(
    predictions: list[dict[str, Any]], settlements: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Flatten archived prediction records (+ optional settlements) into candidate rows, one per
    (record, side) that carries an edge assessment."""
    st_by_id = {s.get("prediction_record_id"): s for s in (settlements or [])}
    rows: list[dict[str, Any]] = []
    for rec in predictions:
        if rec.get("schema") not in (None, "prediction_record_v1"):
            continue
        edge = rec.get("edge") or {}
        ref_yes = _f(rec.get("reference_probability")) or _f(
            (rec.get("recommendation") or {}).get("reference_probability")
        )
        st = st_by_id.get(rec.get("record_id"))
        for side in ("yes", "no"):
            a = edge.get(side)
            if not a or a.get("p_edge_positive") is None:
                continue
            price = _f(a.get("price"))
            fee = _f(a.get("fee_per_contract"))
            row: dict[str, Any] = {
                "record_id": rec.get("record_id"),
                "ticker": rec.get("ticker"),
                "family": rec.get("family"),
                "side": side,
                "p_edge_positive": float(a["p_edge_positive"]),
                "fee_adjusted_edge": float(a.get("fee_adjusted_edge", 0.0)),
                "fair": _f(a.get("fair")),
                "price": price,
                "fee": fee,
                "realised": None,
                "won": None,
                "clv": None,
                "beat_reference": None,
            }
            if ref_yes is not None and row["fair"] is not None:
                ref = ref_yes if side == "yes" else 1.0 - ref_yes
                row["reference_probability"] = ref
                row["beat_reference"] = bool(row["fair"] > ref)
            if st is not None and st.get("outcome") in ("yes", "no") and price is not None:
                won = st["outcome"] == side
                row["won"] = won
                row["realised"] = float(won) - price - (fee or 0.0)
                clv_yes = _f(st.get("clv_yes_points"))
                if clv_yes is not None:
                    row["clv"] = clv_yes if side == "yes" else -clv_yes
            rows.append(row)
    return rows


def proxy_rows(
    draws: np.ndarray,
    p3: np.ndarray,
    p_mkt: np.ndarray,
    *,
    odds: np.ndarray,
    y: np.ndarray,
    meta: dict[str, np.ndarray] | None = None,
    worst_case_q: float = 0.20,
) -> list[dict[str, Any]]:
    """Historical analogue rows: one per (match, side). draws (n,S,3), p3 (n,3) integrated
    predictive, p_mkt (n,3) de-vigged market, odds (n,3) decimal, y (n,) outcome index."""
    n = len(y)
    rows: list[dict[str, Any]] = []
    meta = meta or {}
    for s, side in enumerate(SIDES):
        price = p_mkt[:, s]
        fee = quadratic_fee(price)
        be = price + fee
        ppos = p_edge_positive(draws[:, :, s], be)
        worst = np.quantile(draws[:, :, s], worst_case_q, axis=1) - be
        won = y == s
        realised = won.astype(float) - price - fee
        realised_b365 = np.where(won, odds[:, s] - 1.0, -1.0)
        edge = p3[:, s] - be
        for i in range(n):
            rows.append(
                {
                    "side": side,
                    "p_edge_positive": float(ppos[i]),
                    "fee_adjusted_edge": float(edge[i]),
                    "fair": float(p3[i, s]),
                    "price": float(price[i]),
                    "fee": float(fee[i]),
                    "worst_case_edge": float(worst[i]),
                    "realised": float(realised[i]),
                    "realised_alt": float(realised_b365[i]),
                    "won": bool(won[i]),
                    "clv": None,
                    "beat_reference": bool(p3[i, s] > price[i]),
                    "reference_probability": float(price[i]),
                    **{k: str(v[i]) for k, v in meta.items()},
                }
            )
    return rows


# ----------------------------------------------------------------------------------------------
# Historical proxy study
# ----------------------------------------------------------------------------------------------
def proxy_study(
    cache, k_configs: dict[str, tuple[np.ndarray, np.ndarray, str]], seasons: list[str]
) -> dict[str, Any]:
    from research.recalibration import evaluate

    aligned = np.isin(cache.season, seasons)
    out: dict[str, Any] = {}
    for name, (k, sig, desc) in k_configs.items():
        ev = evaluate(cache, k, sig, keep_draws=True)
        idx = np.where(aligned)[0]
        rows = proxy_rows(
            ev.draws[idx].astype(float),
            ev.p3[idx],
            cache.p_mkt[idx],
            odds=cache.odds[idx],
            y=cache.y[idx],
            meta={"season": cache.season[idx], "division": cache.division[idx]},
        )
        tab = bucket_table(rows)
        res: dict[str, Any] = {
            "description": desc,
            "mean_k_applied": round(float(k[aligned].mean()), 4),
            "n_candidates": len(rows),
            "all_sides": tab,
            "monotonicity_realised_devig": monotonicity(tab, "mean_realised_return"),
            "monotonicity_realised_bet365": monotonicity(tab, "mean_realised_return_alt"),
            "monotonicity_hit_rate": monotonicity(tab, "hit_rate"),
            "by_side": {
                side: bucket_table([r for r in rows if r["side"] == side]) for side in SIDES
            },
            "by_season": {s: bucket_table([r for r in rows if r["season"] == s]) for s in seasons},
        }
        # edge_v1 selection proxy: fee-adjusted edge >= 0.02, P(edge>0) >= 0.80, worst case > 0
        sel = [
            r
            for r in rows
            if r["fee_adjusted_edge"] >= 0.02
            and r["p_edge_positive"] >= 0.80
            and r["worst_case_edge"] > 0
        ]
        res["edge_v1_rule_selection"] = {
            "n": len(sel),
            "share_of_candidates": round(len(sel) / max(len(rows), 1), 4),
            "mean_claimed_fee_adjusted_edge": _mean([r["fee_adjusted_edge"] for r in sel]),
            "mean_realised_return_devig_fee": _mean([r["realised"] for r in sel]),
            "mean_realised_return_bet365": _mean([r["realised_alt"] for r in sel]),
            "hit_rate": _mean([float(r["won"]) for r in sel]),
            "by_side_n": {side: sum(1 for r in sel if r["side"] == side) for side in SIDES},
        }
        # calibration of the *claimed* edge: realised - claimed by bucket
        res["claimed_minus_realised_by_bucket"] = [
            {
                "bucket": t["bucket"],
                "claimed_edge": t["mean_fee_adjusted_edge"],
                "realised_devig_fee": t["mean_realised_return"],
                "gap": round(t["mean_fee_adjusted_edge"] - t["mean_realised_return"], 5)
                if t["mean_fee_adjusted_edge"] is not None and t["mean_realised_return"] is not None
                else None,
            }
            for t in tab
        ]
        out[name] = res
    return out


def _load_cache_or_collect(cache_path: Path, matches_csv: Path):
    from research.recalibration import CACHE_PATH, Cache, Config, collect, load_matches

    path = cache_path or CACHE_PATH
    if path.exists():
        return Cache.load(path), None
    obs, data_hash = load_matches(matches_csv, ("E0", "SP1", "D1", "I1", "F1"), 2017)
    cache = collect(Config(), obs.payload)
    cache.save(path)
    return cache, data_hash


def cmd_proxy(a: argparse.Namespace) -> int:
    from research.recalibration import WORLDS_V1_SIGMA_SHARED, _season_start

    t0 = time.time()
    cache, data_hash = _load_cache_or_collect(Path(a.cache), Path(a.matches_csv))
    n = len(cache)
    seasons = sorted({s for s in set(cache.season) if _season_start(s) >= 2019}, key=_season_start)
    ones, zeros = np.ones(n), np.zeros(n)
    sig = np.full(n, WORLDS_V1_SIGMA_SHARED)
    configs: dict[str, tuple[np.ndarray, np.ndarray, str]] = {
        "current_worlds_v1": (
            ones,
            sig,
            "k=1 posterior + worlds_v1 shared inflation (production proxy)",
        ),
        "posterior_only": (ones, zeros, "k=1, no world-layer inflation"),
    }
    recal_path = Path(a.recalibration_json)
    recal_meta: dict[str, Any] = {}
    if recal_path.exists():
        rj = json.loads(recal_path.read_text())
        wf = rj.get("walk_forward_fitted_scales", {}).get("global_outcome", {})
        k_wf = ones.copy()
        for s, kv in wf.items():
            k_wf[cache.season == s] = float(kv)
        configs["global_outcome_k_walk_forward"] = (
            k_wf,
            sig,
            "walk-forward outcome-based global k from recalibration_v1",
        )
        recal_meta = {
            "recalibration_result_hash": rj.get("result_hash"),
            "decision": rj.get("decision", {}).get("chosen"),
        }
    res = {
        "protocol": PROTOCOL_VERSION,
        "fee_model": {
            "type": "quadratic_taker",
            "coef": FEE_COEF,
            "price": "de-vigged Bet365 pre-match probability",
        },
        "buckets": list(PEDGE_LABELS),
        "n_matches_aligned": int(np.isin(cache.season, seasons).sum()),
        "seasons": seasons,
        "configs": proxy_study(cache, configs, seasons),
        "recalibration": recal_meta,
        "data_provenance": {"cache": str(a.cache), "content_hash": data_hash},
        "notes": [
            "Bet365 is a sharp bookmaker; the de-vigged price is a proxy for a fair Kalshi price, so realised returns are expected to be negative overall",
            "p_edge_positive here is the share of posterior draws above price + fee, exactly as pricing/edge.py computes it from world probabilities",
            "no closing line in the redistribution -> CLV is not available historically",
        ],
    }
    res["elapsed_s"] = round(time.time() - t0, 1)
    res["result_hash"] = content_hash({k: v for k, v in res.items() if k != "elapsed_s"})
    write_json(Path(a.out), res)
    for name, r in res["configs"].items():
        print(f"\n== {name} (mean k {r['mean_k_applied']}) ==")
        for t in r["all_sides"]:
            print(
                f"  {t['bucket']:>8} n={t['n']:6d} claimed={t['mean_fee_adjusted_edge']!s:>9} realised(devig+fee)={t['mean_realised_return']!s:>9} bet365={t.get('mean_realised_return_alt')!s:>9} hit={t['hit_rate']}"
            )
        print("  selection:", json.dumps(r["edge_v1_rule_selection"]))
    print(f"wrote {a.out} ({res['result_hash']}) in {res['elapsed_s']}s")
    return 0


def cmd_records(a: argparse.Namespace) -> int:
    preds = [r for p in a.predictions for r in read_jsonl(Path(p))]
    setts = [r for p in (a.settlements or []) for r in read_jsonl(Path(p))]
    rows = rows_from_records(preds, setts)
    table = bucket_table(rows)
    out = {
        "n_rows": len(rows),
        "n_predictions": len(preds),
        "n_settlements": len(setts),
        "table": table,
        "monotonicity": monotonicity(table),
    }
    if a.out:
        write_json(Path(a.out), out)
    json.dump(out, sys.stdout, indent=1)
    print()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("proxy", help="historical P(edge>0) proxy study vs de-vigged Bet365")
    p.add_argument("--cache", default=str(REPO / "data" / "cache" / "recalibration_cache_v1.npz"))
    p.add_argument("--matches-csv", default=str(REPO / "data" / "cache" / "Matches.csv"))
    p.add_argument(
        "--recalibration-json", default=str(REPO / "data" / "research" / "recalibration_v1.json")
    )
    p.add_argument("--out", default=str(REPO / "data" / "research" / "pedge_proxy_v1.json"))
    p.set_defaults(fn=cmd_proxy)
    r = sub.add_parser("records", help="bucket archived prediction (+settlement) records")
    r.add_argument("--predictions", nargs="+", required=True)
    r.add_argument("--settlements", nargs="*")
    r.add_argument("--out", default=None)
    r.set_defaults(fn=cmd_records)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
