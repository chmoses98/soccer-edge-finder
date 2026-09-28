"""Promotion evaluator v2 (remediation phase 23; audit §Q). Machine-readable, report-only.

For every cell (model_family x market_family x competition group x horizon bucket) it evaluates the
audit's gates on prospective evidence and emits one of

    NOT_ELIGIBLE                 at least one gate fails (every failed gate is named)
    ELIGIBLE_FOR_OWNER_REVIEW    every gate passes; a human decides (audit §Q10)

There is no AUTO_PROMOTE outcome and this module never writes `config/authority.json`; the CLI
(`soccer promote evaluate`) only writes `evaluation/promotion_report.v1.json`.

Gates (all must hold; thresholds are the audit's, frozen here as `PromotionGates`):

  integrity     unaccounted contracts == 0 in every contributing run; archive manifest verifies;
                missing reference close <= 20 %; settlement rate >= 98 % of kickoffs older than 3 h
  clv           >= 200 selected sides from >= 80 fixtures; >= 70 % TRUE_CLOSE among close observations;
                fixture-cluster-bootstrap 95 % lower bound of EV_close > 0; mean EV_close >= +1.0 pt;
                same sign in both halves of the sample
  kalshi        fee-aware Kalshi price CLV mean >= 0
  prediction    log loss <= Kalshi valid-mid log loss + 0.005; <= reference log loss + 0.010; ECE <= 0.04
  uncertainty   realised 80 % interval coverage in [0.70, 0.90]
  liquidity     >= 80 % of selected sides had depth >= 3x the intended size; median spread <= 3 cents;
                reference present for 100 % of selected sides
  reference     a SHARP_REFERENCE source is available (audit §R1); without it no cell can pass
  realised      ROI 95 % lower bound > -10 % (guardrail, not the objective)

EV_close for a settled side = p_side(REFERENCE_CLOSE) - break-even of the entry (entry ask + fee); the
reference close is `close_v2.reference` (TRUE_CLOSE or NEAR_CLOSE) written by settlement; the Kalshi
close is `close_v2.kalshi` (KALSHI_CLOSE only).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

import numpy as np

from soccer_edge.evaluation.metrics import (
    bootstrap_mean_ci,
    expected_calibration_error,
    interval_calibration,
    log_loss,
)
from soccer_edge.kalshi.fees import FeeRegime, fee_per_contract
from soccer_edge.reference.quality import live_sharp_reference_available

VERDICT_NOT_ELIGIBLE = "NOT_ELIGIBLE"
VERDICT_ELIGIBLE = "ELIGIBLE_FOR_OWNER_REVIEW"

TOP5 = {"eng.premier_league", "esp.la_liga", "ger.bundesliga", "ita.serie_a", "fra.ligue_1"}


@dataclass(frozen=True)
class PromotionGates:
    min_selected_sides: int = 200
    min_fixtures: int = 80
    min_true_close_share: float = 0.70
    min_mean_ev_close_points: float = 0.01
    max_missing_close_rate: float = 0.20
    min_settlement_rate: float = 0.98
    max_logloss_gap_vs_kalshi_mid: float = 0.005
    max_logloss_gap_vs_reference: float = 0.010
    max_ece: float = 0.04
    coverage_band: tuple[float, float] = (0.70, 0.90)
    min_depth_multiple: float = 3.0
    min_depth_share: float = 0.80
    max_median_spread: float = 0.03
    roi_lower_bound_min: float = -0.10
    version: str = "promotion_v2"


def competition_group(competition_id: str) -> str:
    if competition_id in TOP5:
        return "top5"
    if competition_id.startswith(("uefa.nations", "fifa.", "concacaf.nations", "uefa.euro")):
        return "international"
    if competition_id in ("usa.mls", "mex.liga_mx", "bra.serie_a", "arg.primera"):
        return "americas"
    return "other"


def horizon_bucket(horizon: str | None) -> str:
    if horizon in ("T-90m", "T-60m", "T-30m", "T-15m", "T-10m", "close", "lineup"):
        return "near_close"
    if horizon in ("T-2h", "T-6h"):
        return "same_day"
    return "far"


def _dec(v: Any) -> float | None:
    if v is None or v in ("None", ""):
        return None
    try:
        return float(Decimal(str(v)))
    except (ValueError, ArithmeticError):
        return None


def _entry_breakeven(rec: dict[str, Any], side: str) -> float | None:
    price = _dec(rec.get("entry_yes_ask") if side == "yes" else rec.get("entry_no_ask"))
    if price is None or not (0 < price < 1):
        return None
    fee_type = (rec.get("fee_regime") or {}).get("fee_type") or "quadratic"
    try:
        fee = float(fee_per_contract(Decimal(str(price)), FeeRegime(fee_type)))
    except Exception:
        fee = 0.07 * price * (1 - price)
    return price + fee


@dataclass
class CellEvidence:
    key: tuple[str, str, str, str]
    ev_close: list[float]
    ev_fixtures: list[str]
    true_close: int
    close_obs: int
    kalshi_fee_aware_clv: list[float]
    p_model: list[float]
    p_kalshi_mid: list[float]
    p_reference: list[float]
    y: list[float]
    p_lo: list[float]
    p_hi: list[float]
    depth_ok: list[bool]
    spreads: list[float]
    reference_present: list[bool]
    realised_returns: list[float]
    settled: int
    due: int


def collect_cells(
    settlements: list[dict[str, Any]], predictions_by_id: dict[str, dict[str, Any]]
) -> dict[tuple, CellEvidence]:
    cells: dict[tuple, CellEvidence] = {}
    for s in settlements:
        if s.get("schema") != "settlement_record_v1":
            continue
        rec = predictions_by_id.get(s.get("prediction_record_id"), {})
        comp = (
            rec.get("competition_id") or s.get("fixture_id", "").split(":")[1]
            if ":" in s.get("fixture_id", "")
            else "unknown"
        )
        key = (
            s.get("model_family", "unknown"),
            s.get("family", "unknown"),
            competition_group(comp),
            horizon_bucket(s.get("horizon")),
        )
        cell = cells.get(key)
        if cell is None:
            cell = cells[key] = CellEvidence(
                key, [], [], 0, 0, [], [], [], [], [], [], [], [], [], [], [], 0, 0
            )
        cell.due += 1
        outcome = s.get("outcome")
        if outcome not in ("yes", "no", "void"):
            continue
        cell.settled += 1
        cv = s.get("close_v2") or {}
        ref_close = cv.get("reference") or {}
        kal_close = cv.get("kalshi") or {}
        if ref_close.get("close_class") in ("TRUE_CLOSE", "NEAR_CLOSE", "STALE", "NONE"):
            if ref_close.get("close_class") in ("TRUE_CLOSE", "NEAR_CLOSE"):
                cell.close_obs += 1
                if ref_close.get("close_class") == "TRUE_CLOSE":
                    cell.true_close += 1
        # selected sides = shadow/recommended sides on the record
        recd = s.get("recommended") or {}
        for side in ("yes", "no"):
            r = recd.get(side) or {}
            if not (r.get("shadow") or r.get("recommended")):
                continue
            be = _entry_breakeven(s, side)
            p_ref_side = (
                ref_close.get("probability_yes")
                if side == "yes"
                else ref_close.get("probability_no")
            )
            if (
                be is not None
                and p_ref_side is not None
                and ref_close.get("close_class") in ("TRUE_CLOSE", "NEAR_CLOSE")
            ):
                cell.ev_close.append(float(p_ref_side) - be)
                cell.ev_fixtures.append(s.get("fixture_id", ""))
            fa = ((s.get("clv") or {}).get(side) or {}).get("clv_fee_aware_points")
            if fa is not None and kal_close.get("close_class") == "KALSHI_CLOSE":
                cell.kalshi_fee_aware_clv.append(float(fa))
            cell.reference_present.append(p_ref_side is not None)
            market = rec.get("market") or {}
            size = _dec(
                market.get("yes_ask_size")
                if side == "yes"
                else (market.get("no_ask_size") or market.get("yes_bid_size"))
            )
            cell.depth_ok.append(
                size is not None and size >= 3.0
            )  # intended size 1 contract in shadow mode
            bid, ask = _dec(market.get("yes_bid")), _dec(market.get("yes_ask"))
            if bid is not None and ask is not None and 0 < bid <= ask < 1:
                cell.spreads.append(ask - bid)
            if outcome in ("yes", "no") and be is not None:
                won = outcome == side
                price = (
                    _dec(s.get("entry_yes_ask") if side == "yes" else s.get("entry_no_ask")) or 0.0
                )
                fee = be - price
                cell.realised_returns.append((1.0 - price - fee) if won else (-price - fee))
        # probability quality on every settled contract of the family (yes side)
        if outcome in ("yes", "no"):
            pm = s.get("fair_probability_mean")
            if pm is not None:
                cell.p_model.append(float(pm))
                cell.y.append(1.0 if outcome == "yes" else 0.0)
                mid = s.get("entry_yes_mid")
                cell.p_kalshi_mid.append(float(mid) if mid is not None else float("nan"))
                pr = s.get("reference_probability_at_prediction")
                cell.p_reference.append(float(pr) if pr is not None else float("nan"))
                lo, hi = s.get("fair_probability_low"), s.get("fair_probability_high")
                cell.p_lo.append(float(lo) if lo is not None else float("nan"))
                cell.p_hi.append(float(hi) if hi is not None else float("nan"))
    return cells


def _cluster_bootstrap_lower(
    values: list[float], clusters: list[str], n_boot: int = 1000, seed: int = 0
) -> float | None:
    if not values:
        return None
    rng = np.random.default_rng(seed)
    v = np.array(values)
    c = np.array(clusters)
    uniq = np.unique(c)
    idx = {u: np.where(c == u)[0] for u in uniq}
    means = []
    for _ in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        ix = np.concatenate([idx[u] for u in pick])
        means.append(v[ix].mean())
    return float(np.percentile(means, 2.5))


def evaluate_cell(
    cell: CellEvidence, *, gates: PromotionGates, integrity: dict[str, Any]
) -> dict[str, Any]:
    failed: list[str] = []
    metrics: dict[str, Any] = {}
    # integrity (archive-wide)
    if integrity.get("unaccounted_contracts_max", 0) != 0:
        failed.append("integrity:unaccounted_contracts")
    if not integrity.get("manifest_ok", False):
        failed.append("integrity:archive_manifest")
    settlement_rate = cell.settled / cell.due if cell.due else 0.0
    metrics["settlement_rate"] = settlement_rate
    if settlement_rate < gates.min_settlement_rate:
        failed.append("integrity:settlement_rate")
    missing_close = 1 - (cell.close_obs / cell.settled) if cell.settled else 1.0
    metrics["missing_close_rate"] = missing_close
    if missing_close > gates.max_missing_close_rate:
        failed.append("integrity:missing_close_rate")
    # reference availability
    sharp_ok, why = live_sharp_reference_available()
    metrics["sharp_reference_available"] = sharp_ok
    if not sharp_ok:
        failed.append("reference:no_live_sharp_source")
    # clv
    n_sel = len(cell.ev_close)
    n_fx = len(set(cell.ev_fixtures))
    metrics.update({"selected_sides": n_sel, "fixtures": n_fx})
    if n_sel < gates.min_selected_sides:
        failed.append("clv:min_selected_sides")
    if n_fx < gates.min_fixtures:
        failed.append("clv:min_fixtures")
    tc_share = cell.true_close / cell.close_obs if cell.close_obs else 0.0
    metrics["true_close_share"] = tc_share
    if tc_share < gates.min_true_close_share:
        failed.append("clv:true_close_share")
    if n_sel:
        mean_ev = float(np.mean(cell.ev_close))
        lower = _cluster_bootstrap_lower(cell.ev_close, cell.ev_fixtures)
        half = n_sel // 2
        first, second = (
            np.mean(cell.ev_close[:half]) if half else float("nan"),
            np.mean(cell.ev_close[half:]) if half else float("nan"),
        )
        metrics.update(
            {
                "mean_ev_close": mean_ev,
                "ev_close_lower95": lower,
                "ev_close_first_half": first,
                "ev_close_second_half": second,
            }
        )
        if lower is None or lower <= 0:
            failed.append("clv:lower_bound_not_positive")
        if mean_ev < gates.min_mean_ev_close_points:
            failed.append("clv:mean_below_1pt")
        if not (np.sign(first) == np.sign(second) and first > 0):
            failed.append("clv:sign_not_stable")
    else:
        failed.extend(["clv:lower_bound_not_positive", "clv:mean_below_1pt", "clv:sign_not_stable"])
    # kalshi movement
    if cell.kalshi_fee_aware_clv:
        m = float(np.mean(cell.kalshi_fee_aware_clv))
        metrics["kalshi_fee_aware_clv_mean"] = m
        if m < 0:
            failed.append("kalshi:fee_aware_clv_negative")
    else:
        failed.append("kalshi:no_close_observations")
    # prediction quality
    if len(cell.y) >= 30:
        y = np.array(cell.y)
        pm = np.array(cell.p_model)
        ll_m = float(log_loss(pm, y))
        metrics["log_loss_model"] = ll_m
        km = np.array(cell.p_kalshi_mid)
        ok = ~np.isnan(km)
        if ok.sum() >= 30:
            ll_k = float(log_loss(km[ok], y[ok]))
            metrics["log_loss_kalshi_mid"] = ll_k
            if float(log_loss(pm[ok], y[ok])) > ll_k + gates.max_logloss_gap_vs_kalshi_mid:
                failed.append("prediction:worse_than_kalshi_mid")
        else:
            failed.append("prediction:no_kalshi_mid_sample")
        pr = np.array(cell.p_reference)
        okr = ~np.isnan(pr)
        if okr.sum() >= 30:
            ll_r = float(log_loss(pr[okr], y[okr]))
            metrics["log_loss_reference"] = ll_r
            if float(log_loss(pm[okr], y[okr])) > ll_r + gates.max_logloss_gap_vs_reference:
                failed.append("prediction:worse_than_reference")
        else:
            failed.append("prediction:no_reference_sample")
        e = float(expected_calibration_error(pm, y))
        metrics["ece"] = e
        if e > gates.max_ece:
            failed.append("prediction:ece")
        lo_a, hi_a = np.array(cell.p_lo), np.array(cell.p_hi)
        okc = ~np.isnan(lo_a) & ~np.isnan(hi_a)
        cov = (
            float(
                interval_calibration(pm[okc], lo_a[okc], hi_a[okc], y[okc], level=0.80)[
                    "weighted_bin_coverage"
                ]
            )
            if okc.sum() >= 30
            else None
        )
        metrics["interval_coverage_80"] = cov
        if cov is None or not (gates.coverage_band[0] <= cov <= gates.coverage_band[1]):
            failed.append("uncertainty:coverage_outside_band")
    else:
        failed.extend(["prediction:insufficient_sample", "uncertainty:insufficient_sample"])
    # liquidity / completeness
    if cell.depth_ok:
        ds = float(np.mean(cell.depth_ok))
        metrics["depth_ok_share"] = ds
        if ds < gates.min_depth_share:
            failed.append("liquidity:depth_share")
    else:
        failed.append("liquidity:no_depth_data")
    if cell.spreads:
        ms = float(np.median(cell.spreads))
        metrics["median_spread"] = ms
        if ms > gates.max_median_spread:
            failed.append("liquidity:median_spread")
    if cell.reference_present:
        rp = float(np.mean(cell.reference_present))
        metrics["reference_present_share"] = rp
        if rp < 1.0:
            failed.append("completeness:reference_missing_on_selected_sides")
    # realised guardrail
    if cell.realised_returns:
        lo, hi = bootstrap_mean_ci(np.array(cell.realised_returns), n_boot=1000)
        metrics["roi_mean"] = float(np.mean(cell.realised_returns))
        metrics["roi_lower95"] = float(lo)
        if lo <= gates.roi_lower_bound_min:
            failed.append("realised:roi_lower_bound")
    verdict = VERDICT_NOT_ELIGIBLE if failed else VERDICT_ELIGIBLE
    return {
        "cell": {
            "model_family": cell.key[0],
            "market_family": cell.key[1],
            "competition_group": cell.key[2],
            "horizon_bucket": cell.key[3],
        },
        "verdict": verdict,
        "failed_gates": failed,
        "n_failed_gates": len(failed),
        "metrics": metrics,
        "due": cell.due,
        "settled": cell.settled,
    }


def evaluate_all(
    settlements: list[dict[str, Any]],
    predictions_by_id: dict[str, dict[str, Any]],
    *,
    integrity: dict[str, Any],
    gates: PromotionGates | None = None,
    as_of: str = "",
) -> dict[str, Any]:
    gates = gates or PromotionGates()
    cells = collect_cells(settlements, predictions_by_id)
    rows = [evaluate_cell(c, gates=gates, integrity=integrity) for c in cells.values()]
    rows.sort(key=lambda r: (r["n_failed_gates"], -r["settled"]))
    closest = rows[0] if rows else None
    return {
        "schema": "promotion_report_v1",
        "as_of": as_of,
        "gates": asdict(gates),
        "integrity": integrity,
        "cells_total": len(rows),
        "eligible_for_owner_review": sum(1 for r in rows if r["verdict"] == VERDICT_ELIGIBLE),
        "not_eligible": sum(1 for r in rows if r["verdict"] == VERDICT_NOT_ELIGIBLE),
        "closest_cell": closest,
        "cells": rows,
        "note": "report only: this evaluator proposes; it never edits config/authority.json and has no AUTO_PROMOTE outcome",
    }
