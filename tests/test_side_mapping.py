"""Regression: a Kalshi team leg must never be priced on the wrong side of the fixture.

Live incident (board of 2026-10-09 for Vasco da Gama v Remo, KXBRASILEIROGAME-26OCT10VDGCR): the
leg code 'CR' (Clube do Remo, the AWAY side) matched Vasco's alias 'CR Vasco da Gama' first, so the
Remo-to-win contract was priced as 'Result: home' (fair 0.574 vs price 0.095, a fabricated edge), and
the same happened to Remo's spread / team-total / first-half legs.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from soccer_edge.identity.models import Fixture
from soccer_edge.kalshi import association as assoc_mod
from soccer_edge.kalshi.association import (
    _code_matches,
    associate,
    index_fixtures,
    structural_position,
)
from soccer_edge.kalshi.client import KalshiPublicClient
from soccer_edge.kalshi.coverage import Disposition
from soccer_edge.kalshi.discovery import discover
from soccer_edge.kalshi.fake import FakeKalshi
from soccer_edge.kalshi.schemas import RawEvent, RawMarket
from soccer_edge.kalshi.taxonomy import MarketFamily, Period, classify
from soccer_edge.pricing.semantics import Semantics
from soccer_edge.run import pipeline as pipeline_mod
from soccer_edge.run.pipeline import (
    RunConfig,
    _cached_semantics_match,
    _duplicate_side_tickers,
    _sem_signature,
    run,
)
from soccer_edge.run.simcache import CachedFixtureSim
from soccer_edge.slate.board import orientation_conflicts
from tests.test_run_pipeline import _inputs

EVENT = "26OCT10VDGCR"


@pytest.fixture
def vasco_remo() -> Fixture:
    return Fixture(
        fixture_id="fx:bra.serie_a:2026:bra.vasco:bra.remo",
        competition_id="bra.serie_a",
        season_id="2026",
        home_team_id="bra.vasco",
        away_team_id="bra.remo",
        kickoff_utc=datetime(2026, 10, 10, 22, 0, tzinfo=UTC),
        kickoff_date="2026-10-10",
    )


def _assoc(registry, fx: Fixture, ticker: str, *, title: str = "Vasco da Gama vs Remo", **extra):
    series, event, _ = ticker.split("-", 2)
    m = RawMarket.from_api(
        {"ticker": ticker, "event_ticker": f"{series}-{event}", "title": "", **extra}
    )
    ev = RawEvent(event_ticker=f"{series}-{event}", series_ticker=series, title=title)
    return associate(classify(m), ev, registry, index_fixtures([fx]))


@pytest.mark.parametrize(
    ("ticker", "side"),
    [
        (f"KXBRASILEIROGAME-{EVENT}-VDG", "bra.vasco"),
        (f"KXBRASILEIROGAME-{EVENT}-CR", "bra.remo"),  # the published 'Result: home' bug
        (f"KXBRASILEIRO1H-{EVENT}-CR", "bra.remo"),
        (f"KXBRASILEIROSPREAD-{EVENT}-CR3", "bra.remo"),
        (f"KXBRASILEIROSPREAD-{EVENT}-VDG2", "bra.vasco"),
        (f"KXBRASILEIROTEAMTOTAL-{EVENT}-CR1", "bra.remo"),
        (f"KXBRASILEIROSCORE-{EVENT}-VDG1CR0", "bra.vasco"),
    ],
)
def test_vasco_remo_legs_map_to_the_team_in_that_position(registry, vasco_remo, ticker, side):
    a = _assoc(registry, vasco_remo, ticker, floor_strike="1.5")
    assert a.status == "mapped", a.detail
    assert a.side_team_id == side


def test_the_draw_leg_carries_no_team(registry, vasco_remo):
    a = _assoc(registry, vasco_remo, f"KXBRASILEIROGAME-{EVENT}-TIE")
    assert a.status == "mapped" and a.side_team_id is None


def test_cr_is_a_genuine_name_collision_resolved_only_by_position(registry):
    # both clubs legitimately answer to 'CR' by name - which is why name matching alone guessed home
    assert _code_matches("CR", "CR Vasco da Gama")
    assert _code_matches("CR", "Clube do Remo")
    assert structural_position("CR", "VDGCR") == 1
    assert structural_position("VDG", "VDGCR") == 0


@pytest.mark.parametrize(
    ("code", "pair"),
    [("CR", "CRCR"), ("XYZ", "VDGCR"), ("CR", None), ("VDGCR", "VDGCR"), ("", "VDGCR")],
)
def test_structural_position_never_guesses(code, pair):
    assert structural_position(code, pair) is None


def test_position_disagreeing_with_the_only_name_match_is_unmappable(registry, vasco_remo):
    # 'VDG' can only be Vasco by name, but sits in Remo's (second) slot of 'CRVDG': refuse, never guess
    a = _assoc(registry, vasco_remo, "KXBRASILEIROGAME-26OCT10CRVDG-VDG")
    assert a.status == "side_conflict"
    assert a.side_team_id is None and "VDG" in a.detail


def test_name_match_on_both_teams_without_position_stays_unresolved(registry, vasco_remo):
    # no pair code to place 'CR' -> no side (the old matcher returned the home team)
    team, conflict = assoc_mod._resolve_side_team(
        "CR", None, ("bra.vasco", "bra.remo"), vasco_remo, registry
    )
    assert team is None and conflict == ""


# ---- pipeline guards ---------------------------------------------------------------------------


def _w(ticker: str, side: str | None, family=MarketFamily.MATCH_RESULT_3WAY, line=None):
    ev = ticker.rsplit("-", 1)[0]
    sem = Semantics(ticker, family, Period.REGULATION, side, line)
    return SimpleNamespace(market=SimpleNamespace(ticker=ticker, event_ticker=ev), sem=sem)


def test_two_contracts_on_one_side_are_both_flagged():
    ws = [
        _w(f"KXBRASILEIROGAME-{EVENT}-VDG", "home"),
        _w(f"KXBRASILEIROGAME-{EVENT}-CR", "home"),
        _w(f"KXBRASILEIROGAME-{EVENT}-TIE", "draw"),
        _w(f"KXBRASILEIROSPREAD-{EVENT}-VDG3", "home", MarketFamily.HANDICAP, 2.5),
        _w(f"KXBRASILEIROSPREAD-{EVENT}-CR3", "away", MarketFamily.HANDICAP, 2.5),
    ]
    dup = _duplicate_side_tickers(ws)  # type: ignore[arg-type]
    assert set(dup) == {f"KXBRASILEIROGAME-{EVENT}-VDG", f"KXBRASILEIROGAME-{EVENT}-CR"}
    assert "collision" in dup[f"KXBRASILEIROGAME-{EVENT}-CR"]


def test_correctly_oriented_board_has_no_collisions():
    ws = [
        _w(f"KXBRASILEIROGAME-{EVENT}-VDG", "home"),
        _w(f"KXBRASILEIROGAME-{EVENT}-CR", "away"),
        _w(f"KXBRASILEIROGAME-{EVENT}-TIE", "draw"),
        _w(f"KXBRASILEIROSPREAD-{EVENT}-CR2", "away", MarketFamily.HANDICAP, 1.5),
        _w(f"KXBRASILEIROSPREAD-{EVENT}-CR3", "away", MarketFamily.HANDICAP, 2.5),
        _w(f"KXBRASILEIROTOTAL-{EVENT}-3", None, MarketFamily.TOTAL_GOALS, 2.5),
    ]
    assert _duplicate_side_tickers(ws) == {}  # type: ignore[arg-type]


def test_cached_price_is_not_replayed_for_a_reoriented_contract():
    home = _w(f"KXBRASILEIROGAME-{EVENT}-CR", "home")
    away = _w(f"KXBRASILEIROGAME-{EVENT}-CR", "away")
    tk = home.market.ticker

    def cache(entry):
        return CachedFixtureSim("k", "fx", "h", {}, {tk: entry})

    assert _cached_semantics_match(cache({"semantics": _sem_signature(away.sem)}), [away])  # type: ignore[list-item]
    # priced on the wrong side before the fix -> recompute, never replay 0.574 as Remo's win prob
    assert not _cached_semantics_match(cache({"semantics": _sem_signature(home.sem)}), [away])  # type: ignore[list-item]
    # entries written before signatures existed are recomputed once
    assert not _cached_semantics_match(cache({"description": "Result: home"}), [away])  # type: ignore[list-item]


@pytest.fixture
def disc(registry, epl_fixtures):
    fake = FakeKalshi(
        epl_fixtures,
        registry,
        fair=lambda f: {"home": 0.45, "draw": 0.27, "away": 0.28, "mean_total": 2.6},
    )
    return discover(KalshiPublicClient(transport=fake.transport))


def test_pipeline_drops_both_legs_when_two_map_to_the_same_side(
    registry, epl_fixtures, disc, monkeypatch
):
    """Reproduce the incident inside a full run: force the away 3-way leg of one fixture onto the
    home team (what the 'CR' matcher did) and check neither leg is priced, boarded or recommended."""
    fx = epl_fixtures[0]  # Arsenal (home) v Leeds (away)
    real = pipeline_mod.associate

    def buggy(spec, event, reg, idx):
        a = real(spec, event, reg, idx)
        if a.side_team_id == fx.away_team_id and spec.family is MarketFamily.MATCH_RESULT_3WAY:
            return assoc_mod.Association(**{**a.__dict__, "side_team_id": fx.home_team_id})
        return a

    monkeypatch.setattr(pipeline_mod, "associate", buggy)
    art = run(
        _inputs(registry, epl_fixtures, disc),
        RunConfig(run_date=date(2026, 10, 10), n_worlds=60, draws_per_world=30),
    )
    legs = [
        tk
        for tk, w in disc.markets.items()
        if w.event_ticker.startswith("KXEPLGAME-") and tk.endswith(("-ARS", "-LEE"))
    ]
    assert len(legs) == 2
    for tk in legs:
        disp, reason = art.coverage.dispositions[tk]
        assert disp is Disposition.UNPRICEABLE and "side mapping collision" in reason
        assert all(r.market_ticker != tk for r in art.output.recommendations)
        assert all(r.market_ticker != tk for r in art.output.shadow_recommendations)
        assert tk not in art.board_entries.get(fx.fixture_id, {}).get("contracts", {})
    # the draw and every other contract of the fixture are unaffected
    tie = next(t for t in disc.markets if t.startswith("KXEPLGAME-") and "ARSLEE-TIE" in t)
    assert art.coverage.dispositions[tie][0] is Disposition.PRICED
    assert art.output.coverage.unaccounted_contracts == 0


def _board_c(ticker: str, family: str, side: str | None, line: str | None = None) -> dict:
    return {
        "event_ticker": ticker.rsplit("-", 1)[0],
        "family": family,
        "side": side,
        "line": line,
        "period": "regulation",
        "description": f"{family}:{side}",
    }


def test_reprice_guard_rejects_the_stale_published_board_entries():
    """The model board on data-archive (2026-10-09T17:57Z) still holds Remo's legs priced as 'home';
    a quote-only reprice must not republish them before the fixture is re-modelled."""
    g, s, t = (f"KXBRASILEIRO{x}-{EVENT}" for x in ("GAME", "SPREAD", "TOTAL"))
    stale = {
        f"{g}-VDG": _board_c(f"{g}-VDG", "match_result_3way", "home"),
        f"{g}-CR": _board_c(f"{g}-CR", "match_result_3way", "home"),
        f"{g}-TIE": _board_c(f"{g}-TIE", "match_result_3way", "draw"),
        f"{s}-CR3": _board_c(f"{s}-CR3", "handicap", "home", "2.5"),
        f"{s}-VDG2": _board_c(f"{s}-VDG2", "handicap", "home", "1.5"),
        f"{t}-3": _board_c(f"{t}-3", "total_goals", None, "2.5"),
    }
    bad = orientation_conflicts(stale)
    assert set(bad) == {f"{g}-VDG", f"{g}-CR", f"{s}-CR3"}
    assert "position 1" in bad[f"{g}-CR"] and "collision" in bad[f"{g}-VDG"]
    fixed = {
        **stale,
        f"{g}-CR": _board_c(f"{g}-CR", "match_result_3way", "away"),
        f"{s}-CR3": _board_c(f"{s}-CR3", "handicap", "away", "2.5"),
    }
    assert orientation_conflicts(fixed) == {}
