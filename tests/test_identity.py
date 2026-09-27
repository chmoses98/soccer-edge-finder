from __future__ import annotations

import pytest

from soccer_edge.core.errors import AmbiguousAliasError, UnknownAliasError
from soccer_edge.identity.models import (
    Fixture,
    FixtureStatus,
    Gender,
    MatchLeg,
    Team,
    TeamKind,
    Tie,
)
from soccer_edge.identity.registry import normalize_alias


def test_registry_loads_without_in_scope_ambiguity(registry):
    assert registry.ambiguous_team_aliases() == {}
    assert len(registry.teams) > 200


@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        ("Man United", "eng.man_united"),
        ("Manchester Utd", "eng.man_united"),
        ("Nott'm Forest", "eng.nottm_forest"),
        ("Paris SG", "fra.psg"),
        ("PSG", "fra.psg"),
        ("Inter", "ita.inter"),
        ("Internazionale", "ita.inter"),
        ("Bayern", "ger.bayern"),
        ("FC Bayern München", "ger.bayern"),
        ("Ath Bilbao", "esp.athletic_bilbao"),
        ("Wolves", "eng.wolves"),
        ("M'gladbach", "ger.gladbach"),
    ],
)
def test_vendor_aliases_resolve(registry, alias, expected):
    assert registry.resolve_team(alias, gender=Gender.MEN).team_id == expected


def test_similar_names_do_not_collide(registry):
    assert registry.resolve_team("Real Madrid", gender=Gender.MEN).team_id == "esp.real_madrid"
    assert registry.resolve_team("Real Betis", gender=Gender.MEN).team_id == "esp.real_betis"
    assert registry.resolve_team("Real Sociedad", gender=Gender.MEN).team_id == "esp.real_sociedad"
    assert registry.resolve_team("Inter", gender=Gender.MEN).team_id == "ita.inter"
    assert registry.resolve_team("Milan", gender=Gender.MEN).team_id == "ita.milan"


def test_women_vs_men_requires_scope(registry):
    with pytest.raises(AmbiguousAliasError):
        registry.resolve_team("Arsenal")
    assert registry.resolve_team("Arsenal", gender=Gender.MEN).team_id == "eng.arsenal"
    assert registry.resolve_team("Arsenal", gender=Gender.WOMEN).team_id == "eng.arsenal_w"


def test_reserve_team_resolves_separately(registry):
    b = registry.resolve_team("Barcelona B")
    assert b.kind is TeamKind.RESERVE and b.parent_team_id == "esp.barcelona"
    assert (
        registry.resolve_team("Barcelona", gender=Gender.MEN, kind=TeamKind.CLUB).team_id
        == "esp.barcelona"
    )


def test_unknown_alias_fails_loudly(registry):
    with pytest.raises(UnknownAliasError):
        registry.resolve_team("FC Nowhere United")


def test_national_teams_scoped_by_kind(registry):
    assert (
        registry.resolve_team("England", kind=TeamKind.NATIONAL, gender=Gender.MEN).team_id
        == "nat.eng"
    )
    assert registry.resolve_team("Korea Republic", gender=Gender.MEN).team_id == "nat.kor"


def test_competition_aliases_and_former_names(registry):
    assert registry.resolve_competition("EPL").competition_id == "eng.premier_league"
    assert (
        registry.resolve_competition("Barclays Premier League").competition_id
        == "eng.premier_league"
    )
    assert (
        registry.resolve_competition("UEFA Europa Conference League").competition_id
        == "uefa.conference_league"
    )
    assert (
        registry.resolve_competition("Champions League").competition_id == "uefa.champions_league"
    )


def test_normalize_alias_strips_diacritics_and_punct():
    assert normalize_alias("Atlético de Madrid") == "atletico de madrid"
    assert normalize_alias("Brighton & Hove Albion") == "brighton and hove albion"
    assert normalize_alias("Nott'm Forest") == "nottm forest"


def test_fixture_id_stable_across_reschedule():
    a = Fixture.make_id(
        "eng.premier_league", "2026-27", "eng.arsenal", "eng.leeds", stage="Matchday 6"
    )
    b = Fixture.make_id(
        "eng.premier_league", "2026-27", "eng.arsenal", "eng.leeds", stage="Matchday 6"
    )
    assert a == b == "fx:eng.premier_league:2026-27:eng.arsenal:eng.leeds:matchday_6"
    replay = Fixture.make_id(
        "eng.fa_cup", "2026-27", "eng.arsenal", "eng.leeds", stage="Round 3", occurrence=2
    )
    assert replay.endswith(":occ2")


def test_rescheduled_fixture_must_point_forward():
    with pytest.raises(ValueError):
        Fixture(
            fixture_id="fx:x",
            competition_id="c",
            season_id="2026-27",
            home_team_id="a",
            away_team_id="b",
            kickoff_date="2026-01-01",
            status=FixtureStatus.RESCHEDULED,
        )
    f = Fixture(
        fixture_id="fx:x",
        competition_id="c",
        season_id="2026-27",
        home_team_id="a",
        away_team_id="b",
        kickoff_date="2026-01-01",
        status=FixtureStatus.RESCHEDULED,
        superseded_by="fx:y",
    )
    assert f.superseded_by == "fx:y"


def test_two_leg_tie_consistency():
    legs = (
        MatchLeg(tie_id="tie:1", fixture_id="fx:a", leg_number=1),
        MatchLeg(tie_id="tie:1", fixture_id="fx:b", leg_number=2),
    )
    tie = Tie(
        tie_id="tie:1",
        competition_id="uefa.champions_league",
        season_id="2026-27",
        stage="Round of 16",
        team_a_id="x",
        team_b_id="y",
        legs=legs,
    )
    assert len(tie.legs) == 2
    with pytest.raises(ValueError):
        Tie(
            tie_id="tie:1",
            competition_id="c",
            season_id="2026-27",
            stage="s",
            team_a_id="x",
            team_b_id="y",
            legs=(legs[0], legs[0]),
        )
    with pytest.raises(ValueError):
        Fixture(
            fixture_id="fx:a",
            competition_id="c",
            season_id="2026-27",
            home_team_id="x",
            away_team_id="y",
            kickoff_date="2026-03-01",
            tie_id="tie:1",
        )


def test_reserve_requires_parent():
    with pytest.raises(ValueError):
        Team(team_id="x.b", name="X B", country="ESP", kind=TeamKind.RESERVE)
