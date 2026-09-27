from __future__ import annotations

import json
from datetime import UTC, datetime

from soccer_edge.providers.base import Observation, Provenance, QualityFlag
from soccer_edge.providers.club_football_data import ClubFootballDataProvider, season_id_for
from soccer_edge.providers.http import CachedFetcher, Fetched
from soccer_edge.providers.openfootball import OpenFootballProvider

OF_SAMPLE = {
    "name": "English Premier League 2026/27",
    "matches": [
        {
            "round": "Matchday 1",
            "date": "2026-08-21",
            "time": "20:00",
            "team1": "Arsenal FC",
            "team2": "Coventry City FC",
            "score": {"ht": [2, 0], "ft": [3, 0]},
        },
        {
            "round": "Matchday 6",
            "date": "2026-10-10",
            "time": "12:30",
            "team1": "Arsenal FC",
            "team2": "Leeds United FC",
        },
    ],
}

CSV = """Division,MatchDate,MatchTime,HomeTeam,AwayTeam,HomeElo,AwayElo,FTHome,FTAway,FTResult,HTHome,HTAway,OddHome,OddDraw,OddAway,Over25,Under25
E0,2026-08-21,20:00:00,Arsenal,Coventry,1900.1,1600.2,3,1,H,2,0,1.25,6.0,12.0,1.6,2.3
E0,2026-08-22,15:00:00,Man United,Tottenham,1800,1790,1,1,D,0,1,2.4,3.4,2.9,,
X9,2026-08-22,,Obscure FC,Other Town,1500,1500,0,0,D,0,0,2,3,3,,
"""


class StubFetcher(CachedFetcher):
    def __init__(self, content: bytes):
        self.content = content

    def fetch(self, url, *, source, license_note=None):
        return Fetched(
            self.content,
            Provenance(
                source=source, source_url=url, observed_at=datetime(2026, 9, 27, tzinfo=UTC)
            ),
            False,
        )


def test_openfootball_fixtures_and_results(registry):
    prov = OpenFootballProvider(registry, StubFetcher(json.dumps(OF_SAMPLE).encode()))
    fx = prov.fixtures("eng.premier_league", "2026-27")
    assert len(fx.payload) == 2 and QualityFlag.UNVERIFIED in fx.flags
    f0 = fx.payload[0]
    assert f0.home_team_id == "eng.arsenal" and f0.away_team_id == "eng.coventry"
    assert f0.kickoff_utc == datetime(2026, 8, 21, 19, 0, tzinfo=UTC)  # BST -> UTC
    res = prov.results("eng.premier_league", "2026-27")
    assert len(res.payload) == 1 and res.payload[0].home_goals_ht == 2


def test_historical_provider_odds_and_provisional_ids(registry):
    prov = ClubFootballDataProvider(registry)
    obs = prov.load(content=CSV.encode())
    rows = obs.payload
    assert len(rows) == 3
    assert rows[0].result.home_team_id == "eng.arsenal" and rows[0].odds[0].decimal_odds == 1.25
    assert rows[0].odds[0].is_closing is None  # honesty: not verified closing
    assert rows[2].result.home_team_id.startswith("prov.fd.x9.")
    assert QualityFlag.PARTIAL in obs.flags
    assert (
        season_id_for("E0", "2026-08-21") == "2026-27"
        and season_id_for("USA", "2026-08-21") == "2026"
    )


def test_observation_flags():
    o = Observation(
        payload=1, provenance=Provenance(source="x", observed_at=datetime(2026, 1, 1, tzinfo=UTC))
    )
    o2 = o.with_flag(QualityFlag.STALE, "old")
    assert QualityFlag.OK not in o2.flags and o2.notes == ("old",)
    assert (
        Observation(
            payload=1, provenance=o.provenance, flags=(QualityFlag.SYNTHETIC,)
        ).is_usable_for_production
        is False
    )
