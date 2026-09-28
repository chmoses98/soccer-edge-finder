"""Replay selection policies against the immutable prediction archive + settlements.

Inputs are the archived records only (never re-simulated), so historical predictions are not
rewritten. Output: per policy, per (family, horizon) counts and flat-unit realised outcomes, with
the MODEL (model_family + parameter hash set), SELECTION (policy hash) and STAKING (policy hash)
identities recorded so that every number is attributable to a layer version.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import numpy as np

from soccer_edge.policy.versions import STAKING_DISABLED, SelectionPolicy, StakingPolicy


@dataclass
class ReplayCell:
    n_candidates: int = 0
    n_selected: int = 0
    n_settled: int = 0
    n_won: int = 0
    n_void: int = 0
    pnl_units: float = 0.0  # flat 1-contract, fee-inclusive, per settled selection
    stake_units: float = 0.0
    clv_prob_points: list[float] = field(default_factory=list)
    rejection_reasons: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def to_json(self) -> dict[str, Any]:
        clv = np.array(self.clv_prob_points) if self.clv_prob_points else np.array([])
        return {
            "n_candidates": self.n_candidates,
            "n_selected": self.n_selected,
            "n_settled": self.n_settled,
            "n_won": self.n_won,
            "n_void": self.n_void,
            "hit_rate": round(self.n_won / (self.n_settled - self.n_void), 4)
            if self.n_settled - self.n_void
            else None,
            "pnl_units": round(self.pnl_units, 4),
            "roi": round(self.pnl_units / self.stake_units, 4) if self.stake_units else None,
            "clv_mean_prob_points": round(float(clv.mean()), 5) if clv.size else None,
            "clv_n": int(clv.size),
            "rejection_reasons": dict(sorted(self.rejection_reasons.items())),
        }


def _settle_pnl(
    side: str, price: Decimal, fee: Decimal, outcome: str
) -> tuple[float, float] | None:
    """Flat one-contract P&L in dollars for a taker fill at `price` + `fee`. None for void/refused."""
    if outcome == "void":
        return 0.0, 0.0
    if outcome not in ("yes", "no"):
        return None
    won = outcome == side
    stake = float(price + fee)
    pnl = (1.0 - float(price) - float(fee)) if won else -stake
    return pnl, stake


def _liquidity(v: Any) -> float:
    """Depth field of an archived record: a number, null, or the string "None" (records written
    before 2026-09-28 stringified missing depth); anything unparsable counts as no depth."""
    if v is None or v in ("None", ""):
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def replay(
    records: list[dict[str, Any]],
    settlements: dict[str, dict[str, Any]],
    policies: tuple[SelectionPolicy, ...],
    staking: StakingPolicy = STAKING_DISABLED,
) -> dict[str, Any]:
    """records: prediction_record_v1 dicts; settlements: prediction_record_id -> settlement dict."""
    model_ids: set[str] = set()
    param_hashes: set[str] = set()
    out: dict[str, Any] = {
        "schema": "policy_replay_v1",
        "policies": {},
        "staking": {
            "version": staking.version,
            "mode": staking.mode,
            "hash": staking.policy_hash(),
        },
    }
    for pol in policies:
        cells: dict[str, ReplayCell] = defaultdict(ReplayCell)
        total = ReplayCell()
        for rec in records:
            model_ids.add(rec.get("model_family", "?"))
            if rec.get("parameter_hash"):
                param_hashes.add(rec["parameter_hash"])
            fam = rec.get("family", "?")
            st = settlements.get(rec.get("record_id"))
            horizon = st["horizon"] if st and st.get("horizon") else rec.get("horizon", "?")
            key = f"{fam}|{horizon}"
            for side in ("yes", "no"):
                edge = (rec.get("edge") or {}).get(side)
                if not edge:
                    continue
                liq_key = "yes_ask_size" if side == "yes" else "no_ask_size"
                liq = _liquidity((rec.get("market") or {}).get(liq_key))
                for cell in (cells[key], total):
                    cell.n_candidates += 1
                ok, reasons = pol.selects(edge, family=fam, horizon=horizon, liquidity=liq)
                if not ok:
                    for cell in (cells[key], total):
                        for r in reasons:
                            cell.rejection_reasons[r] += 1
                    continue
                for cell in (cells[key], total):
                    cell.n_selected += 1
                if st is None or st.get("outcome") in (None, "refused"):
                    continue
                res = _settle_pnl(
                    side,
                    Decimal(str(edge["price"])),
                    Decimal(str(edge.get("fee_per_contract") or "0")),
                    st["outcome"],
                )
                if res is None:
                    continue
                pnl, stake = res
                clv = ((st.get("clv") or {}).get(side) or {}).get("clv_probability_points")
                for cell in (cells[key], total):
                    cell.n_settled += 1
                    if st["outcome"] == "void":
                        cell.n_void += 1
                    elif st["outcome"] == side:
                        cell.n_won += 1
                    cell.pnl_units += pnl
                    cell.stake_units += stake
                    if clv is not None:
                        cell.clv_prob_points.append(float(clv))
        out["policies"][pol.version] = {
            "hash": pol.policy_hash(),
            "description": pol.description,
            "total": total.to_json(),
            "by_family_horizon": {k: v.to_json() for k, v in sorted(cells.items())},
        }
    out["model"] = {"families": sorted(model_ids), "parameter_hash_count": len(param_hashes)}
    out["n_records"] = len(records)
    out["n_settled_records"] = sum(1 for r in records if r.get("record_id") in settlements)
    out["note"] = (
        "flat 1-contract taker accounting for comparison only; staking is DISABLED in production; no historical record was modified"
    )
    return out
