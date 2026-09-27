"""Historical results + Bet365 pre-match odds + ClubElo provider.

Source: github.com/xgabora/Club-Football-Match-Data-2000-2025 (Matches.csv), which is a
redistribution of football-data.co.uk results/odds and clubelo.com ratings. 238k matches
2000-07 .. 2026-09 across 38 divisions. Reachable from GitHub raw (verified 2026-09-27).

Semantics that matter for research honesty:
* OddHome/OddDraw/OddAway are Bet365 *pre-match* odds as collected by football-data.co.uk.
  They are NOT verified closing lines. MARKET_ONLY built on them is a "pre-close bookmaker"
  benchmark, and is labelled that way.
* Elo columns are the rating *before* the match (per README), so they are point-in-time.
* Teams outside the canonical registry receive deterministic provisional ids
  (``prov.fd.<division>.<slug>``). Provisional ids are for research only; production paths
  reject them.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Iterable
from dataclasses import dataclass

from soccer_edge.core.errors import UnknownAliasError
from soccer_edge.identity.models import Fixture, Gender
from soccer_edge.identity.registry import AliasRegistry
from soccer_edge.providers.base import Observation, QualityFlag
from soccer_edge.providers.http import CachedFetcher
from soccer_edge.providers.interfaces import MatchResult, OddsQuote

MATCHES_URL = "https://raw.githubusercontent.com/xgabora/Club-Football-Match-Data-2000-2025/main/data/Matches.csv"
LICENSE = "Redistributed football-data.co.uk + ClubElo data; see upstream README (research use)"

DIVISION_TO_COMPETITION: dict[str, tuple[str, str]] = {
    "E0": ("eng.premier_league", "ENG"),
    "E1": ("eng.championship", "ENG"),
    "SP1": ("esp.la_liga", "ESP"),
    "D1": ("ger.bundesliga", "GER"),
    "I1": ("ita.serie_a", "ITA"),
    "F1": ("fra.ligue_1", "FRA"),
    "N1": ("ned.eredivisie", "NED"),
    "P1": ("por.primeira_liga", "POR"),
    "T1": ("tur.super_lig", "TUR"),
    "SC0": ("sco.premiership", "SCO"),
    "USA": ("usa.mls", "USA"),
    "MEX": ("mex.liga_mx", "MEX"),
    "BRA": ("bra.serie_a", "BRA"),
    "ARG": ("arg.primera", "ARG"),
}

# calendar-year seasons (season_id '2026'), everything else is split-year ('2026-27')
CALENDAR_YEAR_DIVISIONS = {"USA", "BRA", "ARG", "NOR", "SWE", "FIN", "IRL", "JAP", "CHN"}


def season_id_for(division: str, match_date: str) -> str:
    year = int(match_date[:4])
    month = int(match_date[5:7])
    if division in CALENDAR_YEAR_DIVISIONS:
        return str(year)
    start = year if month >= 7 else year - 1
    return f"{start}-{str(start + 1)[2:]}"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


@dataclass(frozen=True)
class HistoricalMatch:
    result: MatchResult
    odds: tuple[OddsQuote, ...]
    home_elo: float | None
    away_elo: float | None
    division: str


class ClubFootballDataProvider:
    provider_id = "club_football_match_data"

    def __init__(self, registry: AliasRegistry, fetcher: CachedFetcher | None = None) -> None:
        self.registry = registry
        self.fetcher = fetcher or CachedFetcher(max_age=None)
        self._provisional: dict[tuple[str, str], str] = {}

    def _team(self, name: str, division: str) -> tuple[str, bool]:
        comp = DIVISION_TO_COMPETITION.get(division)
        if comp is not None:
            try:
                return self.registry.resolve_team(
                    name, country=comp[1], gender=Gender.MEN
                ).team_id, False
            except UnknownAliasError:
                pass
        key = (division, name)
        if key not in self._provisional:
            self._provisional[key] = f"prov.fd.{division.lower()}.{_slug(name)}"
        return self._provisional[key], True

    def load(
        self,
        *,
        divisions: Iterable[str] | None = None,
        start_date: str = "2000-01-01",
        end_date: str = "2999-12-31",
        content: bytes | None = None,
    ) -> Observation[list[HistoricalMatch]]:
        if content is None:
            fetched = self.fetcher.fetch(MATCHES_URL, source=self.provider_id, license_note=LICENSE)
            content, prov = fetched.content, fetched.provenance
        else:
            from soccer_edge.core.time import utc_now
            from soccer_edge.providers.base import Provenance

            prov = Provenance(source=self.provider_id, observed_at=utc_now(), license=LICENSE)
        wanted = set(divisions) if divisions else None
        rows: list[HistoricalMatch] = []
        any_provisional = False
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
        for r in reader:
            div = r["Division"]
            if wanted is not None and div not in wanted:
                continue
            d = r["MatchDate"]
            if not (start_date <= d <= end_date):
                continue
            if r["FTHome"] == "" or r["FTAway"] == "":
                continue
            comp = DIVISION_TO_COMPETITION.get(div, (f"prov.fd.{div.lower()}", div))[0]
            season = season_id_for(div, d)
            home, p1 = self._team(r["HomeTeam"], div)
            away, p2 = self._team(r["AwayTeam"], div)
            any_provisional |= p1 or p2
            fid = Fixture.make_id(comp, season, home, away, stage=d)

            def _i(k: str) -> int | None:
                v = r.get(k, "")
                return int(float(v)) if v not in ("", None) else None

            def _f(k: str) -> float | None:
                v = r.get(k, "")
                return float(v) if v not in ("", None) else None

            res = MatchResult(
                fixture_id=fid,
                competition_id=comp,
                season_id=season,
                match_date=d,
                home_team_id=home,
                away_team_id=away,
                home_goals=int(float(r["FTHome"])),
                away_goals=int(float(r["FTAway"])),
                home_goals_ht=_i("HTHome"),
                away_goals_ht=_i("HTAway"),
                home_shots=_i("HomeShots"),
                away_shots=_i("AwayShots"),
                home_shots_on_target=_i("HomeTarget"),
                away_shots_on_target=_i("AwayTarget"),
                home_corners=_i("HomeCorners"),
                away_corners=_i("AwayCorners"),
                home_yellow=_i("HomeYellow"),
                away_yellow=_i("AwayYellow"),
                home_red=_i("HomeRed"),
                away_red=_i("AwayRed"),
            )
            odds: list[OddsQuote] = []
            for col, sel, mkt, line in (
                ("OddHome", "home", "1x2", None),
                ("OddDraw", "draw", "1x2", None),
                ("OddAway", "away", "1x2", None),
                ("Over25", "over", "ou", 2.5),
                ("Under25", "under", "ou", 2.5),
            ):
                v = _f(col)
                if v and v > 1.0:
                    odds.append(
                        OddsQuote(
                            fixture_id=fid,
                            bookmaker="bet365",
                            market=mkt,
                            selection=sel,
                            decimal_odds=v,
                            line=line,
                            is_closing=None,
                        )
                    )
            rows.append(HistoricalMatch(res, tuple(odds), _f("HomeElo"), _f("AwayElo"), div))
        flags = (QualityFlag.OK,) if not any_provisional else (QualityFlag.PARTIAL,)
        notes = ("odds are Bet365 pre-match (not verified closing)",)
        if any_provisional:
            notes += ("some teams use provisional ids (not in canonical registry)",)
        return Observation(payload=rows, provenance=prov, flags=flags, notes=notes)
