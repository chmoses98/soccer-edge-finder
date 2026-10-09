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
    status: str  # mapped | unmapped_event | unmapped_team | ambiguous_team | side_conflict | competition_only | no_fixture | not_match_scope
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
    if spec.side_team_code and spec.side_team_code != "DRAW":
        side, conflict = _resolve_side_team(
            spec.side_team_code.upper(), spec.team_codes, (a, b), chosen, registry
        )
        if conflict:
            # never guess an orientation: a contract whose team cannot be placed is not priced
            return Association(
                tk,
                "side_conflict",
                fixture_id=chosen.fixture_id,
                competition_id=chosen.competition_id,
                home_team_id=chosen.home_team_id,
                away_team_id=chosen.away_team_id,
                detail=conflict,
            )
    return Association(
        tk,
        "mapped",
        fixture_id=chosen.fixture_id,
        competition_id=chosen.competition_id,
        home_team_id=chosen.home_team_id,
        away_team_id=chosen.away_team_id,
        side_team_id=side,
    )


def structural_position(code: str, pair: str | None) -> int | None:
    """Where a leg's team code sits in the event pair code ('VDGCR': VDG -> 0, CR -> 1).

    Event titles and pair codes are both HOME then AWAY (verified live: 'Sao Paulo vs Santos' ->
    SPASAN), so the position is read in event-title order. Returns None when the code cannot be
    placed, or when it fits both ends (e.g. pair 'CRCR'), so a coincidence never decides a side."""
    if not code or not pair or len(pair) <= len(code):
        return None
    first, second = pair.startswith(code), pair.endswith(code)
    if first == second:
        return None
    return 0 if first else 1


def _resolve_side_team(
    code: str,
    pair: str | None,
    title_ids: tuple[str, str],
    fx: Fixture,
    registry: AliasRegistry,
) -> tuple[str | None, str]:
    """Team a leg code refers to -> (team_id | None, conflict_detail).

    Two independent pieces of evidence: the code's position in the event pair code (structural, in
    event-title order) and the fixture teams whose names/aliases match the code. Name matching alone
    is unsafe ('CR' matches 'CR Vasco da Gama' as well as 'Clube do Remo'), so:
      - names match exactly one team and the structure agrees (or is silent) -> that team;
      - names match both teams and the structure places the code -> the structural team;
      - names match no team -> None (the pipeline's positional fallback decides, as before);
      - names match exactly one team and the structure places the code on the OTHER team -> conflict
        (the contract is unmappable; it is never priced on a guessed side).
    A conflict detail is returned non-empty only in that last case."""
    fixture_ids = (fx.home_team_id, fx.away_team_id)
    named = [
        tid
        for tid in fixture_ids
        if any(
            _code_matches(code, alias)
            for alias in (registry.teams[tid].name, *registry.teams[tid].aliases)
        )
    ]
    pos = structural_position(code, pair)
    structural = title_ids[pos] if pos is not None and title_ids[pos] in fixture_ids else None
    if len(named) == 1:
        if structural is not None and structural != named[0]:
            return None, (
                f"side code {code!r} names {named[0]} but sits at position {pos} of pair "
                f"{pair!r} ({structural})"
            )
        return named[0], ""
    if len(named) == 2:
        # the code fits both names (e.g. 'CR': 'CR Vasco da Gama' and 'Clube do Remo'): only the
        # structure can place it; without it the side stays unresolved (never the first match)
        return structural, ""
    # no name matches: unchanged behaviour - left to the pipeline's positional fallback
    return None, ""


# connecting particles left out of a club's initials ('Clube do Remo' -> CR)
_PARTICLES = frozenset(
    {"DA", "DAS", "DE", "DEL", "DI", "DO", "DOS", "DU", "E", "LA", "LE", "OF", "THE", "Y"}
)


def _code_matches(code: str, alias: str) -> bool:
    letters = re.sub(r"[^A-Z]", "", alias.upper())
    words = [re.sub(r"[^A-Z]", "", w.upper()) for w in alias.split()]
    initials = "".join(w[:1] for w in words if w)
    content_initials = "".join(w[:1] for w in words if w and w not in _PARTICLES)
    return (
        letters.startswith(code)
        or initials == code
        or (len(content_initials) > 1 and content_initials == code)
        or (len(words) > 1 and words[-1].startswith(code))
        or words[0].startswith(code)
    )


def index_fixtures(fixtures: list[Fixture]) -> dict[tuple[str, str], list[Fixture]]:
    out: dict[tuple[str, str], list[Fixture]] = {}
    for f in fixtures:
        out.setdefault((f.home_team_id, f.away_team_id), []).append(f)
    return out
