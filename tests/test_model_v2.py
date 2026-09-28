"""dc_laplace_v2 + world_sim_v2 (remediation phases 12-13; audit B2, B3, §D, §P8-9)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import numpy as np
import pytest

from soccer_edge.kalshi.taxonomy import MarketFamily, Period
from soccer_edge.model.analytic import outcome_probs, score_matrix, total_over
from soccer_edge.model.context import MatchContext
from soccer_edge.model.strength import DixonColesFitter, MatchRow
from soccer_edge.model.strength_v2 import DixonColesFitterV2, StrengthConfigV2
from soccer_edge.model.worlds import WorldConfig, WorldGenerator, WorldSet
from soccer_edge.pricing.analytic_pricer import is_analytic, price_analytic
from soccer_edge.pricing.pricer import price
from soccer_edge.pricing.semantics import Semantics
from soccer_edge.sim.engine_v2 import SimConfigV2, score_matrices, simulate_v2


def _league(seed, home_rate=1.55, away_rate=1.25, n_teams=20, rounds=38, neutral_share=0.0):
    rng = np.random.default_rng(seed)
    teams = [f"t{i}" for i in range(n_teams)]
    att = rng.normal(0, 0.2, n_teams)
    dfc = rng.normal(0, 0.2, n_teams)
    rows = []
    d0 = date(2025, 8, 1)
    for r in range(rounds):
        perm = rng.permutation(n_teams)
        for i in range(0, n_teams, 2):
            h, a = perm[i], perm[i + 1]
            neutral = rng.random() < neutral_share
            lam = (away_rate if neutral else home_rate) * np.exp(att[h] - dfc[a])
            mu = away_rate * np.exp(att[a] - dfc[h])
            rows.append(
                MatchRow(
                    d0 + timedelta(days=7 * r),
                    teams[h],
                    teams[a],
                    int(rng.poisson(lam)),
                    int(rng.poisson(mu)),
                    neutral=neutral,
                )
            )
    return teams, rows


AS_OF = date(2026, 7, 1)


def test_v2_fitted_levels_match_training_levels_and_v1_does_not():
    _, rows = _league(11)
    post = DixonColesFitterV2().fit(rows, as_of=AS_OF)
    pred_h = np.mean([post.expected_goals(r.home, r.away)[0] for r in rows])
    pred_a = np.mean([post.expected_goals(r.home, r.away)[1] for r in rows])
    obs_h = np.mean([r.home_goals for r in rows])
    obs_a = np.mean([r.away_goals for r in rows])
    assert abs(pred_a / obs_a - 1) < 0.02 and abs(pred_h / obs_h - 1) < 0.02
    # the frozen v1 family keeps its documented defect (audit B3) - pinned, not fixed
    v1 = DixonColesFitter().fit(rows, as_of=AS_OF)
    pred_a1 = np.mean([v1.expected_goals(r.home, r.away)[1] for r in rows])
    assert pred_a1 / obs_a < 0.95


def test_v2_hard_centring_layout_and_samples():
    teams, rows = _league(3)
    post = DixonColesFitterV2().fit(rows, as_of=AS_OF)
    n = len(teams)
    assert len(post.mean) == 2 * n + 3
    assert abs(post.mean[:n].sum()) < 1e-9 and abs(post.mean[n : 2 * n].sum()) < 1e-9
    assert np.linalg.matrix_rank(post.cov) == 2 * (n - 1) + 3
    s = post.sample(500, np.random.default_rng(0))
    assert np.abs(s[:, :n].sum(axis=1)).max() < 1e-9
    assert post.idx_intercept == 2 * n + 2 and post.version == "dc_laplace_v2"
    lam, mu, rho = post.rates_for(s, teams[0], teams[1])
    assert lam.shape == (500,) and np.all(np.abs(rho) <= 0.3)
    assert post.param_hash().startswith("sha256:")


def test_v2_neutral_rows_do_not_get_home_advantage():
    teams, rows = _league(5, neutral_share=0.4)
    post = DixonColesFitterV2().fit(rows, as_of=AS_OF)
    assert post.diagnostics["n_neutral_rows"] > 100
    lam_home, _ = post.expected_goals(teams[0], teams[1])
    lam_neutral, _ = post.expected_goals(teams[0], teams[1], neutral=True)
    assert lam_neutral < lam_home
    assert lam_home / lam_neutral == pytest.approx(np.exp(post.diagnostics["fitted_gamma"]))
    # gamma recovers the (non-neutral) home/away ratio, not the home level
    assert 0.10 < post.diagnostics["fitted_gamma"] < 0.32


def test_v2_intercept_likelihood_ratio_and_fixed_intercept():
    _, rows = _league(7)
    fitter = DixonColesFitterV2()
    free = fitter.fit(rows, as_of=AS_OF)
    fixed = fitter.fit(rows, as_of=AS_OF, fix_intercept=0.0)
    assert fixed.diagnostics["fitted_intercept"] == 0.0
    assert 2 * (free.log_likelihood - fixed.log_likelihood) > 6.63
    assert free.diagnostics["fitted_intercept"] > 0.2


def test_v2_config_grid_is_separate_from_v1_defaults():
    cfg = StrengthConfigV2(decay_per_day=0.003, prior_sd_team=0.6, version="dc_laplace_v2.x")
    post = DixonColesFitterV2(cfg).fit(_league(2)[1], as_of=AS_OF)
    assert post.version == "dc_laplace_v2.x" and post.config.prior_sd_team == 0.6


# ------------------------------------------------------------------ world_sim_v2


def _ws(lam, mu, rho=-0.10, W=1000):
    return WorldSet(
        W,
        np.full(W, lam),
        np.full(W, mu),
        np.full(W, rho),
        np.zeros(W),
        np.zeros(W),
        np.ones(W),
        np.ones(W),
        config=WorldConfig(),
    )


CTX = MatchContext("f", "c", "H", "A", datetime(2026, 1, 1, tzinfo=UTC))


@pytest.mark.parametrize("lam,mu", [(2.30, 0.80), (1.52, 1.13), (1.00, 1.90)])
def test_engine_v2_honours_rho_and_preserves_the_mean(lam, mu):
    out = simulate_v2(
        _ws(lam, mu), CTX, SimConfigV2(draws_per_world=100, allocate_player_goals=False), seed=5
    )
    m = score_matrix(lam, mu, -0.10)
    an = outcome_probs(m)
    assert abs((out.home_ft == out.away_ft).mean() - an["draw"]) < 0.006
    assert abs((out.home_ft > out.away_ft).mean() - an["home"]) < 0.006
    assert abs(((out.home_ft + out.away_ft) > 2.5).mean() - total_over(m, 2.5)) < 0.006
    assert abs(out.home_ft.mean() / lam - 1) < 0.01 and abs(out.away_ft.mean() / mu - 1) < 0.01
    assert (
        out.engine_version == "world_sim_v2"
        and "game_state_multipliers" in out.meta["dynamics_dropped"]
    )


def test_engine_v2_timing_is_exact_conditional_on_the_score():
    cfg = SimConfigV2(draws_per_world=200, allocate_player_goals=False, first_half_share=0.441)
    out = simulate_v2(_ws(1.6, 1.2), CTX, cfg, seed=9)
    ht_share = (out.home_ht.sum() + out.away_ht.sum()) / (out.home_ft.sum() + out.away_ft.sum())
    assert abs(ht_share - 0.441) < 0.006
    both = (out.home_ft > 0) & (out.away_ft > 0)
    p_first_home = (out.first_goal_team[both] == 1).mean()
    expected = (out.home_ft[both] / (out.home_ft[both] + out.away_ft[both])).mean()
    assert abs(p_first_home - expected) < 0.01
    assert np.all(out.first_goal_minute[out.home_ft + out.away_ft == 0] == -1)
    assert np.all(out.first_goal_minute[both] >= 0) and np.all(out.home_ht <= out.home_ft)


def test_engine_v2_extra_time_and_penalties_only_when_a_winner_is_required():
    plain = simulate_v2(
        _ws(1.4, 1.4), CTX, SimConfigV2(draws_per_world=50, allocate_player_goals=False), seed=1
    )
    assert not plain.et_played.any() and not plain.pens_played.any()
    ko = MatchContext("f", "c", "H", "A", datetime(2026, 1, 1, tzinfo=UTC), requires_winner=True)
    out = simulate_v2(
        _ws(1.4, 1.4), ko, SimConfigV2(draws_per_world=50, allocate_player_goals=False), seed=1
    )
    level = out.home_ft == out.away_ft
    assert out.et_played[level].all() and not out.et_played[~level].any()
    assert np.all(out.winner_final[level] > 0)
    assert out.pens_played[level].mean() > 0.3  # many level ties stay level after 30 minutes


def test_analytic_pricer_matches_engine_draws_and_has_no_mc_noise():
    ws = _ws(1.7, 1.1, W=400)
    mats = score_matrices(ws.lam_home, ws.mu_away, ws.rho)
    out = simulate_v2(
        ws, CTX, SimConfigV2(draws_per_world=200, allocate_player_goals=False), seed=3
    )
    sems = [
        Semantics("a", MarketFamily.MATCH_RESULT_3WAY, Period.REGULATION, "home", None),
        Semantics("b", MarketFamily.TOTAL_GOALS, Period.REGULATION, None, Decimal("2.5")),
        Semantics("c", MarketFamily.BTTS, Period.REGULATION, None, None),
        Semantics("d", MarketFamily.HANDICAP, Period.REGULATION, "away", Decimal("0.5")),
        Semantics("e", MarketFamily.EXACT_SCORE, Period.REGULATION, "home", None, k=201),
        Semantics("f", MarketFamily.TEAM_TOTAL, Period.REGULATION, "home", Decimal("1.5")),
    ]
    for sem in sems:
        assert is_analytic(sem)
        pa = price_analytic(sem, mats)
        pm = price(sem, out)
        assert abs(pa.fair_mean - pm.fair_mean) < 0.006, sem.ticker
        assert pa.mc_se == 0.0 and pa.effective_draws == 400 and len(pa.world_probs) == 400
    assert not is_analytic(
        Semantics("g", MarketFamily.FIRST_HALF_RESULT, Period.FIRST_HALF, "home", None)
    )
    assert not is_analytic(
        Semantics("h", MarketFamily.FIRST_TO_SCORE, Period.REGULATION, "home", None)
    )


def test_world_generator_accepts_v2_posterior():
    teams, rows = _league(4)
    post = DixonColesFitterV2().fit(rows, as_of=AS_OF)
    ctx = MatchContext("f", "c", teams[0], teams[1], datetime(2026, 1, 1, tzinfo=UTC))
    ws = WorldGenerator(post, WorldConfig()).generate(ctx, 100, np.random.default_rng(0))
    assert ws.n_worlds == 100 and ws.rho.shape == (100,) and ws.lam_home.mean() > 0
