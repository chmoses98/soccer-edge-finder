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


def _body_with_details(details):
    body = _scoreboard_body()
    body["events"][0]["competitions"][0]["details"] = details
    return body


def _results(details):
    from soccer_edge.providers.espn import results_from_events

    emap = EspnMap(
        leagues={"eng.1": "eng.premier_league"},
        teams={"349": "eng.bournemouth", "364": "eng.liverpool"},
    )
    return results_from_events(
        parse_scoreboard("eng.1", _body_with_details(details)), emap, MappingReport()
    )[0]


def test_cards_are_counted_from_real_probe_scoreboard_details():
    """Real ESPN payload (data/samples/espn_xg_probe.json, eng.1 first_event details): cards carry yellowCard/redCard
    flags and the team id; the result row must expose them instead of leaving the slots empty."""
    details = json.loads(PROBE.read_text())["espn"]["eng.1"]["first_event"]["details_sample"]
    yellows = [d for d in details if d.get("yellowCard")]
    assert yellows, "the probe sample must contain a booking"
    r = _results(details)
    want_away = sum(1 for d in yellows if d["team"]["id"] == "364")
    want_home = sum(1 for d in yellows if d["team"]["id"] == "349")
    assert (r.away_yellow, r.home_yellow) == (want_away, want_home)
    assert (r.home_red, r.away_red) == (0, 0) and r.cards_source == "espn_scoreboard_details"


def test_cards_red_cards_and_fail_closed_cases():
    team = lambda i: {"id": i}
    ev = lambda **k: {
        "type": {"text": "x"},
        "clock": {"displayValue": "10'"},
        "scoringPlay": False,
        "yellowCard": False,
        "redCard": False,
        **k,
    }
    r = _results(
        [
            ev(team=team("349"), redCard=True),
            ev(team=team("349"), yellowCard=True),
            ev(team=team("364"), yellowCard=True),
            ev(team=team("364"), yellowCard=True),
        ]
    )
    assert (r.home_red, r.home_yellow, r.away_yellow, r.away_red) == (1, 1, 2, 0)
    # details absent/empty: zero cards cannot be told from 'not served' -> no card fields
    for d in (None, []):
        x = _results(d)
        assert (x.home_yellow, x.away_yellow, x.home_red, x.away_red, x.cards_source) == (None,) * 5
    # a booking with no team id, or from a team that is neither side: emit nothing rather than a wrong count
    assert _results([ev(yellowCard=True)]).home_yellow is None
    assert _results([ev(team=team("777"), yellowCard=True)]).home_yellow is None
    # details with only goals and no bookings: zero cards is a real, complete answer
    g = _results([ev(team=team("364"), scoringPlay=True, scoreValue=1)])
    assert (g.home_yellow, g.away_yellow, g.home_red, g.away_red) == (0, 0, 0, 0)


def test_cards_upgrade_an_archived_row_that_lacked_them(tmp_path):
    from soccer_edge.providers.espn import EspnArchive, result_record

    old = _results(None)
    new = _results(
        [
            {
                "clock": {"displayValue": "46'"},
                "team": {"id": "364"},
                "scoringPlay": False,
                "yellowCard": True,
                "redCard": False,
            }
        ]
    )
    arch = EspnArchive(tmp_path)
    assert arch.append_results("eng.1", [result_record(old, "401879276", "eng.1")]) == 1
    assert (
        arch.append_results("eng.1", [result_record(new, "401879276", "eng.1")]) == 1
    )  # richer row appended, last row wins
    assert arch.results(("eng.1",))[0].away_yellow == 1


# NOTE: the box-score shape below follows ESPN's summary `boxscore.teams[].statistics[]` ({name, displayValue}) as
# documented/observed in the wild; no captured payload is available in this sandbox, so these tests pin the
# parser's behaviour (verbatim capture, whitelist mapping, fail-closed) and are NOT evidence that ESPN's names match.
def _summary_with_stats(state="post", stats_home=None, stats_away=None):
    body = _summary_body(state=state)
    body.setdefault("header", {}).setdefault("competitions", [{"competitors": []}])
    body["header"]["competitions"][0].setdefault("status", {})["type"] = {"state": state}
    mk = lambda tid, ha, st: {
        "team": {"id": tid},
        "homeAway": ha,
        "statistics": [{"name": k, "displayValue": str(v)} for k, v in (st or {}).items()],
    }
    body["boxscore"] = {"teams": [mk("349", "home", stats_home), mk("364", "away", stats_away)]}
    return body


def test_box_stats_are_captured_raw_post_match_only_and_hash_changes():
    from soccer_edge.providers.espn import box_stats_fields, parse_summary_lineups

    now = datetime(2026, 9, 20, 16, 0, tzinfo=UTC)
    post = parse_summary_lineups(
        "eng.1",
        "1",
        _summary_with_stats(
            "post",
            {"totalShots": 14, "wonCorners": 6, "weirdStat": "x"},
            {"totalShots": 9, "wonCorners": 3},
        ),
        captured_at=now,
        source_url="u",
    )
    pre = parse_summary_lineups(
        "eng.1",
        "1",
        _summary_with_stats("pre", {"totalShots": 14}, {"totalShots": 9}),
        captured_at=now,
        source_url="u",
    )
    assert (
        post.team_stats["349"]["stats"]["weirdStat"] == "x"
    )  # verbatim, including names we do not map
    assert pre.team_stats is None  # never captured before the match is over
    assert "team_stats" in post.to_record() and "team_stats" not in pre.to_record()
    nostat = parse_summary_lineups(
        "eng.1", "1", _summary_with_stats("post", None, None), captured_at=now, source_url="u"
    )
    assert nostat.team_stats is None and nostat.content_hash != post.content_hash
    # whitelist mapping: only integer stats reported by BOTH sides
    assert box_stats_fields(post.team_stats, "349", "364") == {
        "home_shots": 14,
        "away_shots": 9,
        "home_corners": 6,
        "away_corners": 3,
    }
    assert (
        box_stats_fields({"349": {"stats": {"totalShots": "7"}}}, "349", "364") == {}
    )  # away side missing -> nothing
    assert (
        box_stats_fields(
            {"349": {"stats": {"totalShots": "n/a"}}, "364": {"stats": {"totalShots": "3"}}},
            "349",
            "364",
        )
        == {}
    )
    assert box_stats_fields(None, "349", "364") == {}


def test_capture_lineups_appends_the_post_match_stats_row_even_if_the_xi_is_unchanged(tmp_path):
    from soccer_edge.providers.espn import parse_summary_lineups

    now = datetime(2026, 9, 20, 16, 0, tzinfo=UTC)
    a = parse_summary_lineups(
        "eng.1", "1", _summary_with_stats("post", None, None), captured_at=now, source_url="u"
    )
    b = parse_summary_lineups(
        "eng.1",
        "1",
        _summary_with_stats("post", {"totalShots": 1}, {"totalShots": 2}),
        captured_at=now,
        source_url="u",
    )
    assert a.content_hash != b.content_hash  # change suppression will NOT swallow the stats row


# ---- real ESPN payload facts: sift-alpha probe run 41543056159 (2026-11-02T23:40Z), match 401882821 (esp.1, a red card) ----
REAL_HOME = {
    "yellowCards": "2",
    "redCards": "0",
    "wonCorners": "2",
    "totalShots": "11",
    "shotsOnTarget": "5",
    "foulsCommitted": "18",
    "possessionPct": "47",
}
REAL_AWAY = {
    "yellowCards": "4",
    "redCards": "1",
    "wonCorners": "2",
    "totalShots": "12",
    "shotsOnTarget": "4",
    "foulsCommitted": "18",
    "possessionPct": "53.7",
}


def test_real_probe_stat_names_map_shots_corners_cards_with_provenance():
    from soccer_edge.providers.espn import box_result_fields

    at = datetime(2026, 11, 2, 23, 40, tzinfo=UTC)
    snap = parse_summary_lineups(
        "eng.1",
        "1",
        _summary_with_stats("post", REAL_HOME, REAL_AWAY),
        captured_at=at,
        source_url="u",
    )
    f = box_result_fields(snap)
    assert (
        f["home_shots"],
        f["away_shots"],
        f["home_shots_on_target"],
        f["away_shots_on_target"],
    ) == (11, 12, 5, 4)
    assert (f["home_corners"], f["away_corners"]) == (2, 2)
    assert (f["home_yellow"], f["away_yellow"], f["home_red"], f["away_red"]) == (2, 4, 0, 1)
    assert (
        f["box_stats_source"] == "espn_summary_boxscore"
        and f["box_stats_captured_at"] == at.isoformat()
    )
    assert (f["cards_source"], f["cards_basis"]) == ("espn_summary_boxscore", "boxscore_exact")
    assert not any("xg" in k for k in f)  # ESPN box scores carry no xG: never invented


def test_missing_box_values_stay_missing_not_zero_and_pre_match_gives_nothing():
    from soccer_edge.providers.espn import box_result_fields

    at = datetime(2026, 11, 2, 23, 40, tzinfo=UTC)
    no_corners_h = {k: v for k, v in REAL_HOME.items() if k != "wonCorners"}
    f = box_result_fields(
        parse_summary_lineups(
            "eng.1",
            "1",
            _summary_with_stats("post", no_corners_h, REAL_AWAY),
            captured_at=at,
            source_url="u",
        )
    )
    assert (
        "home_corners" not in f and "away_corners" not in f and f["home_shots"] == 11
    )  # absent, not 0
    only_yellow = {"yellowCards": "1", "totalShots": "3"}
    g = box_result_fields(
        parse_summary_lineups(
            "eng.1",
            "1",
            _summary_with_stats("post", only_yellow, only_yellow),
            captured_at=at,
            source_url="u",
        )
    )
    assert (
        "home_yellow" not in g and "cards_basis" not in g and g["home_shots"] == 3
    )  # half a card line is dropped
    assert (
        box_result_fields(
            parse_summary_lineups(
                "eng.1",
                "1",
                _summary_with_stats("pre", REAL_HOME, REAL_AWAY),
                captured_at=at,
                source_url="u",
            )
        )
        == {}
    )
    assert box_result_fields(None) == {}


def test_box_score_cards_supersede_unreconciled_scoreboard_cards():
    """Probe match 401882826: scoreboard details counted 4 away yellows, the box score says 3. The box score wins and the
    archived row is upgraded by appending (file stays append-only)."""
    from soccer_edge.providers.espn import EspnArchive, enrich_result_rows, result_record

    team = lambda i: {"id": i}
    ev = lambda t: {
        "type": {"text": "x"},
        "clock": {"displayValue": "10'"},
        "scoringPlay": False,
        "yellowCard": True,
        "redCard": False,
        "team": team(t),
    }
    r = _results([ev("349")] * 2 + [ev("364")] * 4)
    assert (r.home_yellow, r.away_yellow, r.cards_basis) == (2, 4, "scoreboard_unreconciled")
    sb_row = result_record(r, "evt", "eng.1")
    at = datetime(2026, 11, 2, 23, 40, tzinfo=UTC)
    home = {"yellowCards": "2", "redCards": "0", "totalShots": "13"}
    away = {"yellowCards": "3", "redCards": "0", "totalShots": "14"}
    snap = parse_summary_lineups(
        "eng.1", "evt", _summary_with_stats("post", home, away), captured_at=at, source_url="u"
    )
    row = dict(sb_row)
    assert enrich_result_rows([row], {"evt": snap}) == 1
    assert (row["away_yellow"], row["cards_basis"], row["home_shots"]) == (3, "boxscore_exact", 13)
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        arch = EspnArchive(Path(d))
        assert arch.append_results("eng.1", [sb_row]) == 1
        assert (
            arch.append_results("eng.1", [dict(sb_row)]) == 0
        )  # identical re-read: nothing appended
        assert arch.append_results("eng.1", [row]) == 1  # box score upgrades it
        assert arch.append_results("eng.1", [row]) == 0
        got = arch.results(("eng.1",))[0]
        assert (got.away_yellow, got.home_shots, got.box_stats_captured_at) == (
            3,
            13,
            at.isoformat(),
        )


def test_capture_lineups_exposes_post_match_snapshots_even_when_hash_unchanged(tmp_path):
    at = datetime(2026, 11, 2, 23, 40, tzinfo=UTC)
    body = _summary_with_stats("post", REAL_HOME, REAL_AWAY)

    class P:
        def lineup(self, league, eid):
            from types import SimpleNamespace

            return SimpleNamespace(
                payload=parse_summary_lineups(league, eid, body, captured_at=at, source_url="u")
            )

    ev = parse_scoreboard("eng.1", _scoreboard_body())[:1]
    first, second = {}, {}
    s1 = capture_lineups(P(), ev, tmp_path, as_of=at, snapshots_out=first)
    s2 = capture_lineups(P(), ev, tmp_path, as_of=at, snapshots_out=second)
    assert (s1["captured"], s2["unchanged"]) == (1, 1) and len(first) == len(second) == 1


def test_end_to_end_scoreboard_then_box_score_archival_is_append_only_and_timestamped(tmp_path):
    """scoreboard (unreconciled cards) -> lineup capture of the post-match summary -> enrichment -> append-only archive -> read back."""
    from types import SimpleNamespace

    from soccer_edge.providers.espn import (
        EspnArchive,
        enrich_result_rows,
        result_record,
        results_from_events,
    )

    emap = EspnMap(
        leagues={"eng.1": "eng.premier_league"},
        teams={"349": "eng.bournemouth", "364": "eng.liverpool"},
    )
    team = lambda i: {"id": i}
    bk = lambda t: {
        "type": {"text": "x"},
        "clock": {"displayValue": "9'"},
        "scoringPlay": False,
        "yellowCard": True,
        "redCard": False,
        "team": team(t),
    }
    details = [bk("349")] * 2 + [bk("364")] * 4  # scoreboard: away 4 yellows (box score says 3)
    events = parse_scoreboard("eng.1", _body_with_details(details))
    arch = EspnArchive(tmp_path / "arch")

    def write(snaps):
        rows = [result_record(r, "401879276", "eng.1") for r in results_from_events(events, emap)]
        enrich_result_rows(rows, snaps)
        return arch.append_results("eng.1", rows)

    assert write({}) == 1  # run 1: scoreboard only
    first = arch.results(("eng.1",))[0]
    assert (
        first.cards_basis,
        first.away_yellow,
        first.home_shots,
        first.home_xg,
        first.box_stats_captured_at,
    ) == ("scoreboard_unreconciled", 4, None, None, None)

    at = datetime(2026, 9, 20, 15, 30, tzinfo=UTC)
    home = {
        "yellowCards": "2",
        "redCards": "0",
        "totalShots": "13",
        "shotsOnTarget": "5",
        "wonCorners": "6",
    }
    away = {
        "yellowCards": "3",
        "redCards": "0",
        "totalShots": "9",
        "shotsOnTarget": "2",
        "wonCorners": "3",
    }
    body = _summary_with_stats("post", home, away)

    class Prov:
        def lineup(self, league, eid):
            return SimpleNamespace(
                payload=parse_summary_lineups(league, eid, body, captured_at=at, source_url="u")
            )

    snaps: dict = {}
    capture_lineups(Prov(), events, tmp_path / "lineups", as_of=at, snapshots_out=snaps)
    assert write(snaps) == 1  # run 2: box score upgrades the row
    assert write(snaps) == 0  # run 3: identical -> nothing appended
    raw = (tmp_path / "arch" / "results" / "espn" / "eng.1.jsonl").read_text().splitlines()
    assert (
        len(raw) == 2 and json.loads(raw[0])["cards_basis"] == "scoreboard_unreconciled"
    )  # file is append-only: the first row is untouched
    last = arch.results(("eng.1",))[0]
    assert (
        last.home_shots,
        last.away_shots,
        last.home_shots_on_target,
        last.home_corners,
        last.away_corners,
    ) == (13, 9, 5, 6, 3)
    assert (last.home_yellow, last.away_yellow, last.home_red, last.away_red, last.cards_basis) == (
        2,
        3,
        0,
        0,
        "boxscore_exact",
    )
    assert (last.home_xg, last.away_xg) == (None, None)  # xG stays missing
    assert (
        last.box_stats_captured_at == at.isoformat()
        and last.box_stats_source == "espn_summary_boxscore"
    )
