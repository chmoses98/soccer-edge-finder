"""Prospective settlement + evaluation: join archived predictions with official results and
captured close quotes, settle each contract, and emit ModelHealthV1 rows + authority proposals.

Point-in-time rules:
* A record is settled only after kickoff + `grace` and only against a FINISHED fixture result.
* The closing quote is the LAST captured snapshot strictly before kickoff (never after).
* Records are never modified; settlements are appended to their own ledger keyed by record id.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np

from soccer_edge.archive.ledger import PredictionLedger
from soccer_edge.authority.policy import (
    Authority,
    AuthorityKey,
    AuthorityMatrix,
    Evidence,
    recommend_state,
)
from soccer_edge.contracts.v1 import ModelHealthV1, SettlementV1
from soccer_edge.core.serialization import read_jsonl
from soccer_edge.core.time import iso_utc, parse_iso_utc
from soccer_edge.evaluation.metrics import (
    brier,
    expected_calibration_error,
    interval_calibration,
    log_loss,
)
from soccer_edge.identity.models import FixtureStatus
from soccer_edge.kalshi.capture import label_horizon
from soccer_edge.kalshi.fees import FeeRegime, fee_per_contract
from soccer_edge.kalshi.taxonomy import MarketFamily, Period
from soccer_edge.pricing.semantics import Semantics
from soccer_edge.providers.interfaces import MatchResult
from soccer_edge.reference.close import (
    close_completeness,
    kalshi_close_for,
    reference_close_for,
    side_probability,
)
from soccer_edge.reference.schemas import classify_close
from soccer_edge.settlement.engine import OfficialResult, SettlementOutcome, settle
from soccer_edge.settlement.resolve import (
    CoverageRow,
    CoverageRows,
    ResultIndex,
    SettlementState,
    coverage_report,
    derive_exact_score_k,
    et_possible,
    semantics_complete,
    state_for_outcome,
)
from soccer_edge.settlement.resolve import official_from_result as _official_from_result

__all__ = [
    "CoverageRow",
    "CoverageRows",
    "ResultIndex",
    "SettlementState",
    "build_result_index",
    "coverage_report",
    "et_possible",
    "settle_ledger",
]


@dataclass
class CloseQuote:
    captured_at: datetime
    yes_bid: Decimal | None
    yes_ask: Decimal | None
    no_ask: Decimal | None

    @property
    def yes_mid(self) -> float | None:
        return _two_sided_mid(self.yes_bid, self.yes_ask)


def _two_sided_mid(bid: Decimal | None, ask: Decimal | None) -> float | None:
    """YES midpoint only for a real two-sided book. Kalshi reports an empty side as bid 0 / ask 1; those
    sentinels are not prices and must never enter CLV or the market benchmark."""
    if bid is None or ask is None or not (Decimal(0) < bid <= ask < Decimal(1)):
        return None
    return float((bid + ask) / 2)


def load_close_quotes(
    snapshots_dir: Path, kickoff_by_ticker: dict[str, datetime]
) -> dict[str, CloseQuote]:
    """Last snapshot strictly before kickoff per ticker."""
    best: dict[str, CloseQuote] = {}
    if not snapshots_dir.exists():
        return best
    for path in sorted(snapshots_dir.glob("*/*.jsonl")):
        for rec in read_jsonl(path):
            tk = rec.get("ticker")
            ko = kickoff_by_ticker.get(tk)
            if ko is None:
                continue
            cat = parse_iso_utc(rec["captured_at"])
            if cat >= ko:
                continue
            if tk not in best or cat > best[tk].captured_at:
                best[tk] = CloseQuote(
                    cat, _dec(rec.get("yes_bid")), _dec(rec.get("yes_ask")), _dec(rec.get("no_ask"))
                )
    return best


def load_snapshot_rows(snapshots_dir: Path, tickers: set[str]) -> dict[str, list[dict[str, Any]]]:
    """Every archived snapshot row per ticker (the close-v2 search needs the history, not only the last)."""
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not snapshots_dir.exists():
        return out
    for path in sorted(snapshots_dir.glob("*/*.jsonl")):
        for r in read_jsonl(path):
            t = r.get("ticker")
            if t in tickers:
                out[t].append(r)
    return out


def load_reference_rows(
    reference_dir: Path | None, fixture_ids: set[str]
) -> dict[tuple[str, str, str, str | None], list[dict[str, Any]]]:
    """Every archived reference row per (fixture, market, selection, line), all bookmakers."""
    out: dict[tuple[str, str, str, str | None], list[dict[str, Any]]] = defaultdict(list)
    if reference_dir is None or not reference_dir.exists():
        return out
    for path in sorted(reference_dir.glob("*/*.jsonl")):
        for r in read_jsonl(path):
            if r.get("fixture_id") in fixture_ids:
                line = r.get("line")
                key = (
                    r["fixture_id"],
                    r["market"],
                    r["selection"],
                    str(Decimal(str(line))) if line not in (None, "") else None,
                )
                out[key].append(r)
    return out


def close_v2_for_record(
    rec: dict[str, Any],
    kickoff: datetime,
    snapshot_rows: list[dict[str, Any]],
    reference_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Side-aware close capture for one prediction record (docs/PRELAUNCH_AUDIT.md §K, phase 8)."""
    kc = kalshi_close_for(snapshot_rows, kickoff)
    rc = reference_close_for(reference_rows, kickoff)
    market = rec.get("market") or {}
    entry_yes_ask, entry_yes_bid = _dec(market.get("yes_ask")), _dec(market.get("yes_bid"))
    ref_entry = (rec.get("reference") or {}).get("probability_yes")
    entry = {
        "kalshi": {
            "yes": str(entry_yes_ask) if entry_yes_ask is not None else None,
            "no": str(Decimal(1) - entry_yes_bid) if entry_yes_bid is not None else None,
            "captured_at": rec.get("market_as_of"),
        },
        "reference": {
            "probability_yes": ref_entry,
            "probability_no": side_probability(ref_entry, "no"),
            "bookmaker": (rec.get("reference") or {}).get("bookmaker"),
            "observed_at": (rec.get("reference") or {}).get("observed_at"),
        },
    }
    kj = kc.to_json()
    rj = rc.to_json()
    rj["probability_no"] = side_probability(rc.probability_yes, "no")
    return {
        "schema": "close_v2",
        "entry": entry,
        "kalshi": kj,
        "reference": rj,
        "complete": {
            "reference_close": rc.close_class.value in ("TRUE_CLOSE", "NEAR_CLOSE"),
            "kalshi_close": kc.close_class.value == "KALSHI_CLOSE",
        },
    }


def _dec(v: Any) -> Decimal | None:
    return None if v in (None, "", "None") else Decimal(str(v))


def load_reference_close(
    reference_dir: Path, kickoff_by_fixture: dict[str, datetime], bookmaker: str = "consensus"
) -> dict[tuple[str, str, str, str | None], tuple[datetime, float]]:
    """Last reference snapshot strictly before kickoff per (fixture, market, selection, line)."""
    best: dict[tuple[str, str, str, str | None], tuple[datetime, float]] = {}
    if not reference_dir.exists():
        return best
    for path in sorted(reference_dir.glob("*/*.jsonl")):
        for rec in read_jsonl(path):
            if rec.get("bookmaker") != bookmaker:
                continue
            ko = kickoff_by_fixture.get(rec.get("fixture_id"))
            if ko is None:
                continue
            cat = parse_iso_utc(rec["captured_at"])
            if cat >= ko:
                continue
            key = (rec["fixture_id"], rec["market"], rec["selection"], rec.get("line"))
            if key not in best or cat > best[key][0]:
                best[key] = (cat, float(rec["devigged_probability"]))
    return best


def clv_fields(
    *,
    side: str,
    entry_price: Decimal | None,
    close_yes_bid: Decimal | None,
    close_yes_ask: Decimal | None,
    fee_type: str | None,
    fee_multiplier: str | None,
) -> dict[str, Any]:
    """Side-aware CLV in YES-probability units. POSITIVE_IS_GOOD.
    probability CLV: (close mid - entry price) for YES; (entry - close mid) for NO.
    price CLV: executable close on the same side vs entry (YES: close_yes_ask - entry; NO: close_no_ask - entry
    where close_no_ask = 1 - close_yes_bid), i.e. what it would cost to enter at close.
    fee-aware CLV: price CLV minus the change in per-contract fee between entry and close prices."""
    empty = {
        "clv_probability_points": None,
        "clv_price_points": None,
        "clv_fee_aware_points": None,
    }
    if entry_price is None or close_yes_bid is None or close_yes_ask is None:
        return empty
    if not (Decimal(0) < entry_price < Decimal(1)):
        return empty
    # empty-book sentinels (bid 0 / ask 1) are not prices: no mid, and no executable close on that side
    mid_f = _two_sided_mid(close_yes_bid, close_yes_ask)
    mid = Decimal(str(mid_f)) if mid_f is not None else None
    if side == "yes":
        prob = float(mid - entry_price) if mid is not None else None
        close_exec = close_yes_ask
    else:
        prob = float((Decimal(1) - mid) - entry_price) if mid is not None else None
        close_exec = Decimal(1) - close_yes_bid
    if not (Decimal(0) < close_exec < Decimal(1)):
        return {**empty, "clv_probability_points": round(prob, 6) if prob is not None else None}
    price_clv = float(close_exec - entry_price)
    fee_aware = price_clv
    if fee_type in ("quadratic", "quadratic_with_maker_fees"):
        regime = FeeRegime(fee_type, Decimal(fee_multiplier or "1"))
        fee_aware = float(
            (close_exec + fee_per_contract(close_exec, regime))
            - (entry_price + fee_per_contract(entry_price, regime))
        )
    return {
        "clv_probability_points": round(prob, 6) if prob is not None else None,
        "clv_price_points": round(price_clv, 6),
        "clv_fee_aware_points": round(fee_aware, 6),
    }


def semantics_from_record(rec: dict[str, Any]) -> Semantics:
    s = rec["semantics"]
    slot = s.get("player_slot")
    k = int(s["k"]) if s.get("k") is not None else None
    if k is None and rec["family"] in ("exact_score", "first_half_exact_score"):
        k = derive_exact_score_k(rec["ticker"], s.get("description", ""))
    return Semantics(
        rec["ticker"],
        MarketFamily(rec["family"]),
        Period(s["period"]),
        s.get("side"),
        Decimal(s["line"]) if s.get("line") else None,
        k,
        (str(slot[0]), int(slot[1])) if slot else None,
        s.get("description", ""),
    )


def official_from_result(r: MatchResult) -> OfficialResult:
    """Legacy helper (openfootball 90' scores). Universal settlement uses `settlement.resolve`."""
    return OfficialResult(
        r.fixture_id,
        FixtureStatus.FINISHED,
        r.home_goals,
        r.away_goals,
        r.home_goals_ht,
        r.away_goals_ht,
        source=r.result_source or "openfootball",
    )


def build_result_index(
    sources: dict[str, list[MatchResult]], *, competitions_with_source: set[str] | None = None
) -> ResultIndex:
    """Merge results from every provider (`{source_id: rows}`) into one index. Competitions that have a
    source but no rows yet are declared through `competitions_with_source` so their records read
    PENDING_RESULT rather than UNSETTLEABLE."""
    idx = ResultIndex()
    for src, rows in sources.items():
        for r in rows:
            idx.add(r, source=src)
    idx.competitions_with_source |= set(competitions_with_source or ())
    return idx


def settle_ledger(
    ledger: PredictionLedger,
    results: dict[str, MatchResult] | ResultIndex,
    snapshots_dir: Path,
    settlements: PredictionLedger,
    *,
    as_of: datetime,
    grace: timedelta = timedelta(hours=3),
    reference_dir: Path | None = None,
    et_possible_for: dict[str, bool] | None = None,
    coverage_rows: list[CoverageRow] | None = None,
) -> list[dict[str, Any]]:
    """Settle every due record that has sufficient evidence; classify every record into an explicit
    settlement state (appended to `coverage_rows` when given). Only SETTLED outcomes (yes/no/void) are
    written to the settlements ledger: pending states are re-evaluated on the next run, never guessed.

    `results` may be the legacy `{fixture_id: MatchResult}` map (openfootball only) or a `ResultIndex`."""
    index = (
        results
        if isinstance(results, ResultIndex)
        else build_result_index({"openfootball": list(results.values())})
    )
    et_possible_for = et_possible_for or {}
    already = {
        r["prediction_record_id"]
        for r in settlements.iter_records()
        if r.get("outcome") in ("yes", "no", "void")
    }
    records = [r for r in ledger.iter_records() if r.get("schema") == "prediction_record_v1"]
    kickoff_by_ticker = {r["ticker"]: parse_iso_utc(r["kickoff_utc"]) for r in records}
    closes = load_close_quotes(snapshots_dir, kickoff_by_ticker)
    kickoff_by_fixture = {r["fixture_id"]: parse_iso_utc(r["kickoff_utc"]) for r in records}
    ref_close = load_reference_close(reference_dir, kickoff_by_fixture) if reference_dir else {}
    snap_rows = load_snapshot_rows(snapshots_dir, set(kickoff_by_ticker))
    ref_rows = load_reference_rows(reference_dir, set(kickoff_by_fixture))
    close_rows: list[dict[str, Any]] = []

    def _close_v2(rec: dict[str, Any], ko: datetime) -> dict[str, Any]:
        key = _reference_key(rec)
        cv = close_v2_for_record(
            rec, ko, snap_rows.get(rec["ticker"], []), ref_rows.get(key, []) if key else []
        )
        close_rows.append({"close_v2": cv})
        return cv

    written: list[dict[str, Any]] = []

    def _cov(
        rec: dict[str, Any], state: SettlementState, reason: str, sources=(), outcome=None
    ) -> None:
        if coverage_rows is not None:
            coverage_rows.append(
                CoverageRow(
                    rec["record_id"],
                    rec["fixture_id"],
                    rec.get("competition_id", ""),
                    rec.get("family", ""),
                    (rec.get("semantics") or {}).get("period"),
                    rec["kickoff_utc"],
                    state,
                    reason,
                    list(sources),
                    outcome,
                )
            )

    for rec in records:
        rid = rec["record_id"]
        ko = parse_iso_utc(rec["kickoff_utc"])
        if rid in already:
            _cov(rec, SettlementState.SETTLED, "already settled")
            continue
        if ko + grace > as_of:
            _cov(rec, SettlementState.PENDING_KICKOFF, "kickoff + grace in the future")
            continue
        cv2 = _close_v2(rec, ko)
        try:
            sem = semantics_from_record(rec)
        except (KeyError, ValueError) as exc:
            _cov(rec, SettlementState.UNSUPPORTED_SETTLEMENT, f"semantics unreadable: {exc}")
            continue
        incomplete = semantics_complete(sem)
        if incomplete:
            _cov(rec, SettlementState.PENDING_EVIDENCE, incomplete)
            continue
        resolution = index.resolve(
            rec["fixture_id"], ko, competition_id=rec.get("competition_id", "")
        )
        if resolution.state is not SettlementState.SETTLED:
            _cov(rec, resolution.state, resolution.reason, resolution.sources)
            continue
        res = resolution.result
        assert res is not None
        official, why = _official_from_result(
            res, et_possible_in_competition=et_possible_for.get(rec.get("competition_id", ""), True)
        )
        if official is None:
            _cov(
                rec,
                SettlementState.PENDING_EVIDENCE,
                why or "insufficient evidence",
                resolution.sources,
            )
            continue
        st = settle(sem, official)
        state, reason = state_for_outcome(st.outcome)
        if state is not SettlementState.SETTLED:
            _cov(rec, state, reason, resolution.sources)
            continue
        _cov(rec, SettlementState.SETTLED, reason, resolution.sources, st.outcome.value)
        close = closes.get(rec["ticker"])
        entry_yes = _dec(rec["market"].get("yes_ask"))
        entry_no = _dec(rec["market"].get("no_ask"))
        close_minutes = (ko - close.captured_at).total_seconds() / 60 if close else None
        ref_at_pred = (rec.get("reference") or {}).get("probability_yes")
        ref_key = _reference_key(rec)
        ref_c = ref_close.get(ref_key) if ref_key else None
        fee_type = (rec.get("fee_regime") or {}).get("fee_type")
        fee_mult = (rec.get("fee_regime") or {}).get("fee_multiplier")
        clv_yes = clv_fields(
            side="yes",
            entry_price=entry_yes,
            close_yes_bid=close.yes_bid if close else None,
            close_yes_ask=close.yes_ask if close else None,
            fee_type=fee_type,
            fee_multiplier=fee_mult,
        )
        clv_no = clv_fields(
            side="no",
            entry_price=entry_no,
            close_yes_bid=close.yes_bid if close else None,
            close_yes_ask=close.yes_ask if close else None,
            fee_type=fee_type,
            fee_multiplier=fee_mult,
        )
        out = {
            "schema": "settlement_record_v1",
            "prediction_record_id": rid,
            "ticker": rec["ticker"],
            "fixture_id": rec["fixture_id"],
            "family": rec["family"],
            "model_family": rec["model_family"],
            "horizon": label_horizon((ko - parse_iso_utc(rec["as_of"])).total_seconds() / 60).value,
            "outcome": st.outcome.value,
            "evidence": {**st.evidence, "result_sources": resolution.sources},
            "fair_probability_mean": rec["probability"]["fair_probability_mean"],
            "fair_probability_low": rec["probability"]["fair_probability_low"],
            "fair_probability_high": rec["probability"]["fair_probability_high"],
            "entry_yes_ask": str(entry_yes) if entry_yes is not None else None,
            "entry_no_ask": str(entry_no) if entry_no is not None else None,
            "entry_yes_mid": _mid(rec["market"]),
            "close_yes_mid": close.yes_mid if close else None,
            "close_captured_at": iso_utc(close.captured_at) if close else None,
            "clv_yes_points": (close.yes_mid - _mid(rec["market"]))
            if (close and close.yes_mid is not None and _mid(rec["market"]) is not None)
            else None,
            "close_class": classify_close(close_minutes).value,
            "close_minutes_before_kickoff": round(close_minutes, 2)
            if close_minutes is not None
            else None,
            "clv": {"yes": clv_yes, "no": clv_no},
            "reference_probability_at_prediction": ref_at_pred,
            "reference_close_probability": ref_c[1] if ref_c else None,
            "reference_close_class": classify_close((ko - ref_c[0]).total_seconds() / 60).value
            if ref_c
            else "NONE",
            "reference_clv_probability_points_yes": (ref_c[1] - ref_at_pred)
            if (ref_c and ref_at_pred is not None)
            else None,
            "recommended": rec.get("recommendation", {}),
            "settled_at": iso_utc(as_of),
            "close_v2": cv2,
        }
        out["clv_model_signed_points"] = model_signed_clv(out)
        settlements.append(out, when=as_of)
        written.append(out)
    if coverage_rows is not None:
        # close completeness over every due record (settled or pending), attached for the coverage report
        if isinstance(coverage_rows, CoverageRows):
            coverage_rows.close_completeness = close_completeness(close_rows)
    return written


def _reference_key(rec: dict[str, Any]) -> tuple[str, str, str, str | None] | None:
    fam, sem = rec.get("family"), rec.get("semantics") or {}
    if fam == "match_result_3way" and sem.get("side"):
        return (rec["fixture_id"], "1x2", sem["side"], None)
    if fam == "total_goals" and sem.get("line"):
        return (rec["fixture_id"], "ou", "over", str(Decimal(sem["line"])))
    return None


def _mid(market: dict[str, Any]) -> float | None:
    return _two_sided_mid(_dec(market.get("yes_bid")), _dec(market.get("yes_ask")))


def model_signed_clv(r: dict[str, Any]) -> float | None:
    """CLV in the direction the model disagreed with the entry market: +1 x YES drift when the model's fair
    exceeded the entry mid, -1 x YES drift when below. Positive = the market moved toward the model.
    (Raw YES drift averaged over all contracts is side-agnostic and cancels across mutually exclusive legs.)"""
    drift, mid, fair = (
        r.get("clv_yes_points"),
        r.get("entry_yes_mid"),
        r.get("fair_probability_mean"),
    )
    if drift is None or mid is None or fair is None or fair == mid:
        return None
    return float(drift) if fair > mid else -float(drift)


def model_health(
    settlements: PredictionLedger, authority: AuthorityMatrix, *, as_of: datetime
) -> tuple[list[ModelHealthV1], dict[str, Any]]:
    cells: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in settlements.iter_records():
        if r.get("outcome") in ("yes", "no"):
            cells[(r["model_family"], r["family"], r["horizon"])].append(r)
            cells[(r["model_family"], r["family"], "any")].append(r)
    rows: list[ModelHealthV1] = []
    proposals: dict[str, Any] = {}
    for (mf, fam, hz), rs in sorted(cells.items()):
        y = np.array([1 if r["outcome"] == "yes" else 0 for r in rs])
        p = np.array([r["fair_probability_mean"] for r in rs])
        lo = np.array([r["fair_probability_low"] for r in rs])
        hi = np.array([r["fair_probability_high"] for r in rs])
        pm = np.array(
            [r["entry_yes_mid"] if r["entry_yes_mid"] is not None else np.nan for r in rs]
        )
        has_m = ~np.isnan(pm)
        signed = [model_signed_clv(r) for r in rs]
        clv = np.array([c for c in signed if c is not None])
        market_ll = log_loss(pm[has_m], y[has_m]) if has_m.sum() >= 10 else None
        ic = (
            interval_calibration(p, lo, hi, y, level=0.8)["weighted_bin_coverage"]
            if len(rs) >= 30
            else None
        )
        key = AuthorityKey(mf, fam, hz)
        current = authority.get(key)
        ev = Evidence(
            len(rs),
            log_loss(p, y),
            market_ll if market_ll is not None else float("inf"),
            float(clv.mean()) if len(clv) else float("-inf"),
            expected_calibration_error(p, y),
            ic,
        )
        proposed, notes = recommend_state(ev, current)
        rows.append(
            ModelHealthV1(
                sport="soccer",
                model_family=mf,
                market_family=fam,
                horizon=hz,
                authority=current.value,  # type: ignore[arg-type]
                n_settled=len(rs),
                brier=round(brier(p, y), 5),
                log_loss=round(log_loss(p, y), 5),
                market_log_loss=round(market_ll, 5) if market_ll is not None else None,
                ece=round(expected_calibration_error(p, y), 4),
                interval_coverage_80=round(ic, 3) if ic is not None else None,
                clv_points_mean=round(float(clv.mean()), 4) if len(clv) else None,
                last_evaluated_at=as_of,
                notes=notes[:6],
            )
        )
        if proposed is not current:
            proposals[key.as_str()] = {
                "current": current.value,
                "proposed": proposed.value,
                "n": len(rs),
            }
    return rows, {
        "as_of": iso_utc(as_of),
        "proposals": proposals,
        "note": "proposals are applied by a human via config/authority.json",
    }


def settlement_v1_rows(written: list[dict[str, Any]]) -> list[SettlementV1]:
    out = []
    for w in written:
        oc = w["outcome"]
        out.append(
            SettlementV1(
                settlement_id=f"stl_{w['prediction_record_id'][5:]}",
                sport="soccer",
                event_id=w["fixture_id"],
                market_ticker=w["ticker"],
                outcome=oc if oc in ("yes", "no", "void") else "refused",  # type: ignore[arg-type]
                refusal_reason=None if oc in ("yes", "no", "void") else oc,
                settled_at=parse_iso_utc(w["settled_at"]),
                evidence=w["evidence"],
            )
        )
    return out


__all__ = ["Authority", "SettlementOutcome", "model_health", "settle_ledger", "settlement_v1_rows"]
