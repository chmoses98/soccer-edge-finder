from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from soccer_edge.identity.models import FixtureStatus
from soccer_edge.providers.espn import (
    EspnMap,
    MappingReport,
    capture_lineups,
    events_to_fixtures,
    parse_scoreboard,
    parse_summary_lineups,
    parse_teams,
    season_id_for,
)

PROBE = Path(__file__).resolve().parents[1] / "data" / "samples" / "espn_xg_probe.json"


def _scoreboard_body(state="post", status_name="STATUS_FULL_TIME"):
    return {
        "events": [
            {
                "id": "401879276",
                "date": "2026-09-20T13:00Z",
                "season": {"year": 2026, "slug": "2026-27-english-premier-league"},
                "competitions": [
                    {
                        "status": {"type": {"state": state, "name": status_name}},
                        "neutralSite": False,
                        "venue": {"fullName": "Vitality Stadium"},
                        "competitors": [
                            {
                                "homeAway": "home",
                                "score": "0",
                                "team": {
                                    "id": "349",
                                    "abbreviation": "BOU",
                                    "displayName": "AFC Bournemouth",
                                },
                            },
                            {
                                "homeAway": "away",
                                "score": "1",
                                "team": {
                                    "id": "364",
                                    "abbreviation": "LIV",
                                    "displayName": "Liverpool",
                                },
                            },
                        ],
                    }
                ],
            },
            {
                "id": "999",
                "date": "2026-09-21T15:00Z",
                "season": {"year": 2026, "slug": "2026-27-english-premier-league"},
                "competitions": [
                    {
                        "status": {"type": {"state": "pre", "name": "STATUS_SCHEDULED"}},
                        "competitors": [
                            {
                                "homeAway": "home",
                                "team": {
                                    "id": "359",
                                    "abbreviation": "ARS",
                                    "displayName": "Arsenal",
                                },
                            },
                            {
                                "homeAway": "away",
                                "team": {
                                    "id": "424242",
                                    "abbreviation": "XXX",
                                    "displayName": "Unknown Town",
                                },
                            },
                        ],
                    }
                ],
            },
        ]
    }


def test_parse_scoreboard_and_map_to_fixtures_fail_loud_on_unmapped():
    evs = parse_scoreboard("eng.1", _scoreboard_body())
    assert [e.espn_event_id for e in evs] == ["401879276", "999"]
    assert evs[0].kickoff_utc == datetime(2026, 9, 20, 13, tzinfo=UTC) and evs[0].state == "post"
    assert evs[0].home_score == 0 and evs[0].away_score == 1 and evs[0].venue == "Vitality Stadium"
    emap = EspnMap(
        leagues={"eng.1": "eng.premier_league"},
        teams={"349": "eng.bournemouth", "364": "eng.liverpool", "359": "eng.arsenal"},
    )
    rep = MappingReport()
    fx = events_to_fixtures(evs, emap, rep)
    assert len(fx) == 1 and rep.mapped == 1 and rep.skipped_events == 1
    assert rep.unmapped_team_ids == {"424242": "Unknown Town"}  # reported, never guessed
    f = fx[0]
    assert f.fixture_id == "fx:eng.premier_league:2026-27:eng.bournemouth:eng.liverpool"
    assert f.status is FixtureStatus.FINISHED and rep.results[f.fixture_id] == (0, 1)
    assert rep.espn_event_by_fixture[f.fixture_id] == "401879276"
    # unmapped league -> skipped + reported
    rep2 = MappingReport()
    assert events_to_fixtures(
        parse_scoreboard("xx.9", _scoreboard_body()), emap, rep2
    ) == [] and rep2.unmapped_leagues == {"xx.9"}


def test_status_overrides_and_season_ids():
    evs = parse_scoreboard("eng.1", _scoreboard_body(state="pre", status_name="STATUS_POSTPONED"))
    emap = EspnMap(
        leagues={"eng.1": "eng.premier_league"},
        teams={"349": "eng.bournemouth", "364": "eng.liverpool"},
    )
    rep = MappingReport()
    f = events_to_fixtures(evs, emap, rep)[0]
    assert f.status is FixtureStatus.POSTPONED and rep.results == {}
    assert season_id_for("eng.1", evs[0]) == "2026-27"
    assert season_id_for("usa.1", evs[0]) == "2026"


def _summary_body(state="pre", starters=True):
    def roster(team, formation):
        rows = []
        for i in range(1, 19):
            rows.append(
                {
                    "starter": (i <= 11) if starters else False,
                    "jersey": str(i),
                    "formationPlace": str(i) if i <= 11 else "0",
                    "subbedIn": False,
                    "subbedOut": False,
                    "active": True,
                    "position": {"abbreviation": "G" if i == 1 else "M"},
                    "athlete": {"id": f"{team}{i}", "displayName": f"Player {team}{i}"},
                }
            )
        return {
            "homeAway": "home" if team == "H" else "away",
            "team": {"id": "349" if team == "H" else "364"},
            "formation": formation,
            "roster": rows,
        }

    return {
        "header": {
            "competitions": [
                {
                    "date": "2026-09-20T13:00Z",
                    "status": {"type": {"state": state}},
                    "competitors": [
                        {"homeAway": "home", "team": {"id": "349"}},
                        {"homeAway": "away", "team": {"id": "364"}},
                    ],
                }
            ]
        },
        "rosters": [roster("H", "4-2-3-1"), roster("A", "4-3-3")] if starters is not None else [],
    }


def test_lineup_snapshot_states_and_no_backward_leakage():
    at = datetime(2026, 9, 20, 12, 5, tzinfo=UTC)
    pre = parse_summary_lineups(
        "eng.1", "401879276", _summary_body("pre"), captured_at=at, source_url="u"
    )
    assert pre.published and pre.lineup_state == "confirmed" and pre.home_formation == "4-2-3-1"
    assert (
        sum(p.starter for p in pre.home) == 11
        and len(pre.away) == 18
        and pre.home[0].position == "G"
    )
    post = parse_summary_lineups(
        "eng.1", "401879276", _summary_body("post"), captured_at=at, source_url="u"
    )
    assert (
        post.published and post.lineup_state == "post_hoc"
    )  # a team sheet read after kickoff is NOT a pre-match confirmation
    none = parse_summary_lineups(
        "eng.1", "401879276", _summary_body("pre", starters=False), captured_at=at, source_url="u"
    )
    assert not none.published and none.lineup_state == "unconfirmed"
    empty = parse_summary_lineups(
        "eng.1", "401879276", _summary_body("pre", starters=None), captured_at=at, source_url="u"
    )
    assert empty.lineup_state == "unconfirmed" and empty.home == ()
    rec = pre.to_record()
    assert (
        rec["schema"] == "espn_lineup_snapshot_v1"
        and rec["event_state"] == "pre"
        and rec["kickoff_utc"].startswith("2026-09-20T13:00")
    )
    assert pre.content_hash != post.content_hash


def test_capture_lineups_is_append_only_and_change_suppressed(tmp_path):
    class FakeProvider:
        def __init__(self):
            self.calls = 0
            self.body = _summary_body("pre")

        def lineup(self, league, eid):
            from soccer_edge.providers.base import Observation, Provenance

            self.calls += 1
            snap = parse_summary_lineups(
                league,
                eid,
                self.body,
                captured_at=datetime(2026, 9, 20, 12, tzinfo=UTC),
                source_url="u",
            )
            return Observation(
                payload=snap,
                provenance=Provenance(
                    source="espn_site_api", observed_at=datetime(2026, 9, 20, 12, tzinfo=UTC)
                ),
            )

    evs = parse_scoreboard("eng.1", _scoreboard_body("pre", "STATUS_SCHEDULED"))
    prov = FakeProvider()
    s1 = capture_lineups(prov, evs, tmp_path, as_of=datetime(2026, 9, 20, 12, tzinfo=UTC))
    assert s1["captured"] == 2 and s1["published_pre_kickoff"] == 2
    s2 = capture_lineups(prov, evs, tmp_path, as_of=datetime(2026, 9, 20, 12, 30, tzinfo=UTC))
    assert s2["captured"] == 0 and s2["unchanged"] == 2
    prov.body = _summary_body("post")
    s3 = capture_lineups(prov, evs, tmp_path, as_of=datetime(2026, 9, 20, 15, tzinfo=UTC))
    assert s3["captured"] == 2 and s3["published_post"] == 2
    rows = [
        json.loads(line)
        for f in sorted(tmp_path.rglob("*.jsonl"))
        for line in f.read_text().splitlines()
    ]
    assert len(rows) == 4 and {r["lineup_state"] for r in rows} == {"confirmed", "post_hoc"}


def test_probe_sample_teams_parse_and_map_file_is_consistent():
    emap = EspnMap.load()
    assert emap.leagues["eng.1"] == "eng.premier_league" and emap.teams["359"] == "eng.arsenal"
    assert len(set(emap.teams.values())) == len(emap.teams)  # one canonical id per ESPN id
    body = {
        "sports": [
            {
                "leagues": [
                    {
                        "teams": [
                            {
                                "team": {
                                    "id": "349",
                                    "abbreviation": "BOU",
                                    "displayName": "AFC Bournemouth",
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }
    assert parse_teams(body)[0]["id"] == "349"
    if PROBE.exists():
        p = json.loads(PROBE.read_text())
        for t in p["espn"]["teams_eng1"]["sample"]:
            assert t["id"] in emap.teams, t
