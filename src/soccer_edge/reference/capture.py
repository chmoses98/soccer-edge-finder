"""Turn football-data.co.uk upcoming odds into point-in-time ReferenceMarketSnapshots.

Consensus rule (documented, deliberately simple): football-data.co.uk's own multi-book average
columns (`AvgH/AvgD/AvgA`, `Avg>2.5/Avg<2.5`) when present, else the plain mean of the de-vigged
probabilities of the named books available (bet365, pinnacle). The named oracle for research and
CLV is `bet365` (the only book with 26 seasons of history); `pinnacle` is recorded when present
because it is the sharper reference. No source here carries size, so 'liquidity' is unknown.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any

import numpy as np

from soccer_edge.core.time import ensure_utc
from soccer_edge.families.base import devig_power, devig_proportional
from soccer_edge.identity.models import Fixture
from soccer_edge.providers.interfaces import OddsQuote
from soccer_edge.reference.close import NEAR_CLOSE_MAX_MINUTES
from soccer_edge.reference.quality import quality_for_bookmaker
from soccer_edge.reference.schemas import DevigMethod, ReferenceMarketSnapshot

MARKET_FAMILY_FOR = {"1x2": "match_result_3way", "ou": "total_goals", "ah": "handicap"}

SELECTION_ORDER = {"1x2": ("home", "draw", "away"), "ou": ("over", "under"), "ah": ("home", "away")}


def join_to_fixtures(quotes: list[OddsQuote], fixtures: list[Fixture]) -> dict[str, Fixture]:
    """Map provider fixture ids (comp:season:home:away:<date>) to canonical fixtures by teams and date (+-1 day)."""
    by_pair: dict[tuple[str, str], list[Fixture]] = defaultdict(list)
    for f in fixtures:
        by_pair[(f.home_team_id, f.away_team_id)].append(f)
    out: dict[str, Fixture] = {}
    for q in quotes:
        if q.fixture_id in out:
            continue
        parts = q.fixture_id.split(":")
        if len(parts) < 6:
            continue
        home, away, day = parts[3], parts[4], parts[5].replace("_", "-")
        for f in by_pair.get((home, away), []):
            fd = datetime.fromisoformat(f.kickoff_date).date()
            qd = datetime.fromisoformat(day).date()
            if abs((fd - qd).days) <= 1:
                out[q.fixture_id] = f
                break
    return out


def build_snapshots(
    quotes: list[OddsQuote],
    fixtures: list[Fixture],
    *,
    captured_at: datetime,
    source: str = "football_data_couk_fixtures",
    devig: DevigMethod = DevigMethod.PROPORTIONAL,
) -> tuple[list[ReferenceMarketSnapshot], dict[str, Any]]:
    captured_at = ensure_utc(captured_at)
    fx_map = join_to_fixtures(quotes, fixtures)
    groups: dict[tuple[str, str, str, Decimal | None], dict[str, OddsQuote]] = defaultdict(dict)
    for q in quotes:
        groups[
            (
                q.fixture_id,
                q.bookmaker,
                q.market,
                Decimal(str(q.line)) if q.line is not None else None,
            )
        ][q.selection] = q
    snaps: list[ReferenceMarketSnapshot] = []
    unmapped = 0
    incomplete = 0
    for (pfid, book, market, line), sels in groups.items():
        fx = fx_map.get(pfid)
        if fx is None:
            unmapped += 1
            continue
        order = SELECTION_ORDER.get(market)
        if order is None or any(s not in sels for s in order):
            incomplete += 1
            continue
        odds = np.array([[sels[s].decimal_odds for s in order]])
        inv = 1.0 / odds[0]
        probs = (
            devig_proportional(odds)[0]
            if devig is DevigMethod.PROPORTIONAL
            else devig_power(odds)[0]
        )
        mins = (fx.kickoff_utc - captured_at).total_seconds() / 60 if fx.kickoff_utc else None
        for i, s in enumerate(order):
            snaps.append(
                ReferenceMarketSnapshot(
                    source=source,
                    bookmaker=book,
                    fixture_id=fx.fixture_id,
                    competition_id=fx.competition_id,
                    home_team_id=fx.home_team_id,
                    away_team_id=fx.away_team_id,
                    kickoff_utc=fx.kickoff_utc,
                    market=market,
                    selection=s,
                    line=line,
                    raw_odds=Decimal(str(sels[s].decimal_odds)),
                    implied_probability=float(inv[i]),
                    devig_method=devig,
                    devigged_probability=float(probs[i]),
                    overround=float(inv.sum()),
                    captured_at=captured_at,
                    quoted_at=None,
                    is_closing=False,
                    minutes_to_kickoff=mins,
                    market_family=MARKET_FAMILY_FOR.get(market),
                    side=s,
                    decimal_odds=Decimal(str(sels[s].decimal_odds)),
                    horizon_seconds=(mins * 60) if mins is not None else None,
                    is_open=False,
                    is_close_candidate=(mins is not None and 0 <= mins <= NEAR_CLOSE_MAX_MINUTES),
                    source_quality=quality_for_bookmaker(book).value,
                )
            )
    snaps.extend(consensus_snapshots(snaps))
    return snaps, {
        "groups": len(groups),
        "unmapped_fixture_groups": unmapped,
        "incomplete_groups": incomplete,
        "snapshots": len(snaps),
    }


def consensus_snapshots(snaps: list[ReferenceMarketSnapshot]) -> list[ReferenceMarketSnapshot]:
    """Consensus = 'average' book when present else mean of named books; labelled 'consensus'."""
    by_key: dict[tuple, dict[str, ReferenceMarketSnapshot]] = defaultdict(dict)
    for s in snaps:
        if s.bookmaker in ("consensus", "max"):
            continue
        by_key[(s.fixture_id, s.market, s.line, s.selection)][s.bookmaker] = s
    out = []
    for _key, books in by_key.items():
        if "average" in books:
            base = books["average"]
            p = base.devigged_probability
            raw = base.raw_odds
            n = 1
        else:
            named = [b for name, b in books.items() if name in ("bet365", "pinnacle")]
            if not named:
                continue
            p = float(np.mean([b.devigged_probability for b in named]))
            raw = Decimal(str(round(1 / max(p, 1e-6), 4)))
            base = named[0]
            n = len(named)
        out.append(
            base.model_copy(
                update={
                    "bookmaker": "consensus",
                    "raw_odds": raw,
                    "implied_probability": p,
                    "devigged_probability": p,
                    "decimal_odds": raw,
                    "source_quality": quality_for_bookmaker("consensus").value,
                    "liquidity_note": f"consensus of {n} source(s): football-data.co.uk average when present, else mean of named books",
                }
            )
        )
    return out


def reference_lookup(
    snaps: list[ReferenceMarketSnapshot], bookmaker: str = "consensus"
) -> dict[tuple[str, str, str, Decimal | None], float]:
    """(fixture_id, market, selection, line) -> de-vigged probability for one bookmaker."""
    return {
        (s.fixture_id, s.market, s.selection, s.line): s.devigged_probability
        for s in snaps
        if s.bookmaker == bookmaker
    }


def reference_for_contract(
    lookup: dict, fixture_id: str, family: str, side: str | None, line: Decimal | None
) -> float | None:
    """Map a Kalshi contract's semantics to a reference probability when the reference market exists."""
    if family in ("match_result_3way",) and side in ("home", "draw", "away"):
        return lookup.get((fixture_id, "1x2", side, None))
    if family == "total_goals" and line is not None:
        p = lookup.get((fixture_id, "ou", "over", Decimal(str(line))))
        return p
    if family == "double_chance" and side:
        h, d, a = (lookup.get((fixture_id, "1x2", s, None)) for s in ("home", "draw", "away"))
        if None in (h, d, a):
            return None
        return {"home": h + d, "away": a + d, "draw": h + a}.get(side)
    if family == "handicap" and line is not None and side in ("home", "away"):
        # only exact half-line matches are comparable
        return lookup.get((fixture_id, "ah", side, Decimal(str(line))))
    return None
