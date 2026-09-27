"""Alias registry with loud failure on ambiguity.

An alias is matched inside a *scope* (gender, country, team kind). If more than one
canonical entity matches after scoping, `AmbiguousAliasError` is raised: we never guess.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from soccer_edge.core.errors import AmbiguousAliasError, UnknownAliasError
from soccer_edge.identity.models import Competition, Gender, Player, Team, TeamKind

_PUNCT = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")
# Tokens that are commonly dropped by data vendors; only used for a *secondary* lookup.
_WEAK_TOKENS = {
    "fc",
    "afc",
    "cf",
    "sc",
    "ac",
    "as",
    "ss",
    "ssc",
    "us",
    "rc",
    "rcd",
    "cd",
    "ud",
    "sv",
    "fk",
    "bk",
    "if",
    "de",
    "club",
    "1",
    "the",
}


def normalize_alias(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace("&", " and ").replace("'", "").replace("’", "")
    text = _PUNCT.sub(" ", text)
    return _WS.sub(" ", text).strip()


def _weak_form(norm: str) -> str:
    toks = [t for t in norm.split(" ") if t not in _WEAK_TOKENS]
    return " ".join(toks) if toks else norm


class AliasRegistry:
    def __init__(self) -> None:
        self.teams: dict[str, Team] = {}
        self.competitions: dict[str, Competition] = {}
        self.players: dict[str, Player] = {}
        self._team_alias: dict[str, set[str]] = defaultdict(set)
        self._team_weak: dict[str, set[str]] = defaultdict(set)
        self._comp_alias: dict[str, set[str]] = defaultdict(set)
        self._player_alias: dict[str, set[str]] = defaultdict(set)

    # ---- loading -------------------------------------------------------------------------
    @classmethod
    def from_directory(cls, directory: Path) -> AliasRegistry:
        reg = cls()
        for path in sorted(directory.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            for c in payload.get("competitions", []):
                reg.add_competition(Competition(**c))
            for t in payload.get("teams", []):
                reg.add_team(Team(**t))
            for p in payload.get("players", []):
                reg.add_player(Player(**p))
        return reg

    def add_team(self, team: Team) -> None:
        if team.team_id in self.teams:
            raise ValueError(f"duplicate team_id {team.team_id}")
        self.teams[team.team_id] = team
        for alias in (team.name, *team.aliases):
            norm = normalize_alias(alias)
            self._team_alias[norm].add(team.team_id)
            self._team_weak[_weak_form(norm)].add(team.team_id)

    def add_competition(self, comp: Competition) -> None:
        if comp.competition_id in self.competitions:
            raise ValueError(f"duplicate competition_id {comp.competition_id}")
        self.competitions[comp.competition_id] = comp
        for alias in (comp.name, *comp.aliases, *comp.former_names):
            self._comp_alias[normalize_alias(alias)].add(comp.competition_id)

    def add_player(self, player: Player) -> None:
        if player.player_id in self.players:
            raise ValueError(f"duplicate player_id {player.player_id}")
        self.players[player.player_id] = player
        for alias in (player.name, *player.aliases):
            self._player_alias[normalize_alias(alias)].add(player.player_id)

    # ---- resolution ----------------------------------------------------------------------
    def resolve_team(
        self,
        alias: str,
        *,
        country: str | None = None,
        gender: Gender | None = None,
        kind: TeamKind | None = None,
        allow_weak: bool = True,
    ) -> Team:
        norm = normalize_alias(alias)
        candidates = self._filter_teams(self._team_alias.get(norm, set()), country, gender, kind)
        if not candidates and allow_weak:
            candidates = self._filter_teams(
                self._team_weak.get(_weak_form(norm), set()), country, gender, kind
            )
        if not candidates:
            raise UnknownAliasError(
                f"unknown team alias {alias!r} (scope country={country} gender={gender} kind={kind})"
            )
        if len(candidates) > 1:
            raise AmbiguousAliasError(
                f"team alias {alias!r} is ambiguous within scope country={country} gender={gender} kind={kind}: "
                + ", ".join(sorted(candidates))
            )
        return self.teams[next(iter(candidates))]

    def _filter_teams(
        self, ids: Iterable[str], country: str | None, gender: Gender | None, kind: TeamKind | None
    ) -> set[str]:
        out = set()
        for tid in ids:
            t = self.teams[tid]
            if country and t.country != country:
                continue
            if gender and t.gender != gender:
                continue
            if kind and t.kind != kind:
                continue
            out.add(tid)
        return out

    def resolve_competition(self, alias: str, *, gender: Gender | None = None) -> Competition:
        ids = {
            cid
            for cid in self._comp_alias.get(normalize_alias(alias), set())
            if gender is None or self.competitions[cid].gender == gender
        }
        if not ids:
            raise UnknownAliasError(f"unknown competition alias {alias!r}")
        if len(ids) > 1:
            raise AmbiguousAliasError(f"competition alias {alias!r} is ambiguous: {sorted(ids)}")
        return self.competitions[next(iter(ids))]

    def resolve_player(self, alias: str, *, team_hint: str | None = None) -> Player:
        ids = set(self._player_alias.get(normalize_alias(alias), set()))
        if not ids:
            raise UnknownAliasError(f"unknown player alias {alias!r}")
        if len(ids) > 1:
            raise AmbiguousAliasError(f"player alias {alias!r} is ambiguous: {sorted(ids)}")
        return self.players[next(iter(ids))]

    # ---- diagnostics ---------------------------------------------------------------------
    def ambiguous_team_aliases(self) -> dict[str, set[str]]:
        """Aliases that collide *within the same scope* (country+gender+kind)."""
        out: dict[str, set[str]] = {}
        for alias, ids in self._team_alias.items():
            if len(ids) < 2:
                continue
            scopes = defaultdict(set)
            for tid in ids:
                t = self.teams[tid]
                scopes[(t.country, t.gender, t.kind)].add(tid)
            for members in scopes.values():
                if len(members) > 1:
                    out[alias] = members
        return out
