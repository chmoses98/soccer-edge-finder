"""Universal settlement: result resolution, explicit states, ESPN evidence, coverage (audit B4, phase 4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from soccer_edge.archive.ledger import PredictionLedger
from soccer_edge.identity.models import CompetitionFormat
from soccer_edge.kalshi.taxonomy import MarketFamily, Period
from soccer_edge.pricing.semantics import Semantics
from soccer_edge.providers.espn import (
    ESPN_POOLS,
    EspnArchive,
    EspnMap,
    parse_scoreboard,
    result_record,
    results_from_events,
)
from soccer_edge.providers.interfaces import MatchResult
from soccer_edge.providers.openfootball import COMPETITION_FILES
from soccer_edge.run.inputs import DEFAULT_COMPETITIONS
from soccer_edge.run.settle import build_result_index, coverage_report, settle_ledger
from soccer_edge.settlement.resolve import (
    CoverageRow,
    SettlementState,
    et_possible,
    official_from_result,
    parse_fixture_id,
    semantics_complete,
)

KO = datetime(2026, 9, 27, 18, 0, tzinfo=UTC)
AS_OF = KO + timedelta(hours=6)


def _mr(
    fid="fx:uefa.nations_league:2026-27:nat.svk:nat.kaz", comp="uefa.nations_league", h=2, a=1, **kw
):
    base = dict(
        fixture_id=fid,
        competition_id=comp,
        season_id="2026-27",
        match_date="2026-09-27",
        home_team_id="nat.svk",
        away_team_id="nat.kaz",
        home_goals=h,
        away_goals=a,
    )
    base.update(kw)
    return MatchResult(**base)


def _rec(
    fid="fx:uefa.nations_league:2026-27:nat.svk:nat.kaz",
    comp="uefa.nations_league",
    family="match_result_3way",
    side="home",
    period="regulation",
    line=None,
    k=None,
    ticker="T1",
    ko=KO,
):
    return {
        "schema": "prediction_record_v1",
        "run_id": "run-x",
        "as_of": (ko - timedelta(hours=5)).isoformat().replace("+00:00", "Z"),
        "ticker": ticker,
        "fixture_id": fid,
        "competition_id": comp,
        "kickoff_utc": ko.isoformat().replace("+00:00", "Z"),
        "family": family,
        "semantics": {"side": side, "line": line, "period": period, "k": k, "description": ""},
        "model_family": "data_only.world_sim_v1",
        "probability": {
            "fair_probability_mean": 0.5,
            "fair_probability_low": 0.4,
            "fair_probability_high": 0.6,
        },
        "market": {"yes_bid": "0.40", "yes_ask": "0.45", "no_bid": "0.55", "no_ask": "0.60"},
        "fee_regime": {"fee_type": "quadratic", "fee_multiplier": "1"},
        "recommendation": {},
    }


def _run(tmp_path: Path, records, index, *, as_of=AS_OF, et=None):
    led = PredictionLedger(tmp_path / "pred")
    for r in records:
        led.append(r, when=AS_OF - timedelta(hours=11))
    stl = PredictionLedger(tmp_path / "stl")
    rows: list[CoverageRow] = []
    written = settle_ledger(
        led,
        index,
        tmp_path / "snaps",
        stl,
        as_of=as_of,
        et_possible_for=et or {},
        coverage_rows=rows,
    )
    return written, rows, stl


# ------------------------------------------------------------------ resolution states


def test_every_record_gets_exactly_one_state(tmp_path):
    recs = [
        _rec(ticker="a"),  # settles (result present)
        _rec(ticker="b", ko=AS_OF + timedelta(hours=1)),  # pending kickoff
        _rec(ticker="c", fid="fx:uefa.nations_league:2026-27:nat.svn:nat.mkd"),  # no result yet
        _rec(ticker="d", comp="xyz.unknown", fid="fx:xyz.unknown:2026:t.a:t.b"),  # no source at all
        _rec(
            ticker="e", family="exact_score", side=None, k=None
        ),  # semantics incomplete (no k, no derivable description)
        _rec(ticker="f", family="first_half_result", period="first_half"),  # needs HT split
        _rec(ticker="g", family="player_goals", side=None, k=1),  # unsupported
    ]
    idx = build_result_index(
        {"openfootball": [_mr()]}, competitions_with_source={"uefa.nations_league"}
    )
    written, rows, _ = _run(tmp_path, recs, idx)
    by_ticker = {r.prediction_record_id: r for r in rows}
    states = {
        t: next(r.state for r in rows if r.prediction_record_id == rid)
        for rid, t in [(PredictionLedger.record_id(x), x["ticker"]) for x in recs]
    }
    assert states == {
        "a": SettlementState.SETTLED,
        "b": SettlementState.PENDING_KICKOFF,
        "c": SettlementState.PENDING_RESULT,
        "d": SettlementState.UNSETTLEABLE,
        "e": SettlementState.PENDING_EVIDENCE,
        "f": SettlementState.PENDING_EVIDENCE,
        "g": SettlementState.UNSUPPORTED_SETTLEMENT,
    }
    assert len(written) == 1 and written[0]["outcome"] == "yes"
    rep = coverage_report(rows, as_of=AS_OF, grace=timedelta(hours=3))
    assert rep["predictions_total"] == 7 and rep["unaccounted_settlement_records"] == 0
    assert rep["settled"] == 1 and rep["pending_kickoff"] == 1 and rep["pending_result"] == 1
    assert (
        rep["unsettleable"] == 1
        and rep["pending_evidence"] == 2
        and rep["unsupported_settlement"] == 1
    )
    assert rep["settleable_now"] == 6
    assert len(by_ticker) == 7


def test_pending_states_are_not_written_and_are_retried(tmp_path):
    rec = _rec(family="first_half_result", period="first_half")
    idx = build_result_index({"espn_site_api": [_mr()]})
    written, rows, stl = _run(tmp_path, [rec], idx)
    assert written == [] and rows[0].state is SettlementState.PENDING_EVIDENCE
    assert list(stl.iter_records()) == []
    # the half-time split arrives later (ESPN upgrade row): the record settles on the next run
    idx2 = build_result_index(
        {"espn_site_api": [_mr(home_goals_ht=1, away_goals_ht=0, status_name="STATUS_FULL_TIME")]}
    )
    written2, rows2, _ = _run(tmp_path, [rec], idx2)
    assert rows2[0].state is SettlementState.SETTLED and written2[0]["outcome"] == "yes"


def test_fuzzy_match_by_teams_and_date_across_id_conventions(tmp_path):
    # record from an openfootball fixture id (stage suffix), result from ESPN (no stage)
    rec = _rec(
        fid="fx:eng.premier_league:2026-27:eng.arsenal:eng.chelsea:matchday_6",
        comp="eng.premier_league",
    )
    res = _mr(
        fid="fx:eng.premier_league:2026-27:eng.arsenal:eng.chelsea",
        comp="eng.premier_league",
        home_team_id="eng.arsenal",
        away_team_id="eng.chelsea",
        status_name="STATUS_FULL_TIME",
        match_date="2026-09-28",
    )
    idx = build_result_index({"espn_site_api": [res]})
    written, rows, _ = _run(tmp_path, [rec], idx, et={"eng.premier_league": False})
    assert rows[0].state is SettlementState.SETTLED and written[0]["evidence"][
        "result_sources"
    ] == ["espn_site_api"]


def test_ambiguous_candidates_pend_mapping(tmp_path):
    rec = _rec(fid="fx:mex.liga_mx:2026:mex.a:mex.b", comp="mex.liga_mx")
    r1 = _mr(
        fid="fx:mex.liga_mx:2026:mex.a:mex.b",
        comp="mex.liga_mx",
        home_team_id="mex.a",
        away_team_id="mex.b",
        h=1,
        a=0,
        match_date="2026-09-27",
    )
    r2 = _mr(
        fid="fx:mex.liga_mx:2026:mex.a:mex.b",
        comp="mex.liga_mx",
        home_team_id="mex.a",
        away_team_id="mex.b",
        h=3,
        a=3,
        match_date="2026-09-28",
    )
    idx = build_result_index({"espn_site_api": [r1, r2]})
    _, rows, _ = _run(tmp_path, [rec], idx, et={"mex.liga_mx": False})
    assert rows[0].state is SettlementState.PENDING_MAPPING


def test_conflicting_sources_pend_evidence(tmp_path):
    rec = _rec()
    idx = build_result_index(
        {
            "openfootball": [_mr(h=2, a=1)],
            "espn_site_api": [_mr(h=1, a=1, status_name="STATUS_FULL_TIME")],
        }
    )
    _, rows, _ = _run(tmp_path, [rec], idx)
    assert rows[0].state is SettlementState.PENDING_EVIDENCE and "disagree" in rows[0].reason


def test_agreeing_sources_settle_with_richest_evidence(tmp_path):
    rec = _rec(family="first_half_result", period="first_half", side="draw")
    idx = build_result_index(
        {
            "openfootball": [_mr(h=2, a=1)],
            "espn_site_api": [
                _mr(h=2, a=1, home_goals_ht=0, away_goals_ht=0, status_name="STATUS_FULL_TIME")
            ],
        }
    )
    written, rows, _ = _run(tmp_path, [rec], idx)
    assert rows[0].state is SettlementState.SETTLED and written[0]["outcome"] == "yes"
    assert sorted(written[0]["evidence"]["result_sources"]) == ["espn_site_api", "openfootball"]


# ------------------------------------------------------------------ extra time / penalties / abandoned


def test_espn_score_with_unknown_et_status_pends_where_et_is_possible(tmp_path):
    rec = _rec(comp="uefa.nations_league")
    res = _mr(h=2, a=1)  # legacy ESPN row: no status token, no split
    _, rows, _ = _run(
        tmp_path,
        [rec],
        build_result_index({"espn_site_api": [res]}),
        et={"uefa.nations_league": True},
    )
    assert (
        rows[0].state is SettlementState.PENDING_EVIDENCE
        and "extra-time status unknown" in rows[0].reason
    )
    # a league format cannot have extra time: the reported score is the regulation score
    _, rows2, _ = _run(
        tmp_path,
        [rec],
        build_result_index({"espn_site_api": [res]}),
        et={"uefa.nations_league": False},
    )
    assert rows2[0].state is SettlementState.SETTLED


def test_regulation_split_settles_regulation_contract_on_an_aet_match(tmp_path):
    res = _mr(
        h=3,
        a=2,
        home_goals_regulation=2,
        away_goals_regulation=2,
        home_goals_et=1,
        away_goals_et=0,
        extra_time_played=True,
        status_name="STATUS_FINAL_AET",
    )
    idx = build_result_index({"espn_site_api": [res]})
    draw = _rec(ticker="d", side="draw")
    total = _rec(ticker="t", family="total_goals", side=None, line="4.5")
    adv = _rec(ticker="w", family="match_winner_2way", side="home", period="including_penalties")
    written, rows, _ = _run(tmp_path, [draw, total, adv], idx, et={"uefa.nations_league": True})
    by = {w["ticker"]: w["outcome"] for w in written}
    assert by == {
        "d": "yes",
        "t": "no",
        "w": "yes",
    }  # 90' draw; 4 goals in 90'; home advanced after ET


def test_penalties_need_a_winner(tmp_path):
    res = _mr(
        h=1,
        a=1,
        home_goals_regulation=1,
        away_goals_regulation=1,
        home_goals_et=0,
        away_goals_et=0,
        extra_time_played=True,
        decided_on_penalties=True,
    )
    adv = _rec(family="match_winner_2way", side="home", period="including_penalties")
    _, rows, _ = _run(
        tmp_path,
        [adv],
        build_result_index({"espn_site_api": [res]}),
        et={"uefa.nations_league": True},
    )
    assert rows[0].state is SettlementState.PENDING_EVIDENCE
    res2 = res.model_copy(
        update={"winner_after_penalties": "away", "home_shootout": 3, "away_shootout": 4}
    )
    written, rows2, _ = _run(
        tmp_path,
        [adv],
        build_result_index({"espn_site_api": [res2]}),
        et={"uefa.nations_league": True},
    )
    assert rows2[0].state is SettlementState.SETTLED and written[0]["outcome"] == "no"


def test_abandoned_and_postponed_never_settle(tmp_path):
    for token in ("STATUS_ABANDONED", "STATUS_POSTPONED", "STATUS_CANCELED"):
        res = _mr(h=0, a=0, status_name=token)
        _, rows, _ = _run(tmp_path / token, [_rec()], build_result_index({"espn_site_api": [res]}))
        assert rows[0].state is SettlementState.PENDING_EVIDENCE, token


def test_first_to_score_needs_first_scorer(tmp_path):
    rec = _rec(family="first_to_score", side="away", period="regulation")
    res = _mr(h=1, a=1, status_name="STATUS_FULL_TIME")
    _, rows, _ = _run(tmp_path, [rec], build_result_index({"espn_site_api": [res]}))
    assert rows[0].state is SettlementState.PENDING_EVIDENCE
    res2 = res.model_copy(
        update={"first_scorer_team": "away", "home_goals_regulation": 1, "away_goals_regulation": 1}
    )
    written, rows2, _ = _run(tmp_path / "b", [rec], build_result_index({"espn_site_api": [res2]}))
    assert written[0]["outcome"] == "yes"


def test_exact_score_with_k_settles_and_without_k_fails_closed(tmp_path):
    with_k = _rec(ticker="k", family="exact_score", side=None, k=201)
    without = _rec(ticker="n", family="exact_score", side=None, k=None)
    written, rows, _ = _run(
        tmp_path, [with_k, without], build_result_index({"openfootball": [_mr(h=2, a=1)]})
    )
    assert {w["ticker"]: w["outcome"] for w in written} == {"k": "yes"}
    assert {r.state for r in rows} == {SettlementState.SETTLED, SettlementState.PENDING_EVIDENCE}
    assert (
        semantics_complete(
            Semantics("x", MarketFamily.EXACT_SCORE, Period.REGULATION, None, None, None, None)
        )
        is not None
    )


def test_official_from_result_openfootball_is_regulation():
    off, why = official_from_result(
        _mr(result_source="openfootball", h=2, a=1), et_possible_in_competition=True
    )
    assert why is None and (off.home_ft, off.away_ft) == (2, 1)


def test_parse_fixture_id_and_et_possible():
    assert parse_fixture_id("fx:eng.premier_league:2026-27:eng.a:eng.b:matchday_6") == (
        "eng.premier_league",
        "2026-27",
        "eng.a",
        "eng.b",
    )
    assert parse_fixture_id("nonsense") is None
    assert et_possible(CompetitionFormat.LEAGUE, None) is False
    assert et_possible(CompetitionFormat.FRIENDLY, None) is False
    assert et_possible(CompetitionFormat.GROUP_KNOCKOUT, True) is True
    assert (
        et_possible(CompetitionFormat.GROUP_KNOCKOUT, None) is True
    )  # unknown → assume possible (fail closed)


# ------------------------------------------------------------------ ESPN evidence parsing


def _scoreboard(details, status="STATUS_FULL_TIME", hs="2", as_="1", shootout=None):
    home = {"homeAway": "home", "score": hs, "team": {"id": "10", "displayName": "H"}}
    away = {"homeAway": "away", "score": as_, "team": {"id": "20", "displayName": "A"}}
    if shootout:
        home["shootoutScore"], away["shootoutScore"] = shootout
    return {
        "events": [
            {
                "id": "555",
                "date": "2026-09-27T18:00Z",
                "season": {"year": 2026, "slug": "2026-27"},
                "competitions": [
                    {
                        "competitors": [home, away],
                        "status": {"type": {"state": "post", "name": status}},
                        "details": details,
                        "neutralSite": True,
                    }
                ],
            }
        ]
    }


def _goal(team, disp, own=False, shootout=False):
    return {
        "scoringPlay": True,
        "clock": {"displayValue": disp},
        "team": {"id": team},
        "ownGoal": own,
        "shootout": shootout,
    }


def _emap():
    return EspnMap(
        leagues={"uefa.nations": "uefa.nations_league"},
        teams={"10": "nat.h", "20": "nat.a"},
        version=0,
    )


def test_espn_goal_events_give_ht_split_first_scorer_and_regulation_score():
    body = _scoreboard(
        [_goal("20", "12'"), _goal("10", "45'+2'"), _goal("10", "78'")], hs="2", as_="1"
    )
    (ev,) = parse_scoreboard("uefa.nations", body)
    assert (
        len(ev.goal_events) == 3
        and ev.goal_events[1].minute == 45
        and ev.goal_events[1].stoppage == 2
    )
    (r,) = results_from_events([ev], _emap())
    assert (r.home_goals_ht, r.away_goals_ht) == (1, 1)
    assert (r.home_goals_regulation, r.away_goals_regulation) == (2, 1)
    assert r.first_scorer_team == "away" and r.extra_time_played is False and r.neutral_site is True
    assert r.status_name == "STATUS_FULL_TIME" and r.kickoff_utc == "2026-09-27T18:00:00Z"


def test_espn_aet_and_shootout_are_split_out():
    body = _scoreboard(
        [_goal("10", "30'"), _goal("20", "88'"), _goal("10", "104'"), _goal("20", "119'")],
        status="STATUS_FINAL_PEN",
        hs="2",
        as_="2",
        shootout=("4", "3"),
    )
    (ev,) = parse_scoreboard("uefa.nations", body)
    (r,) = results_from_events([ev], _emap())
    assert (r.home_goals_regulation, r.away_goals_regulation) == (1, 1) and (
        r.home_goals_et,
        r.away_goals_et,
    ) == (1, 1)
    assert r.extra_time_played and r.decided_on_penalties and r.winner_after_penalties == "home"


def test_espn_inconsistent_details_emit_no_split():
    body = _scoreboard([_goal("10", "30'")], hs="2", as_="0", status="STATUS_FINAL")
    (ev,) = parse_scoreboard("uefa.nations", body)
    (r,) = results_from_events([ev], _emap())
    assert r.home_goals_regulation is None and r.home_goals_ht is None


def test_espn_own_goal_credits_the_opponent():
    body = _scoreboard([_goal("20", "10'", own=True)], hs="1", as_="0")
    (ev,) = parse_scoreboard("uefa.nations", body)
    (r,) = results_from_events([ev], _emap())
    assert r.first_scorer_team == "home" and (r.home_goals_regulation, r.away_goals_regulation) == (
        1,
        0,
    )


def test_espn_archive_appends_an_upgrade_row_but_never_a_new_score(tmp_path):
    arch = EspnArchive(tmp_path)
    legacy = result_record(_mr(), "555", "uefa.nations")
    assert arch.append_results("uefa.nations", [legacy]) == 1
    assert arch.append_results("uefa.nations", [legacy]) == 0
    richer = result_record(
        _mr(status_name="STATUS_FULL_TIME", home_goals_regulation=2, away_goals_regulation=1),
        "555",
        "uefa.nations",
    )
    assert arch.append_results("uefa.nations", [richer]) == 1
    different = result_record(_mr(h=5, a=5, status_name="STATUS_FULL_TIME"), "555", "uefa.nations")
    assert arch.append_results("uefa.nations", [different]) == 0
    (r,) = arch.results(("uefa.nations",))
    assert r.home_goals_regulation == 2 and r.home_goals == 2


# ------------------------------------------------------------------ every priced competition has a source


def test_every_priced_competition_has_a_settlement_source():
    emap = EspnMap.load()
    espn_comps = set(emap.leagues.values())
    priced = set(DEFAULT_COMPETITIONS) | set(ESPN_POOLS)
    missing = sorted(c for c in priced if c not in COMPETITION_FILES and c not in espn_comps)
    assert missing == [], f"priced competitions without a result source: {missing}"
    # and the intl pool's own competitions (which records carry as competition_id) are covered too
    for comp in (
        "uefa.nations_league",
        "concacaf.nations_league",
        "fifa.friendly",
        "fifa.world_cup_qualifiers",
        "fra.ligue_1",
        "usa.mls",
        "mex.liga_mx",
        "bra.serie_a",
        "arg.primera",
        "uefa.champions_league",
    ):
        assert comp in espn_comps or comp in COMPETITION_FILES, comp
