"""openfootball/football.json fixture + result provider (free, public domain, GitHub-hosted).

Coverage verified 2026-09-27 from a cloud runner: 2026-27 files exist for en.1, en.2, es.1, de.1,
it.1; fr.1 is only published through 2025-26; UEFA competitions are not in football.json.
Kickoff times are local to the competition country and are converted with zoneinfo; the
observation is flagged UNVERIFIED for time zone because openfootball does not state it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from soccer_edge.core.errors import ProviderError
from soccer_edge.identity.models import Fixture, FixtureStatus
from soccer_edge.identity.registry import AliasRegistry
from soccer_edge.providers.base import Observation, QualityFlag
from soccer_edge.providers.http import CachedFetcher
from soccer_edge.providers.interfaces import MatchResult

RAW_BASE = "https://raw.githubusercontent.com/openfootball/football.json/master"

# competition_id -> (openfootball file stem, IANA zone for kickoff times)
COMPETITION_FILES: dict[str, tuple[str, str]] = {
    "eng.premier_league": ("en.1", "Europe/London"),
    "eng.championship": ("en.2", "Europe/London"),
    "esp.la_liga": ("es.1", "Europe/Madrid"),
    "ger.bundesliga": ("de.1", "Europe/Berlin"),
    "ita.serie_a": ("it.1", "Europe/Rome"),
    "fra.ligue_1": ("fr.1", "Europe/Paris"),
    "ned.eredivisie": ("nl.1", "Europe/Amsterdam"),
    "por.primeira_liga": ("pt.1", "Europe/Lisbon"),
    "tur.super_lig": ("tr.1", "Europe/Istanbul"),
}

LICENSE = "Public domain (openfootball: CC0 / 'free public domain' per repo README)"


def season_dir(season_id: str) -> str:
    # '2026-27' -> '2026-27'; calendar seasons are not used by openfootball for these leagues
    return season_id


class OpenFootballProvider:
    provider_id = "openfootball"

    def __init__(self, registry: AliasRegistry, fetcher: CachedFetcher | None = None) -> None:
        self.registry = registry
        self.fetcher = fetcher or CachedFetcher()

    def _load(self, competition_id: str, season_id: str) -> tuple[dict, object]:
        if competition_id not in COMPETITION_FILES:
            raise ProviderError(f"openfootball has no file mapping for {competition_id}")
        stem, _ = COMPETITION_FILES[competition_id]
        url = f"{RAW_BASE}/{season_dir(season_id)}/{stem}.json"
        fetched = self.fetcher.fetch(url, source=self.provider_id, license_note=LICENSE)
        try:
            payload = json.loads(fetched.content)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"openfootball payload not JSON: {url}") from exc
        if "matches" not in payload:
            raise ProviderError(f"openfootball payload missing 'matches': {url}")
        return payload, fetched.provenance

    def _team(self, name: str, competition_id: str) -> str:
        comp = self.registry.competitions[competition_id]
        return self.registry.resolve_team(name, country=comp.country, gender=comp.gender).team_id

    def fixtures(self, competition_id: str, season_id: str) -> Observation[list[Fixture]]:
        payload, prov = self._load(competition_id, season_id)
        _, zone_name = COMPETITION_FILES[competition_id]
        zone = ZoneInfo(zone_name)
        out: list[Fixture] = []
        seen: dict[str, int] = {}
        for m in payload["matches"]:
            home = self._team(m["team1"], competition_id)
            away = self._team(m["team2"], competition_id)
            stage = m.get("round")
            base_id = Fixture.make_id(competition_id, season_id, home, away, stage=stage)
            occ = seen.get(base_id, 0) + 1
            seen[base_id] = occ
            fid = Fixture.make_id(
                competition_id, season_id, home, away, stage=stage, occurrence=occ
            )
            kickoff = None
            if m.get("time"):
                local = datetime.fromisoformat(f"{m['date']}T{m['time']}:00").replace(tzinfo=zone)
                kickoff = local.astimezone(UTC)
            status = (
                FixtureStatus.FINISHED
                if "score" in m and "ft" in m["score"]
                else FixtureStatus.SCHEDULED
            )
            out.append(
                Fixture(
                    fixture_id=fid,
                    competition_id=competition_id,
                    season_id=season_id,
                    home_team_id=home,
                    away_team_id=away,
                    kickoff_utc=kickoff,
                    kickoff_date=m["date"],
                    status=status,
                    stage=stage,
                    occurrence=occ,
                )
            )
        return Observation(
            payload=out,
            provenance=prov,
            flags=(QualityFlag.UNVERIFIED,),
            notes=(
                "kickoff time zone assumed from competition country; openfootball does not declare it",
            ),
        )

    def results(self, competition_id: str, season_id: str) -> Observation[list[MatchResult]]:
        fx = self.fixtures(competition_id, season_id)
        payload, _ = self._load(competition_id, season_id)
        results: list[MatchResult] = []
        by_key = {(f.home_team_id, f.away_team_id, f.stage, f.occurrence): f for f in fx.payload}
        seen: dict[tuple, int] = {}
        for m in payload["matches"]:
            score = m.get("score") or {}
            if "ft" not in score:
                continue
            home = self._team(m["team1"], competition_id)
            away = self._team(m["team2"], competition_id)
            key0 = (home, away, m.get("round"))
            occ = seen.get(key0, 0) + 1
            seen[key0] = occ
            f = by_key[(home, away, m.get("round"), occ)]
            ht = score.get("ht")
            results.append(
                MatchResult(
                    fixture_id=f.fixture_id,
                    competition_id=competition_id,
                    season_id=season_id,
                    match_date=m["date"],
                    home_team_id=home,
                    away_team_id=away,
                    home_goals=int(score["ft"][0]),
                    away_goals=int(score["ft"][1]),
                    home_goals_ht=int(ht[0]) if ht else None,
                    away_goals_ht=int(ht[1]) if ht else None,
                )
            )
        return Observation(
            payload=results, provenance=fx.provenance, flags=fx.flags, notes=fx.notes
        )
