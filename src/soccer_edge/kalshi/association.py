"""Associate a classified contract with a physical fixture / competition / player.

Kalshi event tickers carry a US-local date and 2-4 letter team codes. Team codes are NOT a
stable identity, so the mapping goes: event title -> registry aliases (competition-scoped) ->
team ids -> fixture within +-1 day of the ticker date. Anything that does not resolve
unambiguously is UNMAPPED (retained, counted, never guessed).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from soccer_edge.core.errors import AmbiguousAliasError, UnknownAliasError
from soccer_edge.identity.models import Fixture
from soccer_edge.identity.registry import AliasRegistry
from soccer_edge.kalshi.schemas import RawEvent
from soccer_edge.kalshi.taxonomy import ContractSpec, Scope

_VS = re.compile(r"^(?P<a>.+?)\s+(?:vs\.?|v\.?|at|@|-)\s+(?P<b>.+?)(?:\s*[:(].*)?$", re.IGNORECASE)


@dataclass(frozen=True)
class Association:
    ticker: str
    status: str  # mapped | unmapped_event | unmapped_team | ambiguous_team | competition_only | no_fixture | not_match_scope
    fixture_id: str | None = None
    competition_id: str | None = None
    home_team_id: str | None = None
    away_team_id: str | None = None
    side_team_id: str | None = None
    detail: str = ""


def _split_title(title: str) -> tuple[str, str] | None:
    m = _VS.match(title.strip())
    if not m:
        return None
    return m["a"].strip(), m["b"].strip()


def associate(
    spec: ContractSpec,
    event: RawEvent | None,
    registry: AliasRegistry,
    fixtures_by_teams: dict[tuple[str, str], list[Fixture]],
) -> Association:
    tk = spec.ticker
    if spec.scope is Scope.COMPETITION:
        return Association(tk, "competition_only", competition_id=spec.competition_id)
    if spec.scope not in (Scope.MATCH, Scope.PLAYER):
        return Association(tk, "not_match_scope", detail=f"scope={spec.scope.value}")
    if spec.competition_id is None:
        return Association(
            tk,
            "unmapped_event",
            detail=f"competition code {spec.competition_code!r} has no canonical id",
        )
    if event is None:
        return Association(
            tk,
            "unmapped_event",
            competition_id=spec.competition_id,
            detail="event metadata missing",
        )
    pair = _split_title(event.title) or _split_title(event.sub_title)
    if pair is None:
        return Association(
            tk,
            "unmapped_event",
            competition_id=spec.competition_id,
            detail=f"cannot split title {event.title!r}",
        )
    comp = registry.competitions.get(spec.competition_id)
    ids = []
    for name in pair:
        try:
            ids.append(
                registry.resolve_team(
                    name,
                    country=comp.country
                    if comp and comp.country not in ("UEFA", "FIFA", "CONMEBOL", "CONCACAF")
                    else None,
                    gender=comp.gender if comp else None,
                ).team_id
            )
        except AmbiguousAliasError as exc:
            return Association(
                tk, "ambiguous_team", competition_id=spec.competition_id, detail=str(exc)[:160]
            )
        except UnknownAliasError:
            return Association(
                tk,
                "unmapped_team",
                competition_id=spec.competition_id,
                detail=f"unknown team {name!r}",
            )
    a, b = ids
    # Verified on live soccer tickers: event titles and event codes are HOME then AWAY
    # ('Sao Paulo vs Santos' -> SPASAN). Prefer that orientation, fall back to the reverse.
    candidates = fixtures_by_teams.get((a, b), []) + fixtures_by_teams.get((b, a), [])
    target = (
        date.fromisoformat(spec.event_date)
        if spec.event_date
        else (event.strike_date.date() if event.strike_date else None)
    )
    chosen: Fixture | None = None
    for fx in candidates:
        fd = date.fromisoformat(fx.kickoff_date)
        if target is None or abs(fd - target) <= timedelta(days=1):
            chosen = fx if chosen is None else chosen
    if chosen is None:
        return Association(
            tk,
            "no_fixture",
            competition_id=spec.competition_id,
            home_team_id=b,
            away_team_id=a,
            detail=f"no fixture within 1 day of {target}",
        )
    side = None
    if spec.side_team_code:
        # map side code to whichever team name starts with the code letters (best effort, else None)
        code = spec.side_team_code.upper()
        for tid in (chosen.home_team_id, chosen.away_team_id):
            t = registry.teams[tid]
            if any(_code_matches(code, alias) for alias in (t.name, *t.aliases)):
                side = tid
                break
    return Association(
        tk,
        "mapped",
        fixture_id=chosen.fixture_id,
        competition_id=chosen.competition_id,
        home_team_id=chosen.home_team_id,
        away_team_id=chosen.away_team_id,
        side_team_id=side,
    )


def _code_matches(code: str, alias: str) -> bool:
    letters = re.sub(r"[^A-Z]", "", alias.upper())
    words = [re.sub(r"[^A-Z]", "", w.upper()) for w in alias.split()]
    initials = "".join(w[:1] for w in words if w)
    return (
        letters.startswith(code)
        or initials == code
        or (len(words) > 1 and words[-1].startswith(code))
        or words[0].startswith(code)
    )


def index_fixtures(fixtures: list[Fixture]) -> dict[tuple[str, str], list[Fixture]]:
    out: dict[tuple[str, str], list[Fixture]] = {}
    for f in fixtures:
        out.setdefault((f.home_team_id, f.away_team_id), []).append(f)
    return out
