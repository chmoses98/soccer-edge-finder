"""Lightweight repricing: cached fixture distributions x fresh Kalshi executable prices -> actionable slate.

    model board (cached probabilities, never recomputed here)
      -> latest Kalshi sweep (executable asks, sizes, fee regimes)
      -> fees -> every cached contract, both sides
      -> fee-adjusted EV, robust (q0.20) edge, bet-up-to, reference-anchored EV (stored Pinnacle rows)
      -> production selection policy -> best expression per fixture x family
      -> freshness per input + action per contract side

What this module never does: fit a model, simulate, call The Odds API or any other network endpoint,
change authority, write the prediction ledger, or place anything. Its output is the mutable latest-state
slate; the immutable prospective ledger is written only by model runs.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from soccer_edge.authority.policy import Authority, AuthorityKey, AuthorityMatrix
from soccer_edge.contracts.slate_v1 import (
    ActionableSlateV1,
    InputFreshnessV1,
    SlateComputeV1,
    SlateContractV1,
    SlateFixtureV1,
    SlateLineupStateV1,
    SlateModelStateV1,
    SlateReferenceStateV1,
)
from soccer_edge.core.serialization import append_jsonl, content_hash, read_json_or, write_json
from soccer_edge.core.time import ensure_utc, iso_utc
from soccer_edge.kalshi.capture import label_horizon
from soccer_edge.kalshi.executable import top_of_book
from soccer_edge.policy.versions import SELECTION_V2, SelectionPolicy
from soccer_edge.pricing.edge import EdgeConfig, assess
from soccer_edge.pricing.edge_v2 import EdgeV2Config, assess_v2
from soccer_edge.reference.capture import reference_for_contract
from soccer_edge.run.pipeline import INTL_POOL_COMPETITIONS
from soccer_edge.slate.board import priced_from_entry
from soccer_edge.slate.freshness import SlateFreshnessPolicy, classify
from soccer_edge.slate.invalidation import current_kickoff, invalidation_reasons
from soccer_edge.slate.market_view import MarketView
from soccer_edge.slate.observations import (
    FixtureContext,
    LineupObservation,
    fixture_context,
    lineup_observations,
    pinnacle_rows,
)

SLATE_FILE = "runs/latest.actionable_slate.v1.json"
SLATE_MD = "runs/LATEST_ACTIONABLE_SLATE.md"
SLATE_LOG_DIR = "dispatch/slate_log"
DEFAULT_LOOKAHEAD_HOURS = 48.0
ACTION_ORDER = (
    "ACTIONABLE",
    "RESEARCH_CANDIDATE",
    "NO_EDGE",
    "EXCLUDED_BY_GATE",
    "STALE_PRICE",
    "MODEL_INVALIDATED",
    "MODEL_STALE",
    "FEE_UNVERIFIED",
    "NO_QUOTE",
)
CLOSED_STATUSES = (
    "closed",
    "finalized",
    "settled",
    "determined",
    "paused",
    "unopened",
    "initialized",
)

CONSUMER_RULE = (
    "Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). "
    "Recompute at READ time: a price is CURRENT only before its `action_valid_until` "
    "(= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER "
    "SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, "
    "so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from "
    "another file or another time."
)


@dataclass
class RepriceContext:
    """Everything a reprice reads. All of it is local data; nothing here can make a network call."""

    board: dict[str, Any]
    view: MarketView | None
    roots: list[Path]
    now: datetime
    trigger: str
    lookahead_hours: float = DEFAULT_LOOKAHEAD_HOURS
    versions: dict[str, str] | None = None
    policy: SlateFreshnessPolicy = field(default_factory=SlateFreshnessPolicy)
    authority: AuthorityMatrix = field(default_factory=AuthorityMatrix)
    selection: SelectionPolicy = SELECTION_V2
    edge_cfg: EdgeConfig = field(default_factory=EdgeConfig)
    edge_v2_cfg: EdgeV2Config = field(default_factory=EdgeV2Config)
    intl_shadows_enabled: bool = False
    compute: dict[str, Any] = field(default_factory=dict)


def _dt(v: Any) -> datetime | None:
    if not v:
        return None
    if isinstance(v, datetime):
        return ensure_utc(v)
    return ensure_utc(datetime.fromisoformat(str(v).replace("Z", "+00:00")))


def _side(p: float | None, side: str) -> float | None:
    if p is None:
        return None
    return p if side == "yes" else 1.0 - p


def _ref_for(
    rows: dict, fid: str, family: str, sem_side: str | None, line: Decimal | None
) -> tuple[float | None, list[dict]]:
    """(YES-side reference probability, the Pinnacle rows it came from) for one cached contract."""
    probs = {k: r["devigged_probability"] for k, r in rows.items() if k[0] == fid}
    if not probs:
        return None, []
    p = reference_for_contract(probs, fid, family, sem_side, line)
    if p is None:
        return None, []
    if family == "double_chance":
        used = [rows.get((fid, "1x2", s, None)) for s in ("home", "draw", "away")]
    elif family == "match_result_3way":
        used = [rows.get((fid, "1x2", sem_side, None))]
    elif family == "total_goals":
        used = [rows.get((fid, "ou", "over", line))]
    else:
        used = [rows.get((fid, "ah", sem_side, line))]
    return p, [u for u in used if u]


def _ref_role(minutes_to_kickoff: Any) -> str:
    try:
        m = float(minutes_to_kickoff)
    except (TypeError, ValueError):
        return "other"
    if m <= 15:
        return "close"
    if m <= 66:
        return "entry"
    return "other"


def _name_from_id(fid: str) -> str:
    parts = fid.split(":")
    if len(parts) >= 5:
        return f"{parts[3]} vs {parts[4]}"
    return fid


def reprice(rc: RepriceContext) -> ActionableSlateV1:
    t0 = time.perf_counter()
    now = ensure_utc(rc.now)
    pol = rc.policy
    ctx: FixtureContext = fixture_context(rc.roots)
    lineups: dict[str, LineupObservation] = lineup_observations(
        rc.roots, ctx.espn_event_ids, now=now
    )
    ref_rows = pinnacle_rows(rc.roots, now=now)
    view = rc.view
    kal = (
        classify(view.observed_at, now, pol.kalshi, detail=f"sweep {view.run_id}")
        if view is not None
        else InputFreshnessV1(status="UNAVAILABLE", detail="no Kalshi sweep available")
    )
    horizon_end = now + timedelta(hours=rc.lookahead_hours)
    fixtures_out: list[SlateFixtureV1] = []
    contracts_out: list[SlateContractV1] = []
    removed: list[str] = []
    warnings: list[str] = []
    if view is not None and not view.complete:
        warnings.append(
            "Kalshi sweep incomplete: contracts absent from it are UNAVAILABLE, not closed"
        )
    entries = sorted(
        (rc.board.get("fixtures") or {}).values(),
        key=lambda e: (e["inputs"].get("kickoff_utc") or "", e["fixture_id"]),
    )
    for e in entries:
        fid = e["fixture_id"]
        ko = current_kickoff(e, ctx)
        if ko is None:
            continue
        if ko <= now:
            removed.append(fid)
            continue
        if ko > horizon_end:
            continue
        lu = lineups.get(fid)
        reasons = invalidation_reasons(e, ctx=ctx, lineup=lu, versions=rc.versions)
        validity = "INVALIDATED" if reasons else "VALID"
        model_fr = classify(_dt(e["model_generated_at"]), now, pol.model)
        ctx_obs = max(
            (t for t in (ctx.as_of, _dt(e.get("fixtures_observed_at"))) if t is not None),
            default=None,
        )
        context_fr = classify(ctx_obs, now, pol.context)
        lineup_fr = classify(lu.checked_at if lu else None, now, pol.lineup)
        fx_rows = [r for k, r in ref_rows.items() if k[0] == fid]
        ref_obs = max((_dt(r["captured_at"]) for r in fx_rows), default=None)
        latest_ref = max(fx_rows, key=lambda r: r["captured_at"]) if fx_rows else None
        ref_fr = classify(ref_obs, now, pol.reference)
        inp = e["inputs"]
        mins = (ko - now).total_seconds() / 60
        horizon = label_horizon(mins).value
        model_family = inp.get("model_family") or "?"
        fr_map = {
            "model": model_fr.status if validity == "VALID" else "STALE",
            "kalshi": kal.status,
            "reference": ref_fr.status,
            "lineup": lineup_fr.status,
            "context": context_fr.status,
        }
        fx_contracts: list[SlateContractV1] = []
        board_tickers = set(e["contracts"])
        for ticker, c in sorted(e["contracts"].items()):
            m = view.markets.get(ticker) if view is not None else None
            regime = view.regime(m) if (view is not None and m is not None) else None
            priced = priced_from_entry(ticker, c)
            line = Decimal(c["line"]) if c.get("line") is not None else None
            p_ref_yes, used_rows = _ref_for(ref_rows, fid, c["family"], c.get("side"), line)
            ref_at = min((_dt(r["captured_at"]) for r in used_rows), default=None)
            ref_c = classify(ref_at, now, pol.reference)
            ref_age = ref_c.age_minutes_at_publish
            ref_quality = "SHARP_REFERENCE" if p_ref_yes is not None else "UNAVAILABLE"
            for side in ("yes", "no"):
                quote = top_of_book(m, side) if m is not None else None
                quoted = bool(
                    quote is not None
                    and quote.is_quote
                    and str(m.status).lower() not in CLOSED_STATUSES  # type: ignore[union-attr]
                )
                ea = assess(priced, quote, regime, rc.edge_cfg) if (quoted and regime) else None
                p_ref = _side(p_ref_yes, side)
                v2 = (
                    assess_v2(
                        ticker=ticker,
                        side=side,
                        family=c["family"],
                        p_model=_side(priced.fair_mean, side),
                        p_ref=p_ref,
                        reference_quality=ref_quality,
                        reference_age_minutes=ref_age,
                        quote=quote,
                        regime=regime,
                        cfg=rc.edge_v2_cfg,
                    )
                    if (quoted and regime)
                    else None
                )
                auth = rc.authority.get(AuthorityKey(model_family, c["family"], horizon))
                action, why = _action(
                    rc,
                    quoted=quoted,
                    market=m,
                    regime=regime,
                    validity=validity,
                    reasons=reasons,
                    model_status=model_fr.status,
                    kalshi_status=kal.status,
                    ea=ea,
                    liquidity=float(quote.size or 0) if quoted else 0.0,
                    family=c["family"],
                    horizon=horizon,
                    competition=e["competition_id"],
                    authority=auth,
                    complete=bool(view and view.complete),
                )
                p_side = _side(priced.fair_mean, side)
                lo = priced.p_low if side == "yes" else 1 - priced.p_high
                hi = priced.p_high if side == "yes" else 1 - priced.p_low
                fx_contracts.append(
                    SlateContractV1(
                        fixture_id=fid,
                        event_name=e["event_name"],
                        competition=e["competition_id"],
                        kickoff=ko,
                        market_family=c["family"],
                        market_description=c.get("description") or ticker,
                        ticker=ticker,
                        event_ticker=c.get("event_ticker"),
                        side=side,  # type: ignore[arg-type]
                        model_probability=round(float(p_side), 6),
                        model_probability_low=round(float(lo), 6),
                        model_probability_high=round(float(hi), 6),
                        model_family=model_family,
                        model_version=inp.get("model_version") or "?",
                        model_generated_at=_dt(e["model_generated_at"]),
                        kalshi_price=quote.price if quoted else None,
                        kalshi_yes_bid=m.yes_bid if m is not None else None,
                        kalshi_yes_ask=m.yes_ask if m is not None else None,
                        kalshi_no_bid=m.no_bid if m is not None else None,
                        kalshi_no_ask=m.no_ask if m is not None else None,
                        kalshi_observed_at=view.observed_at if m is not None else None,
                        available_size=quote.size if quoted else None,
                        breakeven_price=ea.breakeven if ea else None,
                        fee_per_contract=ea.fee_per_contract if ea else None,
                        reference_probability=None if p_ref is None else round(p_ref, 6),
                        reference_quality=ref_quality,
                        reference_observed_at=ref_at,
                        reference_freshness=ref_c.status,
                        fee_adjusted_ev=None if ea is None else round(ea.fee_adjusted_edge, 6),
                        worst_case_edge=None if ea is None else round(ea.worst_case_edge, 6),
                        model_posterior_edge_share=None
                        if ea is None
                        else round(ea.p_edge_positive, 4),
                        reference_anchored_ev=(
                            round(v2.expected_net_ev, 6)
                            if v2 is not None and v2.expected_net_ev is not None
                            else None
                        ),
                        reference_anchored_ev_lower=(
                            round(v2.ev_lower, 6)
                            if v2 is not None and v2.ev_lower is not None
                            else None
                        ),
                        bet_up_to_price=ea.bet_up_to_price if ea else None,
                        lineup_status=lu.state if lu else "unknown",
                        lineup_observed_at=lu.last_change_at if lu else None,
                        context_observed_at=ctx_obs,
                        authority=auth.value,  # type: ignore[arg-type]
                        research_status=_research_status(auth),
                        bet_permitted=action == "ACTIONABLE",
                        action=action,  # type: ignore[arg-type]
                        action_reasons=why,
                        action_valid_until=kal.current_until,
                        freshness=fr_map,  # type: ignore[arg-type]
                    )
                )
        best = _best_expressions(fx_contracts)
        fx_contracts = [
            c.model_copy(update={"best_expression": f"{c.ticker}|{c.side}" in best})
            for c in fx_contracts
        ]
        contracts_out.extend(fx_contracts)
        events = {c.get("event_ticker") for c in e["contracts"].values() if c.get("event_ticker")}
        unmodelled = (
            {t for ev in events for t in view.tickers_by_event.get(ev, ())} - board_tickers
            if view is not None
            else set()
        )
        fixtures_out.append(
            SlateFixtureV1(
                fixture_id=fid,
                event_name=e["event_name"],
                competition=e["competition_id"],
                competition_name=e.get("competition_name"),
                kickoff=ko,
                minutes_to_kickoff_at_publish=round(mins, 1),
                model=SlateModelStateV1(
                    validity=validity,  # type: ignore[arg-type]
                    invalidation_reasons=reasons,
                    model_family=model_family,
                    model_version=inp.get("model_version"),
                    engine_version=inp.get("engine_version"),
                    worlds_version=inp.get("worlds_version"),
                    parameter_hash=inp.get("parameter_hash"),
                    sim_key=e.get("sim_key"),
                    source_run_id=e.get("source_run_id"),
                    freshness=model_fr,
                ),
                lineup=SlateLineupStateV1(
                    status=(lu.state if lu else "unknown"),  # type: ignore[arg-type]
                    last_change_at=lu.last_change_at if lu else None,
                    freshness=lineup_fr,
                ),
                context=context_fr,
                reference=SlateReferenceStateV1(
                    bookmaker="pinnacle" if fx_rows else None,
                    quality="SHARP_REFERENCE" if fx_rows else "UNAVAILABLE",
                    role=_ref_role(latest_ref.get("minutes_to_kickoff")) if latest_ref else None,
                    quoted_at=_dt(latest_ref.get("quoted_at")) if latest_ref else None,
                    freshness=ref_fr,
                ),
                contracts_priced=len(board_tickers),
                contracts_without_model=len(unmodelled),
                best_expressions=sorted(best),
            )
        )
    # fixtures with Kalshi markets that the board has no model for (new listing, or out of the last window)
    board_ids = set((rc.board.get("fixtures") or {}).keys())
    for fid, row in sorted(ctx.schedule.items()):
        if fid in board_ids or row.get("source") != "run_output":
            continue
        ko = _dt(row.get("kickoff_utc"))
        if ko is None or not (now < ko <= horizon_end):
            continue
        fixtures_out.append(
            SlateFixtureV1(
                fixture_id=fid,
                event_name=_name_from_id(fid),
                competition=row.get("competition_id") or "?",
                kickoff=ko,
                minutes_to_kickoff_at_publish=round((ko - now).total_seconds() / 60, 1),
                model=SlateModelStateV1(
                    validity="MISSING",
                    invalidation_reasons=[
                        "no cached model for this fixture: awaiting model refresh"
                    ],
                    freshness=InputFreshnessV1(status="UNAVAILABLE"),
                ),
                lineup=SlateLineupStateV1(
                    status="unknown", freshness=InputFreshnessV1(status="UNAVAILABLE")
                ),
                context=classify(ctx.as_of, now, pol.context),
                reference=SlateReferenceStateV1(freshness=InputFreshnessV1(status="UNAVAILABLE")),
                contracts_without_model=int(row.get("markets_discovered") or 0),
            )
        )
    fixtures_out.sort(key=lambda f: (f.kickoff, f.fixture_id))
    # candidates first (a reader of the top of the file sees what matters), then by kickoff and fixture
    contracts_out.sort(
        key=lambda c: (ACTION_ORDER.index(c.action), c.kickoff, c.fixture_id, c.ticker, c.side)
    )
    counts: dict[str, int] = {
        "fixtures": len(fixtures_out),
        "contract_sides": len(contracts_out),
        "fixtures_model_invalidated": sum(f.model.validity == "INVALIDATED" for f in fixtures_out),
        "fixtures_model_missing": sum(f.model.validity == "MISSING" for f in fixtures_out),
    }
    for c in contracts_out:
        counts[f"action_{c.action}"] = counts.get(f"action_{c.action}", 0) + 1
    comp = dict(rc.compute)
    comp.setdefault("mode", "reprice_only")
    comp.setdefault("trigger", rc.trigger)
    comp["reprice_runtime_s"] = round(time.perf_counter() - t0, 3)
    actionable = [c for c in contracts_out if c.action == "ACTIONABLE"]
    slate_id = "slate-{:%Y%m%dT%H%M%SZ}-{}".format(
        now,
        content_hash({"k": view.run_id if view else None, "b": rc.board.get("generated_at")})[7:13],
    )
    return ActionableSlateV1(
        slate_id=slate_id,
        generated_at=now,
        lookahead_hours=rc.lookahead_hours,
        consumer_rule=CONSUMER_RULE,
        freshness_policy=pol.to_contract(),
        kalshi=kal,
        kalshi_discovery_run_id=view.run_id if view else None,
        kalshi_discovery_complete=bool(view and view.complete),
        actionable_until=kal.current_until,
        model_board_generated_at=_dt(rc.board.get("generated_at")),
        authority_summary=(
            "every model family x market family x horizon is RESEARCH_ONLY: no contract side is "
            "bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only"
            if not actionable
            else f"{len(actionable)} contract sides under LIMITED/TRUSTED authority"
        ),
        no_bets=not actionable,
        compute=SlateComputeV1(**comp),
        counts=counts,
        fixtures=fixtures_out,
        contracts=contracts_out,
        removed_started=sorted(removed),
        warnings=warnings,
    )


def _research_status(auth: Authority) -> str:
    if auth in (Authority.LIMITED, Authority.TRUSTED):
        return f"{auth.value}: bets permitted when every gate passes"
    return f"{auth.value}: shadow / research only, never a bet"


def _action(
    rc: RepriceContext,
    *,
    quoted: bool,
    market: Any,
    regime: Any,
    validity: str,
    reasons: list[str],
    model_status: str,
    kalshi_status: str,
    ea: Any,
    liquidity: float,
    family: str,
    horizon: str,
    competition: str,
    authority: Authority,
    complete: bool,
) -> tuple[str, list[str]]:
    if market is None:
        return "NO_QUOTE", ["contract absent from the latest Kalshi sweep (not open / not swept)"]
    if not quoted:
        return "NO_QUOTE", [f"no executable ask (market status {market.status})"]
    if regime is None:
        return "FEE_UNVERIFIED", ["series fee regime missing or not verified"]
    if validity != "VALID":
        return "MODEL_INVALIDATED", reasons
    if model_status == "STALE":
        return "MODEL_STALE", ["cached model probability older than the model freshness limit"]
    if kalshi_status != "CURRENT":
        return "STALE_PRICE", [f"Kalshi price {kalshi_status}: NO ACTION until a fresh capture"]
    selected, why = rc.selection.selects(
        ea.to_json(), family=family, horizon=horizon, liquidity=liquidity
    )
    if not selected:
        return "NO_EDGE", why
    if not rc.intl_shadows_enabled and competition in INTL_POOL_COMPETITIONS:
        return "EXCLUDED_BY_GATE", ["intl_pool_not_validated (audit §E6)"]
    if authority in (Authority.LIMITED, Authority.TRUSTED) and complete:
        return "ACTIONABLE", []
    return "RESEARCH_CANDIDATE", [f"authority {authority.value}: no bet"]


def _best_expressions(contracts: list[SlateContractV1]) -> set[str]:
    """Per fixture x market family, the candidate side with the largest robust (worst-case) edge. The
    draw-level correlation reducer needs joint simulation draws and runs only inside model refreshes."""
    best: dict[str, SlateContractV1] = {}
    for c in contracts:
        if c.action not in ("ACTIONABLE", "RESEARCH_CANDIDATE") or c.worst_case_edge is None:
            continue
        cur = best.get(c.market_family)
        if cur is None or c.worst_case_edge > (cur.worst_case_edge or -1):
            best[c.market_family] = c
    return {f"{c.ticker}|{c.side}" for c in best.values()}


# ------------------------------------------------------------------------------------------- output


def price_changes(prev: dict[str, Any] | None, slate: ActionableSlateV1) -> list[dict[str, Any]]:
    if not prev:
        return []
    old = {(c["ticker"], c["side"]): c.get("kalshi_price") for c in prev.get("contracts", [])}
    out = []
    for c in slate.contracts:
        k = (c.ticker, c.side)
        if k in old and old[k] != (None if c.kalshi_price is None else str(c.kalshi_price)):
            out.append(
                {
                    "fixture_id": c.fixture_id,
                    "ticker": c.ticker,
                    "side": c.side,
                    "old": old[k],
                    "new": None if c.kalshi_price is None else str(c.kalshi_price),
                }
            )
    return out


def write_slate(
    out_root: Path, slate: ActionableSlateV1, *, prev: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Write the latest slate + its markdown, append one reprice-log row (dispatch/slate_log/<day>.jsonl)."""
    from soccer_edge.slate.render import render_slate_markdown

    doc = slate.model_dump(mode="json")
    write_json(out_root / SLATE_FILE, doc)
    (out_root / SLATE_MD).write_text(render_slate_markdown(slate), encoding="utf-8")
    changes = price_changes(prev, slate)
    row = {
        "slate_id": slate.slate_id,
        "generated_at": iso_utc(slate.generated_at),
        "trigger": slate.compute.trigger,
        "mode": slate.compute.mode,
        "kalshi_observed_at": iso_utc(slate.kalshi.observed_at)
        if slate.kalshi.observed_at
        else None,
        "kalshi_run_id": slate.kalshi_discovery_run_id,
        "model_board_generated_at": iso_utc(slate.model_board_generated_at)
        if slate.model_board_generated_at
        else None,
        "fixtures": slate.counts.get("fixtures", 0),
        "contract_sides": slate.counts.get("contract_sides", 0),
        "counts": slate.counts,
        "simulations_run": slate.compute.simulations_run,
        "fixtures_resimulated": slate.compute.fixtures_resimulated,
        "odds_api_calls": slate.compute.odds_api_calls,
        "odds_api_credits": slate.compute.odds_api_credits,
        "reprice_runtime_s": slate.compute.reprice_runtime_s,
        "model_refresh_runtime_s": slate.compute.model_refresh_runtime_s,
        "kalshi_capture_runtime_s": slate.compute.kalshi_capture_runtime_s,
        "price_changes_vs_previous": len(changes),
        "price_change_sample": changes[:12],
        "removed_started": slate.removed_started,
    }
    append_jsonl(out_root / SLATE_LOG_DIR / f"{slate.generated_at:%Y-%m-%d}.jsonl", row)
    return row


def previous_slate(*roots: Path) -> dict[str, Any] | None:
    """The newest slate among roots (by Kalshi observation, then generation time)."""
    best = None
    for r in roots:
        d = read_json_or(r / SLATE_FILE, None)
        if d and (best is None or slate_order_key(d) > slate_order_key(best)):
            best = d
    return best


def slate_order_key(doc: dict[str, Any]) -> tuple[str, str]:
    return ((doc.get("kalshi") or {}).get("observed_at") or "", doc.get("generated_at") or "")
