"""Game-script engine (soccer_scripts_v1): partition, exact decomposition, coherence, market blindness, zero-
simulation survivability repricing, authority / freshness gates, explorer publication (docs/GAME_SCRIPTS.md)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pytest

import soccer_edge.run.pipeline as pipeline_mod
from soccer_edge.gamescript import kernel as K
from soccer_edge.gamescript.cells import CellSpec, cell_indicator
from soccer_edge.gamescript.conditional import ScriptLayer
from soccer_edge.gamescript.context import match_context
from soccer_edge.gamescript.expressions import JointSpace, thesis_groups
from soccer_edge.gamescript.presentation import script_engine_payload
from soccer_edge.gamescript.survivability import survivability
from soccer_edge.gamescript.taxonomy import (
    FT_AWAY,
    FT_HOME,
    FT_NONE,
    MATERIAL_SHARE_MIN,
    SCRIPT_IDS,
    script_of,
)
from soccer_edge.kalshi.client import KalshiPublicClient
from soccer_edge.kalshi.discovery import discover
from soccer_edge.kalshi.fake import FakeKalshi
from soccer_edge.kalshi.taxonomy import MarketFamily, Period
from soccer_edge.model.context import MatchContext
from soccer_edge.pricing.semantics import Semantics
from soccer_edge.run.pipeline import RunConfig, run
from soccer_edge.run.simcache import SimCache
from soccer_edge.sim.engine_v2 import SimConfigV2, score_matrices, simulate_v2
from soccer_edge.slate.board import merge_boards
from soccer_edge.slate.reprice import reprice
from tests.test_actionable_slate import NOW, _epl_fixtures, _no_compute, _rc, _view
from tests.test_run_pipeline import _inputs

G1 = K.MAX_GOALS + 1


def _mats(lam=1.55, mu=1.1, rho=-0.06, w=400, seed=3):
    rng = np.random.default_rng(seed)
    lam_w = np.exp(rng.normal(np.log(lam), 0.15, w))
    mu_w = np.exp(rng.normal(np.log(mu), 0.15, w))
    return score_matrices(lam_w, mu_w, np.full(w, rho)), lam_w, mu_w


@pytest.fixture(scope="module")
def built(registry, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("scripts")
    fixtures = _epl_fixtures(registry)
    fake = FakeKalshi(
        fixtures,
        registry,
        fair=lambda f: {"home": 0.45, "draw": 0.27, "away": 0.28, "mean_total": 2.6},
    )
    disc = discover(KalshiPublicClient(transport=fake.transport))
    cfg = RunConfig(
        run_date=date(2026, 10, 10), n_worlds=300, draws_per_world=60, engine_version="world_sim_v2"
    )
    art = run(_inputs(registry, fixtures, disc), cfg, sim_cache=SimCache(tmp / "cache"))
    board = merge_boards({"fixtures": art.board_entries}, now=NOW)
    return {"board": board, "disc": disc, "art": art, "cfg": cfg, "tmp": tmp, "fixtures": fixtures}


# ------------------------------------------------------------------------------------------- partition
def test_every_realisation_has_exactly_one_script():
    seen = set()
    for h in range(G1):
        for a in range(G1):
            firsts = (
                [FT_NONE] if h + a == 0 else [f for f, n in ((FT_HOME, h), (FT_AWAY, a)) if n > 0]
            )
            for f in firsts:
                s = script_of(h, a, f)
                assert s in SCRIPT_IDS
                seen.add(s)
    assert seen == set(SCRIPT_IDS)
    oh = K.script_onehot()
    pf = K.first_scorer_given_score(0.441)
    # every reachable cell is one-hot; unreachable cells carry no probability
    assert np.all(oh.sum(axis=-1)[pf > 0] == 1)
    assert np.allclose(K.script_given_score(0.441).sum(axis=-1), 1.0)


def test_impossible_realisations_are_rejected():
    for args in ((0, 0, FT_HOME), (1, 0, FT_NONE), (0, 2, FT_HOME)):
        with pytest.raises(ValueError):
            script_of(*args)


def test_kernel_is_a_distribution_and_matches_engine_timing():
    k = K.cell_kernel(0.441)
    assert np.allclose(k.sum(axis=(2, 3, 4)), 1.0)
    # half-time split is binomial thinning; first scorer exchangeable: P(home first | h, a) = h / (h + a)
    pf = k.sum(axis=(2, 3))
    for h, a in ((2, 1), (1, 3), (4, 0)):
        assert pf[h, a, FT_HOME] == pytest.approx(h / (h + a), abs=1e-12)
    # world_sim_v2 draws: half-time share and first-scorer share agree with the kernel within MC error
    mats, lam, mu = _mats(w=200)
    from soccer_edge.model.worlds import WorldConfig, WorldSet

    ws = WorldSet(
        n_worlds=200,
        lam_home=lam,
        mu_away=mu,
        rho=np.full(200, -0.06),
        red_hazard_home=np.zeros(200),
        red_hazard_away=np.zeros(200),
        trailing_mult=np.ones(200),
        leading_mult=np.ones(200),
        home_players_on=None,
        away_players_on=None,
        home_goal_shares=None,
        away_goal_shares=None,
        components={},
        posterior_hash="x",
        config=WorldConfig(),
    )
    ctx = MatchContext("fx", "c", "h", "a", None)
    out = simulate_v2(ws, ctx, SimConfigV2(draws_per_world=200), seed=7)
    layer = ScriptLayer(mats, first_half_share=0.441)
    p_cell = layer.p_cell
    H, A, H1, A1, F = (np.indices(p_cell.shape)[i] for i in range(5))
    exact_ht_home = float((p_cell * (H1 > A1)).sum())
    sim_ht_home = float((out.home_ht > out.away_ht).mean())
    assert sim_ht_home == pytest.approx(exact_ht_home, abs=0.006)
    exact_fts_home = float((p_cell * (F == FT_HOME)).sum())
    assert float((out.first_goal_team == 1).mean()) == pytest.approx(exact_fts_home, abs=0.006)


def test_cell_indicator_matches_settlement_semantics():
    """The script layer settles every family with the same rule as pricing/semantics.settle_indicator."""
    mats, lam, mu = _mats(w=30)
    from soccer_edge.model.worlds import WorldConfig, WorldSet

    ws = WorldSet(
        n_worlds=30,
        lam_home=lam,
        mu_away=mu,
        rho=np.full(30, -0.06),
        red_hazard_home=np.zeros(30),
        red_hazard_away=np.zeros(30),
        trailing_mult=np.ones(30),
        leading_mult=np.ones(30),
        home_players_on=None,
        away_players_on=None,
        home_goal_shares=None,
        away_goal_shares=None,
        components={},
        posterior_hash="x",
        config=WorldConfig(),
    )
    out = simulate_v2(
        ws, MatchContext("fx", "c", "h", "a", None), SimConfigV2(draws_per_world=200), seed=1
    )
    cases = [
        (MarketFamily.MATCH_RESULT_3WAY, Period.REGULATION, "home", None, None),
        (MarketFamily.MATCH_RESULT_3WAY, Period.REGULATION, "draw", None, None),
        (MarketFamily.TOTAL_GOALS, Period.REGULATION, None, Decimal("2.5"), None),
        (MarketFamily.TEAM_TOTAL, Period.REGULATION, "away", Decimal("0.5"), None),
        (MarketFamily.HANDICAP, Period.REGULATION, "home", Decimal("1.5"), None),
        (MarketFamily.BTTS, Period.REGULATION, None, None, None),
        (MarketFamily.CLEAN_SHEET, Period.REGULATION, "home", None, None),
        (MarketFamily.DRAW_NO_BET, Period.REGULATION, "away", None, None),
        (MarketFamily.EXACT_SCORE, Period.REGULATION, "home", None, 201),
        (MarketFamily.FIRST_HALF_RESULT, Period.FIRST_HALF, "draw", None, None),
        (MarketFamily.FIRST_HALF_TOTAL, Period.FIRST_HALF, None, Decimal("0.5"), None),
        (MarketFamily.FIRST_HALF_BTTS, Period.FIRST_HALF, None, None, None),
        (MarketFamily.FIRST_HALF_HANDICAP, Period.FIRST_HALF, "away", Decimal("0.5"), None),
        (MarketFamily.FIRST_HALF_TEAM_TOTAL, Period.FIRST_HALF, "home", Decimal("0.5"), None),
        (MarketFamily.FIRST_HALF_EXACT_SCORE, Period.FIRST_HALF, "home", None, 100),
        (MarketFamily.SECOND_HALF_RESULT, Period.SECOND_HALF, "home", None, None),
        (MarketFamily.FIRST_TO_SCORE, Period.REGULATION, "away", None, None),
        (MarketFamily.MATCH_WINNER_2WAY, Period.INCLUDING_PENS, "home", None, None),
    ]
    for fam, per, side, line, k in cases:
        sem = Semantics("T", fam, per, side, line, k)
        ind = cell_indicator(CellSpec.from_semantics(sem), requires_winner=False)
        h1 = np.minimum(out.home_ht, K.MAX_GOALS)
        via_cells = ind[out.home_ft, out.away_ft, h1, out.away_ht, out.first_goal_team]
        assert np.array_equal(via_cells.astype(bool), sem.settle(out).astype(bool)), fam


# ------------------------------------------------------------------------------------------- decomposition
def test_shares_sum_to_one_and_decomposition_is_exact():
    mats, _, _ = _mats()
    layer = ScriptLayer(mats, first_half_share=0.441)
    assert layer.share.sum() == pytest.approx(1.0, abs=1e-12)
    specs = (
        [CellSpec("match_result_3way", "regulation", s, None) for s in ("home", "draw", "away")]
        + [CellSpec("total_goals", "regulation", None, x) for x in (0.5, 1.5, 2.5, 3.5, 4.5)]
        + [
            CellSpec("first_to_score", "regulation", "home", None),
            CellSpec("first_half_result", "first_half", "home", None),
            CellSpec("second_half_result", "second_half", "draw", None),
            CellSpec("exact_score", "regulation", "home", None, 102),
        ]
    )
    for spec in specs:
        j = layer.joint_by_world(spec)
        p = j.sum(axis=1).mean()
        cond = j.sum(axis=0) / layer.pw_s.sum(axis=0)
        assert float((layer.share * cond).sum()) == pytest.approx(float(p), abs=1e-12)


def test_board_decomposition_reconciles_with_the_priced_probability(built):
    checked = 0
    for e in built["board"]["fixtures"].values():
        sc = e["scripts"]
        assert sc["status"] == "OK"
        assert sum(sc["shares"]) == pytest.approx(1.0, abs=1e-4)
        for tk, c in e["contracts"].items():
            if "sc" not in c:
                continue
            recon = sum(s * p for s, p in zip(sc["shares"], c["sc"]["sp"]) if p is not None)
            assert recon == pytest.approx(c["sc"]["p"], abs=2e-4), tk
            fam = c["family"]
            if fam in (
                "match_result_3way",
                "total_goals",
                "team_total",
                "handicap",
                "btts",
                "exact_score",
            ):
                assert c["sc"]["p"] == pytest.approx(c["p"], abs=2e-6), tk  # analytic: identical
            else:
                assert c["sc"]["p"] == pytest.approx(c["p"], abs=0.03), (
                    tk
                )  # board draw-based: MC error
            checked += 1
    assert checked > 20


def test_three_way_and_ladder_coherence_within_every_script(built):
    for e in built["board"]["fixtures"].values():
        sc = e["scripts"]
        for sid in SCRIPT_IDS + ("__overall__",):
            p = sc["overall_profile"] if sid == "__overall__" else sc["profiles"][sid]
            assert p["p_home_win"] + p["p_draw"] + p["p_away_win"] == pytest.approx(1.0, abs=2e-4)
            assert p["p_over_1_5"] >= p["p_over_2_5"] >= p["p_over_3_5"]
            assert p["p_home_1plus"] >= p["p_home_2plus"] >= p["p_home_3plus"]
            assert sum(p["ht_ft"].values()) == pytest.approx(1.0, abs=5e-4)
        totals = sorted(
            (float(c["line"]), c["sc"]["sp"])
            for c in e["contracts"].values()
            if c["family"] == "total_goals" and "sc" in c
        )
        for (_, lo), (_, hi) in zip(totals, totals[1:]):
            for s in range(len(SCRIPT_IDS)):
                if lo[s] is not None and hi[s] is not None:
                    assert lo[s] >= hi[s] - 1e-9


def test_scripts_are_reproducible(built, registry, tmp_path):
    art2 = run(
        _inputs(registry, built["fixtures"], built["disc"]),
        built["cfg"],
        sim_cache=SimCache(tmp_path / "c"),
    )
    for fid, e in art2.board_entries.items():
        a, b = e["scripts"], built["board"]["fixtures"][fid]["scripts"]
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
        assert {t: c.get("sc") for t, c in e["contracts"].items()} == {
            t: c.get("sc") for t, c in built["board"]["fixtures"][fid]["contracts"].items()
        }


def test_cache_hit_reuses_scripts_without_simulation(built, registry, monkeypatch):
    """A second run on the same cache serves scripts from the cache: no simulation, no world rebuild."""
    calls = {"sim": 0}
    real = pipeline_mod._simulate_fixture

    def counting(*a, **k):
        calls["sim"] += 1
        return real(*a, **k)

    monkeypatch.setattr(pipeline_mod, "_simulate_fixture", counting)
    art = run(
        _inputs(registry, built["fixtures"], built["disc"]),
        built["cfg"],
        sim_cache=SimCache(built["tmp"] / "cache"),
    )
    assert art.diagnostics["script_layer"]["worlds_rebuilt_without_simulation"] == []
    for fid, e in art.board_entries.items():
        assert e["scripts"]["shares"] == built["board"]["fixtures"][fid]["scripts"]["shares"]
    assert calls["sim"] == len(
        art.fixtures_resimulated_for_reducer
    )  # only the pre-existing reducer path


def test_old_cache_without_scripts_rebuilds_worlds_not_simulations(
    built, registry, monkeypatch, tmp_path
):
    cache = SimCache(tmp_path / "old")
    run(_inputs(registry, built["fixtures"], built["disc"]), built["cfg"], sim_cache=cache)
    for p in (tmp_path / "old").glob("*.json"):
        d = json.loads(p.read_text())
        d.pop("scripts", None)
        p.write_text(json.dumps(d))
    calls = {"sim": 0}
    real = pipeline_mod._simulate_fixture

    def counting(*a, **k):
        calls["sim"] += 1
        return real(*a, **k)

    monkeypatch.setattr(pipeline_mod, "_simulate_fixture", counting)
    art = run(_inputs(registry, built["fixtures"], built["disc"]), built["cfg"], sim_cache=cache)
    assert sorted(art.diagnostics["script_layer"]["worlds_rebuilt_without_simulation"]) == sorted(
        art.board_entries
    )
    # the only simulations are the pre-existing reducer re-simulations of candidate fixtures, never the scripts
    assert calls["sim"] == len(art.fixtures_resimulated_for_reducer)
    # and the repaired cache now serves the scripts directly
    art2 = run(_inputs(registry, built["fixtures"], built["disc"]), built["cfg"], sim_cache=cache)
    assert art2.diagnostics["script_layer"]["worlds_rebuilt_without_simulation"] == []
    for fid, e in art.board_entries.items():
        assert e["scripts"]["shares"] == built["board"]["fixtures"][fid]["scripts"]["shares"]


# ------------------------------------------------------------------------------------------- market blindness
def test_kalshi_prices_never_change_scripts(built, registry, tmp_path):
    """Scripts are market-blind: a different Kalshi surface (prices) leaves shares and conditionals unchanged."""
    fake = FakeKalshi(
        built["fixtures"],
        registry,
        fair=lambda f: {"home": 0.25, "draw": 0.30, "away": 0.45, "mean_total": 3.4},
    )
    disc2 = discover(KalshiPublicClient(transport=fake.transport))
    art = run(
        _inputs(registry, built["fixtures"], disc2),
        built["cfg"],
        sim_cache=SimCache(tmp_path / "c"),
    )
    for fid, e in art.board_entries.items():
        b = built["board"]["fixtures"][fid]
        assert e["scripts"]["shares"] == b["scripts"]["shares"]
        for tk, c in e["contracts"].items():
            if tk in b["contracts"] and "sc" in c:
                assert c["sc"] == b["contracts"][tk]["sc"]


def test_quote_only_reprice_runs_zero_simulations_and_moves_survivability(built, monkeypatch):
    _no_compute(monkeypatch)
    board = built["board"]
    fid, e = next(iter(board["fixtures"].items()))
    tk, c = max(
        ((t, c) for t, c in e["contracts"].items() if c["family"] == "match_result_3way"),
        key=lambda x: x[1]["p"],
    )
    cheap = Decimal(str(round(c["p"] - 0.20, 2)))
    dear = Decimal(str(round(min(c["p"] + 0.10, 0.97), 2)))
    s1 = reprice(_rc(board, _view(built["disc"], moves={tk: cheap})))
    s2 = reprice(_rc(board, _view(built["disc"], moves={tk: dear})))
    r1 = next(x for x in s1.contracts if x.ticker == tk and x.side == "yes").script_robustness
    r2 = next(x for x in s2.contracts if x.ticker == tk and x.side == "yes").script_robustness
    assert s1.compute.simulations_run == 0 and s2.compute.simulations_run == 0
    assert r1.overall_edge > 0 > r2.overall_edge
    assert r1.stance != r2.stance  # at least one script flips SUPPORT/NEUTRAL/OPPOSE on price alone
    assert r1.label != "NO_EDGE" and r2.label == "NO_EDGE"
    f1 = next(f for f in s1.fixtures if f.fixture_id == fid).scripts
    f2 = next(f for f in s2.fixtures if f.fixture_id == fid).scripts
    assert f1.shares == f2.shares == e["scripts"]["shares"]  # price never moves a share
    assert f"{tk}|yes" in f1.robust_edges + f1.mixed_edges + f1.script_specific_edges
    assert f"{tk}|yes" not in f2.robust_edges + f2.mixed_edges + f2.script_specific_edges


def test_survivability_identity_overall_edge_is_share_weighted_conditional_edge(built):
    s = reprice(_rc(built["board"], _view(built["disc"])))
    shares = {f.fixture_id: f.scripts.shares for f in s.fixtures}
    n = 0
    for c in s.contracts:
        sr = c.script_robustness
        if sr is None:
            continue
        w = shares[c.fixture_id]
        recon = sum(a * e for a, e in zip(w, sr.conditional_edges) if e is not None)
        assert recon == pytest.approx(sr.overall_edge, abs=2e-4)
        assert sr.p_script - float(c.breakeven_price) == pytest.approx(sr.overall_edge, abs=2e-4)
        n += 1
    assert n > 50


# ------------------------------------------------------------------------------------------- labels
def test_survivability_labels_follow_the_published_rules():
    shares = [0.30, 0.10, 0.30, 0.12, 0.08, 0.10]
    # wins in nearly every script -> VERY_ROBUST
    v = survivability(shares, [0.95, 0.9, 0.9, 0.85, 0.5, 0.6], 0.70)
    assert v["label"] == "VERY_ROBUST" and v["category"] == "ROBUST_ACROSS_SCRIPTS"
    # one script carries it -> SCRIPT_DEPENDENT
    d = survivability(shares, [1.0, 0.0, 0.2, 0.1, 0.0, 0.0], 0.33)
    assert d["label"] == "SCRIPT_DEPENDENT" and d["supporting_scripts"] == 1
    assert d["counter_case"]["reason_code"] == "BELOW_BREAKEVEN"
    # below break-even everywhere that matters -> NO_EDGE
    assert survivability(shares, [0.1] * 6, 0.5)["label"] == "NO_EDGE"
    # immaterial scripts never count (AWAY_CHASE 0.08 < 1/12)
    assert pytest.approx(1 / 12) == MATERIAL_SHARE_MIN
    assert d["stance"][4] == "IMMATERIAL" and d["material_scripts"] == 5
    # the counter-case is the most damaging material script
    z = survivability(shares, [1.0, 1.0, 0.6, 0.6, 0.0, 0.0], 0.55)
    assert (
        z["counter_case"]["script"] == "AWAY_CONTROL"
        and z["counter_case"]["reason_code"] == "SCRIPT_SETTLES_AGAINST"
    )


def test_same_thesis_expressions_group_together():
    mats, _, _ = _mats(lam=2.2, mu=0.8)
    layer = ScriptLayer(mats, first_half_share=0.441)
    blk = layer.fixture_block()
    space = JointSpace(blk["score_grid"], blk["first_half_share"], requires_winner=False)
    specs = {
        "ML": (CellSpec("match_result_3way", "regulation", "home", None), "yes"),
        "H-0.5": (CellSpec("handicap", "regulation", "home", 0.5), "yes"),
        "H_O1.5": (CellSpec("team_total", "regulation", "home", 1.5), "yes"),
        "A_U0.5": (CellSpec("team_total", "regulation", "away", 0.5), "no"),
        "O3.5": (CellSpec("total_goals", "regulation", None, 3.5), "yes"),
    }
    rows = []
    for key, (spec, side) in specs.items():
        p = layer.contract(spec)
        sp = p["sp"] if side == "yes" else [None if x is None else 1 - x for x in p["sp"]]
        be = (p["p"] if side == "yes" else 1 - p["p"]) - 0.03
        sv = survivability(blk["shares"], sp, be)
        rows.append(
            {
                "key": key,
                "spec": spec,
                "side": side,
                "shares": blk["shares"],
                "worst_case_edge": 0.01,
                "script_robustness": sv,
            }
        )
    groups, corr = thesis_groups(rows, space, fixture_id="fx")
    by = {k: r["thesis_group"] for k, r in ((r["key"], r) for r in rows)}
    assert (
        by["ML"] == by["H-0.5"] == by["H_O1.5"]
    )  # one dominant-home thesis, not three discoveries
    assert corr["ML"]["H-0.5"] == pytest.approx(1.0, abs=1e-9)  # identical payoff
    g = next(g for g in groups if "ML" in g["members"])
    assert g["anchor_script"] == "HOME_CONTROL"


# ------------------------------------------------------------------------------------------- gates
def test_stale_price_and_invalidated_model_fail_closed(built):
    stale = _view(built["disc"], observed_at=NOW - timedelta(hours=2))
    s = reprice(_rc(built["board"], stale))
    for f in s.fixtures:
        assert f.scripts.no_compelling_edge
        assert f.scripts.robust_edges == [] and f.scripts.script_specific_edges == []
        assert "not" in (f.scripts.no_compelling_edge_reason or "") or "STALE" in (
            f.scripts.no_compelling_edge_reason or ""
        )
    vers = dict(_rc(built["board"], stale).versions)
    vers["model_version"] = "other"
    s2 = reprice(_rc(built["board"], _view(built["disc"]), versions=vers))
    for f in s2.fixtures:
        assert f.model.validity == "INVALIDATED"
        assert f.scripts.robust_edges == [] and f.scripts.no_compelling_edge


def test_script_fields_never_grant_authority(built):
    cheap = {}
    for e in built["board"]["fixtures"].values():
        for t, c in e["contracts"].items():
            if c["family"] in ("total_goals", "match_result_3way"):
                cheap[t] = Decimal(str(max(0.02, round(c["p"] - 0.25, 2))))
    s = reprice(_rc(built["board"], _view(built["disc"], moves=cheap)))
    assert s.no_bets
    assert all(not c.bet_permitted and c.authority == "RESEARCH_ONLY" for c in s.contracts)
    assert any(f.scripts.robust_edges for f in s.fixtures)  # robust research edges exist ...
    assert not any(c.action == "ACTIONABLE" for c in s.contracts)  # ... and permit nothing


def test_started_fixture_has_no_pregame_script_edge(built):
    later = NOW + timedelta(hours=4)  # kickoff + 1 h
    s = reprice(
        _rc(
            built["board"],
            _view(built["disc"], observed_at=later - timedelta(minutes=2)),
            now=later,
        )
    )
    assert s.fixtures == [] and s.contracts == []
    assert sorted(s.removed_started) == sorted(built["board"]["fixtures"])


def test_script_layer_runs_inside_the_temporal_guard(built, registry):
    from soccer_edge.core.temporal import FutureInformationError

    inp = _inputs(registry, built["fixtures"], built["disc"])
    inp.results_observed_at = inp.as_of + timedelta(hours=1)
    with pytest.raises(FutureInformationError):
        run(inp, built["cfg"])


# ------------------------------------------------------------------------------------------- lineups
def test_lineup_history_is_carried_only_for_genuine_state_changes(built):
    fid, e = next(iter(built["board"]["fixtures"].items()))
    later = dict(
        e,
        model_generated_at="2026-10-10T12:00:00Z",
        inputs=dict(e["inputs"], lineup_key="sha256:xi"),
    )
    m = merge_boards({"fixtures": {fid: later}}, {"fixtures": {fid: e}}, now=NOW)
    hist = m["fixtures"][fid]["lineup_history"]
    assert len(hist) == 1 and hist[0]["lineup_key"] == "none"
    assert hist[0]["scripts"]["shares"] == e["scripts"]["shares"]
    # same lineup key: no history invented
    same = dict(e, model_generated_at="2026-10-10T12:00:00Z")
    assert (
        "lineup_history"
        not in merge_boards({"fixtures": {fid: e}}, {"fixtures": {fid: same}}, now=NOW)["fixtures"][
            fid
        ]
    )
    payload = script_engine_payload(m["fixtures"][fid], None, [], intl_pool=False)
    lr = payload["lineup_rescripting"]
    assert lr["refreshed_after_lineup"] and lr["model_uses_lineups"] is False
    assert all(v == 0 for v in lr["script_share_changes"].values())
    assert "unchanged" in lr["statement"]


# ------------------------------------------------------------------------------------------- context
def test_context_classifies_friendlies_knockouts_and_leagues(registry):
    fr = match_context(
        competition=registry.competitions["fifa.friendly"],
        competition_id="fifa.friendly",
        stage=None,
        leg_number=None,
        requires_winner=False,
        neutral_site=True,
        national=True,
        rest_days_home=None,
        rest_days_away=4,
    )
    assert fr["competition_type"]["value"] == "INTERNATIONAL_FRIENDLY"
    assert {"FRIENDLY", "NEUTRAL_SITE"} <= set(fr["flags"])
    assert fr["rotation_uncertainty"]["value"] == "ELEVATED_UNQUANTIFIED"
    assert fr["must_win"]["status"] == "UNAVAILABLE" and fr["must_win"]["value"] is None
    ko = match_context(
        competition=registry.competitions["uefa.champions_league"],
        competition_id="uefa.champions_league",
        stage="Round of 16",
        leg_number=2,
        requires_winner=True,
        neutral_site=False,
        national=False,
        rest_days_home=3,
        rest_days_away=3,
    )
    assert ko["competition_type"]["value"] == "CONTINENTAL_CLUB"
    assert {"KNOCKOUT", "SECOND_LEG"} <= set(ko["flags"])
    assert ko["aggregate"]["status"] == "UNAVAILABLE"
    lg = match_context(
        competition=registry.competitions["eng.premier_league"],
        competition_id="eng.premier_league",
        stage="Matchday 6",
        leg_number=None,
        requires_winner=False,
        neutral_site=False,
        national=False,
        rest_days_home=None,
        rest_days_away=None,
    )
    assert lg["competition_type"]["value"] == "LEAGUE" and lg["flags"] == []
    final = match_context(
        competition=registry.competitions["fifa.world_cup"],
        competition_id="fifa.world_cup",
        stage="Final",
        leg_number=None,
        requires_winner=True,
        neutral_site=True,
        national=True,
        rest_days_home=None,
        rest_days_away=None,
    )
    assert (
        final["competition_type"]["value"] == "INTERNATIONAL_COMPETITIVE"
        and "FINAL" in final["flags"]
    )


def test_knockout_advance_contract_decomposes_exactly():
    mats, lam, mu = _mats(w=200)
    layer = ScriptLayer(mats, first_half_share=0.441, lam=lam, mu=mu, requires_winner=True)
    spec = CellSpec("match_winner_2way", "including_penalties", "home", None)
    other = CellSpec("match_winner_2way", "including_penalties", "away", None)
    a, b = layer.contract(spec), layer.contract(other)
    assert a["p"] + b["p"] == pytest.approx(1.0, abs=1e-6)
    assert sum(s * p for s, p in zip(layer.share, a["sp"])) == pytest.approx(a["p"], abs=1e-5)
    blk = layer.fixture_block()
    assert blk["overall_profile"]["p_extra_time"] == pytest.approx(blk["overall_profile"]["p_draw"])
    assert a["sp"][0] == pytest.approx(1.0)  # HOME_CONTROL always advances the home side


# ------------------------------------------------------------------------------------------- matchup
def test_matchup_is_opponent_adjusted_and_labelled(built):
    e = next(iter(built["board"]["fixtures"].values()))
    mu = e["matchup"]
    assert mu["metric_kind"].startswith("DIXON_COLES") and "not xG" in mu["metric_kind"]
    for k in ("HOME_ATTACK_vs_AWAY_DEFENSE", "AWAY_ATTACK_vs_HOME_DEFENSE"):
        m = mu["matchups"][k]
        assert m["label"] and 0 <= m["p_attack_advantage"] <= 1
        assert m["z_gap"] == pytest.approx(m["attack_z"] - m["defence_z"], abs=2e-3)
    assert mu["primary_mismatch"] in mu["matchups"]


# ------------------------------------------------------------------------------------------- publication
def test_payload_is_complete_tiered_and_bounded(built):
    s = reprice(_rc(built["board"], _view(built["disc"])))
    d = s.model_dump(mode="json")
    for fid, e in built["board"]["fixtures"].items():
        fx = next(f for f in d["fixtures"] if f["fixture_id"] == fid)
        rows = [c for c in d["contracts"] if c["fixture_id"] == fid]
        p = script_engine_payload(
            e,
            fx,
            rows,
            intl_pool=False,
            slate_meta={"slate_id": d["slate_id"], "kalshi": d["kalshi"]},
        )
        assert p["status"] == "OK" and p["research_only"]
        g = p["glance"]
        assert set(g) >= {
            "h_d_a",
            "expected_goals",
            "primary_script",
            "secondary_script",
            "data_confidence",
            "lineup",
            "competition",
            "no_compelling_edge",
            "story",
        }
        assert "not xG" in g["expected_goals"]["basis"]
        assert sum(c["simulation_share"] for c in p["scripts"]["cards"]) == pytest.approx(
            1.0, abs=1e-4
        )
        assert len(p["matrix"]["rows"]) == sum(1 for c in e["contracts"].values() if "sc" in c)
        codes = {x["code"] for x in p["data_gaps"]}
        assert {"XG_UNAVAILABLE", "LINEUP_NOT_MODELLED", "SCRIPT_SHARES_NOT_CALIBRATED"} <= codes
        assert g["story"]["sentence"].endswith(".")
        assert len(json.dumps(p)) < 75_000


def test_explorer_publishes_the_script_engine_per_event(built, tmp_path):
    from edge_finder_contract import research as R

    from soccer_edge import app_export, research_export
    from soccer_edge.slate.reprice import write_slate

    root = tmp_path / "archive"
    (root / "runs").mkdir(parents=True)
    (root / "runs" / "latest.model_board.v1.json").write_text(json.dumps(built["board"]))
    slate = reprice(_rc(built["board"], _view(built["disc"])))
    write_slate(root, slate)
    out = root / "app" / "latest"
    noop = lambda *a, **k: None
    assert app_export.export(data_root=root, out=out, now=NOW, log=noop) == 0
    assert (
        research_export.export_explorer(
            app_root=out, data_root=root, now=NOW, log=noop, min_interval_seconds=0
        )
        == 0
    )
    assert R.verify_explorer(out) == []
    index = json.loads((out / "explorer" / "index.json").read_text())
    assert len(index["events"]) == len(built["board"]["fixtures"])
    for ev in index["events"]:
        doc = json.loads(
            (out / ev["path"]).read_text()
        )  # discovered through the index, never guessed
        p = doc["extensions"]["soccer_script_engine"]
        assert p["status"] == "OK" and p["contract"] == "soccer_script_engine.v1"
        assert len(json.dumps(doc)) <= research_export.EVENT_MAX_BYTES
    markets = json.loads((out / "markets.json").read_text())["items"]
    assert any("script_robustness" in (m.get("extensions") or {}) for m in markets)


def test_v1_engine_publishes_scripts_as_unavailable(registry, tmp_path):
    fixtures = _epl_fixtures(registry)[:1]
    fake = FakeKalshi(
        fixtures,
        registry,
        fair=lambda f: {"home": 0.45, "draw": 0.27, "away": 0.28, "mean_total": 2.6},
    )
    disc = discover(KalshiPublicClient(transport=fake.transport))
    cfg = RunConfig(
        run_date=date(2026, 10, 10),
        n_worlds=60,
        draws_per_world=20,
        engine_version="minute_engine_v1",
    )
    art = run(_inputs(registry, fixtures, disc), cfg)
    for e in art.board_entries.values():
        assert e["scripts"]["status"] == "UNAVAILABLE"
        assert all("sc" not in c for c in e["contracts"].values())
    p = script_engine_payload(next(iter(art.board_entries.values())), None, [], intl_pool=False)
    assert p["status"] == "UNAVAILABLE"


def test_payload_sizes_stay_bounded(built):
    for e in built["board"]["fixtures"].values():
        assert len(json.dumps(e["scripts"])) < 20_000
        assert len(json.dumps({t: c.get("sc") for t, c in e["contracts"].items()})) < 15_000
