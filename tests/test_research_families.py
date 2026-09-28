"""Fast unit tests for the pure helpers behind the research studies (Phases 12/16/17)."""

from __future__ import annotations

import os

import numpy as np
import pytest
from research import wf_common as wf
from research.disagreement import GAP_EDGES
from research.home_bias import fit_logistic, market_implied_rates, predict_logistic
from research.market_families import (
    ah_probs,
    ah_settle_score,
    btts_prob,
    devig_two_way,
    paired_ci_weighted,
    snap_quarter,
    split_line,
    team_total_over,
    weighted_ll,
)

from soccer_edge.model.analytic import outcome_probs, score_matrix, total_over


def point_mass(hg: int, ag: int, g: int = 10) -> np.ndarray:
    m = np.zeros((g + 1, g + 1))
    m[hg, ag] = 1.0
    return m


# ---------------------------------------------------------------- Asian handicap settlement
def test_snap_quarter_handles_football_data_rounding():
    assert snap_quarter(-0.3) == -0.25
    assert snap_quarter(-0.8) == -0.75
    assert snap_quarter(1.3) == 1.25
    assert snap_quarter(0.5) == 0.5
    assert snap_quarter(0.0) == 0.0


def test_split_line_quarter_vs_whole():
    assert split_line(-0.25) == [-0.5, 0.0]
    assert split_line(0.75) == [0.5, 1.0]
    assert split_line(-1.0) == [-1.0]
    assert split_line(0.5) == [0.5]
    assert split_line(-0.3) == [-0.5, 0.0]


@pytest.mark.parametrize(
    ("hg", "ag", "size", "expected"),
    [
        (1, 0, -0.5, (1.0, 0.0, 0.0)),  # home -0.5 wins by one
        (1, 0, -1.0, (0.0, 1.0, 0.0)),  # exact push
        (1, 0, -1.5, (0.0, 0.0, 1.0)),  # loss
        (1, 0, -1.25, (0.0, 0.5, 0.5)),  # half push / half loss
        (1, 0, -0.75, (0.5, 0.5, 0.0)),  # half win / half push
        (0, 0, 0.25, (0.5, 0.5, 0.0)),  # home +0.25, draw: half win half push
        (0, 0, -0.25, (0.0, 0.5, 0.5)),  # home -0.25, draw: half push half loss
        (0, 2, 1.0, (0.0, 0.0, 1.0)),  # +1 not enough
        (0, 1, 1.0, (0.0, 1.0, 0.0)),  # +1 push
        (2, 3, 1.3, (0.5, 0.5, 0.0)),  # +1.25 (stored as 1.3) lose by one: half win half push
    ],
)
def test_ah_settle_score(hg, ag, size, expected):
    assert ah_settle_score(hg, ag, size) == pytest.approx(expected)
    # settlement from a point-mass score matrix must agree with the scalar settlement
    assert ah_probs(point_mass(hg, ag), size) == pytest.approx(expected)


def test_ah_probs_sum_to_one_and_match_enumeration():
    m = score_matrix(1.6, 1.1, -0.05)
    for size in (-1.75, -1.25, -1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0):
        w, p, lo = ah_probs(m, size)
        assert w + p + lo == pytest.approx(1.0, abs=1e-9)
        # brute-force enumeration over the grid
        ew = ep = el = 0.0
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                a, b, c = ah_settle_score(i, j, size)
                ew += m[i, j] * a
                ep += m[i, j] * b
                el += m[i, j] * c
        assert (w, p, lo) == pytest.approx((ew, ep, el), abs=1e-12)
    # a level line (0) never pushes on a decided match and pushes exactly on draws
    w0, p0, l0 = ah_probs(m, 0.0)
    op = outcome_probs(m)
    assert (w0, p0, l0) == pytest.approx((op["home"], op["draw"], op["away"]), abs=1e-12)


def test_ah_half_line_equals_1x2_complement():
    m = score_matrix(1.3, 1.3, 0.0)
    w, p, lo = ah_probs(m, -0.5)  # home must win outright
    op = outcome_probs(m)
    assert p == 0.0
    assert w == pytest.approx(op["home"])
    assert lo == pytest.approx(op["draw"] + op["away"])


# ---------------------------------------------------------------- devig / matrix helpers
def test_devig_two_way_proportional():
    assert devig_two_way(2.0, 2.0) == pytest.approx(0.5)
    p = devig_two_way(1.9, 1.9)
    assert p == pytest.approx(0.5)
    p1 = devig_two_way(1.5, 2.6)
    assert p1 == pytest.approx((1 / 1.5) / (1 / 1.5 + 1 / 2.6))
    assert p1 + devig_two_way(2.6, 1.5) == pytest.approx(1.0)


def test_btts_and_team_totals_from_matrix():
    m = score_matrix(1.4, 1.2, 0.0)
    ph0 = m[0, :].sum()
    pa0 = m[:, 0].sum()
    assert btts_prob(m) == pytest.approx(1 - ph0 - pa0 + m[0, 0])
    assert team_total_over(m, "home", 0.5) == pytest.approx(1 - ph0)
    assert team_total_over(m, "away", 1.5) == pytest.approx(m[:, 2:].sum())
    assert total_over(m, 2.5) == pytest.approx(wf.total_over_matrix(m, 2.5))


def test_vectorised_score_matrices_match_analytic():
    lams = np.array([0.8, 1.5, 2.2])
    mus = np.array([1.1, 0.9, 1.7])
    rhos = np.array([-0.1, 0.0, 0.12])
    ms = wf.score_matrices(lams, mus, rhos)
    for k in range(3):
        assert np.abs(ms[k] - score_matrix(lams[k], mus[k], rhos[k])).max() < 1e-12
    op = wf.outcome_probs_batch(ms)
    ref = outcome_probs(score_matrix(1.5, 0.9, 0.0))
    assert op[1] == pytest.approx([ref["home"], ref["draw"], ref["away"]])


# ---------------------------------------------------------------- binning / weighting
def test_bin_labels_and_terciles():
    x = np.array([-0.2, -0.12, -0.07, 0.0, 0.05, 0.12, 0.2])
    lab = wf.bin_labels(x, GAP_EDGES)
    assert list(lab) == [
        "<-0.15",
        "[-0.15,-0.10)",
        "[-0.10,-0.05)",
        "[-0.05,+0.05)",
        "[+0.05,+0.10)",
        "[+0.10,+0.15)",
        ">=+0.15",
    ]
    t, cuts = wf.tercile_labels(np.arange(9, dtype=float))
    assert list(t) == ["low"] * 3 + ["mid"] * 3 + ["high"] * 3
    assert len(cuts) == 2 and cuts[0] < cuts[1]


def test_weighted_metrics_and_ci():
    p = np.array([0.7, 0.4, 0.9])
    y = np.array([1.0, 0.0, 1.0])
    w = np.array([1.0, 0.5, 0.0])
    ll = weighted_ll(p, y, w)
    assert ll == pytest.approx((-np.log(0.7) * 1 + -np.log(0.6) * 0.5) / 1.5)
    ci = paired_ci_weighted(np.array([0.1, -0.1, 5.0]), w, n_boot=200)
    assert ci["mean"] == pytest.approx((0.1 - 0.05) / 1.5, abs=1e-5)
    assert ci["ci95"][0] <= ci["mean"] <= ci["ci95"][1]
    # ECE with weights ignores zero-weight rows
    assert wf.ece(p, y, w=w) == pytest.approx(wf.ece(p[:2], y[:2], w=w[:2]))


# ---------------------------------------------------------------- inversion / calibration
def test_market_implied_rates_round_trip():
    lam, mu, rho = 1.55, 1.05, -0.06
    m = score_matrix(lam, mu, rho)
    op = outcome_probs(m)
    p3 = np.array([op["home"], op["draw"], op["away"]])
    lam_hat, mu_hat = market_implied_rates(p3, total_over(m, 2.5), rho)
    assert (lam_hat, mu_hat) == pytest.approx((lam, mu), abs=1e-4)


def test_fit_logistic_recovers_slope():
    rng = np.random.default_rng(1)
    x = rng.normal(0, 1.5, 4000)
    p = 1 / (1 + np.exp(-(0.3 + 0.8 * x)))
    y = (rng.uniform(size=4000) < p).astype(float)
    b = fit_logistic(x[:, None], y)
    assert b[0] == pytest.approx(0.3, abs=0.15)
    assert b[1] == pytest.approx(0.8, abs=0.15)
    assert predict_logistic(b, np.array([[0.0]]))[0] == pytest.approx(1 / (1 + np.exp(-b[0])))


def test_variant_configs_do_not_touch_defaults():
    from soccer_edge.model.strength import StrengthConfig

    v = wf.strength_for("dc_laplace_v1.decay003")
    assert v.decay_per_day == 0.003 and v.version == "dc_laplace_v1.decay003"
    assert StrengthConfig().decay_per_day == 0.0065
    assert wf.strength_for("dc_laplace_v1") == StrengthConfig()


# ---------------------------------------------------------------- integration (cache-backed)
def test_cached_base_table_is_aligned_and_sane():
    """Reads the cached walk-forward table if a study has already been run; skips otherwise."""
    if os.environ.get("CI") or not wf.CACHE_DIR.exists():
        pytest.skip("no research cache")
    files = sorted(wf.CACHE_DIR.glob("wf_dc_laplace_v1_*.npz"))
    if not files:
        pytest.skip("base walk-forward cache not built")
    with np.load(files[-1], allow_pickle=False) as z:
        if "mat" not in z.files:
            pytest.skip("cached table was built without score matrices (keep_matrix=False)")
        T = {k: z[k] for k in ("season", "p_data", "p_mkt", "y", "mat", "ah_size")}
    am = wf.aligned_mask(T)
    assert int(am.sum()) == 12248  # identical aligned sample to walk_forward_v1
    assert np.allclose(T["p_data"].sum(axis=1), 1.0, atol=1e-6)
    assert np.allclose(T["p_mkt"].sum(axis=1), 1.0, atol=1e-6)
    assert np.allclose(T["mat"].sum(axis=(1, 2)), 1.0, atol=1e-4)
