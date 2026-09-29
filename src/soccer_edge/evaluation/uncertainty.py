"""Interval coverage report (remediation phase 15; audit section F, item 4).

For every cell (model family x market family x horizon, plus `any`) of SETTLED prediction records it
reports how honest the published 80 % interval was against OUTCOMES with the grouped estimator
(`evaluation.metrics.interval_calibration`: bin by fair probability, compare the bin's realised rate
with the bin's average interval), the interval's mean width, and, as a sanity diagnostic only, the
share of entry Kalshi mids that fell inside the interval (the audit's expected range is 75-88 %; it is
not the target). Verdict per cell: WITHIN_BAND when the grouped coverage lies in [0.70, 0.90] (the
promotion gate), OUTSIDE_BAND otherwise, INSUFFICIENT below 30 settled records.

This is a report. It changes nothing; the promotion evaluator reads the same estimator on its own.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from soccer_edge.evaluation.metrics import interval_calibration

COVERAGE_BAND = (0.70, 0.90)
MIN_N = 30


def coverage_cells(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cells: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        if r.get("outcome") not in ("yes", "no"):
            continue
        if r.get("fair_probability_low") is None or r.get("fair_probability_high") is None:
            continue
        key = (r["model_family"], r.get("worlds_version") or "unknown", r["family"], r["horizon"])
        cells[key].append(r)
        cells[(key[0], key[1], key[2], "any")].append(r)
    rows = []
    for (mf, wv, fam, hz), rs in sorted(cells.items()):
        y = np.array([1 if r["outcome"] == "yes" else 0 for r in rs])
        p = np.array([float(r["fair_probability_mean"]) for r in rs])
        lo = np.array([float(r["fair_probability_low"]) for r in rs])
        hi = np.array([float(r["fair_probability_high"]) for r in rs])
        mids = np.array(
            [
                float(r["entry_yes_mid"]) if r.get("entry_yes_mid") is not None else np.nan
                for r in rs
            ]
        )
        has_m = np.isfinite(mids)
        row: dict[str, Any] = {
            "model_family": mf,
            "worlds_version": wv,
            "market_family": fam,
            "horizon": hz,
            "n_settled": len(rs),
            "mean_width": float((hi - lo).mean()),
            "naive_outcome_inside_share": float(((y >= lo) & (y <= hi)).mean()),
            "market_mid_inside_share": float(((mids >= lo) & (mids <= hi))[has_m].mean())
            if has_m.sum() >= 10
            else None,
            "n_with_market_mid": int(has_m.sum()),
        }
        if len(rs) >= MIN_N:
            ic = interval_calibration(p, lo, hi, y, level=0.80)
            cov = float(ic["weighted_bin_coverage"])
            row["grouped_coverage_80"] = cov
            row["bins"] = ic.get("bins") or ic.get("rows")
            row["verdict"] = (
                "WITHIN_BAND" if COVERAGE_BAND[0] <= cov <= COVERAGE_BAND[1] else "OUTSIDE_BAND"
            )
            row["direction"] = (
                "too_narrow"
                if cov < COVERAGE_BAND[0]
                else "too_wide"
                if cov > COVERAGE_BAND[1]
                else "ok"
            )
        else:
            row["grouped_coverage_80"] = None
            row["verdict"] = "INSUFFICIENT"
            row["direction"] = None
        rows.append(row)
    return rows


def coverage_report(
    records: list[dict[str, Any]], *, as_of: datetime | None = None
) -> dict[str, Any]:
    rows = coverage_cells(records)
    n_any = [r for r in rows if r["horizon"] == "any"]
    return {
        "schema": "uncertainty_coverage_v1",
        "generated_at": (as_of or datetime.now(UTC)).isoformat(),
        "estimator": "grouped (bin by fair probability; realised rate vs the bin's mean interval)",
        "band": list(COVERAGE_BAND),
        "min_n": MIN_N,
        "n_cells": len(rows),
        "verdict_counts": {
            v: sum(1 for r in n_any if r["verdict"] == v)
            for v in ("WITHIN_BAND", "OUTSIDE_BAND", "INSUFFICIENT")
        },
        "cells": rows,
        "note": "market_mid_inside_share is a sanity diagnostic (expected 0.75-0.88), never the target",
    }


def write_report(report: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, default=str) + "\n")
