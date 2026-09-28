"""football-data.co.uk direct CSV provider (free; blocked from some corporate egress, fine from Actions).

Supplies the same columns as the GitHub redistribution plus *closing* odds columns
(B365CH/B365CD/B365CA, PSCH/PSCD/PSCA, and AvgC*) for seasons from 2019-20 onward.
Used by the research-fetch workflow to build a genuine closing-line benchmark.
"""

from __future__ import annotations

import csv
import io

from soccer_edge.core.errors import IdentityError
from soccer_edge.identity.models import Fixture, Gender
from soccer_edge.providers.base import Observation, QualityFlag
from soccer_edge.providers.http import CachedFetcher
from soccer_edge.providers.interfaces import MatchResult

BASE = "https://www.football-data.co.uk/mmz4281"
LICENSE = "football-data.co.uk free data; attribution requested"

CLOSING_COLUMNS = {
    "bet365": ("B365CH", "B365CD", "B365CA"),
    "pinnacle": ("PSCH", "PSCD", "PSCA"),
    "average": ("AvgCH", "AvgCD", "AvgCA"),
}


def season_code(season_id: str) -> str:
    # '2026-27' -> '2627'
    start, end = season_id.split("-")
    return start[2:] + end


FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"
DIVISION_TO_COMPETITION = {
    "E0": "eng.premier_league",
    "E1": "eng.championship",
    "SP1": "esp.la_liga",
    "D1": "ger.bundesliga",
    "I1": "ita.serie_a",
    "F1": "fra.ligue_1",
    "N1": "ned.eredivisie",
    "P1": "por.primeira_liga",
    "T1": "tur.super_lig",
    "SC0": "sco.premiership",
}
DIVISION_COUNTRY = {
    "E0": "ENG",
    "E1": "ENG",
    "SP1": "ESP",
    "D1": "GER",
    "I1": "ITA",
    "F1": "FRA",
    "N1": "NED",
    "P1": "POR",
    "T1": "TUR",
    "SC0": "SCO",
}
BOOK_COLUMNS = {
    "bet365": ("B365H", "B365D", "B365A"),
    "pinnacle": ("PSH", "PSD", "PSA"),
    "average": ("AvgH", "AvgD", "AvgA"),
    "max": ("MaxH", "MaxD", "MaxA"),
}
OU_COLUMNS = {
    "bet365": ("B365>2.5", "B365<2.5"),
    "pinnacle": ("P>2.5", "P<2.5"),
    "average": ("Avg>2.5", "Avg<2.5"),
}


class FootballDataCoUkProvider:
    provider_id = "football_data_couk"

    def __init__(self, fetcher: CachedFetcher | None = None, registry=None) -> None:
        self.fetcher = fetcher or CachedFetcher()
        self.registry = registry

    def upcoming_odds(self, content: bytes | None = None):
        """Current bookmaker odds for upcoming fixtures (`fixtures.csv`) -> list[OddsQuote].
        Reference market for HYBRID/MARKET_ONLY at capture time. Quotes are 'current', not closing.
        Requires a registry to map team names; unmapped rows are skipped and counted in notes."""
        from datetime import UTC, datetime

        from soccer_edge.core.errors import IdentityError
        from soccer_edge.identity.models import Fixture, Gender
        from soccer_edge.providers.base import Provenance
        from soccer_edge.providers.interfaces import OddsQuote

        if content is None:
            fetched = self.fetcher.fetch(
                FIXTURES_URL, source=self.provider_id, license_note=LICENSE
            )
            content, prov = fetched.content, fetched.provenance
        else:
            prov = Provenance(
                source=self.provider_id,
                source_url=FIXTURES_URL,
                observed_at=datetime.now(UTC),
                license=LICENSE,
            )
        text = content.decode("utf-8-sig", errors="replace")
        rows = [r for r in csv.DictReader(io.StringIO(text)) if r.get("Date")]
        quotes: list[OddsQuote] = []
        skipped = 0
        skipped_by_division: dict[str, int] = {}
        unknown_teams: dict[str, int] = {}
        for r in rows:
            div = r.get("Div", "")
            comp = DIVISION_TO_COMPETITION.get(div)
            if comp is None or self.registry is None:
                skipped += 1
                skipped_by_division[div or "?"] = skipped_by_division.get(div or "?", 0) + 1
                continue
            try:
                home = self.registry.resolve_team(
                    r["HomeTeam"], country=DIVISION_COUNTRY[div], gender=Gender.MEN
                ).team_id
                away = self.registry.resolve_team(
                    r["AwayTeam"], country=DIVISION_COUNTRY[div], gender=Gender.MEN
                ).team_id
            except IdentityError as exc:
                skipped += 1
                skipped_by_division[div] = skipped_by_division.get(div, 0) + 1
                name = str(exc).split("'")[1] if "'" in str(exc) else "?"
                unknown_teams[f"{div}:{name}"] = unknown_teams.get(f"{div}:{name}", 0) + 1
                continue
            d, m, y = r["Date"].split("/")
            iso = f"{int(y) + 2000 if len(y) == 2 else y}-{m}-{d}"
            season_start = int(iso[:4]) if int(iso[5:7]) >= 7 else int(iso[:4]) - 1
            fid = Fixture.make_id(
                comp, f"{season_start}-{str(season_start + 1)[2:]}", home, away, stage=iso
            )
            quoted_at = prov.observed_at
            for book, cols in BOOK_COLUMNS.items():
                vals = [r.get(c, "") for c in cols]
                if all(vals):
                    for sel, v in zip(("home", "draw", "away"), vals):
                        quotes.append(
                            OddsQuote(
                                fixture_id=fid,
                                bookmaker=book,
                                market="1x2",
                                selection=sel,
                                decimal_odds=float(v),
                                quoted_at=quoted_at,
                                is_closing=False,
                            )
                        )
            for book, cols in OU_COLUMNS.items():
                vals = [r.get(c, "") for c in cols]
                if all(vals):
                    for sel, v in zip(("over", "under"), vals):
                        quotes.append(
                            OddsQuote(
                                fixture_id=fid,
                                bookmaker=book,
                                market="ou",
                                selection=sel,
                                decimal_odds=float(v),
                                line=2.5,
                                quoted_at=quoted_at,
                                is_closing=False,
                            )
                        )
        flags = (QualityFlag.OK,) if quotes else (QualityFlag.PARTIAL,)
        notes = (
            f"{len(rows)} rows, {skipped} skipped (unmapped division/team)",
            f"skipped_by_division={dict(sorted(skipped_by_division.items()))}",
            f"unknown_teams={dict(sorted(unknown_teams.items(), key=lambda kv: -kv[1])[:20])}",
            "fixture ids use the match DATE as stage; join to openfootball fixtures by (home, away, date)",
        )
        return Observation(payload=quotes, provenance=prov, flags=flags, notes=notes)

    def raw_rows(self, division: str, season_id: str) -> Observation[list[dict[str, str]]]:
        url = f"{BASE}/{season_code(season_id)}/{division}.csv"
        fetched = self.fetcher.fetch(url, source=self.provider_id, license_note=LICENSE)
        text = fetched.content.decode("utf-8", errors="replace")
        rows = [r for r in csv.DictReader(io.StringIO(text)) if r.get("Date")]
        has_closing = bool(rows) and any(
            c in rows[0] for cols in CLOSING_COLUMNS.values() for c in cols
        )
        flags = (QualityFlag.OK,) if has_closing else (QualityFlag.PARTIAL,)
        notes = () if has_closing else ("no closing-odds columns in this season file",)
        return Observation(payload=rows, provenance=fetched.provenance, flags=flags, notes=notes)

    def results_with_xg(self, division: str, season_id: str) -> Observation[list[MatchResult]]:
        """Current-season results with match xG where the file carries HxG/AxG (2026-27 onward).

        xG is a third-party model output of undisclosed provenance; it is carried as a covariate
        (`MatchResult.home_xg/away_xg`), never as an observation. Rows without xG keep None."""
        obs = self.raw_rows(division, season_id)
        comp = DIVISION_TO_COMPETITION.get(division)
        out: list[MatchResult] = []
        skipped = 0
        has_xg = bool(obs.payload) and "HxG" in obs.payload[0]
        for r in obs.payload:
            if comp is None or self.registry is None or not r.get("FTHG"):
                skipped += 1
                continue
            try:
                home = self.registry.resolve_team(
                    r["HomeTeam"], country=DIVISION_COUNTRY[division], gender=Gender.MEN
                ).team_id
                away = self.registry.resolve_team(
                    r["AwayTeam"], country=DIVISION_COUNTRY[division], gender=Gender.MEN
                ).team_id
            except IdentityError:
                skipped += 1
                continue
            d, m, y = r["Date"].split("/")
            iso = f"{int(y) + 2000 if len(y) == 2 else y}-{m}-{d}"

            def _f(k: str) -> float | None:
                v = r.get(k, "")
                return float(v) if v not in ("", None) else None

            out.append(
                MatchResult(
                    fixture_id=Fixture.make_id(comp, season_id, home, away, stage=iso),
                    competition_id=comp,
                    season_id=season_id,
                    match_date=iso,
                    home_team_id=home,
                    away_team_id=away,
                    home_goals=int(float(r["FTHG"])),
                    away_goals=int(float(r["FTAG"])),
                    home_goals_ht=int(float(r["HTHG"])) if r.get("HTHG") else None,
                    away_goals_ht=int(float(r["HTAG"])) if r.get("HTAG") else None,
                    home_shots=int(float(r["HS"])) if r.get("HS") else None,
                    away_shots=int(float(r["AS"])) if r.get("AS") else None,
                    home_xg=_f("HxG"),
                    away_xg=_f("AxG"),
                )
            )
        notes = obs.notes + (
            f"{len(out)} results, {skipped} skipped; xg_columns={'present' if has_xg else 'absent'}; xg_source=football_data_couk",
        )
        flags = (
            obs.flags
            if has_xg
            else tuple(f for f in obs.flags if f != QualityFlag.OK) + (QualityFlag.PARTIAL,)
        )
        return Observation(
            payload=out,
            provenance=obs.provenance,
            flags=flags or (QualityFlag.PARTIAL,),
            notes=notes,
        )
