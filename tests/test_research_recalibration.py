"""Unit tests for the pure functions in research/recalibration.py and research/pedge_eval.py.
No dataset needed; the one integration check is skipped when the npz cache is absent."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from research import pedge_eval as pe
from research import recalibration as rc

from soccer_edge.model.analytic import outcome_probs, score_matrix, total_over

REPO = Path(__file__).resolve().parents[1]


def test_dc_probs_vec_matches_analytic_score_matrix():
    rng = np.random.default_rng(1)
    lam = np.exp(rng.normal(0.3, 0.3, 20))
    mu = np.exp(rng.normal(0.0, 0.3, 20))
    rho = rng.uniform(-0.2, 0.1, 20)
    p3, tot = rc.dc_probs_vec(lam, mu, rho)
    assert p3.shape == (20, 3) and tot.shape == (20, 21)
    for i in range(20):
        m = score_matrix(lam[i], mu[i], rho[i])
        op = outcome_probs(m)
        assert np.allclose(p3[i], [op["home"], op["draw"], op["away"]], atol=1e-12)
        assert abs(tot[i, 3:].sum() - total_over(m, 2.5)) < 1e-12
    assert np.allclose(tot.sum(axis=1), 1.0)


def test_scaled_rates_is_exact_linear_scaling_of_deviations():
    base = np.array([[np.log(1.5), np.log(1.1), -0.05]])
    dev = np.array([[[0.2, -0.1, 0.02], [-0.3, 0.1, -0.01]]])
    lam0, mu0, rho0 = rc.scaled_rates(base, dev, np.array([0.0]), np.zeros((1, 2)))
    assert np.allclose(lam0, 1.5) and np.allclose(mu0, 1.1) and np.allclose(rho0, -0.05)
    lam2, mu2, rho2 = rc.scaled_rates(base, dev, np.array([2.0]), np.zeros((1, 2)))
    assert np.allclose(np.log(lam2[0]) - np.log(1.5), 2 * dev[0, :, 0])
    assert np.allclose(np.log(mu2[0]) - np.log(1.1), 2 * dev[0, :, 1])
    assert np.allclose(rho2[0], -0.05 + 2 * dev[0, :, 2])
    # a shared shift multiplies both rates by the same factor
    lam_s, mu_s, _ = rc.scaled_rates(base, dev, np.array([1.0]), np.full((1, 2), 0.1))
    lam1, mu1, _ = rc.scaled_rates(base, dev, np.array([1.0]), np.zeros((1, 2)))
    assert np.allclose(lam_s / lam1, np.exp(0.1)) and np.allclose(mu_s / mu1, np.exp(0.1))
    # rho is clipped to the same range as ParameterPosterior.rates_for
    _, _, rho_big = rc.scaled_rates(base, dev * 100, np.array([1.0]), np.zeros((1, 2)))
    assert np.all(np.abs(rho_big) <= 0.3)


def test_randomized_pit_is_uniform_when_the_model_is_true():
    rng = np.random.default_rng(2)
    n = 20000
    pmf = rng.dirichlet(np.ones(4), size=n)
    y = np.array([rng.choice(4, p=p) for p in pmf])
    u = rc.randomized_pit(pmf, y, rng)
    s = rc.pit_summary(u)
    assert u.min() >= 0 and u.max() <= 1
    assert abs(s["variance"] - 1 / 12) < 0.003 and abs(s["variance_z"]) < 3
    assert s["chi2_uniform"] < 30 and abs(s["mean"] - 0.5) < 0.01
    # a hugely over-dispersed predictive (near-uniform pmf for peaked truth) piles PIT in the middle
    peaked = np.zeros(n, int)
    wide = np.full((n, 4), 0.25)
    u2 = rc.randomized_pit(wide, peaked + 1, rng)  # truth always category 1 -> u in [0.25,0.5]
    assert rc.pit_summary(u2)["variance"] < 1 / 12


def test_logloss_dispersion_z_is_small_when_the_model_is_true():
    rng = np.random.default_rng(3)
    P = rng.dirichlet(np.ones(3) * 2, size=20000)
    y = np.array([rng.choice(3, p=p) for p in P])
    d = rc.logloss_dispersion(P, y)
    assert abs(d["z_excess_loss"]) < 3
    assert abs(d["realised_mean"] - d["expected_mean"]) < 0.01


def test_standardized_disagreement_recovers_known_scale():
    rng = np.random.default_rng(4)
    sd = np.full(5000, 0.1)
    p_d = np.full(5000, 0.45)
    p_m = p_d + rng.normal(0, 0.06, 5000)  # true dispersion is 0.6 x the claimed sd
    d = rc.standardized_disagreement(p_d, p_m, sd)
    assert abs(d["market_implied_k"] - 0.6) < 0.03
    assert abs(d["sd_z"] - 0.6) < 0.03


def _synthetic_groups(
    k_true: float, n_teams: int = 400, per_group: int = 4, seed: int = 0, updated: bool = False
):
    """Groups whose residuals carry exactly the model's cross covariance at scale k.
    updated=False: no refit inside the window (cross cov = k^2 M).
    updated=True : a refit between every pair; Gaussian innovations with cross cov (k^2 - 1) M."""
    rng = np.random.default_rng(seed)
    groups = []
    idx0 = 0
    for t in range(n_teams):
        rates = rng.uniform(0.9, 2.0, per_group)
        v_shared = 0.03  # Var(att_t): shared by the team's matches in the window
        v_own = rng.uniform(0.01, 0.03, per_group)  # Var(def_opp_i): one per opponent
        S_log = np.full((per_group, per_group), v_shared) + np.diag(v_own)
        M = np.outer(rates, rates) * S_log  # delta-method covariance of the rates at k = 1
        idx = np.arange(idx0, idx0 + per_group)
        idx0 += per_group
        if updated:
            off = M - np.diag(np.diag(M))
            cov = np.diag(rates + k_true**2 * np.diag(M)) + (k_true**2 - 1.0) * off
            goals = rng.multivariate_normal(rates, cov)  # Gaussian stand-in for the counts
            upd = ~np.eye(per_group, dtype=bool)
        else:
            eps = rng.multivariate_normal(np.zeros(per_group), (k_true**2) * S_log)
            goals = rng.poisson(rates * np.exp(eps - (k_true**2) * np.diag(S_log) / 2))
            upd = np.zeros((per_group, per_group), dtype=bool)
        groups.append(rc.Group("X", "2020-21", f"t{t}", "for", 0, idx, goals, rates, M, upd))
    return groups, idx0


@pytest.mark.parametrize("k_true", [0.5, 1.0])
def test_estimate_k_recovers_the_scale_on_synthetic_groups(k_true):
    groups, n = _synthetic_groups(k_true, n_teams=1500)
    shift = np.zeros(n)
    k_hat = rc.estimate_k(groups, shift)
    lo, hi = rc.bootstrap_k(groups, shift, n_boot=100)
    assert abs(k_hat - k_true) < 0.15, (k_hat, k_true)
    assert lo <= k_hat <= hi
    phi = rc.estimate_phi(groups, np.full(n, k_hat), shift)
    assert 0.85 < phi < 1.15


@pytest.mark.parametrize("k_true", [0.7, 1.0, 1.3])
def test_estimate_k_recovers_the_scale_with_refits_between_matches(k_true):
    groups, n = _synthetic_groups(k_true, n_teams=2000, updated=True, seed=11)
    shift = np.zeros(n)
    k_hat = rc.estimate_k(groups, shift)
    assert abs(k_hat - k_true) < 0.12, (k_hat, k_true)
    num, den, den_upd = rc.cross_moments(groups, np.ones(n), shift)
    assert den_upd == pytest.approx(den)  # every pair is refit-separated here
    # under k = 1 the raw cross products are ~0 (innovation whiteness), not ~den
    if k_true == 1.0:
        assert abs(num) < 0.15 * den


def test_group_gauss_score_prefers_the_true_scale():
    groups, n = _synthetic_groups(0.5, n_teams=1500, seed=5)
    shift = np.zeros(n)
    s_true = rc.group_gauss_scores(groups, np.full(n, 0.5), 1.0, shift).mean()
    s_wide = rc.group_gauss_scores(groups, np.full(n, 1.5), 1.0, shift).mean()
    assert s_true > s_wide
    groups_u, n_u = _synthetic_groups(0.7, n_teams=1500, seed=6, updated=True)
    shift_u = np.zeros(n_u)
    s_07 = rc.group_gauss_scores(groups_u, np.full(n_u, 0.7), 1.0, shift_u).mean()
    s_13 = rc.group_gauss_scores(groups_u, np.full(n_u, 1.3), 1.0, shift_u).mean()
    assert s_07 > s_13


def test_tercile_helpers():
    p = np.linspace(0.1, 0.9, 300)
    e = rc.tercile_edges(p)
    t = rc.tercile_index(p, e)
    assert set(t) == {0, 1, 2}
    assert abs((t == 0).mean() - 1 / 3) < 0.02


def test_pedge_fee_breakeven_and_p_edge_positive():
    assert pe.quadratic_fee(0.5) == pytest.approx(0.0175)
    assert pe.breakeven(0.5) == pytest.approx(0.5175)
    draws = np.array([[0.50, 0.55, 0.60, 0.40], [0.9, 0.9, 0.9, 0.9]])
    be = np.array([0.5175, 0.95])
    assert np.allclose(pe.p_edge_positive(draws, be), [0.5, 0.0])


def test_pedge_binning_edges():
    p = np.array([0.0, 0.59, 0.6, 0.699, 0.7, 0.8, 0.9, 0.949, 0.95, 1.0])
    assert pe.bin_index(p).tolist() == [0, 0, 1, 1, 2, 3, 4, 4, 5, 5]
    assert len(pe.PEDGE_LABELS) == len(pe.PEDGE_EDGES) - 1


def test_bucket_table_and_records_join():
    pred = {
        "schema": "prediction_record_v1",
        "record_id": "pred_1",
        "ticker": "T1",
        "family": "moneyline",
        "reference_probability": 0.40,
        "edge": {
            "yes": {
                "p_edge_positive": 0.92,
                "fee_adjusted_edge": 0.05,
                "fair": 0.5,
                "price": "0.42",
                "fee_per_contract": "0.017052",
            },
            "no": {
                "p_edge_positive": 0.10,
                "fee_adjusted_edge": -0.07,
                "fair": 0.5,
                "price": "0.58",
                "fee_per_contract": "0.017052",
            },
        },
    }
    unsettled = {**pred, "record_id": "pred_2"}
    sett = {
        "schema": "settlement_record_v1",
        "prediction_record_id": "pred_1",
        "outcome": "yes",
        "clv_yes_points": 0.03,
    }
    rows = pe.rows_from_records([pred, unsettled], [sett])
    assert len(rows) == 4
    yes = next(r for r in rows if r["record_id"] == "pred_1" and r["side"] == "yes")
    assert yes["won"] is True and yes["realised"] == pytest.approx(1 - 0.42 - 0.017052)
    assert yes["clv"] == pytest.approx(0.03) and yes["beat_reference"] is True
    no = next(r for r in rows if r["record_id"] == "pred_1" and r["side"] == "no")
    assert (
        no["won"] is False and no["clv"] == pytest.approx(-0.03) and no["beat_reference"] is False
    )
    table = pe.bucket_table(rows)
    assert [t["bucket"] for t in table] == list(pe.PEDGE_LABELS)
    top = table[-2]  # 0.9-0.95
    assert top["n"] == 2 and top["n_settled"] == 1 and top["hit_rate"] == 1.0
    assert top["mean_clv"] == pytest.approx(0.03) and top["share_beating_reference"] == 1.0
    low = table[0]
    assert low["n"] == 2 and low["n_settled"] == 1 and low["hit_rate"] == 0.0
    assert pe.monotonicity(table)["spearman"] is None  # too few populated buckets


def test_proxy_rows_shapes_and_returns():
    rng = np.random.default_rng(6)
    n, S = 30, 50
    draws = rng.dirichlet(np.ones(3) * 5, size=(n, S))
    p3 = draws.mean(axis=1)
    p_mkt = rng.dirichlet(np.ones(3) * 5, size=n)
    odds = 1 / (p_mkt * 0.95)
    y = rng.integers(0, 3, n)
    rows = pe.proxy_rows(
        draws, p3, p_mkt, odds=odds, y=y, meta={"season": np.array(["2020-21"] * n)}
    )
    assert len(rows) == 3 * n
    r = rows[0]
    assert r["fee"] == pytest.approx(pe.quadratic_fee(r["price"]))
    assert r["realised"] == pytest.approx(float(r["won"]) - r["price"] - r["fee"])
    assert 0 <= r["p_edge_positive"] <= 1 and r["season"] == "2020-21"
    tab = pe.bucket_table(rows)
    assert sum(t["n"] for t in tab) == 3 * n


@pytest.mark.skipif(not rc.CACHE_PATH.exists(), reason="recalibration cache not built")
def test_cached_draws_reproduce_walk_forward_interval_width():
    cache = rc.Cache.load(rc.CACHE_PATH)
    n = len(cache)
    assert cache.dev.shape[0] == n and cache.dev.shape[2] == 3
    sub = np.arange(0, n, max(1, n // 300))
    small = rc.Cache(
        **{k: (v[sub] if isinstance(v, np.ndarray) else v) for k, v in cache.__dict__.items()}
    )
    ev = rc.evaluate(small, np.ones(len(sub)), np.zeros(len(sub)))
    width = float((ev.hi - ev.lo).mean())
    assert 0.2 < width < 0.4  # walk_forward_v1 reports 0.2945 for k = 1
    ev_half = rc.evaluate(small, np.full(len(sub), 0.5), np.zeros(len(sub)))
    assert float((ev_half.hi - ev_half.lo).mean()) < 0.6 * width
