from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from soccer_edge.model.analytic import outcome_probs, score_matrix, total_over
from soccer_edge.model.context import LineupState, MatchContext, PlayerAvailability
from soccer_edge.model.strength import DixonColesFitter
from soccer_edge.model.worlds import WorldConfig, WorldGenerator
from soccer_edge.sim.engine import SimConfig, minute_profile, simulate
from tests.conftest import synthetic_league


def _ctx(home="t00", away="t01", **kw):
    return MatchContext("fx", "c", home, away, datetime(2026, 10, 10, 14, tzinfo=UTC), **kw)


def test_fit_recovers_structure(synthetic_posterior):
    post, teams, att, dfn = synthetic_posterior
    est = np.array([post.mean[post.idx_attack(t)] for t in teams])
    assert np.corrcoef(est, att)[0, 1] > 0.8
    assert 0.1 < post.mean[post.idx_home] < 0.4
    assert abs(post.mean[post.idx_rho]) < 0.15


def test_point_in_time_fit_ignores_future(synthetic_posterior):
    teams, att, dfn, rows = synthetic_league()
    early = DixonColesFitter().fit(rows, as_of=rows[100].date)
    assert early.n_matches == len([r for r in rows if r.date < rows[100].date])


def test_sparse_team_has_wider_posterior():
    teams, att, dfn, rows = synthetic_league()
    from datetime import date

    rows2 = [r for r in rows if not (r.home == "t00" or r.away == "t00")][: len(rows) - 30]
    # give t00 only two matches
    keep = [r for r in rows if r.home == "t00" or r.away == "t00"][:2]
    post = DixonColesFitter().fit(rows2 + keep, as_of=date(2026, 6, 1))
    s_sparse = post.team_summary("t00")["attack_sd"]
    s_full = np.median([post.team_summary(t)["attack_sd"] for t in teams if t != "t00"])
    assert s_sparse > 1.3 * s_full


def test_minute_profile_mean_one():
    p = minute_profile(SimConfig())
    assert abs(p.mean() - 1) < 1e-9 and p[-1] > p[0]


def test_reproducible(synthetic_posterior):
    post = synthetic_posterior[0]
    ws = WorldGenerator(post).generate(_ctx(), 50, np.random.default_rng(7))
    a = simulate(ws, _ctx(), SimConfig(draws_per_world=40), seed=11)
    b = simulate(ws, _ctx(), SimConfig(draws_per_world=40), seed=11)
    assert np.array_equal(a.home_ft, b.home_ft) and np.array_equal(a.away_ht, b.away_ht)
    assert a.outcome_hash() == b.outcome_hash()


@pytest.fixture(scope="module")
def big_sim(synthetic_posterior):
    post = synthetic_posterior[0]
    ws = WorldGenerator(post).generate(_ctx(), 400, np.random.default_rng(3))
    return ws, simulate(ws, _ctx(), SimConfig(draws_per_world=100), seed=5)


def test_expected_goals_sane(big_sim):
    ws, out = big_sim
    assert abs(out.home_ft.mean() - ws.lam_home.mean()) < 0.12
    assert abs(out.away_ft.mean() - ws.mu_away.mean()) < 0.12
    assert 0.3 < out.home_ft.mean() < 4


def test_halftime_consistent_with_fulltime(big_sim):
    _, out = big_sim
    assert np.all(out.home_ht <= out.home_ft) and np.all(out.away_ht <= out.away_ft)
    share = out.total_ht.sum() / max(out.total_ft.sum(), 1)
    assert 0.40 < share < 0.50  # second half share ~0.54 by construction


def test_result_probabilities_partition(big_sim):
    _, out = big_sim
    s = out.compact_summary()
    assert abs(s["p_home"] + s["p_draw"] + s["p_away"] - 1) < 1e-12
    grid = np.array(s["score_grid"])
    assert abs(grid.sum() - 1) < 1e-4  # grid rounded to 5 dp


def test_ladder_monotone(big_sim):
    _, out = big_sim
    probs = [(out.total_ft > x + 0.5).mean() for x in range(6)]
    assert all(a >= b for a, b in zip(probs, probs[1:]))
    tt = [(out.home_ft > x + 0.5).mean() for x in range(5)]
    assert all(a >= b for a, b in zip(tt, tt[1:]))


def test_red_cards_reduce_scoring_for_offender(synthetic_posterior):
    post = synthetic_posterior[0]
    hi = WorldConfig(red_card_mean_per_team=0.0)
    ws0 = WorldGenerator(post, hi).generate(_ctx(), 300, np.random.default_rng(1))
    # force a certain early home red card by giving home a huge hazard and away none
    ws1 = WorldGenerator(post, WorldConfig(red_card_mean_per_team=0.0)).generate(
        _ctx(), 300, np.random.default_rng(1)
    )
    ws1.red_hazard_home[:] = 1.0  # red in minute 1
    o0 = simulate(ws0, _ctx(), SimConfig(draws_per_world=60), seed=2)
    o1 = simulate(ws1, _ctx(), SimConfig(draws_per_world=60), seed=2)
    assert o1.home_ft.mean() < o0.home_ft.mean() * 0.85
    assert o1.away_ft.mean() > o0.away_ft.mean() * 1.10
    assert o1.home_red.mean() > 0.95


def test_game_state_effects_change_draw_rate(synthetic_posterior):
    post = synthetic_posterior[0]
    flat = WorldConfig(trailing_attack_mult=1.0, leading_attack_mult=1.0, state_mult_sd=0.0)
    strong = WorldConfig(trailing_attack_mult=1.5, leading_attack_mult=0.6, state_mult_sd=0.0)
    w0 = WorldGenerator(post, flat).generate(_ctx(), 300, np.random.default_rng(4))
    w1 = WorldGenerator(post, strong).generate(_ctx(), 300, np.random.default_rng(4))
    d0 = (simulate(w0, _ctx(), SimConfig(draws_per_world=80), seed=1).result_ft() == 0).mean()
    d1 = (simulate(w1, _ctx(), SimConfig(draws_per_world=80), seed=1).result_ft() == 0).mean()
    assert d1 > d0 + 0.02


def test_sim_matches_analytic_when_dynamics_disabled(synthetic_posterior):
    post = synthetic_posterior[0]
    cfg = WorldConfig(
        sigma_model_log_rate=0.0,
        sigma_environment=0.0,
        red_card_mean_per_team=0.0,
        trailing_attack_mult=1.0,
        leading_attack_mult=1.0,
        state_mult_sd=0.0,
    )
    ws = WorldGenerator(post, cfg).generate(_ctx(), 1, np.random.default_rng(0))
    ws.lam_home[:] = 1.6
    ws.mu_away[:] = 1.1
    out = simulate(ws, _ctx(), SimConfig(draws_per_world=60000), seed=9)
    m = score_matrix(1.6, 1.1, 0.0)
    an = outcome_probs(m)
    s = out.compact_summary()
    assert abs(s["p_home"] - an["home"]) < 0.01
    assert abs(s["p_draw"] - an["draw"]) < 0.01
    assert abs(s["p_over_2_5"] - total_over(m, 2.5)) < 0.01


def test_knockout_requires_winner(synthetic_posterior):
    post = synthetic_posterior[0]
    ctx = _ctx(requires_winner=True)
    ws = WorldGenerator(post).generate(ctx, 100, np.random.default_rng(1))
    out = simulate(ws, ctx, SimConfig(draws_per_world=50), seed=3)
    assert np.all(out.winner_final != 0)
    assert out.et_played.mean() > 0.15 and out.pens_played.mean() > 0.03
    assert np.all(out.et_played[out.pens_played])
    assert np.all((out.home_et + out.away_et)[~out.et_played] == 0)


def test_second_leg_aggregate(synthetic_posterior):
    post = synthetic_posterior[0]
    ctx = _ctx(
        requires_winner=True,
        two_leg_second_leg=True,
        first_leg_home_goals=0,
        first_leg_away_goals=3,
    )
    ws = WorldGenerator(post).generate(ctx, 100, np.random.default_rng(1))
    out = simulate(ws, ctx, SimConfig(draws_per_world=50), seed=3)
    # away leads tie by 3: away should progress most of the time
    assert (out.winner_final == 2).mean() > 0.8


def test_lineup_confirmation_reduces_uncertainty(synthetic_posterior):
    post = synthetic_posterior[0]
    players = tuple(
        PlayerAvailability(f"p{i}", "t00", 0.5, 0.5, importance=0.3, goal_share_if_play=0.2)
        for i in range(4)
    )
    unk = _ctx(lineup_state=LineupState.PROJECTED, home_players=players)
    con = _ctx(lineup_state=LineupState.CONFIRMED, home_players=players)
    rng = np.random.default_rng(5)
    w_unk = WorldGenerator(post).generate(unk, 2000, rng)
    w_con = WorldGenerator(post).generate(con, 2000, np.random.default_rng(5))
    cv = lambda x: x.std() / x.mean()
    assert cv(w_unk.lam_home) > cv(w_con.lam_home) * 1.03
    assert w_con.home_players_on.all()


def test_absent_star_lowers_attack_and_removes_goals(synthetic_posterior):
    post = synthetic_posterior[0]
    star = PlayerAvailability("star", "t00", 0.0, 0.0, importance=0.3, goal_share_if_play=0.5)
    other = PlayerAvailability("other", "t00", 1.0, 1.0, importance=0.05, goal_share_if_play=0.5)
    ctx_out = _ctx(lineup_state=LineupState.CONFIRMED, home_players=(star, other))
    ctx_in = _ctx(
        lineup_state=LineupState.CONFIRMED,
        home_players=(
            PlayerAvailability("star", "t00", 1.0, 1.0, importance=0.3, goal_share_if_play=0.5),
            other,
        ),
    )
    w_out = WorldGenerator(post).generate(ctx_out, 300, np.random.default_rng(1))
    w_in = WorldGenerator(post).generate(ctx_in, 300, np.random.default_rng(1))
    assert w_out.lam_home.mean() < w_in.lam_home.mean()
    o_out = simulate(w_out, ctx_out, SimConfig(draws_per_world=50), seed=1)
    assert o_out.home_player_goals[:, 0].sum() == 0  # absent player cannot score
    assert np.array_equal(o_out.home_player_goals.sum(axis=1), o_out.home_ft)  # goals conserved


def test_wider_inputs_wider_outputs(synthetic_posterior):
    post = synthetic_posterior[0]
    narrow = WorldGenerator(post, WorldConfig(sigma_model_log_rate=0.0)).generate(
        _ctx(), 1000, np.random.default_rng(2)
    )
    wide = WorldGenerator(post, WorldConfig(sigma_model_log_rate=0.4)).generate(
        _ctx(), 1000, np.random.default_rng(2)
    )
    assert wide.lam_home.std() > narrow.lam_home.std() * 1.5
