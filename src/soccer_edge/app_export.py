"""App export: the SOCCER data-archive -> the unified Edge Finder app payload (``app/latest``).

A pure adapter (docs/APP_EXPORT.md). It reads what the production pipeline already publishes to the
``data-archive`` branch -- the merged live slate, the latest run output, the model board, the ESPN
and Kalshi status pointers, the dispatch heartbeat -- plus the routed-wager ledger on
``accounting-data``, and translates each internal object into the vendored contract's documents
(``contract/edge_finder_contract``). It changes no model, gate, authority or staking logic: every
probability, edge, price and action is copied from the slate/run output that produced it.

Three objects are kept distinct: a MODEL PRICE (one per Kalshi ticker, P(YES)), a RECOMMENDATION
(a slate row whose action is ACTIONABLE / RESEARCH_CANDIDATE, for the row's own side) and a WAGER
(a row the kalshi-bet-router filed on the accounting ledger). An edge is never a wager.

Failure policy: any exception in the build leaves the previous ``app/latest`` byte-identical and
writes ONLY ``health.json`` with ``export_failed=True``; the process exits 1.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

# The vendored contract lives at <repo>/contract; put it on sys.path when it is not installed.
_CONTRACT_DIR = Path(__file__).resolve().parents[2] / "contract"
try:
    import edge_finder_contract  # noqa: F401
except ImportError:  # pragma: no cover - only outside pytest/CI, which put contract/ on the path
    if (_CONTRACT_DIR / "edge_finder_contract").is_dir():
        sys.path.insert(0, str(_CONTRACT_DIR))

from edge_finder_contract import board as app_board  # noqa: E402
from edge_finder_contract import (  # noqa: E402
    build,
    freshness,
    linkage,
    performance,
    publish,
    timeutil,
)
from edge_finder_contract import health as app_health  # noqa: E402
from edge_finder_contract.routed_ledger import read_jsonl  # noqa: E402

from soccer_edge.accounting import LEDGER_BRANCH, REPO_FULL_NAME  # noqa: E402
from soccer_edge.accounting import SPEC as LEDGER_SPEC  # noqa: E402
from soccer_edge.contracts.slate_v1 import (  # noqa: E402
    ActionableSlateV1,
    SlateContractV1,
    SlateFixtureV1,
)
from soccer_edge.contracts.v1 import EventV1, RecommendationV1, RunOutputV1  # noqa: E402
from soccer_edge.core.serialization import read_json  # noqa: E402

SPORT = "SOCCER"
SOURCE_REPO = REPO_FULL_NAME
SOURCE_BRANCH = "data-archive"
REPO_ROOT = Path(__file__).resolve().parents[2]

#: Kalshi is swept every ~15 min by kalshi-capture; the slate's own policy is current <= 20 min,
#: aging <= 30 min. The model board is refreshed by RUN SOCCER (policy: current <= 12 h, aging <= 36 h).
MARKET_THRESHOLDS = freshness.Thresholds(20 * 60, 60 * 60)
MODEL_THRESHOLDS = freshness.Thresholds(12 * 3600, 36 * 3600)
SCHEDULE_THRESHOLDS = freshness.Thresholds(24 * 3600, 72 * 3600)
THRESHOLDS = {"market_data": MARKET_THRESHOLDS, "model": MODEL_THRESHOLDS}

SLATE_FILE = "runs/latest.actionable_slate.v1.json"
RUN_OUTPUT_FILE = "runs/latest.run_output.v1.json"
BOARD_FILE = "runs/latest.model_board.v1.json"
ESPN_STATUS_FILE = "STATUS.json"
KALSHI_STATUS_FILE = "snapshots/STATUS.json"
HEARTBEATS_DIR = "dispatch/heartbeats"
MODEL_HEALTH_FILE = "evaluation/model_health.v1.json"
ESPN_FIXTURES_DIR = "fixtures/espn"
AUTHORITY_FILE = REPO_ROOT / "config" / "authority.json"
ESPN_DAYS_SCANNED = 7

RESEARCH_ACTIONS = ("ACTIONABLE", "RESEARCH_CANDIDATE")
DEGRADED_ACTIONS = ("MODEL_INVALIDATED", "MODEL_STALE")
_FRESH = {"CURRENT": "FRESH", "AGING": "AGING", "STALE": "STALE"}
_EVENT_STATUS = {
    "scheduled": "SCHEDULED",
    "not_started": "SCHEDULED",
    "pregame": "SCHEDULED",
    "live": "LIVE",
    "in_progress": "LIVE",
    "finished": "FINAL",
    "final": "FINAL",
    "awarded": "FINAL",
    "postponed": "POSTPONED",
    "cancelled": "CANCELLED",
    "abandoned": "CANCELLED",
}
_SECRET_MARKERS = ("PRIVATE KEY", "ghp_", "github_pat_", "Bearer ", "AIRTABLE")

# The repository's pricing semantics describe every priced contract deterministically
# (soccer_edge.pricing.semantics._describe); these parse that encoding back into the contract's
# side vocabulary. Anything else (btts, exact score, player props) has no single side: null.
_RE_RESULT = re.compile(
    r"^(?:Result|First-half result|Second-half result|First team to score): (home|away|draw)$"
)
_RE_HANDICAP = re.compile(r"^(?:First half: )?(home|away) wins by more than (\S+)$")
_RE_TEAM_TOTAL = re.compile(r"^(?:First half: )?(home|away) team total over (\S+)$")
_RE_TOTAL = re.compile(r"^(?:Total goals|First-half total goals) over (\S+)$")


class AppExportError(Exception):
    pass


# ----------------------------------------------------------------------------- small helpers
def _aware(value: datetime | str | None, what: str) -> datetime | None:
    """Timezone-aware UTC or None; a naive timestamp is refused, never converted silently."""
    if value is None:
        return None
    if isinstance(value, str):
        value = timeutil.parse_ts(value)
    if value.tzinfo is None or value.utcoffset() is None:
        raise AppExportError(f"{what}: naive timestamp refused ({value.isoformat()})")
    return value.astimezone(UTC)


def _num(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(Decimal(str(value)))
    except (ValueError, ArithmeticError):
        return None


def _latest(*stamps: datetime | None) -> datetime | None:
    real = [s for s in stamps if s is not None]
    return max(real) if real else None


def _parse_fixture_id(fixture_id: str) -> tuple[str | None, str | None, str | None, str | None]:
    """``fx:<competition>:<season>:<home_team_id>:<away_team_id>`` -> its four parts (or Nones)."""
    parts = fixture_id.split(":")
    if len(parts) == 5 and parts[0] == "fx":
        return parts[1], parts[2], parts[3], parts[4]
    return None, None, None, None


def _side_from_description(description: str) -> tuple[str | None, str | None, float | None]:
    """(side, team_slot, line) from the repository's own contract description."""
    m = _RE_RESULT.match(description)
    if m:
        who = m.group(1)
        return who.upper(), (who if who != "draw" else None), None
    m = _RE_HANDICAP.match(description)
    if m:
        return m.group(1).upper(), m.group(1), _num(m.group(2))
    m = _RE_TEAM_TOTAL.match(description)
    if m:
        return "OVER", m.group(1), _num(m.group(2))
    m = _RE_TOTAL.match(description)
    if m:
        return "OVER", None, _num(m.group(1))
    return None, None, None


def _series_ticker(event_ticker: str | None) -> str | None:
    return event_ticker.split("-")[0] if event_ticker and "-" in event_ticker else None


# ----------------------------------------------------------------------------- inputs
@dataclass
class Inputs:
    data_root: Path
    slate: ActionableSlateV1
    run_output: RunOutputV1 | None
    board: dict[str, Any]
    authority_default: str
    espn_status: dict[str, Any] | None
    kalshi_status: dict[str, Any] | None
    heartbeat: dict[str, Any] | None
    model_health: list[dict[str, Any]]
    espn_ids: dict[str, str]
    wager_rows: list[dict[str, Any]]
    settlement_rows: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)


def _read_optional(path: Path, warnings: list[str], what: str) -> Any:
    if not path.exists():
        warnings.append(f"{what} missing ({path.name})")
        return None
    return read_json(path)


def _newest_heartbeat(root: Path, warnings: list[str]) -> dict[str, Any] | None:
    d = root / HEARTBEATS_DIR
    if not d.is_dir():
        warnings.append("no dispatch heartbeats")
        return None
    for day_file in sorted(d.glob("*.jsonl"), reverse=True):
        lines = [ln for ln in day_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if lines:
            try:
                row = json.loads(lines[-1])
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                return row
    warnings.append("no readable dispatch heartbeat")
    return None


def _espn_event_ids(root: Path, wanted: set[str]) -> dict[str, str]:
    """fixture_id -> espn_event_id from the newest ESPN fixture dumps (newest day first)."""
    out: dict[str, str] = {}
    d = root / ESPN_FIXTURES_DIR
    if not d.is_dir():
        return out
    for day in sorted((p for p in d.iterdir() if p.is_dir()), reverse=True)[:ESPN_DAYS_SCANNED]:
        for dump in sorted(day.glob("*.json"), reverse=True):
            try:
                doc = read_json(dump)
            except (OSError, ValueError):
                continue
            for item in doc.get("fixtures", []) if isinstance(doc, dict) else []:
                fid, eid = item.get("fixture_id"), item.get("espn_event_id")
                if fid in wanted and fid not in out and eid:
                    out[fid] = str(eid)
        if wanted <= set(out):
            break
    return out


def load_inputs(data_root: Path, accounting_dir: Path | None = None) -> Inputs:
    root = Path(data_root)
    warnings: list[str] = []
    slate_path = root / SLATE_FILE
    if not slate_path.exists():
        raise AppExportError(f"no actionable slate at {slate_path}")
    slate = ActionableSlateV1.model_validate(read_json(slate_path))
    run_raw = _read_optional(root / RUN_OUTPUT_FILE, warnings, "run output")
    run_output = RunOutputV1.model_validate(run_raw) if run_raw is not None else None
    board = _read_optional(root / BOARD_FILE, warnings, "model board") or {}
    authority_default = "RESEARCH_ONLY"
    if AUTHORITY_FILE.exists():
        authority_default = str(read_json(AUTHORITY_FILE).get("default", authority_default))
    espn_status = _read_optional(root / ESPN_STATUS_FILE, warnings, "ESPN status")
    kalshi_status = _read_optional(root / KALSHI_STATUS_FILE, warnings, "Kalshi capture status")
    heartbeat = _newest_heartbeat(root, warnings)
    mh = _read_optional(root / MODEL_HEALTH_FILE, warnings, "model health")
    model_health = mh if isinstance(mh, list) else []
    wanted = {f.fixture_id for f in slate.fixtures}
    if run_output is not None:
        wanted |= {e.event_id for e in run_output.events}
    espn_ids = _espn_event_ids(root, wanted)
    wager_rows: list[dict[str, Any]] = []
    settlement_rows: list[dict[str, Any]] = []
    if accounting_dir is not None:
        wager_rows = read_jsonl(LEDGER_SPEC.wagers_path(Path(accounting_dir)))
        settlement_rows = read_jsonl(LEDGER_SPEC.settlements_path(Path(accounting_dir)))
    else:
        warnings.append("no accounting dir: wagers/settlements not read")
    return Inputs(
        data_root=root,
        slate=slate,
        run_output=run_output,
        board=board,
        authority_default=authority_default,
        espn_status=espn_status,
        kalshi_status=kalshi_status,
        heartbeat=heartbeat,
        model_health=model_health,
        espn_ids=espn_ids,
        wager_rows=wager_rows,
        settlement_rows=settlement_rows,
        warnings=warnings,
    )


# ----------------------------------------------------------------------------- build
@dataclass
class Bundle:
    run_id: str
    generated_at: datetime
    documents: dict[str, dict[str, Any]]
    health: dict[str, Any]
    freshness: dict[str, dict[str, Any]]
    warnings: list[str]
    model_version: str | None
    commit_sha: str | None
    counts: dict[str, int]


def _team(team_id: str, name: str) -> dict[str, Any]:
    return build.participant(
        sport=SPORT,
        participant_type="TEAM",
        source="team_id",
        source_id=team_id,
        display_name=name,
        short_name=None,
    )


def _event_from_run(
    ev: EventV1,
    slate_fx: SlateFixtureV1 | None,
    inputs: Inputs,
    run_generated_at: datetime,
    fixtures_observed_at: datetime | None,
) -> dict[str, Any]:
    home, away = _team(ev.home_id, ev.home), _team(ev.away_id, ev.away)
    _, season, _, _ = _parse_fixture_id(ev.event_id)
    espn_id = inputs.espn_ids.get(ev.event_id)
    source_ids = {"fixture_id": ev.event_id}
    if espn_id:
        source_ids["espn_event_id"] = espn_id
    return build.event(
        sport=SPORT,
        source="fixture_id",
        source_id=ev.event_id,
        start_time_utc=_aware(ev.start_time, f"{ev.event_id} start_time"),
        participants=[home, away],
        home_participant=home["participant_id"],
        away_participant=away["participant_id"],
        league=ev.league_id,
        season=season,
        competition=ev.league,
        status=_EVENT_STATUS.get(str(ev.status).lower(), "UNKNOWN"),
        start_time_source="espn_fixtures" if espn_id else "fixture_registry",
        start_time_confidence="SCHEDULED",
        venue=ev.venue,
        source_ids=source_ids,
        schedule_updated_at=fixtures_observed_at,
        last_updated_at=run_generated_at,
        extensions=_event_extensions(ev, slate_fx),
    )


def _event_from_slate(fx: SlateFixtureV1, inputs: Inputs) -> dict[str, Any]:
    """A fixture the slate carries but the latest run output does not (added by a later refresh)."""
    _, season, home_id, away_id = _parse_fixture_id(fx.fixture_id)
    bf = inputs.board.get("fixtures", {}).get(fx.fixture_id, {})
    home_id = bf.get("home") or home_id
    away_id = bf.get("away") or away_id
    if not home_id or not away_id:
        raise AppExportError(f"{fx.fixture_id}: cannot resolve home/away team ids")
    names = fx.event_name.split(" vs ", 1)
    home_name = names[0] if len(names) == 2 else home_id
    away_name = names[1] if len(names) == 2 else away_id
    home, away = _team(home_id, home_name), _team(away_id, away_name)
    espn_id = inputs.espn_ids.get(fx.fixture_id)
    source_ids = {"fixture_id": fx.fixture_id}
    if espn_id:
        source_ids["espn_event_id"] = espn_id
    return build.event(
        sport=SPORT,
        source="fixture_id",
        source_id=fx.fixture_id,
        start_time_utc=_aware(fx.kickoff, f"{fx.fixture_id} kickoff"),
        participants=[home, away],
        home_participant=home["participant_id"],
        away_participant=away["participant_id"],
        league=fx.competition,
        season=season,
        competition=fx.competition_name or bf.get("competition_name") or fx.competition,
        status="SCHEDULED",
        start_time_source="espn_fixtures" if espn_id else "actionable_slate",
        start_time_confidence="SCHEDULED",
        source_ids=source_ids,
        schedule_updated_at=_aware(bf.get("fixtures_observed_at"), "board fixtures_observed_at"),
        last_updated_at=_aware(inputs.slate.generated_at, "slate generated_at"),
        extensions=_event_extensions(None, fx),
    )


def _event_extensions(ev: EventV1 | None, fx: SlateFixtureV1 | None) -> dict[str, Any]:
    ext: dict[str, Any] = {}
    if ev is not None:
        ext.update(
            {
                "neutral_site": ev.neutral_site,
                "stage": ev.stage,
                "lineup_status": ev.lineup_status,
                "markets_discovered": ev.markets_discovered,
                "markets_evaluated": ev.markets_evaluated,
            }
        )
    if fx is not None:
        ext["slate"] = {
            "minutes_to_kickoff_at_publish": fx.minutes_to_kickoff_at_publish,
            "model_validity": fx.model.validity,
            "model_invalidation_reasons": list(fx.model.invalidation_reasons),
            "model_family": fx.model.model_family,
            "lineup_status": fx.lineup.status,
            "lineup_last_change_at": timeutil.to_iso_or_none(fx.lineup.last_change_at),
            "reference_quality": fx.reference.quality,
            "reference_bookmaker": fx.reference.bookmaker,
            "contracts_priced": fx.contracts_priced,
            "contracts_without_model": fx.contracts_without_model,
            "best_expressions": list(fx.best_expressions),
        }
    return ext


def _market(
    ticker: str,
    rows: dict[str, SlateContractV1],
    event: dict[str, Any],
    board_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    any_row = rows.get("yes") or rows["no"]
    description = (
        any_row.market_description
        or (board_entry or {}).get("description")
        or any_row.market_family
    )
    side, team_slot, line = _side_from_description(description)
    participant_id = None
    if team_slot == "home":
        participant_id = event["home_participant"]
    elif team_slot == "away":
        participant_id = event["away_participant"]
    if line is None and board_entry is not None:
        line = _num(board_entry.get("line"))
    period = (board_entry or {}).get("period")
    captured_at = _aware(any_row.kalshi_observed_at, f"{ticker} kalshi_observed_at")
    actions = {s: r.action for s, r in sorted(rows.items())}
    ext: dict[str, Any] = {
        "actions": actions,
        "fee_per_contract": _num(any_row.fee_per_contract),
        "available_size": {s: _num(r.available_size) for s, r in sorted(rows.items())},
        "breakeven_price": {s: _num(r.breakeven_price) for s, r in sorted(rows.items())},
        "best_expression": any(r.best_expression for r in rows.values()),
        "kalshi_freshness": any_row.freshness.get("kalshi"),
    }
    if period:
        ext["period"] = period
    return build.market(
        sport=SPORT,
        kalshi_ticker=ticker,
        market_family=any_row.market_family,
        yes_description=description,
        source="actionable_slate",
        event_id=event["event_id"],
        kalshi_event_ticker=any_row.event_ticker,
        kalshi_series_ticker=_series_ticker(any_row.event_ticker),
        period=period,
        participant_id=participant_id,
        side=side,
        line=line,
        yes_bid=_num(any_row.kalshi_yes_bid),
        yes_ask=_num(any_row.kalshi_yes_ask),
        no_bid=_num(any_row.kalshi_no_bid),
        no_ask=_num(any_row.kalshi_no_ask),
        market_status="OPEN",
        close_time_utc=_aware(any_row.kickoff, f"{ticker} kickoff"),
        captured_at=captured_at,
        extensions=ext,
    )


def _model_price(
    *,
    run_id: str,
    ticker: str,
    rows: dict[str, SlateContractV1],
    event: dict[str, Any],
    fx: SlateFixtureV1 | None,
    board_entry: dict[str, Any] | None,
    market: dict[str, Any],
) -> dict[str, Any]:
    yes, no = rows.get("yes"), rows.get("no")
    any_row = yes or no
    assert any_row is not None
    if board_entry is not None and _num(board_entry.get("p")) is not None:
        p_yes = _num(board_entry["p"])
        lo, hi = _num(board_entry.get("p_low")), _num(board_entry.get("p_high"))
    elif yes is not None:
        p_yes, lo, hi = yes.model_probability, yes.model_probability_low, yes.model_probability_high
    else:
        assert no is not None
        p_yes = 1.0 - no.model_probability
        lo, hi = 1.0 - no.model_probability_high, 1.0 - no.model_probability_low
    actions = {r.action for r in rows.values()}
    model_state = _FRESH.get(str(any_row.freshness.get("model")), "UNKNOWN")
    fresh = freshness.worst(model_state, "STALE") if "MODEL_STALE" in actions else model_state
    degraded = bool(actions & set(DEGRADED_ACTIONS))
    ext: dict[str, Any] = {
        "model_family": any_row.model_family,
        "actions": {s: r.action for s, r in sorted(rows.items())},
        "fee_adjusted_ev": {s: r.fee_adjusted_ev for s, r in sorted(rows.items())},
        "worst_case_edge": {s: r.worst_case_edge for s, r in sorted(rows.items())},
        "model_posterior_edge_share": {
            s: r.model_posterior_edge_share for s, r in sorted(rows.items())
        },
    }
    if board_entry is not None:
        for k in ("n_worlds", "interval_level", "param_sd"):
            if board_entry.get(k) is not None:
                ext[k] = board_entry[k]
    inputs_as_of = (
        fx.model.freshness.observed_at if fx is not None else None
    ) or any_row.model_generated_at
    return build.model_price(
        run_id=run_id,
        market_id=market["market_id"],
        fair_probability=p_yes,
        generated_at=_aware(any_row.model_generated_at, f"{ticker} model_generated_at"),
        event_id=event["event_id"],
        model_version=any_row.model_version,
        lower_bound=lo,
        upper_bound=hi,
        market_probability=_num(any_row.kalshi_yes_ask),
        edge=yes.fee_adjusted_ev if yes is not None else None,
        inputs_as_of=_aware(inputs_as_of, f"{ticker} inputs_as_of"),
        freshness_status=fresh,
        data_quality_status="DEGRADED" if degraded else "OK",
        support_status=fx.model.validity if fx is not None else None,
        extensions=ext,
    )


def _recommendation(
    *,
    run_id: str,
    row: SlateContractV1,
    event: dict[str, Any],
    market: dict[str, Any],
    fx: SlateFixtureV1 | None,
    slate: ActionableSlateV1,
    thesis_id: str | None,
) -> dict[str, Any]:
    price = _num(row.kalshi_price)
    bet_up_to = _num(row.bet_up_to_price)
    actionable = row.action == "ACTIONABLE" and row.bet_permitted
    return build.recommendation(
        sport=SPORT,
        source_repo=SOURCE_REPO,
        event_id=event["event_id"],
        market_id=market["market_id"],
        run_id=run_id,
        selection=row.side.upper(),
        market_description=row.market_description,
        created_at=_aware(slate.generated_at, "slate generated_at"),
        status="RECOMMENDED" if actionable else "RESEARCH_CANDIDATE",
        authority=row.authority,
        research_only=not row.bet_permitted,
        native_id=f"{slate.slate_id}|{row.ticker}|{row.side}",
        current_probability=price,
        current_price=price,
        fair_probability=row.model_probability,
        edge=row.fee_adjusted_ev,
        bet_up_to_probability=bet_up_to,
        bet_up_to_price=bet_up_to,
        thesis_id=thesis_id,
        expires_at=_aware(row.action_valid_until, f"{row.ticker} action_valid_until"),
        data_freshness=_FRESH.get(str(row.freshness.get("kalshi")), "UNKNOWN"),
        lineup_status=fx.lineup.status if fx is not None else row.lineup_status,
        source_ids={"slate_id": slate.slate_id, "ticker": row.ticker, "fixture_id": row.fixture_id},
        extensions={
            "action": row.action,
            "action_reasons": list(row.action_reasons),
            "research_status": row.research_status,
            "model_probability_low": row.model_probability_low,
            "model_probability_high": row.model_probability_high,
            "worst_case_edge": row.worst_case_edge,
            "model_posterior_edge_share": row.model_posterior_edge_share,
            "breakeven_price": _num(row.breakeven_price),
            "fee_per_contract": _num(row.fee_per_contract),
            "available_size": _num(row.available_size),
            "reference_probability": row.reference_probability,
            "reference_quality": row.reference_quality,
            "reference_anchored_ev": row.reference_anchored_ev,
            "reference_anchored_ev_lower": row.reference_anchored_ev_lower,
            "model_family": row.model_family,
            "model_version": row.model_version,
            "best_expression": row.best_expression,
            "freshness": dict(row.freshness),
        },
    )


def _run_recommendation(
    run_id: str,
    rec: RecommendationV1,
    event: dict[str, Any],
    market: dict[str, Any],
    thesis_id: str | None,
) -> dict[str, Any]:
    """A RunOutputV1 recommendation (authority LIMITED/TRUSTED; none today)."""
    price = _num(rec.current_price)
    bet_up_to = _num(rec.bet_up_to_price)
    return build.recommendation(
        sport=SPORT,
        source_repo=SOURCE_REPO,
        event_id=event["event_id"],
        market_id=market["market_id"],
        run_id=run_id,
        selection=rec.side.upper(),
        market_description=rec.market_description,
        created_at=_aware(rec.model_as_of, f"{rec.recommendation_id} model_as_of"),
        status="RECOMMENDED",
        authority=rec.authority,
        research_only=rec.authority in ("RESEARCH_ONLY", "SHADOW"),
        native_id=rec.recommendation_id,
        current_probability=price,
        current_price=price,
        fair_probability=rec.fair_probability,
        edge=rec.fee_adjusted_edge,
        bet_up_to_probability=bet_up_to,
        bet_up_to_price=bet_up_to,
        confidence=rec.confidence_label,
        stake_units=rec.stake_units,
        thesis_id=thesis_id,
        data_freshness="UNKNOWN",
        lineup_status=rec.lineup_status,
        source_ids={"recommendation_id": rec.recommendation_id, "ticker": rec.market_ticker},
        extensions={
            "worst_case_edge": rec.worst_case_edge,
            "probability_edge_positive": rec.probability_edge_positive,
            "fair_probability_low": rec.fair_probability_low,
            "fair_probability_high": rec.fair_probability_high,
            "model_family": rec.model_family,
            "model_version": rec.model_version,
            "prediction_record_id": rec.prediction_record_id,
            "market_as_of": timeutil.to_iso_or_none(rec.market_as_of),
        },
    )


def _theses(
    run_id: str, run_output: RunOutputV1 | None, events: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """One thesis per event from the run's own recommendation text (RecommendationV1.thesis/risks).
    The text is produced by RUN SOCCER; nothing is written here."""
    out: dict[str, dict[str, Any]] = {}
    if run_output is None:
        return out
    by_event: dict[str, list[RecommendationV1]] = {}
    for rec in [*run_output.recommendations, *run_output.shadow_recommendations]:
        if rec.event_id in events:
            by_event.setdefault(rec.event_id, []).append(rec)
    generated_at = _aware(run_output.generated_at, "run generated_at")
    for event_id in sorted(by_event):
        recs = sorted(by_event[event_id], key=lambda r: r.recommendation_id)
        lead = recs[0]
        summary = lead.thesis.strip() or None
        evidence = {
            "run_id": run_output.run_id,
            "recommendations": [
                {
                    "recommendation_id": r.recommendation_id,
                    "market_ticker": r.market_ticker,
                    "side": r.side,
                    "fair_probability": r.fair_probability,
                    "fee_adjusted_edge": r.fee_adjusted_edge,
                    "worst_case_edge": r.worst_case_edge,
                    "probability_edge_positive": r.probability_edge_positive,
                    "reference_probability": r.reference_probability,
                    "reference_bookmaker": r.reference_bookmaker,
                }
                for r in recs
            ],
        }
        out[event_id] = build.thesis(
            sport=SPORT,
            run_id=run_id,
            event_id=events[event_id]["event_id"],
            generated_at=generated_at,
            summary=summary,
            opposing_factors=list(lead.risks),
            context_notes={"lineups": lead.lineup_status},
            confidence_label=lead.confidence_label,
            evidence=evidence,
        )
    return out


def _wagers_and_settlements(
    inputs: Inputs,
    markets: dict[str, dict[str, Any]],
    model_prices: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Ledger rows -> wagers + settlements; returns (wagers, settlements, market stubs added)."""
    stubs: list[dict[str, Any]] = []
    wagers_by_key: dict[str, dict[str, Any]] = {}
    for row in sorted(inputs.wager_rows, key=lambda r: str(r.get("source_bet_key"))):
        ticker = str(row["market_ticker"])
        market = markets.get(ticker)
        if market is None:
            market = build.market_stub(sport=SPORT, kalshi_ticker=ticker)
            markets[ticker] = market
            stubs.append(market)
        wager = build.wager(
            sport=SPORT,
            kalshi_ticker=ticker,
            selection=str(row["side"]),
            contracts=row["contracts"],
            stake=row["stake"],
            average_price=row["execution_price"],
            placed_at=_aware(row["executed_at"], "wager executed_at"),
            source="KALSHI_ROUTER",
            destination_repo=SOURCE_REPO,
            source_bet_key=row["source_bet_key"],
            event_id=market.get("event_id"),
            side=row.get("execution_action"),
            fees=row.get("fees_paid"),
            settlement_status="PENDING",
            source_ids={
                "ledger_wager_id": row.get("wager_id"),
                "import_batch_id": row.get("import_batch_id"),
            },
            extensions={
                "game_date": row.get("game_date"),
                "venue": row.get("venue"),
                "entry_method": row.get("entry_method"),
                "fee_state": row.get("fee_state"),
                "ledger_branch": LEDGER_BRANCH,
            },
        )
        wagers_by_key[str(row["source_bet_key"])] = wager
    settlements: list[dict[str, Any]] = []
    for row in sorted(inputs.settlement_rows, key=lambda r: str(r.get("source_bet_key"))):
        wager = wagers_by_key.get(str(row.get("source_bet_key")))
        if wager is None:
            inputs.warnings.append("settlement row without its wager on the ledger (skipped)")
            continue
        gross, net = row.get("gross_return"), row.get("net_profit_loss")
        established = gross is not None and net is not None
        refusals = [str(r) for r in (row.get("refusals") or [])]
        settlement = build.settlement(
            wager_id=wager["wager_id"],
            market_id=wager["market_id"],
            result=str(row.get("result") or "UNKNOWN"),
            settled_at=_aware(row["settled_at"], "settlement settled_at"),
            source="KALSHI_ROUTER",
            verification_status="EXCHANGE_CONFIRMED" if established else "REFUSED",
            winning_side=str(row["side"]) if row.get("result") == "WON" else None,
            gross_payout=gross,
            net_pnl=net,
            refusals=refusals,
            source_ids={"ledger_settlement_id": row.get("settlement_id")},
            extensions={"economics_version": row.get("economics_version")},
        )
        wager["settlement_id"] = settlement["settlement_id"]
        wager["settlement_status"] = "SETTLED"
        wager["payout"] = gross
        wager["profit_loss"] = net
        settlements.append(settlement)
    all_markets = list(markets.values())
    wagers = [
        linkage.apply_links(w, model_prices, recommendations, all_markets)
        for w in wagers_by_key.values()
    ]
    return wagers, settlements, stubs


def _next_scheduled_run(heartbeat: dict[str, Any] | None) -> datetime | None:
    if not heartbeat:
        return None
    done = _aware(heartbeat.get("completed_at"), "heartbeat completed_at")
    window = _num(heartbeat.get("next_window_minutes"))
    if done is None or window is None:
        return None
    return done + timedelta(minutes=window)


def build_bundle(
    inputs: Inputs,
    *,
    now: datetime,
    commit_sha: str | None = None,
    workflow_run_id: str | None = None,
) -> Bundle:
    now = _aware(now, "now")
    assert now is not None
    slate, run_output = inputs.slate, inputs.run_output
    warnings = list(inputs.warnings)
    slate_generated_at = _aware(slate.generated_at, "slate generated_at")
    run_generated_at = _aware(run_output.generated_at, "run generated_at") if run_output else None
    completed_at = _latest(slate_generated_at, run_generated_at)
    assert completed_at is not None
    heartbeat_sha = (inputs.heartbeat or {}).get("commit_sha")
    sha = str(heartbeat_sha) if heartbeat_sha else commit_sha
    run_model_version: str | None = None
    versions = sorted({c.model_version for c in slate.contracts})
    if versions:
        run_model_version = versions[0] if len(versions) == 1 else "|".join(versions)

    run_doc = build.run(
        sport=SPORT,
        repo=SOURCE_REPO,
        completed_at=completed_at,
        scope=f"slate {slate.slate_id} (lookahead {slate.lookahead_hours:g}h)",
        status="SUCCESS",
        native_run_id=slate.slate_id,
        commit_sha=sha,
        workflow_run_id=workflow_run_id,
        model_version=run_model_version,
        source_ids={
            "slate_id": slate.slate_id,
            "run_id": run_output.run_id if run_output else None,
            "kalshi_discovery_run_id": slate.kalshi_discovery_run_id,
        },
    )
    run_id = run_doc["run_id"]

    # events: every event the latest run output knows plus any slate-only fixture
    fixtures_observed_at = None
    if run_output is not None:
        fixtures_observed_at = _aware(
            run_output.freshness.get("fixtures_observed_at"), "fixtures_observed_at"
        )
    slate_fx = {f.fixture_id: f for f in slate.fixtures}
    events: dict[str, dict[str, Any]] = {}
    if run_output is not None:
        assert run_generated_at is not None
        for ev in sorted(run_output.events, key=lambda e: e.event_id):
            events[ev.event_id] = _event_from_run(
                ev, slate_fx.get(ev.event_id), inputs, run_generated_at, fixtures_observed_at
            )
    for fid in sorted(slate_fx):
        if fid not in events:
            events[fid] = _event_from_slate(slate_fx[fid], inputs)

    # markets + model prices: one per ticker (the slate has one row per side)
    by_ticker: dict[str, dict[str, SlateContractV1]] = {}
    for row in slate.contracts:
        by_ticker.setdefault(row.ticker, {})[row.side] = row
    board_fixtures = inputs.board.get("fixtures", {}) if isinstance(inputs.board, dict) else {}
    markets: dict[str, dict[str, Any]] = {}
    model_prices: list[dict[str, Any]] = []
    for ticker in sorted(by_ticker):
        rows = by_ticker[ticker]
        any_row = rows.get("yes") or rows["no"]
        event = events.get(any_row.fixture_id)
        if event is None:
            raise AppExportError(f"{ticker}: fixture {any_row.fixture_id} is not an event")
        board_entry = (
            (board_fixtures.get(any_row.fixture_id) or {}).get("contracts", {}).get(ticker)
        )
        market = _market(ticker, rows, event, board_entry)
        markets[ticker] = market
        model_prices.append(
            _model_price(
                run_id=run_id,
                ticker=ticker,
                rows=rows,
                event=event,
                fx=slate_fx.get(any_row.fixture_id),
                board_entry=board_entry,
                market=market,
            )
        )

    theses = _theses(run_id, run_output, events)
    recommendations: list[dict[str, Any]] = []
    for ticker in sorted(by_ticker):
        for side in ("yes", "no"):
            row = by_ticker[ticker].get(side)
            if row is None or row.action not in RESEARCH_ACTIONS:
                continue
            event = events[row.fixture_id]
            thesis = theses.get(row.fixture_id)
            recommendations.append(
                _recommendation(
                    run_id=run_id,
                    row=row,
                    event=event,
                    market=markets[ticker],
                    fx=slate_fx.get(row.fixture_id),
                    slate=slate,
                    thesis_id=thesis["thesis_id"] if thesis else None,
                )
            )
    if run_output is not None:
        for rec in sorted(run_output.recommendations, key=lambda r: r.recommendation_id):
            if rec.authority not in ("LIMITED", "TRUSTED"):
                continue
            event, market = events.get(rec.event_id), markets.get(rec.market_ticker)
            if event is None or market is None:
                warnings.append(
                    f"run recommendation {rec.recommendation_id} not on the slate; skipped"
                )
                continue
            thesis = theses.get(rec.event_id)
            recommendations.append(
                _run_recommendation(
                    run_id, rec, event, market, thesis["thesis_id"] if thesis else None
                )
            )

    wagers, settlements, _stubs = _wagers_and_settlements(
        inputs, markets, model_prices, recommendations
    )

    # health
    kalshi_as_of = _aware(slate.kalshi.observed_at, "slate kalshi observed_at")
    model_as_of = _aware(slate.model_board_generated_at, "model_board_generated_at") or (
        _aware(run_output.freshness.get("as_of"), "run freshness as_of") if run_output else None
    )
    router_as_of = _latest(*[_aware(w["placed_at"], "placed_at") for w in wagers])
    settlement_as_of = _latest(*[_aware(s["settled_at"], "settled_at") for s in settlements])
    extra: dict[str, dict[str, Any]] = {}
    if inputs.espn_status:
        extra["espn_fixtures"] = app_health.component(
            _aware(inputs.espn_status.get("as_of"), "ESPN as_of"),
            thresholds=SCHEDULE_THRESHOLDS,
            now=now,
            required=False,
            detail="ESPN fixture/lineup sync (STATUS.json)",
        )
    if inputs.kalshi_status:
        extra["kalshi_sweep"] = app_health.component(
            _aware(inputs.kalshi_status.get("captured_at"), "Kalshi captured_at"),
            thresholds=MARKET_THRESHOLDS,
            now=now,
            required=False,
            detail="exhaustive Kalshi soccer sweep (snapshots/STATUS.json)",
        )
    if inputs.heartbeat:
        extra["dispatch"] = app_health.component(
            _aware(inputs.heartbeat.get("completed_at"), "heartbeat completed_at"),
            thresholds=MARKET_THRESHOLDS,
            now=now,
            required=False,
            detail="kickoff dispatcher heartbeat",
        )
    health_warnings = [*warnings, *slate.warnings, *(run_output.warnings if run_output else [])]
    if slate.no_bets:
        health_warnings.append(
            "no_bets: every model family is RESEARCH_ONLY; nothing here is a bet"
        )
    health_doc = app_health.build_health(
        sport=SPORT,
        run_id=run_id,
        bet_authority=inputs.authority_default,
        last_market_capture=kalshi_as_of,
        last_model_generated=model_as_of,
        last_successful_run=completed_at,
        payload_run_id=run_id,
        payload_available=True,
        export_failed=False,
        commit_sha=sha,
        next_scheduled_run=_next_scheduled_run(inputs.heartbeat),
        router_as_of=router_as_of,
        settlement_as_of=settlement_as_of,
        model_required=True,
        thresholds=THRESHOLDS,
        warnings=health_warnings,
        extra_components=extra,
        now=now,
    )

    def _fresh_entry(as_of: datetime | None, th: freshness.Thresholds) -> dict[str, Any]:
        return {
            "as_of": timeutil.to_iso_or_none(as_of),
            "status": freshness.classify(freshness.age_seconds(as_of, now) if as_of else None, th),
        }

    fresh = {
        "kalshi": _fresh_entry(kalshi_as_of, MARKET_THRESHOLDS),
        "model": _fresh_entry(model_as_of, MODEL_THRESHOLDS),
        "fixtures": _fresh_entry(fixtures_observed_at, SCHEDULE_THRESHOLDS),
    }

    # finish the run document now that the counts are known
    run_doc = build.run(
        sport=SPORT,
        repo=SOURCE_REPO,
        completed_at=completed_at,
        scope=run_doc["scope"],
        status="SUCCESS",
        native_run_id=slate.slate_id,
        commit_sha=sha,
        workflow_run_id=workflow_run_id,
        model_version=run_model_version,
        started_at=run_generated_at,
        events_processed=len(events),
        markets_discovered=len(markets),
        markets_priced=len(model_prices),
        recommendations_created=len(recommendations),
        data_sources=["kalshi", "espn", "actionable_slate", "model_board", "accounting_ledger"],
        input_freshness={
            "kalshi": kalshi_as_of,
            "model": model_as_of,
            "fixtures": fixtures_observed_at,
        },
        warnings=health_warnings,
        source_ids=run_doc["source_ids"],
    )
    assert run_doc["run_id"] == run_id

    event_list = [events[k] for k in sorted(events)]
    market_list = [markets[k] for k in sorted(markets)]
    thesis_list = [theses[k] for k in sorted(theses)]
    documents: dict[str, dict[str, Any]] = {
        "events": build.collection("events", SPORT, run_id, now, event_list),
        "markets": build.collection("markets", SPORT, run_id, now, market_list),
        "model_prices": build.collection("model_prices", SPORT, run_id, now, model_prices),
        "recommendations": build.collection("recommendations", SPORT, run_id, now, recommendations),
        "theses": build.collection("theses", SPORT, run_id, now, thesis_list),
        "wagers": build.collection("wagers", SPORT, run_id, now, wagers),
        "settlements": build.collection("settlements", SPORT, run_id, now, settlements),
        "runs": build.collection("runs", SPORT, run_id, now, [run_doc]),
        "board": app_board.build_board(
            sport=SPORT,
            run_id=run_id,
            generated_at=now,
            events=event_list,
            markets=market_list,
            model_prices=model_prices,
            recommendations=recommendations,
            wagers=wagers,
            health=health_doc,
            thresholds=THRESHOLDS,
            now=now,
        ),
        "performance": performance.build_performance(
            sport=SPORT,
            run_id=run_id,
            generated_at=now,
            wagers=wagers,
            settlements=settlements,
            markets=market_list,
            recommendations=recommendations,
            notes=[
                "P&L is the router-filed ledger's own exchange-confirmed economics; nothing is derived here"
            ],
        ),
    }
    kalshi_state = _FRESH.get(str(slate.kalshi.status), "UNKNOWN")
    for event in event_list:
        eid = event["event_id"]
        fx = slate_fx.get(eid)
        context: dict[str, Any] = {"slate_id": slate.slate_id, "consumer_rule": slate.consumer_rule}
        if fx is not None:
            context["fixture"] = event["extensions"].get("slate", {})
        documents[f"event_detail/{eid}"] = app_board.build_event_detail(
            sport=SPORT,
            run_id=run_id,
            generated_at=now,
            event=event,
            markets=[m for m in market_list if m.get("event_id") == eid],
            model_prices=[p for p in model_prices if p.get("event_id") == eid],
            recommendations=[r for r in recommendations if r["event_id"] == eid],
            theses=[t for t in thesis_list if t["event_id"] == eid],
            wagers=[w for w in wagers if w.get("event_id") == eid],
            settlements=[
                s
                for s in settlements
                if any(w["wager_id"] == s["wager_id"] and w.get("event_id") == eid for w in wagers)
            ],
            context=context,
            data_freshness=kalshi_state,
        )
    counts = {
        "events": len(event_list),
        "markets": len(market_list),
        "model_prices": len(model_prices),
        "recommendations": len(recommendations),
        "theses": len(thesis_list),
        "wagers": len(wagers),
        "settlements": len(settlements),
    }
    return Bundle(
        run_id, now, documents, health_doc, fresh, health_warnings, run_model_version, sha, counts
    )


# ----------------------------------------------------------------------------- export
def _check_no_secrets(root: Path) -> None:
    for p in sorted(root.rglob("*.json")):
        text = p.read_text(encoding="utf-8")
        for marker in _SECRET_MARKERS:
            if marker in text:
                raise AppExportError(f"{p.name}: secret-shaped content ({marker!r}) refused")


def export(
    *,
    data_root: Path,
    out: Path,
    accounting_dir: Path | None = None,
    now: datetime | None = None,
    commit_sha: str | None = None,
    workflow_run_id: str | None = None,
    log=print,
) -> int:
    """Build and publish; on any failure write health only (export_failed) and return 1."""
    now = _aware(now, "now") if now is not None else timeutil.now_utc()
    assert now is not None
    out = Path(out)
    try:
        inputs = load_inputs(Path(data_root), accounting_dir)
        bundle = build_bundle(
            inputs, now=now, commit_sha=commit_sha, workflow_run_id=workflow_run_id
        )
        manifest = publish.publish(
            root=out,
            sport=SPORT,
            run_id=bundle.run_id,
            generated_at=bundle.generated_at,
            documents=bundle.documents,
            source_repo=SOURCE_REPO,
            source_branch=SOURCE_BRANCH,
            commit_sha=bundle.commit_sha,
            model_version=bundle.model_version,
            status="SUCCESS",
            freshness=bundle.freshness,
            warnings=bundle.warnings,
            health=bundle.health,
        )
        _check_no_secrets(out)
    except Exception as exc:  # the failure path is the point: health-only, exit 1
        previous = None
        manifest_path = out / publish.MANIFEST_NAME
        if manifest_path.exists():
            try:
                previous = json.loads(manifest_path.read_text(encoding="utf-8")).get("run_id")
            except (OSError, ValueError):
                previous = None
        # last-known-good stamps from the previous health document, so the UI can still say
        # "payload from 14:20, refresh at 15:05 FAILED" rather than going blank
        last_good: dict[str, Any] = {}
        health_path = out / publish.HEALTH_NAME
        if health_path.exists():
            try:
                last_good = json.loads(health_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                last_good = {}
        failed_run = build.run(
            sport=SPORT,
            repo=SOURCE_REPO,
            completed_at=now,
            scope="app export (failed)",
            status="FAILED",
            native_run_id="app-export-failed",
            errors=[str(exc)],
        )
        health_doc = app_health.build_health(
            sport=SPORT,
            run_id=failed_run["run_id"],
            bet_authority=str(last_good.get("bet_authority") or "RESEARCH_ONLY"),
            last_market_capture=last_good.get("last_market_capture"),
            last_model_generated=last_good.get("last_model_generated"),
            last_successful_run=last_good.get("last_successful_run"),
            payload_run_id=previous,
            payload_available=previous is not None,
            export_failed=True,
            commit_sha=commit_sha,
            thresholds=THRESHOLDS,
            errors=[f"{type(exc).__name__}: {exc}"],
            now=now,
        )
        publish.write_health_only(out, health_doc)
        log(f"app-export FAILED ({type(exc).__name__}: {exc}); health-only written to {out}")
        return 1
    log(
        f"app-export OK run_id={bundle.run_id} {json.dumps(bundle.counts, sort_keys=True)} "
        f"health={bundle.health['overall_status']} files={len(manifest.get('files', []))} -> {out}"
    )
    return 0


def add_arguments(ap: argparse.ArgumentParser) -> None:
    ap.add_argument(
        "--data-root", required=True, help="archive root (what archive_publish.sh works in)"
    )
    ap.add_argument("--out", required=True, help="app root to publish, e.g. <archive>/app/latest")
    ap.add_argument(
        "--accounting-dir", default=None, help="checkout of the accounting-data branch (optional)"
    )
    ap.add_argument("--now", default=None, help="ISO-8601 UTC instant (tests: determinism)")
    ap.add_argument("--commit-sha", default=None)
    ap.add_argument("--workflow-run-id", default=None)


def run_from_args(args: argparse.Namespace) -> int:
    return export(
        data_root=Path(args.data_root),
        out=Path(args.out),
        accounting_dir=Path(args.accounting_dir) if args.accounting_dir else None,
        now=_aware(args.now, "--now") if args.now else None,
        commit_sha=args.commit_sha or None,
        workflow_run_id=args.workflow_run_id or None,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    add_arguments(ap)
    return run_from_args(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
