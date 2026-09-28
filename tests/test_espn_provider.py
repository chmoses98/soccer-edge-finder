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
        lists = p["espn"].get("team_lists", {})
        for lg in ("eng.1", "usa.1", "mex.1", "bra.1", "arg.1", "uefa.nations"):
            for t in lists.get(lg, {}).get("teams", []):
                assert str(t["id"]) in emap.teams, (
                    lg,
                    t,
                )  # every id in these leagues is mapped explicitly


def test_results_from_events_and_archive_round_trip(tmp_path):
    from soccer_edge.providers.espn import EspnArchive, result_record, results_from_events

    emap = EspnMap(
        leagues={"eng.1": "eng.premier_league"},
        teams={"349": "eng.bournemouth", "364": "eng.liverpool", "359": "eng.arsenal"},
    )
    evs = parse_scoreboard("eng.1", _scoreboard_body())
    rep = MappingReport()
    res = results_from_events(evs, emap, rep)
    assert (
        len(res) == 1
        and res[0].home_goals == 0
        and res[0].away_goals == 1
        and res[0].match_date == "2026-09-20"
    )
    assert (
        rep.skipped_events == 0
    )  # the scheduled event is simply not a result, not a mapping failure
    # postponed never counts as a result even with scores present
    assert (
        results_from_events(
            parse_scoreboard("eng.1", _scoreboard_body("post", "STATUS_POSTPONED")), emap
        )
        == []
    )
    arch = EspnArchive(tmp_path)
    rows = [result_record(r, "401879276", "eng.1") for r in res]
    assert arch.append_results("eng.1", rows) == 1
    assert arch.append_results("eng.1", rows) == 0  # idempotent
    back = arch.results(("eng.1", "nope.9"))
    assert (
        len(back) == 1 and back[0].fixture_id == res[0].fixture_id and back[0].neutral_site is False
    )


def test_assemble_reads_espn_archive(tmp_path, registry):
    import json as _json

    from soccer_edge.providers.espn import EspnArchive, result_record
    from soccer_edge.providers.interfaces import MatchResult
    from soccer_edge.run.inputs import assemble

    # 60 synthetic MLS results between 6 canonical teams + one upcoming fixture
    teams = [
        "usa.atlanta_united",
        "usa.austin",
        "usa.charlotte",
        "usa.chicago_fire",
        "usa.cincinnati",
        "usa.colorado_rapids",
    ]
    arch = EspnArchive(tmp_path)
    rows = []
    k = 0
    for i, h in enumerate(teams):
        for j, a in enumerate(teams):
            if h == a:
                continue
            for rep_ in range(2):
                k += 1
                d = f"2026-0{3 + (k % 6)}-{1 + (k % 27):02d}"
                r = MatchResult(
                    fixture_id=f"fx:usa.mls:2026:{h}:{a}:{k}",
                    competition_id="usa.mls",
                    season_id="2026",
                    match_date=d,
                    home_team_id=h,
                    away_team_id=a,
                    home_goals=(i + k) % 4,
                    away_goals=(j + k) % 3,
                )
                rows.append(result_record(r, f"e{k}", "usa.1"))
    assert arch.append_results("usa.1", rows) == 60
    fx_dir = tmp_path / "fixtures" / "espn" / "2026-09-28"
    fx_dir.mkdir(parents=True)
    fx = {
        "fixture_id": "fx:usa.mls:2026:usa.atlanta_united:usa.austin",
        "competition_id": "usa.mls",
        "season_id": "2026",
        "home_team_id": "usa.atlanta_united",
        "away_team_id": "usa.austin",
        "kickoff_utc": "2026-10-03T23:30:00+00:00",
        "kickoff_date": "2026-10-03",
        "status": "scheduled",
        "espn_event_id": "e999",
    }
    (fx_dir / "espn-000000.json").write_text(
        _json.dumps({"as_of": "2026-09-28T03:00:00+00:00", "fixtures": [fx]})
    )
    data = assemble(
        registry,
        competitions=("usa.mls",),
        today=datetime(2026, 9, 28, tzinfo=UTC).date(),
        historical_content=b"",
        espn_dir=tmp_path,
    )
    assert any(f.fixture_id == fx["fixture_id"] for f in data.fixtures)
    assert "usa.mls" in data.models and len(data.results["usa.mls"]) == 60
    assert any("espn 1 fixtures, 60 pooled results" in n for n in data.notes)
