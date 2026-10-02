"""Live slate: cached model distributions repriced against fresh Kalshi captures (docs/ACTIONABLE_SLATE.md).

The board comes from a real pipeline run on the synthetic Kalshi surface; every reprice afterwards must
run without a model fit, a simulation, a network call or a ledger write."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

import soccer_edge.run.pipeline as pipeline_mod
from soccer_edge.archive.ledger import PredictionLedger
from soccer_edge.contracts.slate_v1 import ActionableSlateV1
from soccer_edge.dispatch.horizons import DueHorizon, ScheduledFixture
from soccer_edge.kalshi.client import KalshiPublicClient
from soccer_edge.kalshi.discovery import discover
from soccer_edge.kalshi.fake import FakeKalshi
from soccer_edge.run.pipeline import RunConfig, run
from soccer_edge.run.simcache import SimCache
from soccer_edge.slate.board import load_board, merge_boards, priced_from_entry, save_board
from soccer_edge.slate.invalidation import expected_versions
from soccer_edge.slate.market_view import MarketView
from soccer_edge.slate.observations import LineupObservation, fixture_context
from soccer_edge.slate.refresh import refresh_plan
from soccer_edge.slate.reprice import (
    SLATE_FILE,
    SLATE_LOG_DIR,
    RepriceContext,
    previous_slate,
    reprice,
    write_slate,
)
from tests.test_run_pipeline import _inputs

ROOT = Path(__file__).resolve().parents[1]
KO = datetime(2026, 10, 10, 14, 0, tzinfo=UTC)
NOW = KO - timedelta(hours=3)  # inside the 48 h lookahead
VERSIONS = expected_versions()


# ------------------------------------------------------------------------------------------- helpers


@pytest.fixture(scope="module")
def built(registry, tmp_path_factory):
    """One real model run (synthetic Kalshi surface) -> board + the sweep it priced against."""
    tmp = tmp_path_factory.mktemp("slate")
    fixtures = _epl_fixtures(registry)
    fake = FakeKalshi(
        fixtures,
        registry,
        fair=lambda f: {"home": 0.45, "draw": 0.27, "away": 0.28, "mean_total": 2.6},
    )
    disc = discover(KalshiPublicClient(transport=fake.transport))
    cfg = RunConfig(
        run_date=date(2026, 10, 10),
        n_worlds=120,
        draws_per_world=40,
        engine_version="world_sim_v2",
    )
    art = run(_inputs(registry, fixtures, disc), cfg, sim_cache=SimCache(tmp / "cache"))
    board = merge_boards({"fixtures": art.board_entries}, now=NOW)
    return {"board": board, "disc": disc, "art": art, "fixtures": fixtures, "cfg": cfg}


def _epl_fixtures(registry):
    from soccer_edge.identity.models import Fixture

    pairs = [
        ("eng.arsenal", "eng.leeds"),
        ("eng.chelsea", "eng.bournemouth"),
        ("eng.liverpool", "eng.man_city"),
    ]
    return [
        Fixture(
            fixture_id=Fixture.make_id("eng.premier_league", "2026-27", h, a, stage="Matchday 6"),
            competition_id="eng.premier_league",
            season_id="2026-27",
            home_team_id=h,
            away_team_id=a,
            kickoff_utc=KO,
            kickoff_date="2026-10-10",
            stage="Matchday 6",
        )
        for h, a in pairs
    ]


def _view(disc, observed_at=None, moves: dict[str, Decimal] | None = None) -> MarketView:
    v = MarketView.from_discovery(disc)
    v.observed_at = observed_at or NOW - timedelta(minutes=2)
    if moves:
        for tk, ask in moves.items():
            m = v.markets[tk]
            v.markets[tk] = m.model_copy(update={"yes_ask": ask, "no_bid": Decimal(1) - ask})
    return v


def _rc(board, view, roots=(), now=NOW, **kw) -> RepriceContext:
    return RepriceContext(
        board=board,
        view=view,
        roots=list(roots),
        now=now,
        trigger=kw.pop("trigger", "test"),
        versions=kw.pop("versions", VERSIONS),
        **kw,
    )


def _no_compute(monkeypatch):
    """Any model fit, simulation or network call during a reprice fails the test."""

    def boom(*a, **k):
        raise AssertionError("reprice must not simulate / fit / call the network")

    monkeypatch.setattr(pipeline_mod, "_simulate_fixture", boom)
    monkeypatch.setattr(pipeline_mod, "simulate_v2", boom)
    monkeypatch.setattr(pipeline_mod, "simulate", boom)
    import soccer_edge.run.modeling as modeling

    monkeypatch.setattr(modeling, "fit_competition", boom)
    import httpx

    monkeypatch.setattr(httpx.Client, "send", boom)
    import soccer_edge.providers.the_odds_api as toa

    monkeypatch.setattr(toa.OddsApiClient, "__init__", boom)


def _cheap(board, fid=None) -> dict[str, Decimal]:
    """A YES ask far below the model probability on one 3-way contract per fixture (a clear edge)."""
    out = {}
    for f, e in board["fixtures"].items():
        if fid is not None and f != fid:
            continue
        tk, c = max(
            ((t, c) for t, c in e["contracts"].items() if c["family"] == "match_result_3way"),
            key=lambda x: x[1]["p"],
        )
        out[tk] = Decimal(str(round(c["p"] - 0.15, 2)))
    return out


def _a_contract(board) -> tuple[str, str]:
    """(fixture_id, ticker) of a 3-way contract on the board."""
    for fid, e in board["fixtures"].items():
        for tk, c in e["contracts"].items():
            if c["family"] == "match_result_3way":
                return fid, tk
    raise AssertionError("no 3-way contract")


def _write_root(root: Path, *, fixtures=(), lineups=(), pinnacle=(), status=None, as_of=None):
    day = (as_of or NOW).strftime("%Y-%m-%d")
    if fixtures:
        p = root / "fixtures" / "espn" / day / "espn-000000.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"as_of": (as_of or NOW).isoformat(), "fixtures": list(fixtures)}))
    if lineups:
        p = root / "lineups" / day / "eng.1.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("".join(json.dumps(r) + "\n" for r in lineups))
    if pinnacle:
        p = root / "reference" / day / "oddsapi-kd-test.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("".join(json.dumps(r) + "\n" for r in pinnacle))
    if status:
        (root / "STATUS.json").write_text(json.dumps(status))


def _espn_row(fid, *, kickoff=KO, neutral=False, eid="9001"):
    return {
        "fixture_id": fid,
        "kickoff_utc": kickoff.isoformat(),
        "neutral_site": neutral,
        "competition_id": "eng.premier_league",
        "stage": "Matchday 6",
        "espn_event_id": eid,
    }


def _lineup_row(eid="9001", *, published=True, captured=None, h="sha256:xi1"):
    return {
        "espn_event_id": eid,
        "league": "eng.1",
        "captured_at": (captured or NOW - timedelta(minutes=10)).isoformat(),
        "lineup_state": "confirmed" if published else "unconfirmed",
        "published": published,
        "content_hash": h,
    }


# ------------------------------------------------------------------------------------------- board


def test_run_writes_a_board_entry_per_priced_fixture(built):
    board, art = built["board"], built["art"]
    assert set(board["fixtures"]) == {f.fixture_id for f in built["fixtures"]}
    e = next(iter(board["fixtures"].values()))
    assert e["inputs"]["engine_version"] == "world_sim_v2"
    assert e["inputs"]["lineup_key"] == "none" and e["sim_key"].startswith("sha256:")
    priced = {r["ticker"] for r in art.per_contract}
    on_board = {t for e in board["fixtures"].values() for t in e["contracts"]}
    assert priced <= on_board  # every archived (PRICED) contract is on the board
    for c in e["contracts"].values():
        assert len(c["q"]) == 100 and c["q"] == sorted(c["q"])
        assert c["p_low"] <= c["p"] <= c["p_high"]


def test_board_quantiles_reproduce_the_robust_edge(built):
    """The 100 stored quantiles reproduce the run's own worst-case edge and bet-up-to on the same quote."""
    from soccer_edge.kalshi.executable import top_of_book
    from soccer_edge.kalshi.fees import FeeRegime
    from soccer_edge.pricing.edge import assess

    art, board = built["art"], built["board"]
    rec = next(r for r in art.per_contract if r["edge"]["yes"])
    c = board["fixtures"][rec["fixture_id"]]["contracts"][rec["ticker"]]
    m = built["disc"].markets[rec["ticker"]]
    regime = FeeRegime(rec["fee_regime"]["fee_type"], Decimal(rec["fee_regime"]["fee_multiplier"]))
    a = assess(priced_from_entry(rec["ticker"], c), top_of_book(m, "yes"), regime)
    orig = rec["edge"]["yes"]
    assert a.fee_adjusted_edge == pytest.approx(orig["fee_adjusted_edge"], abs=1e-5)
    assert a.worst_case_edge == pytest.approx(orig["worst_case_edge"], abs=0.01)
    assert abs(float(a.bet_up_to_price or 0) - float(orig["bet_up_to_price"] or 0)) <= 0.01


def test_board_merge_is_order_safe_and_drops_started(built):
    board = built["board"]
    fid = next(iter(board["fixtures"]))
    older = json.loads(json.dumps(board))
    older["fixtures"][fid]["model_generated_at"] = "2026-10-01T00:00:00Z"
    older["fixtures"][fid]["source_run_id"] = "old"
    a = merge_boards(older, board, now=NOW)
    b = merge_boards(board, older, now=NOW)
    assert a["fixtures"][fid]["source_run_id"] == b["fixtures"][fid]["source_run_id"] != "old"
    gone = merge_boards(board, now=KO + timedelta(hours=2))
    assert gone["fixtures"] == {}


# ------------------------------------------------------------------------------------------- reprice


def test_price_change_with_unchanged_model_reprices_without_simulation(
    built, monkeypatch, tmp_path
):
    board, disc = built["board"], built["disc"]
    fid, tk = _a_contract(board)
    s1 = reprice(_rc(board, _view(disc)))
    write_slate(tmp_path, s1)
    _no_compute(monkeypatch)
    old_ask = disc.markets[tk].yes_ask
    new_ask = (old_ask or Decimal("0.5")) - Decimal("0.07")
    s2 = reprice(
        _rc(
            board,
            _view(disc, NOW + timedelta(minutes=1), {tk: new_ask}),
            now=NOW + timedelta(minutes=2),
        )
    )
    row = write_slate(tmp_path, s2, prev=previous_slate(tmp_path))
    y1 = next(c for c in s1.contracts if c.ticker == tk and c.side == "yes")
    y2 = next(c for c in s2.contracts if c.ticker == tk and c.side == "yes")
    assert y1.kalshi_price == old_ask and y2.kalshi_price == new_ask
    assert y2.model_probability == y1.model_probability  # the model did not move
    assert y2.fee_adjusted_ev > y1.fee_adjusted_ev  # a cheaper ask is a better bet
    assert s2.compute.simulations_run == 0 and s2.compute.mode == "reprice_only"
    assert s2.compute.odds_api_calls == 0 and s2.compute.odds_api_credits == 0
    assert row["price_changes_vs_previous"] >= 1
    assert any(ch["ticker"] == tk for ch in row["price_change_sample"])
    assert (tmp_path / SLATE_LOG_DIR).is_dir() and (tmp_path / SLATE_FILE).exists()
    ActionableSlateV1.model_validate_json((tmp_path / SLATE_FILE).read_text())


def test_stale_kalshi_price_is_never_actionable(built):
    board, disc = built["board"], built["disc"]
    fresh = reprice(_rc(board, _view(disc, moves=_cheap(board))))
    assert fresh.kalshi.status == "CURRENT"
    assert any(c.action == "RESEARCH_CANDIDATE" for c in fresh.contracts)
    stale = reprice(_rc(board, _view(disc, NOW - timedelta(minutes=45), _cheap(board))))
    assert stale.kalshi.status == "STALE"
    quoted = [c for c in stale.contracts if c.kalshi_price is not None]
    assert quoted and all(c.action == "STALE_PRICE" for c in quoted)
    assert not any(c.bet_permitted for c in stale.contracts)
    aging = reprice(_rc(board, _view(disc, NOW - timedelta(minutes=25), _cheap(board))))
    assert aging.kalshi.status == "AGING"
    assert all(c.action in ("STALE_PRICE", "NO_QUOTE") for c in aging.contracts)
    # the read-time deadline is explicit
    assert fresh.actionable_until == fresh.kalshi.current_until
    assert fresh.kalshi.current_until == (NOW - timedelta(minutes=2)) + timedelta(minutes=20)


def test_no_kalshi_sweep_means_no_action(built):
    s = reprice(_rc(built["board"], None))
    assert s.kalshi.status == "UNAVAILABLE"
    assert s.contracts and all(c.action == "NO_QUOTE" for c in s.contracts)


def test_everything_is_research_only(built):
    s = reprice(_rc(built["board"], _view(built["disc"], moves=_cheap(built["board"]))))
    assert s.no_bets and not any(c.bet_permitted for c in s.contracts)
    assert {c.authority for c in s.contracts} == {"RESEARCH_ONLY"}
    assert all(c.action != "ACTIONABLE" for c in s.contracts)
    best = [c for c in s.contracts if c.best_expression]
    assert best and all(c.action == "RESEARCH_CANDIDATE" for c in best)


# ------------------------------------------------------------------------------------------- invalidation


def test_lineup_change_invalidates_cached_simulation(built, registry, tmp_path):
    board, disc = built["board"], built["disc"]
    fid = sorted(board["fixtures"])[0]
    root = tmp_path / "arch"
    _write_root(root, fixtures=[_espn_row(fid)], lineups=[_lineup_row(published=False)])
    s = reprice(_rc(board, _view(disc), [root]))
    assert next(f for f in s.fixtures if f.fixture_id == fid).model.validity == "VALID"
    _write_root(root, fixtures=[_espn_row(fid)], lineups=[_lineup_row(published=True)])
    s = reprice(_rc(board, _view(disc), [root]))
    f = next(f for f in s.fixtures if f.fixture_id == fid)
    assert f.model.validity == "INVALIDATED" and f.model.invalidation_reasons[0].startswith(
        "lineup_changed"
    )
    assert f.lineup.status == "confirmed"
    quoted = [c for c in s.contracts if c.fixture_id == fid and c.kalshi_price is not None]
    assert quoted and {c.action for c in quoted} == {"MODEL_INVALIDATED"}
    # other fixtures are untouched
    assert all(f2.model.validity == "VALID" for f2 in s.fixtures if f2.fixture_id != fid)
    # and the model run itself does not reuse the cached simulation for the new XI
    cache = SimCache(tmp_path / "cache")
    inputs = _inputs(registry, built["fixtures"], built["disc"])
    a = run(inputs, built["cfg"], sim_cache=cache)
    assert len(a.fixtures_simulated) == 3
    b = run(_inputs(registry, built["fixtures"], built["disc"]), built["cfg"], sim_cache=cache)
    assert b.fixtures_repriced and not b.fixtures_simulated
    inputs = _inputs(registry, built["fixtures"], built["disc"])
    inputs.lineup_observations = {
        fid: LineupObservation("confirmed", "sha256:xi1", NOW, NOW, "eng.1")
    }
    c = run(inputs, built["cfg"], sim_cache=cache)
    assert c.fixtures_simulated == [fid]
    assert c.board_entries[fid]["inputs"]["lineup_key"] == "sha256:xi1"


def test_model_version_change_invalidates(built):
    board, disc = built["board"], built["disc"]
    s = reprice(
        _rc(board, _view(disc), versions=expected_versions(engine_version="minute_engine_v1"))
    )
    assert {f.model.validity for f in s.fixtures} == {"INVALIDATED"}
    assert all(
        "model_version_changed:engine_version" in f.model.invalidation_reasons[0]
        for f in s.fixtures
    )
    s = reprice(_rc(board, _view(disc), versions=expected_versions(model_version="dc_laplace_v2")))
    assert {f.model.validity for f in s.fixtures} == {"INVALIDATED"}


def test_kickoff_and_venue_changes_invalidate_but_price_moves_do_not(built, tmp_path):
    board, disc = built["board"], built["disc"]
    fid = sorted(board["fixtures"])[0]
    _, tk = _a_contract(board)
    root = tmp_path / "arch"
    _write_root(root, fixtures=[_espn_row(fid, kickoff=KO + timedelta(minutes=30))])
    s = reprice(_rc(board, _view(disc), [root]))
    f = next(f for f in s.fixtures if f.fixture_id == fid)
    assert f.model.invalidation_reasons[0].startswith("kickoff_changed")
    _write_root(root, fixtures=[_espn_row(fid, neutral=True)])
    s = reprice(_rc(board, _view(disc), [root]))
    assert (
        next(f for f in s.fixtures if f.fixture_id == fid)
        .model.invalidation_reasons[0]
        .startswith("venue_changed")
    )
    s = reprice(_rc(board, _view(disc, moves={tk: Decimal("0.11")})))
    assert {f.model.validity for f in s.fixtures} == {"VALID"}


# ------------------------------------------------------------------------------------------- rolling slate


def _shift(board, fid, new_fid, *, kickoff, comp=None):
    e = json.loads(json.dumps(board["fixtures"][fid]))
    e["fixture_id"] = new_fid
    e["inputs"]["kickoff_utc"] = kickoff.isoformat().replace("+00:00", "Z")
    if comp:
        e["competition_id"] = comp
        e["inputs"]["competition_id"] = comp
        e["inputs"]["model_family"] = "data_only.world_sim_v2" + (
            ".intl_pool" if comp.startswith("concacaf") else ""
        )
    return e


def test_started_fixture_leaves_and_later_fixture_enters_rolling_slate(built):
    board, disc = built["board"], built["disc"]
    fid = sorted(board["fixtures"])[0]
    b = json.loads(json.dumps(board))
    late = _shift(
        board, fid, "fx:usa.mls:2026:late", kickoff=KO + timedelta(hours=46), comp="usa.mls"
    )
    b["fixtures"][late["fixture_id"]] = late
    s = reprice(_rc(b, _view(disc)))
    assert late["fixture_id"] not in {f.fixture_id for f in s.fixtures}  # beyond the 48 h lookahead
    later = NOW + timedelta(hours=4)  # EPL kicked off; the MLS game is now within 48 h
    s = reprice(_rc(b, _view(disc, later - timedelta(minutes=1)), now=later))
    ids = {f.fixture_id for f in s.fixtures}
    assert late["fixture_id"] in ids and not (ids & set(board["fixtures"]))
    assert set(s.removed_started) == set(board["fixtures"])
    assert not any(c.fixture_id in board["fixtures"] for c in s.contracts)


def test_multiple_leagues_and_time_zones_in_one_slate(built):
    board, disc = built["board"], built["disc"]
    fids = sorted(board["fixtures"])
    b = json.loads(json.dumps(board))
    mls = _shift(
        board, fids[1], fids[1], kickoff=KO + timedelta(hours=11), comp="usa.mls"
    )  # 01:00Z
    cnl = _shift(
        board, fids[2], fids[2], kickoff=KO + timedelta(hours=9), comp="concacaf.nations_league"
    )
    b["fixtures"][fids[1]], b["fixtures"][fids[2]] = mls, cnl
    s = reprice(_rc(b, _view(disc, moves=_cheap(b))))
    assert [f.competition for f in s.fixtures] == [
        "eng.premier_league",
        "concacaf.nations_league",
        "usa.mls",
    ]
    assert len({f.kickoff for f in s.fixtures}) == 3
    by_comp = {}
    for c in s.contracts:
        by_comp.setdefault(c.competition, set()).add(c.action)
    assert "RESEARCH_CANDIDATE" in by_comp["usa.mls"]
    # the international pool is never a candidate (audit §E6)
    assert "RESEARCH_CANDIDATE" not in by_comp["concacaf.nations_league"]
    assert "EXCLUDED_BY_GATE" in by_comp["concacaf.nations_league"]


def test_kalshi_listed_fixture_without_model_is_listed_as_missing(built, tmp_path):
    root = tmp_path / "arch"
    (root / "dispatch").mkdir(parents=True)
    (root / "dispatch" / "schedule.json").write_text(
        json.dumps(
            {
                "fixtures": [
                    {
                        "fixture_id": "fx:usa.mls:2026:usa.a:usa.b",
                        "kickoff_utc": (NOW + timedelta(hours=5)).isoformat(),
                        "competition_id": "usa.mls",
                        "source": "run_output",
                        "markets_discovered": 12,
                    }
                ]
            }
        )
    )
    s = reprice(_rc(built["board"], _view(built["disc"]), [root]))
    f = next(f for f in s.fixtures if f.fixture_id == "fx:usa.mls:2026:usa.a:usa.b")
    assert f.model.validity == "MISSING" and f.contracts_without_model == 12
    assert s.counts["fixtures_model_missing"] == 1


# ------------------------------------------------------------------------------------------- reference


def test_pinnacle_reference_is_read_from_stored_rows_only(built, monkeypatch, tmp_path):
    board, disc = built["board"], built["disc"]
    fid, tk = _a_contract(board)
    sel = board["fixtures"][fid]["contracts"][tk]["side"]
    root = tmp_path / "arch"
    rows = [
        {
            "bookmaker": "pinnacle",
            "fixture_id": fid,
            "market": "1x2",
            "selection": s,
            "line": None,
            "devigged_probability": p,
            "captured_at": (NOW - timedelta(minutes=5)).isoformat(),
            "quoted_at": (NOW - timedelta(minutes=5, seconds=10)).isoformat(),
            "minutes_to_kickoff": 175,
        }
        for s, p in (("home", 0.5), ("draw", 0.25), ("away", 0.25))
    ]
    _write_root(root, pinnacle=rows)
    _no_compute(monkeypatch)
    s = reprice(_rc(board, _view(disc), [root]))
    y = next(c for c in s.contracts if c.ticker == tk and c.side == "yes")
    want = {"home": 0.5, "draw": 0.25, "away": 0.25}[sel]
    assert y.reference_probability == pytest.approx(want)
    assert y.reference_quality == "SHARP_REFERENCE" and y.reference_freshness == "CURRENT"
    assert y.reference_anchored_ev is not None  # edge_v2 evaluated against the fresh close/entry
    assert s.compute.odds_api_calls == 0
    late = reprice(
        _rc(
            board, _view(disc, NOW + timedelta(minutes=29)), [root], now=NOW + timedelta(minutes=30)
        )
    )
    y = next(c for c in late.contracts if c.ticker == tk and c.side == "yes")
    assert y.reference_freshness == "AGING" and y.reference_anchored_ev is None


# ------------------------------------------------------------------------------------------- evidence


def test_reprice_never_writes_the_immutable_ledger(built, tmp_path):
    led_dir = tmp_path / "ledger"
    led = PredictionLedger(led_dir)
    rec = dict(built["art"].per_contract[0])
    rid, _ = led.append(rec, when=NOW)
    before = sorted(p.read_bytes() for p in led_dir.rglob("*") if p.is_file())
    for i in range(5):
        s = reprice(
            _rc(built["board"], _view(built["disc"]), [tmp_path], now=NOW + timedelta(minutes=i))
        )
        write_slate(tmp_path, s)
    after = sorted(p.read_bytes() for p in led_dir.rglob("*") if p.is_file())
    assert before == after and led.verify() == []
    assert not (tmp_path / "predictions").exists()
    log = (tmp_path / SLATE_LOG_DIR).glob("*.jsonl")
    rows = [json.loads(ln) for f in log for ln in f.read_text().splitlines()]
    assert len(rows) == 5 and all(r["simulations_run"] == 0 for r in rows)
    assert all(r["odds_api_calls"] == 0 for r in rows)


def test_reprice_only_cli_spends_no_odds_api_credit(built, monkeypatch, tmp_path):
    """`soccer slate reprice` on a captured catalog: no network, no budget-ledger row, 0 credits."""
    import soccer_edge.cli as cli
    from soccer_edge.slate.board import BOARD_FILE

    root = tmp_path / "arch"
    save_board(root / BOARD_FILE, built["board"])
    cat = tmp_path / "latest_catalog.json"
    doc = built["disc"].to_json()
    doc["started_at"] = (NOW - timedelta(minutes=1)).isoformat()
    cat.write_text(json.dumps(doc))
    _no_compute(monkeypatch)
    monkeypatch.setattr(cli, "utc_now", lambda: NOW)
    import soccer_edge.slate.reprice as rp

    out = tmp_path / "out"
    args = cli.build_parser().parse_args(
        ["slate", "reprice", "--catalog", str(cat), "--out-dir", str(out), "--root", str(root)]
    )
    assert args.func(args) == 0
    doc = json.loads((out / SLATE_FILE).read_text())
    assert doc["compute"]["odds_api_calls"] == 0 and doc["compute"]["simulations_run"] == 0
    assert doc["kalshi"]["status"] == "CURRENT" and doc["counts"]["contract_sides"] > 0
    assert not (out / "odds_api").exists() and not (root / "odds_api").exists()
    assert rp.SLATE_FILE == SLATE_FILE


def test_slate_merge_keeps_the_newer_kalshi_observation(built, tmp_path):
    import soccer_edge.cli as cli

    old = reprice(_rc(built["board"], _view(built["disc"], NOW - timedelta(minutes=10))))
    new = reprice(_rc(built["board"], _view(built["disc"], NOW - timedelta(minutes=1))))
    dst, src = tmp_path / "dst.json", tmp_path / "src.json"
    dst.write_text(new.model_dump_json())
    src.write_text(old.model_dump_json())
    a = cli.build_parser().parse_args(
        ["slate", "merge-latest", "--kind", "slate", "--src", str(src), "--dst", str(dst)]
    )
    a.func(a)
    assert json.loads(dst.read_text())["slate_id"] == new.slate_id  # an older slate never wins
    dst.write_text(old.model_dump_json())
    src.write_text(new.model_dump_json())
    a.func(a)
    assert json.loads(dst.read_text())["slate_id"] == new.slate_id


# ------------------------------------------------------------------------------------------- cadence


def _due(fid, h, *, mins=None):
    fx = ScheduledFixture(fid, KO, "eng.premier_league", "run_output", 40)
    return DueHorizon(fx, h, mins if mins is not None else h)


def test_refresh_plan_is_selective(built, tmp_path):
    board = built["board"]
    fid = sorted(board["fixtures"])[0]
    ctx = fixture_context([tmp_path])
    t60_entry = json.loads(json.dumps(board))
    t60_entry["fixtures"][fid]["model_generated_at"] = (KO - timedelta(minutes=61)).isoformat()
    plan = lambda due, b=t60_entry, lu=None, **k: refresh_plan(
        due, b, ctx=ctx, lineups=lu or {}, versions=VERSIONS, **k
    )
    assert plan([_due(fid, 60)]) == {fid: "T-60:primary_refresh"}
    assert plan([_due(fid, 120)]) == {} and plan([_due(fid, 30)]) == {}
    assert plan([_due(fid, 15)]) == {}  # refreshed at T-60, nothing changed
    assert plan([_due(fid, 5)]) == {}
    stale = json.loads(json.dumps(board))
    stale["fixtures"][fid]["model_generated_at"] = (KO - timedelta(hours=8)).isoformat()
    assert plan([_due(fid, 15)], stale) == {fid: "T-15:no_model_refresh_since_t60"}
    xi = {fid: LineupObservation("confirmed", "sha256:xi", NOW, NOW, "eng.1")}
    assert plan([_due(fid, 15)], lu=xi)[fid].startswith("T-15:invalidated:lineup_changed")
    assert plan([_due(fid, 5)], lu=xi)[fid].startswith("T-5:invalidated:lineup_changed")
    assert plan([_due("fx:new", 120)]) == {"fx:new": "T-120:model_missing"}
    espn_only = DueHorizon(ScheduledFixture("fx:espn-only", KO, "x", "espn", 0), 120, 120)
    assert plan([espn_only]) == {}  # no Kalshi markets: nothing to price
    assert plan([_due(fid, 5)], mode="every") == {fid: "T-5:every_horizon"}
    assert plan([_due(fid, 60)], mode="off") == {}


# ------------------------------------------------------------------------------------------- dispatch batch


class _Recorder:
    def __init__(self):
        self.calls: list[str] = []


def _batch(
    monkeypatch,
    tmp_path,
    built,
    due,
    *,
    odds="odds_api:nothing_eligible:credits=0:paid=0:rows=0",
    lineup_rows=(),
):
    """One real `_dispatch_actions` batch with the network edges replaced: the Kalshi sweep is the synthetic
    discovery, the paid action and the lineup sync are recorded stubs, and the model refresh is the real
    `_slate_model_refresh` stubbed only at its `soccer run` call (records the requested fixtures)."""
    import soccer_edge.cli as cli
    from soccer_edge.slate.board import BOARD_FILE

    rec = _Recorder()
    out, arch = tmp_path / "out", tmp_path / "arch"
    arch.mkdir(exist_ok=True)
    save_board(arch / BOARD_FILE, built["board"])
    disc = built["disc"]
    disc_now = replace_started(disc, NOW - timedelta(minutes=1))

    def cap(a):
        rec.calls.append("kalshi_capture")
        return 0, disc_now

    def odds_action(*a, **k):
        rec.calls.append("odds_api")
        return odds

    def lineups(o, comps):
        rec.calls.append("lineups")
        if lineup_rows:
            _write_root(o, lineups=lineup_rows)
        return "lineups:ok:1"

    def model_refresh(o, archive, d, *, games, **k):
        rec.calls.append(f"model_refresh:{','.join(games)}")
        return {"rc": 0, "simulated": [], "reused_from_cache": list(games)}

    monkeypatch.setattr(cli, "_capture_sweep", cap)
    monkeypatch.setattr(cli, "_odds_api_action", odds_action)
    monkeypatch.setattr(cli, "_lineup_action", lineups)
    monkeypatch.setattr(cli, "_slate_model_refresh", model_refresh)
    monkeypatch.setattr(cli, "utc_now", lambda: NOW)
    monkeypatch.setattr(cli, "cmd_capture_reference", lambda a: 2)  # free fd.co.uk fetch: offline
    args = cli.build_parser().parse_args(
        ["dispatch", "tick", "--archive-dir", str(arch), "--out-dir", str(out), "--chain"]
    )
    actions = cli._dispatch_actions(out, due, "kd-test", args)
    return rec, actions, out


def replace_started(disc, started):
    from copy import copy

    d = copy(disc)
    d.started_at = started
    return d


def test_t60_batch_refreshes_model_after_entry_reference(monkeypatch, tmp_path, built):
    fid = sorted(built["board"]["fixtures"])[0]
    rec, actions, out = _batch(
        monkeypatch,
        tmp_path,
        built,
        [_due(fid, 60, mins=60)],
        odds="odds_api:ok:credits=3:paid=1:rows=7",
    )
    assert rec.calls == ["kalshi_capture", "odds_api", "lineups", f"model_refresh:{fid}"]
    assert any(a.startswith("model_refresh:ok") and "why=T-60" in a for a in actions)


def test_t15_batch_reprices_only_when_nothing_changed(monkeypatch, tmp_path, built):
    fid = sorted(built["board"]["fixtures"])[0]
    b = json.loads(json.dumps(built["board"]))
    b["fixtures"][fid]["model_generated_at"] = (KO - timedelta(minutes=61)).isoformat()
    rec, actions, out = _batch(
        monkeypatch,
        tmp_path,
        {**built, "board": b},
        [_due(fid, 15, mins=15)],
        odds="odds_api:ok:credits=3:paid=1:rows=7",
    )
    assert rec.calls == ["kalshi_capture", "odds_api", "lineups"]  # no model run
    assert "model_refresh:skipped:selective:no_input_change" in actions
    doc = json.loads((out / SLATE_FILE).read_text())
    assert doc["compute"]["simulations_run"] == 0
    assert doc["compute"]["odds_api_calls"] == 1  # the batch's own approved T-15 close, reported
    assert doc["compute"]["mode"] == "reprice_only"


def test_t15_batch_reruns_model_when_the_xi_is_published(monkeypatch, tmp_path, built):
    fid = sorted(built["board"]["fixtures"])[0]
    b = json.loads(json.dumps(built["board"]))
    b["fixtures"][fid]["model_generated_at"] = (KO - timedelta(minutes=61)).isoformat()
    arch = tmp_path / "arch"
    _write_root(arch, fixtures=[_espn_row(fid)])
    rec, actions, out = _batch(
        monkeypatch,
        tmp_path,
        {**built, "board": b},
        [_due(fid, 15, mins=15)],
        lineup_rows=[_lineup_row(published=True)],
    )
    assert rec.calls == ["kalshi_capture", "odds_api", "lineups", f"model_refresh:{fid}"]
    assert any("why=T-15" in a for a in actions if a.startswith("model_refresh:ok"))


def test_t5_batch_reprices_without_model_or_paid_call(monkeypatch, tmp_path, built):
    fid = sorted(built["board"]["fixtures"])[0]
    b = json.loads(json.dumps(built["board"]))
    b["fixtures"][fid]["model_generated_at"] = (KO - timedelta(minutes=16)).isoformat()
    rec, actions, out = _batch(monkeypatch, tmp_path, {**built, "board": b}, [_due(fid, 5, mins=5)])
    assert rec.calls == ["kalshi_capture", "odds_api", "lineups"]
    doc = json.loads((out / SLATE_FILE).read_text())
    assert doc["compute"]["odds_api_calls"] == 0 and doc["compute"]["simulations_run"] == 0
    assert any(a.startswith("slate_reprice:ok") for a in actions)


def test_archive_publish_merges_latest_pointers(built, tmp_path):
    """scripts/archive_publish.sh: the newer slate survives an older publish; boards union by fixture."""
    from soccer_edge.slate.board import BOARD_FILE

    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    seed = tmp_path / "seed"
    subprocess.run(["git", "init", "-q", "-b", "data-archive", str(seed)], check=True)
    (seed / "README.md").write_text("archive\n")
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    import os

    env = {**os.environ, **env}
    env.pop("GITHUB_TOKEN", None)
    subprocess.run(["git", "-C", str(seed), "add", "."], check=True, env=env)
    subprocess.run(["git", "-C", str(seed), "commit", "-qm", "seed"], check=True, env=env)
    subprocess.run(
        ["git", "-C", str(seed), "push", "-q", str(bare), "data-archive"], check=True, env=env
    )
    caller = tmp_path / "caller"
    subprocess.run(["git", "init", "-q", str(caller)], check=True)
    subprocess.run(["git", "-C", str(caller), "remote", "add", "origin", str(bare)], check=True)

    def publish(payload: Path, msg: str):
        p = subprocess.run(
            [str(ROOT / "scripts" / "archive_publish.sh"), str(payload), ".", msg],
            cwd=caller,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert p.returncode == 0, p.stdout + p.stderr

    new = reprice(_rc(built["board"], _view(built["disc"], NOW - timedelta(minutes=1))))
    old = reprice(_rc(built["board"], _view(built["disc"], NOW - timedelta(minutes=9))))
    fids = sorted(built["board"]["fixtures"])
    half = {k: v for k, v in built["board"].items()}
    a, b = tmp_path / "a", tmp_path / "b"
    for d, s, keep in ((a, new, fids[:1]), (b, old, fids[1:])):
        (d / "runs").mkdir(parents=True)
        write_slate(d, s)
        save_board(
            d / BOARD_FILE, {**half, "fixtures": {f: built["board"]["fixtures"][f] for f in keep}}
        )
        (d / "predictions").mkdir()
        (d / "predictions" / "index.json").write_text(json.dumps({f"pred_{d.name}": "x.jsonl"}))
    publish(a, "newer slate")
    publish(b, "older slate, other fixtures")
    show = lambda rel: (
        subprocess.run(
            ["git", "-C", str(bare), "show", f"data-archive:{rel}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    assert json.loads(show(SLATE_FILE))["slate_id"] == new.slate_id
    assert set(json.loads(show(BOARD_FILE))["fixtures"]) == set(fids)
    assert set(json.loads(show("predictions/index.json"))) == {"pred_a", "pred_b"}
    log = show(f"{SLATE_LOG_DIR}/{NOW:%Y-%m-%d}.jsonl").splitlines()
    assert len(log) == 2  # both reprices are on the append-only log


def test_board_load_skips_missing_paths(tmp_path):
    assert load_board(tmp_path / "nope.json", now=NOW)["fixtures"] == {}


def test_chain_reprices_every_15_minutes_between_horizons_for_free(monkeypatch, tmp_path):
    """A link with --slate-refresh-minutes 15: free capture + reprice between horizons while a fixture is
    within the active window; paid calls stay at the horizon batches (T-60 / T-15) only."""
    import time as time_mod

    import soccer_edge.cli as cli
    from tests.test_fixture_chain import Clock

    clock = Clock(KO - timedelta(hours=6))
    sched = [ScheduledFixture("fx:a", KO, "eng.premier_league", "run_output", 40)]
    horizon_batches, refreshes = [], []

    def fake_actions(out, due, batch_id, args):
        paid = 1 if {d.horizon for d in due} & {60, 15} else 0
        horizon_batches.append((clock.now(), sorted(d.horizon for d in due), paid))
        return ["kalshi_capture:ok", f"odds_api:ok:credits={3 * paid}:paid={paid}:rows=0"]

    def fake_refresh(out, batch_id, args):
        refreshes.append(clock.now())
        clock.sleep(150)  # a fast capture takes ~2.5 min
        return ["kalshi_capture:ok", "slate_reprice:ok:sides=10:sim=0"]

    monkeypatch.setattr(cli, "_dispatch_actions", fake_actions)
    monkeypatch.setattr(cli, "_slate_refresh", fake_refresh)
    monkeypatch.setattr(
        cli,
        "_dispatch_schedule",
        lambda a, n: {
            "generated_at": n.isoformat(),
            "kalshi_listing_as_of": n.isoformat(),
            "fixtures": [f.to_json() for f in sched],
        },
    )
    monkeypatch.setattr(cli, "utc_now", clock.now)
    monkeypatch.setattr(time_mod, "sleep", clock.sleep)
    (tmp_path / "arch").mkdir()
    args = cli.build_parser().parse_args(
        [
            "dispatch",
            "tick",
            "--archive-dir",
            str(tmp_path / "arch"),
            "--out-dir",
            str(tmp_path / "out"),
            "--chain",
            "--max-tick-minutes",
            "420",
            "--slate-refresh-minutes",
            "15",
            "--summary-out",
            str(tmp_path / "tick.json"),
        ]
    )
    assert args.func(args) == 0
    t = json.loads((tmp_path / "tick.json").read_text())
    assert [h for _, h, _ in horizon_batches] == [[120], [60], [30], [15], [5]]
    assert t["paid_calls"] == 2  # unchanged: entry + close only
    assert t["slate_refreshes"] == len(refreshes) >= 14
    captures = sorted([*refreshes, *(at for at, _, _ in horizon_batches)])
    gaps = [(b - a).total_seconds() / 60 for a, b in zip(captures, captures[1:])]
    assert max(gaps) <= 15.5  # the Kalshi price never ages past the CURRENT window while active
    assert all(r < KO for r in refreshes)


def test_model_refresh_end_to_end_reuses_cache_and_never_pays(
    built, registry, monkeypatch, tmp_path
):
    """The real `_slate_model_refresh` (= `soccer run --fast` on the caller's sweep): board + slate +
    prediction records under runs/<day>/<run_id>/; a second refresh with unchanged inputs simulates
    nothing; nothing touches The Odds API."""
    import soccer_edge.cli as cli
    import soccer_edge.kalshi.reconcile as reconcile
    import soccer_edge.run.inputs as run_inputs
    from soccer_edge.run.inputs import AssembledData
    from soccer_edge.slate.board import BOARD_FILE
    from tests.test_run_pipeline import _epl_model

    fixtures = built["fixtures"]
    model = _epl_model(fixtures)
    monkeypatch.setattr(
        run_inputs,
        "assemble",
        lambda *a, **k: AssembledData(
            fixtures,
            NOW - timedelta(hours=2),
            {},
            NOW - timedelta(days=1),
            {"eng.premier_league": model},
            [],
        ),
    )
    monkeypatch.setattr(
        reconcile, "reconcile_fast_vs_full", lambda *a, **k: {"complete_relative_to_full": True}
    )
    monkeypatch.setattr(cli, "_reference_capture", lambda *a, **k: ({}, None, {}))
    monkeypatch.setattr(cli, "utc_now", lambda: NOW)
    import soccer_edge.providers.the_odds_api as toa

    def no_paid(*a, **k):
        raise AssertionError("a model refresh must not call The Odds API")

    monkeypatch.setattr(toa.OddsApiClient, "__init__", no_paid)
    out, arch = tmp_path / "out", tmp_path / "arch"
    arch.mkdir()
    disc = replace_started(built["disc"], NOW - timedelta(minutes=1))
    fid = sorted(b.fixture_id for b in fixtures)[0]
    kw = dict(
        games=[fid],
        window_hours=4,  # kickoff is 3 h after NOW
        sim_cache=tmp_path / "simcache",
        versions_args=cli.build_parser().parse_args(
            ["dispatch", "tick", "--archive-dir", str(arch), "--out-dir", str(out)]
        ),
        trigger="kickoff_chain:T-60",
        lookahead_hours=48,
        capture_runtime_s=150.0,
    )
    s1 = cli._slate_model_refresh(out, arch, disc, **kw)
    assert s1["rc"] == 0 and s1["simulated"] == [fid] and s1["board_fixtures"] == 1
    run_dir = Path(s1["run_dir"])
    assert run_dir.parent.name == f"{NOW:%Y-%m-%d}" and run_dir.name.startswith("run-")
    assert (run_dir / "run_output.v1.json").exists() and not (out / "runs" / "_pending").exists()
    board = json.loads((out / BOARD_FILE).read_text())
    assert set(board["fixtures"]) == {fid}
    slate = json.loads((out / SLATE_FILE).read_text())
    assert slate["compute"]["mode"] == "model_refresh_and_reprice"
    assert slate["compute"]["simulations_run"] >= 1 and slate["compute"]["odds_api_calls"] == 0
    assert slate["compute"]["kalshi_capture_runtime_s"] == 150.0
    assert {c["fixture_id"] for c in slate["contracts"]} == {fid}
    records = [
        json.loads(ln)
        for f in (out / "ledger").glob("*/predictions.jsonl")
        for ln in f.read_text().splitlines()
    ]
    assert records and {r["fixture_id"] for r in records} == {fid}
    assert {r["run_id"] for r in records} == {run_dir.name}
    # unchanged inputs at T-15: the cached simulation is reused (no new simulation)
    s2 = cli._slate_model_refresh(out, arch, disc, **{**kw, "trigger": "kickoff_chain:T-15"})
    assert s2["simulated"] == [] and s2["reused_from_cache"] == [fid]
    # a cache-hit fixture with a shadow candidate is re-simulated deterministically once, only to rebuild
    # joint draws for the expression reducer; it is counted, never hidden
    slate2 = json.loads((out / SLATE_FILE).read_text())
    assert slate2["compute"]["simulations_run"] == len(s2["resimulated_for_reducer"]) <= 1
    ids = [
        json.loads(ln)["record_id"]
        for f in (out / "ledger").glob("*/predictions.jsonl")
        for ln in f.read_text().splitlines()
    ]
    assert len(ids) == len(set(ids))  # no record is archived twice


def test_cli_model_defaults_match_the_invalidation_versions():
    import soccer_edge.cli as cli
    from soccer_edge.slate import invalidation as inv

    want = (inv.DEFAULT_MODEL_VERSION, inv.DEFAULT_ENGINE_VERSION, inv.DEFAULT_WORLDS_VERSION)
    r = cli.build_parser().parse_args(["run"])
    assert (r.model_version, r.engine_version, r.worlds_version) == want
    t = cli.build_parser().parse_args(["dispatch", "tick", "--archive-dir", "a", "--out-dir", "o"])
    assert (t.run_model_version, t.run_engine_version, t.run_worlds_version) == want
    assert t.model_refresh == "selective" and t.slate_refresh_minutes == 0
