"""Kickoff-timed Pinnacle reference capture through The Odds API (slate-batched, budget-guarded).

Called by the kickoff dispatcher with the (fixture, horizon) pairs that are due now. Kalshi has already
decided WHICH fixtures matter (the schedule's `run_output` fixtures are the ones with discovered Kalshi
markets); this module only fetches the external reference for them.

Per tick:

1. eligible fixtures = due fixtures with Kalshi markets whose minutes-to-kickoff fall in the ENTRY window
   (default (30, 66], one capture per fixture) or the CLOSE window (default (0, 15], one capture per fixture,
   always a TRUE_CLOSE by construction) and that have no successful capture of that purpose yet;
2. nothing eligible -> no HTTP at all;
3. free `/sports` (active sport keys + the account's remaining quota, which includes MLB's spend);
4. per sport key: free `/events` for the kickoff span, deterministic join to the canonical fixtures;
5. ONE paid `/odds` call per sport key (eventIds = every joined fixture of that key in this tick, entry and
   close together), gated by the budget guard; cost = markets x 1 region-equivalent, independent of the
   number of fixtures, so a Saturday 15:00 EPL cluster costs the same as a single match;
6. every row is written (no change suppression: a repeated price at T-5 is the evidence of the close) as a
   `ReferenceMarketSnapshot` under `reference/<date>/oddsapi-<batch>.jsonl`, where the settlement's close_v2
   already looks; the raw provider payload is archived gzipped under `odds_api/raw/`.
"""

from __future__ import annotations

import gzip
import json
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np

from soccer_edge.core.errors import IdentityError
from soccer_edge.core.time import iso_utc, parse_iso_utc
from soccer_edge.families.base import devig_power
from soccer_edge.identity.models import Gender, TeamKind
from soccer_edge.identity.registry import AliasRegistry
from soccer_edge.providers.the_odds_api import (
    SPORT_KEYS,
    OddsApiClient,
    OddsApiResponse,
    api_key_configured,
    expected_cost,
)
from soccer_edge.reference.close import NEAR_CLOSE_MAX_MINUTES
from soccer_edge.reference.odds_budget import (
    STATUS_BLOCKED,
    STATUS_FAILED,
    STATUS_NOT_CONFIGURED,
    STATUS_OK,
    BudgetConfig,
    BudgetLedger,
    charge,
    decide,
)
from soccer_edge.reference.quality import quality_for_bookmaker
from soccer_edge.reference.schemas import DevigMethod, ReferenceMarketSnapshot

SOURCE = "the_odds_api"
# Pinnacle's price as republished by an aggregator: the bookmaker's own last_update is kept (quoted_at) and
# the gap to our capture is recorded, because an aggregated feed can lag the book itself.
FEED_QUALITY = "PINNACLE_AGGREGATED_DELAYED"
MARKET_FOR = {"h2h": "1x2", "totals": "ou", "spreads": "ah"}
MARKET_FAMILY_FOR = {"1x2": "match_result_3way", "ou": "total_goals", "ah": "handicap"}
INTERNATIONAL_PREFIXES = (
    "fifa.world_cup",
    "fifa.friendly",
    "fifa.womens_world_cup",
    "uefa.nations_league",
    "uefa.euro",
    "concacaf.",
    "conmebol.copa_america",
)


@dataclass(frozen=True)
class DueFixture:
    fixture_id: str  # fx:<comp>:<season>:<home>:<away>[:...]
    competition_id: str
    kickoff_utc: datetime
    minutes_to_kickoff: float
    has_kalshi_markets: bool

    @property
    def home_team_id(self) -> str:
        return self.fixture_id.split(":")[3]

    @property
    def away_team_id(self) -> str:
        return self.fixture_id.split(":")[4]


def _purpose(d: DueFixture, cfg: BudgetConfig) -> str | None:
    lo, hi = cfg.close_window_minutes
    if lo < d.minutes_to_kickoff <= hi:
        return "close"
    lo, hi = cfg.entry_window_minutes
    if lo < d.minutes_to_kickoff <= hi:
        return "entry"
    return None


def _resolve(registry: AliasRegistry, name: str, competition_id: str) -> str | None:
    comp = registry.competitions.get(competition_id)
    national = competition_id.startswith(INTERNATIONAL_PREFIXES)
    country = comp.country if comp is not None and len(comp.country) == 3 and not national else None
    try:
        return registry.resolve_team(
            name,
            country=country,
            gender=Gender.MEN,
            kind=TeamKind.NATIONAL if national else TeamKind.CLUB,
        ).team_id
    except IdentityError:
        return None


def join_events(
    events: list[dict[str, Any]],
    fixtures: list[DueFixture],
    registry: AliasRegistry,
    cfg: BudgetConfig,
) -> tuple[dict[str, DueFixture], dict[str, Any]]:
    """Odds API event id -> canonical due fixture. Exact team pair within the tolerance, else one resolved
    side + kickoff within the tight tolerance + a unique candidate; anything else is recorded, never guessed."""
    out: dict[str, DueFixture] = {}
    unresolved: list[str] = []
    ambiguous = 0
    for ev in events:
        try:
            t = parse_iso_utc(ev["commence_time"])
        except (KeyError, ValueError):
            continue
        comp = fixtures[0].competition_id if fixtures else ""
        h = _resolve(registry, ev.get("home_team", ""), comp)
        a = _resolve(registry, ev.get("away_team", ""), comp)
        for nm, tid in ((ev.get("home_team"), h), (ev.get("away_team"), a)):
            if tid is None:
                unresolved.append(str(nm))
        tol = cfg.event_join_tolerance_minutes
        cands = [
            f
            for f in fixtures
            if h is not None
            and a is not None
            and (f.home_team_id, f.away_team_id) == (h, a)
            and abs((f.kickoff_utc - t).total_seconds()) / 60 <= tol
        ]
        if not cands and (h is None) != (a is None):
            tol = cfg.one_side_join_tolerance_minutes
            cands = [
                f
                for f in fixtures
                if abs((f.kickoff_utc - t).total_seconds()) / 60 <= tol
                and (
                    (h is not None and f.home_team_id == h)
                    or (a is not None and f.away_team_id == a)
                )
            ]
        if len(cands) == 1:
            out[ev["id"]] = cands[0]
        elif len(cands) > 1:
            ambiguous += 1
    joined = {f.fixture_id for f in out.values()}
    return out, {
        "events": len(events),
        "joined": len(out),
        "ambiguous": ambiguous,
        "unresolved_names": sorted(set(unresolved)),
        "unjoined_fixtures": sorted(f.fixture_id for f in fixtures if f.fixture_id not in joined),
    }


def snapshots_from_event(
    ev: dict[str, Any], fx: DueFixture, captured_at: datetime
) -> tuple[list[ReferenceMarketSnapshot], int]:
    """One provider event -> Pinnacle snapshots (power de-vig). Returns (snapshots, incomplete markets)."""
    snaps: list[ReferenceMarketSnapshot] = []
    incomplete = 0
    mins = (fx.kickoff_utc - captured_at).total_seconds() / 60
    for bk in ev.get("bookmakers") or []:
        book = bk.get("key")
        for mk in bk.get("markets") or []:
            market = MARKET_FOR.get(mk.get("key"))
            if market is None:
                continue
            quoted = mk.get("last_update") or bk.get("last_update")
            try:
                q_at = parse_iso_utc(quoted) if quoted else None
            except ValueError:
                q_at = None
            latency = (captured_at - q_at).total_seconds() if q_at is not None else None
            groups: dict[Decimal | None, dict[str, tuple[float, Decimal | None]]] = defaultdict(
                dict
            )
            for o in mk.get("outcomes") or []:
                name, price, point = o.get("name"), o.get("price"), o.get("point")
                if price is None:
                    continue
                if market == "1x2":
                    sel = {
                        ev.get("home_team"): "home",
                        ev.get("away_team"): "away",
                        "Draw": "draw",
                    }.get(name)
                    groups[None][sel] = (float(price), None)
                elif market == "ou":
                    sel = {"Over": "over", "Under": "under"}.get(name)
                    groups[Decimal(str(point)) if point is not None else None][sel] = (
                        float(price),
                        None,
                    )
                else:  # ah: pair keyed by the home handicap; each side keeps its own line
                    side = {ev.get("home_team"): "home", ev.get("away_team"): "away"}.get(name)
                    if side is None or point is None:
                        continue
                    pt = Decimal(str(point))
                    home_line = pt if side == "home" else -pt
                    groups[home_line][side] = (float(price), pt)
            order = {
                "1x2": ("home", "draw", "away"),
                "ou": ("over", "under"),
                "ah": ("home", "away"),
            }[market]
            for gline, sels in groups.items():
                if any(s not in sels for s in order) or (market != "1x2" and gline is None):
                    incomplete += 1
                    continue
                odds = np.array([[sels[s][0] for s in order]])
                inv = 1.0 / odds[0]
                probs = devig_power(odds)[0]
                for i, s in enumerate(order):
                    line = sels[s][1] if market == "ah" else gline
                    snaps.append(
                        ReferenceMarketSnapshot(
                            source=SOURCE,
                            bookmaker=book,
                            fixture_id=fx.fixture_id,
                            competition_id=fx.competition_id,
                            home_team_id=fx.home_team_id,
                            away_team_id=fx.away_team_id,
                            kickoff_utc=fx.kickoff_utc,
                            market=market,
                            selection=s,
                            line=line,
                            raw_odds=Decimal(str(sels[s][0])),
                            implied_probability=float(inv[i]),
                            devig_method=DevigMethod.POWER,
                            devigged_probability=float(probs[i]),
                            overround=float(inv.sum()),
                            captured_at=captured_at,
                            quoted_at=q_at,
                            is_closing=False,
                            minutes_to_kickoff=mins,
                            liquidity_note=f"{book} screen price via The Odds API (event {ev.get('id')}); no size information",
                            market_family=MARKET_FAMILY_FOR[market],
                            side=s,
                            decimal_odds=Decimal(str(sels[s][0])),
                            horizon_seconds=mins * 60,
                            is_open=False,
                            is_close_candidate=0 <= mins <= NEAR_CLOSE_MAX_MINUTES,
                            source_quality=quality_for_bookmaker(book).value,
                            feed_quality=FEED_QUALITY if book == "pinnacle" else None,
                            observation_latency_seconds=latency,
                        )
                    )
    return snaps, incomplete


def _row(resp: OddsApiResponse, **extra: Any) -> dict[str, Any]:
    return {**resp.meta(), **extra}


def capture(
    due: list[DueFixture],
    *,
    registry: AliasRegistry,
    out_root: Path,
    cfg: BudgetConfig,
    now: datetime,
    batch_id: str,
    client_factory: Callable[[], OddsApiClient] | None = None,
    force_purpose: str | None = None,
    max_paid_calls: int | None = None,
    claim_fn: Callable[[list[str]], set[str]] | None = None,
) -> dict[str, Any]:
    """`force_purpose` (e.g. 'sample') ignores the entry/close windows and the already-captured check: every
    Kalshi-listed fixture given is eligible, it is ledgered under that purpose (so it never counts as an
    entry or close capture), and it is guarded like an entry capture. `max_paid_calls` bounds the tick.

    `claim_fn` (the dispatcher passes a data-archive ClaimStore) is called with the idempotency identities
    `the_odds_api|<purpose>|<fixture_id>` right before a paid call and returns the ones this run now owns;
    fixtures another run already claimed are dropped, and nothing is spent when none are left. Without it
    the durable ledger check alone applies (sequential runs)."""
    ledger = BudgetLedger(out_root)
    stats: dict[str, Any] = {
        "batch_id": batch_id,
        "calls": [],
        "credits_charged": 0,
        "paid_calls": 0,
        "snapshots": 0,
    }
    by_purpose = {p: ledger.fixtures_captured(now, p) for p in ("entry", "close")}
    groups: dict[str, list[tuple[DueFixture, str]]] = defaultdict(list)
    no_key: set[str] = set()
    no_key_items: list[tuple[DueFixture, str]] = []
    seen: set[str] = set()
    for d in due:
        p = force_purpose or _purpose(d, cfg)
        if (
            not d.has_kalshi_markets
            or p is None
            or (force_purpose is None and d.fixture_id in by_purpose[p])
            or d.fixture_id in seen
        ):
            continue
        seen.add(d.fixture_id)
        sk = SPORT_KEYS.get(d.competition_id)
        if sk is None:
            no_key.add(d.competition_id)
            no_key_items.append((d, p))
            continue
        groups[sk].append((d, p))
    stats["no_sport_key"] = sorted(no_key)
    # a close/entry window with no possible reference is recorded once, so the close report can say why
    logged_nokey = ledger.fixtures_with_status(now, "NO_SPORT_KEY")
    fresh = [(d, p) for d, p in no_key_items if (d.fixture_id, p) not in logged_nokey]
    if fresh:
        ledger.append(
            now,
            {
                "kind": "odds",
                "status": "NO_SPORT_KEY",
                "batch_id": batch_id,
                "request_made": False,
                "credits_charged": 0,
                "close_fixtures": [d.fixture_id for d, p in fresh if p == "close"],
                "entry_fixtures": [d.fixture_id for d, p in fresh if p == "entry"],
                "competitions": sorted({d.competition_id for d, _ in fresh}),
            },
        )
    stats["eligible_fixtures"] = sum(len(v) for v in groups.values())
    if not groups:
        stats["status"] = "NOTHING_ELIGIBLE"
        return stats
    if not api_key_configured() and client_factory is None:
        ledger.append(
            now,
            {
                "kind": "tick",
                "status": STATUS_NOT_CONFIGURED,
                "batch_id": batch_id,
                "eligible_fixtures": stats["eligible_fixtures"],
                "credits_charged": 0,
            },
        )
        stats["status"] = STATUS_NOT_CONFIGURED
        return stats
    client = client_factory() if client_factory else OddsApiClient()
    try:
        sports = client.get_sports()
        c, basis = charge(sports.quota, 0) if sports.http_status is not None else (0, "NO_RESPONSE")
        ledger.append(
            now,
            _row(
                sports,
                batch_id=batch_id,
                status=STATUS_OK if sports.ok else STATUS_FAILED,
                credits_charged=c,
                charge_basis=basis,
            ),
        )
        stats["calls"].append(sports.meta())
        if not sports.ok:
            stats["status"] = "SPORTS_LIST_FAILED"
            return stats
        active = {s.get("key") for s in sports.payload or [] if s.get("active")}
        remaining = _remaining(sports)
        events_cost = max(
            [
                int(r.get("credits_charged") or 0)
                for r in ledger.rows_since(now, 7)
                if r.get("kind") == "events"
            ]
            or [0]
        )
        cost = expected_cost(cfg.markets, cfg.bookmakers)
        # close captures first so they win the budget on a busy tick
        order = sorted(groups, key=lambda k: min(0 if p == "close" else 1 for _, p in groups[k]))
        per_sport: dict[str, Any] = {}
        paid_calls = 0
        for sk in order:
            items = groups[sk]
            ps: dict[str, Any] = {"fixtures": len(items)}
            per_sport[sk] = ps
            if max_paid_calls is not None and paid_calls >= max_paid_calls:
                ps["status"] = "SKIPPED_MAX_PAID_CALLS"
                continue
            if sk not in active:
                ps["status"] = "SPORT_NOT_ACTIVE"
                _no_call_row(ledger, now, batch_id, sk, "SPORT_NOT_ACTIVE", items)
                continue
            has_close = any(p == "close" for _, p in items)
            if events_cost:
                g = decide(
                    ledger,
                    cfg,
                    now=now,
                    cost=events_cost,
                    remaining_now=remaining,
                    close_capture=has_close,
                )
                if not g["allowed"]:
                    ps["status"] = f"{STATUS_BLOCKED}:events:{g['reason']}"
                    continue
            kos = [d.kickoff_utc for d, _ in items]
            ev_resp = client.get_events(
                sk, min(kos) - timedelta(hours=3), max(kos) + timedelta(hours=3)
            )
            c, basis = (
                charge(ev_resp.quota, events_cost)
                if ev_resp.http_status is not None
                else (0, "NO_RESPONSE")
            )
            ledger.append(
                now,
                _row(
                    ev_resp,
                    batch_id=batch_id,
                    status=STATUS_OK if ev_resp.ok else STATUS_FAILED,
                    credits_charged=c,
                    charge_basis=basis,
                ),
            )
            stats["calls"].append(ev_resp.meta())
            stats["credits_charged"] += c
            remaining = _remaining(ev_resp, remaining)
            if not ev_resp.ok:
                ps["status"] = "EVENTS_FAILED"
                continue
            fx_by_event, jstats = join_events(
                ev_resp.payload or [], [d for d, _ in items], registry, cfg
            )
            ps["join"] = jstats
            if not fx_by_event:
                ps["status"] = "NO_JOINED_EVENTS"
                _no_call_row(ledger, now, batch_id, sk, "NO_JOINED_EVENTS", items)
                continue
            purpose_of = {d.fixture_id: p for d, p in items}
            joined_close = [
                f.fixture_id for f in fx_by_event.values() if purpose_of[f.fixture_id] == "close"
            ]
            joined_entry = [
                f.fixture_id for f in fx_by_event.values() if purpose_of[f.fixture_id] == "entry"
            ]
            joined_other = [
                f.fixture_id
                for f in fx_by_event.values()
                if purpose_of[f.fixture_id] not in ("entry", "close")
            ]
            g = decide(
                ledger,
                cfg,
                now=now,
                cost=cost,
                remaining_now=remaining,
                close_capture=bool(joined_close),
            )
            if not g["allowed"]:
                ledger.append(
                    now,
                    {
                        "kind": "odds",
                        "sport_key": sk,
                        "batch_id": batch_id,
                        "status": STATUS_BLOCKED,
                        "request_made": False,
                        "credits_charged": 0,
                        "close_fixtures": joined_close,
                        "entry_fixtures": joined_entry,
                        "other_fixtures": joined_other,
                        "purpose": force_purpose,
                        **g,
                    },
                )
                ps["status"] = f"{STATUS_BLOCKED}:{g['reason']}"
                continue
            if claim_fn is not None:
                idents = {
                    f"the_odds_api|{purpose_of[f.fixture_id]}|{f.fixture_id}": ev
                    for ev, f in fx_by_event.items()
                }
                won = claim_fn(sorted(idents))
                lost = [i for i in idents if i not in won]
                if lost:
                    ps["claimed_elsewhere"] = len(lost)
                fx_by_event = {ev: fx_by_event[ev] for i, ev in idents.items() if i in won}
                joined_close = [f for f in joined_close if f"the_odds_api|close|{f}" in won]
                joined_entry = [f for f in joined_entry if f"the_odds_api|entry|{f}" in won]
                joined_other = [
                    f for f in joined_other if f"the_odds_api|{purpose_of[f]}|{f}" in won
                ]
                if not fx_by_event:
                    ps["status"] = "NO_ACTION_ALREADY_CLAIMED"
                    continue
            od = client.get_odds(
                sk, event_ids=sorted(fx_by_event), markets=cfg.markets, bookmakers=cfg.bookmakers
            )
            paid_calls += 1
            stats["paid_calls"] += 1
            # a paid call with no response may still have been billed: charge the design cost
            c, basis = (
                charge(od.quota, cost)
                if od.http_status is not None
                else (cost, "NO_RESPONSE_DESIGN_COST")
            )
            stats["credits_charged"] += c
            stats["calls"].append(od.meta())
            remaining = _remaining(od, remaining)
            written = incomplete = 0
            quoted: set[str] = set()
            if od.ok:
                captured_at = od.responded_at or now
                path = (
                    out_root / "reference" / f"{captured_at:%Y-%m-%d}" / f"oddsapi-{batch_id}.jsonl"
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a") as fh:
                    for ev in od.payload or []:
                        fx = fx_by_event.get(ev.get("id"))
                        if fx is None:
                            continue
                        snaps, inc = snapshots_from_event(ev, fx, captured_at)
                        incomplete += inc
                        if snaps:
                            quoted.add(fx.fixture_id)
                        for sn in snaps:
                            fh.write(
                                json.dumps(sn.to_record(batch_id), sort_keys=True, default=str)
                                + "\n"
                            )
                            written += 1
                raw = (
                    out_root
                    / "odds_api"
                    / "raw"
                    / f"{captured_at:%Y-%m-%d}"
                    / f"{batch_id}-{sk}.json.gz"
                )
                raw.parent.mkdir(parents=True, exist_ok=True)
                raw.write_bytes(
                    gzip.compress(
                        json.dumps(
                            {"meta": od.meta(), "payload": od.payload}, sort_keys=True, default=str
                        ).encode()
                    )
                )
            ledger.append(
                now,
                _row(
                    od,
                    batch_id=batch_id,
                    status=STATUS_OK if od.ok else STATUS_FAILED,
                    request_made=True,
                    credits_charged=c,
                    charge_basis=basis,
                    close_fixtures=joined_close if od.ok else [],
                    entry_fixtures=joined_entry if od.ok else [],
                    other_fixtures=joined_other,
                    unjoined_fixtures=jstats.get("unjoined_fixtures", []),
                    quoted_fixtures=sorted(quoted),
                    purpose=force_purpose,
                    snapshots_written=written,
                    incomplete_markets=incomplete,
                    **g,
                ),
            )
            stats["snapshots"] += written
            ps.update(
                status=STATUS_OK if od.ok else STATUS_FAILED,
                credits=c,
                snapshots=written,
                incomplete_markets=incomplete,
                close_fixtures=len(joined_close),
                entry_fixtures=len(joined_entry),
            )
        stats["per_sport"] = per_sport
        stats["remaining_after"] = remaining
        stats["status"] = STATUS_OK
        return stats
    finally:
        client.close()


def _no_call_row(  # noqa: PLR0917
    ledger: BudgetLedger,
    now: datetime,
    batch_id: str,
    sport_key: str,
    status: str,
    items: list[tuple[DueFixture, str]],
) -> None:
    """Record a window where no paid call was possible (sport inactive, no joinable event)."""
    ledger.append(
        now,
        {
            "kind": "odds",
            "sport_key": sport_key,
            "status": status,
            "batch_id": batch_id,
            "request_made": False,
            "credits_charged": 0,
            "close_fixtures": [d.fixture_id for d, p in items if p == "close"],
            "entry_fixtures": [d.fixture_id for d, p in items if p == "entry"],
        },
    )


def _remaining(resp: OddsApiResponse, default: int | None = None) -> int | None:
    v = resp.quota.get("x-requests-remaining")
    try:
        return int(float(v)) if v is not None else default
    except (TypeError, ValueError):
        return default


def status_summary(stats: dict[str, Any], now: datetime) -> dict[str, Any]:
    return {"captured_at": iso_utc(now), **{k: v for k, v in stats.items() if k != "calls"}}
