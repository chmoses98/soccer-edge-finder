"""Model board: the cached per-fixture probability distributions that a reprice reuses.

MODEL COMPUTATION writes it (every RUN SOCCER, full or fast, merges its priced fixtures in);
MARKET REPRICING only reads it. One entry per fixture holds what the model knew (versions, parameter
hash, simulation content key, the pricing-input fingerprint used for invalidation, the lineup observation)
and, per Kalshi contract, the fair probability, its interval and 100 quantiles of the per-world
probability distribution. The quantiles are enough to recompute every robust-edge quantity
(P(edge>0), the q0.20 worst case, bet-up-to) against any new executable price without re-simulating.

Published as `runs/latest.model_board.v1.json` (mutable pointer). It is NOT evidence: the immutable
prediction ledger keeps what each model run predicted at its own time.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from soccer_edge.core.serialization import content_hash, read_json_or, write_json
from soccer_edge.core.time import ensure_utc, iso_utc
from soccer_edge.pricing.pricer import PricedProbability

BOARD_FILE = "runs/latest.model_board.v1.json"
BOARD_CONTRACT = "model_board.v1"
QUANTILE_N = 100
QUANTILE_LEVELS = (np.arange(QUANTILE_N) + 0.5) / QUANTILE_N
# a started fixture leaves the board this long after kickoff; any entry older than MAX_ENTRY_AGE leaves too
KEEP_AFTER_KICKOFF = timedelta(hours=1)
MAX_ENTRY_AGE = timedelta(days=7)

# the fields of an entry's pricing inputs that a reprice can re-observe cheaply (invalidation.py)
FINGERPRINT_FIELDS = (
    "kickoff_utc",
    "neutral_site",
    "requires_winner",
    "competition_id",
    "stage",
    "lineup_key",
    "model_family",
    "model_version",
    "parameter_hash",
    "engine_version",
    "worlds_version",
    "n_worlds",
    "draws_per_world",
)


def _dt(v: str | datetime | None) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return ensure_utc(v)
    return ensure_utc(datetime.fromisoformat(v.replace("Z", "+00:00")))


def world_quantiles(world_probs: np.ndarray) -> list[float]:
    """100 mid-quantiles of the per-world probabilities (exact enough for shares at 1 % resolution)."""
    pw = np.asarray(world_probs, dtype=float)
    if pw.size == 0:
        return []
    return [round(float(v), 5) for v in np.quantile(pw, QUANTILE_LEVELS)]


def contract_entry(
    priced: PricedProbability,
    *,
    family: str,
    event_ticker: str | None,
    side: str | None,
    line: Any,
    period: str | None,
    k: int | None = None,
    script: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out = {
        "event_ticker": event_ticker,
        "family": family,
        "side": side,
        "line": None if line is None else str(line),
        "period": period,
        "description": priced.description,
        "p": round(priced.fair_mean, 6),
        "p_low": round(priced.p_low, 6),
        "p_high": round(priced.p_high, 6),
        "interval_level": priced.interval_level,
        "param_sd": round(priced.param_sd, 6),
        "n_worlds": priced.n_worlds,
        "q": world_quantiles(priced.world_probs),
    }
    if k is not None:
        out["k"] = (
            k  # packed exact score / player threshold: lets a reprice rebuild the settlement rule
        )
    if script is not None:
        # P(YES | script) per script in the taxonomy order (gamescript/), its interval, and the exact P(YES)
        # on the script basis (equal to `p` for analytic families; within Monte Carlo error otherwise)
        out["sc"] = script
    return out


def fingerprint(inputs: dict[str, Any]) -> str:
    return content_hash({k: inputs.get(k) for k in FINGERPRINT_FIELDS})


def fixture_entry(
    *,
    fixture_id: str,
    event_name: str,
    competition_id: str,
    competition_name: str | None,
    home: str,
    away: str,
    inputs: dict[str, Any],
    model_generated_at: datetime,
    model_fitted_at: datetime,
    results_observed_at: datetime,
    fixtures_observed_at: datetime,
    source_run_id: str,
    sim_key: str,
    lineup: dict[str, Any] | None,
    summary: dict[str, Any],
    contracts: dict[str, dict[str, Any]],
    scripts: dict[str, Any] | None = None,
    matchup: dict[str, Any] | None = None,
    match_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    keep = (
        "p_home",
        "p_draw",
        "p_away",
        "p_over_2_5",
        "p_btts",
        "mean_home_goals",
        "mean_away_goals",
    )
    return {
        "fixture_id": fixture_id,
        "event_name": event_name,
        "competition_id": competition_id,
        "competition_name": competition_name,
        "home": home,
        "away": away,
        "inputs": inputs,
        "input_fingerprint": fingerprint(inputs),
        "model_generated_at": iso_utc(model_generated_at),
        "model_fitted_at": iso_utc(model_fitted_at),
        "results_observed_at": iso_utc(results_observed_at),
        "fixtures_observed_at": iso_utc(fixtures_observed_at),
        "source_run_id": source_run_id,
        "sim_key": sim_key,
        "lineup": lineup,
        "summary": {k: summary[k] for k in keep if k in summary},
        "contracts": contracts,
        # model-time intelligence for the script engine / SIFT (all market-blind; docs/GAME_SCRIPTS.md)
        "scripts": scripts,
        "matchup": matchup,
        "match_context": match_context,
    }


def empty_board() -> dict[str, Any]:
    return {
        "contract": BOARD_CONTRACT,
        "generated_at": None,
        "quantile_levels": f"(i + 0.5) / {QUANTILE_N}, i = 0..{QUANTILE_N - 1}",
        "fixtures": {},
    }


def merge_boards(*boards: dict[str, Any] | None, now: datetime) -> dict[str, Any]:
    """Union by fixture; the entry with the later model_generated_at wins (ties: the later argument).
    Fixtures that kicked off more than KEEP_AFTER_KICKOFF ago and entries older than MAX_ENTRY_AGE drop.
    Deterministic and order-safe, so concurrent writers (run-soccer, the kickoff chain, a manual refresh)
    can each merge onto whatever the archive holds without losing each other's fixtures."""
    now = ensure_utc(now)
    out = empty_board()
    for b in boards:
        if not b:
            continue
        for fid, e in (b.get("fixtures") or {}).items():
            cur = out["fixtures"].get(fid)
            if cur is None:
                out["fixtures"][fid] = e
                continue
            newer, older = (
                (e, cur)
                if _dt(e["model_generated_at"]) >= _dt(cur["model_generated_at"])
                else (cur, e)
            )
            out["fixtures"][fid] = carry_lineup_history(newer, older)
    for fid in list(out["fixtures"]):
        e = out["fixtures"][fid]
        ko = _dt(e["inputs"].get("kickoff_utc"))
        gen = _dt(e["model_generated_at"])
        if (ko is not None and ko < now - KEEP_AFTER_KICKOFF) or (
            gen and gen < now - MAX_ENTRY_AGE
        ):
            del out["fixtures"][fid]
    gens = [_dt(e["model_generated_at"]) for e in out["fixtures"].values()]
    out["generated_at"] = iso_utc(max(gens)) if gens else None
    out["fixtures"] = dict(sorted(out["fixtures"].items()))
    return out


LINEUP_HISTORY_MAX = 4


def model_snapshot(e: dict[str, Any]) -> dict[str, Any]:
    """The pricing state of one board entry, small enough to keep as history (lineup re-scripting)."""
    sc = e.get("scripts") or {}
    snap = {
        "model_generated_at": e.get("model_generated_at"),
        "lineup_key": (e.get("inputs") or {}).get("lineup_key"),
        "lineup_state": (e.get("lineup") or {}).get("state"),
        "sim_key": e.get("sim_key"),
        "summary": e.get("summary"),
    }
    if sc.get("status") == "OK":
        snap["scripts"] = {
            "taxonomy_version": sc.get("taxonomy_version"),
            "shares": sc.get("shares"),
            "primary": sc.get("primary"),
            "secondary": sc.get("secondary"),
        }
    return snap


def carry_lineup_history(newer: dict[str, Any], older: dict[str, Any]) -> dict[str, Any]:
    """When a fixture's lineup input changed between two model states, keep the earlier state(s) on the newer
    entry as `lineup_history` (oldest first) so a reader can show pre-lineup vs current scripts. Only genuine
    model states are kept - nothing is reconstructed. Deterministic and order-safe like the merge itself."""
    if newer is older:
        return newer
    hist = list(older.get("lineup_history") or [])
    for h in newer.get("lineup_history") or []:
        if h not in hist:
            hist.append(h)
    new_key = (newer.get("inputs") or {}).get("lineup_key")
    old_key = (older.get("inputs") or {}).get("lineup_key")
    if new_key != old_key:
        snap = model_snapshot(older)
        if snap not in hist:
            hist.append(snap)
    hist = sorted(hist, key=lambda h: h.get("model_generated_at") or "")
    hist = [h for h in hist if h.get("model_generated_at") != newer.get("model_generated_at")]
    if not hist:
        return newer
    return {**newer, "lineup_history": hist[-LINEUP_HISTORY_MAX:]}


def load_board(*paths: Path, now: datetime) -> dict[str, Any]:
    return merge_boards(*(read_json_or(p, None) for p in paths if p is not None), now=now)


def save_board(path: Path, board: dict[str, Any]) -> None:
    write_json(path, board)


def priced_from_entry(ticker: str, c: dict[str, Any]) -> PricedProbability:
    """Rebuild a PricedProbability from a board contract: the 100 quantiles stand in for the worlds."""
    q = np.asarray(c.get("q") or [c["p"]], dtype=float)
    return PricedProbability(
        ticker=ticker,
        fair_mean=float(c["p"]),
        fair_median=float(np.median(q)),
        p_low=float(c["p_low"]),
        p_high=float(c["p_high"]),
        interval_level=float(c.get("interval_level", 0.8)),
        param_sd=float(c.get("param_sd", 0.0)),
        mc_se=0.0,
        n_worlds=int(c.get("n_worlds", q.size)),
        n_draws=0,
        effective_draws=0,
        world_probs=q,
        description=c.get("description", ""),
    )
