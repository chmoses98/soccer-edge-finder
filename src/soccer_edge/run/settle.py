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
from soccer_edge.kalshi.taxonomy import MarketFamily, Period
from soccer_edge.pricing.semantics import Semantics
from soccer_edge.providers.interfaces import MatchResult
from soccer_edge.settlement.engine import OfficialResult, SettlementOutcome, settle


@dataclass
class CloseQuote:
    captured_at: datetime
    yes_bid: Decimal | None
    yes_ask: Decimal | None
    no_ask: Decimal | None

    @property
    def yes_mid(self) -> float | None:
        if self.yes_bid is None or self.yes_ask is None:
            return None
        return float((self.yes_bid + self.yes_ask) / 2)


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


def _dec(v: Any) -> Decimal | None:
    return None if v in (None, "", "None") else Decimal(str(v))


def semantics_from_record(rec: dict[str, Any]) -> Semantics:
    s = rec["semantics"]
    return Semantics(
        rec["ticker"],
        MarketFamily(rec["family"]),
        Period(s["period"]),
        s.get("side"),
        Decimal(s["line"]) if s.get("line") else None,
        None,
        None,
        s.get("description", ""),
    )


def official_from_result(r: MatchResult) -> OfficialResult:
    return OfficialResult(
        r.fixture_id,
        FixtureStatus.FINISHED,
        r.home_goals,
        r.away_goals,
        r.home_goals_ht,
        r.away_goals_ht,
        source="openfootball",
    )


def settle_ledger(
    ledger: PredictionLedger,
    results: dict[str, MatchResult],
    snapshots_dir: Path,
    settlements: PredictionLedger,
    *,
    as_of: datetime,
    grace: timedelta = timedelta(hours=3),
) -> list[dict[str, Any]]:
    already = {r["prediction_record_id"] for r in settlements.iter_records()}
    records = [r for r in ledger.iter_records() if r.get("schema") == "prediction_record_v1"]
    kickoff_by_ticker = {r["ticker"]: parse_iso_utc(r["kickoff_utc"]) for r in records}
    closes = load_close_quotes(snapshots_dir, kickoff_by_ticker)
    written: list[dict[str, Any]] = []
    for rec in records:
        rid = rec["record_id"]
        if rid in already:
            continue
        ko = parse_iso_utc(rec["kickoff_utc"])
        if ko + grace > as_of:
            continue
        res = results.get(rec["fixture_id"])
        if res is None:
            continue
        sem = semantics_from_record(rec)
        st = settle(sem, official_from_result(res))
        close = closes.get(rec["ticker"])
        entry_yes = _dec(rec["market"].get("yes_ask"))
        entry_no = _dec(rec["market"].get("no_ask"))
        out = {
            "schema": "settlement_record_v1",
            "prediction_record_id": rid,
            "ticker": rec["ticker"],
            "fixture_id": rec["fixture_id"],
            "family": rec["family"],
            "model_family": rec["model_family"],
            "horizon": label_horizon((ko - parse_iso_utc(rec["as_of"])).total_seconds() / 60).value,
            "outcome": st.outcome.value,
            "evidence": st.evidence,
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
            "recommended": rec.get("recommendation", {}),
            "settled_at": iso_utc(as_of),
        }
        settlements.append(out, when=as_of)
        written.append(out)
    return written


def _mid(market: dict[str, Any]) -> float | None:
    yb, ya = _dec(market.get("yes_bid")), _dec(market.get("yes_ask"))
    if yb is None or ya is None:
        return None
    return float((yb + ya) / 2)


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
        clv = np.array([r["clv_yes_points"] for r in rs if r["clv_yes_points"] is not None])
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
