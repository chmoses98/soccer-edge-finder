"""worlds_v2 (remediation phase 15; audit section F): posterior scale, frozen v1, structural term study,
interval coverage report, and the recalibration study's v2 deviations."""

from __future__ import annotations

from datetime import UTC, date, datetime

import numpy as np
from research.recalibration import deviations_for
from research.sigma_struct import edge_v2_points, family_dispersion, from_table

from soccer_edge.evaluation.uncertainty import coverage_report
from soccer_edge.model.context import MatchContext
from soccer_edge.model.strength_v2 import DixonColesFitterV2
from soccer_edge.model.worlds import (
    WORLDS_V1,
    WORLDS_V2,
    WorldConfig,
    WorldGenerator,
    world_config_for,
    worlds_v2_config,
)
from tests.conftest import synthetic_league


def _ctx(home, away):
    return MatchContext(
        fixture_id="f1",
        competition_id="eng.premier_league",
        home_team_id=home,
        away_team_id=away,
        kickoff_utc=datetime(2026, 6, 2, 15, tzinfo=UTC),
    )


def test_posterior_scale_scales_log_rate_sd_exactly(synthetic_posterior):
    post, teams, _, _ = synthetic_posterior
    ctx = _ctx(teams[0], teams[1])
    sds = {}
    for k in (1.0, 0.5, 0.0):
        cfg = WorldConfig(sigma_model_log_rate=0.0, sigma_environment=0.0, posterior_sd_scale=k)
        ws = WorldGenerator(post, cfg).generate(ctx, 4000, np.random.default_rng(7))
        sds[k] = np.log(ws.lam_home).std()
    assert sds[0.0] < 1e-12  # every world at the posterior mean
    assert abs(sds[0.5] / sds[1.0] - 0.5) < 0.02  # log rates are linear in the parameters


def test_worlds_v1_is_frozen_and_v2_drops_the_hand_set_inflation():
    v1 = world_config_for(WORLDS_V1)
    assert v1 == WorldConfig() and v1.posterior_sd_scale == 1.0 and v1.sigma_model_log_rate == 0.05
    v2 = world_config_for(WORLDS_V2)
    assert v2.version == WORLDS_V2 and v2.sigma_model_log_rate == 0.0
    assert worlds_v2_config(0.8).posterior_sd_scale == 0.8
    # the version and scale are part of the world components -> part of the archived record
    teams, _, _, rows = synthetic_league(seed=3)
    post = DixonColesFitterV2().fit(rows, as_of=date(2026, 6, 1))
    ws = WorldGenerator(post, v2).generate(_ctx(teams[0], teams[1]), 50, np.random.default_rng(1))
    assert ws.components["worlds_version"] == WORLDS_V2
    assert ws.components["posterior_sd_scale"] == v2.posterior_sd_scale


def test_recalibration_deviations_include_the_v2_intercept():
    teams, _, _, rows = synthetic_league(seed=4)
    post = DixonColesFitterV2().fit(rows, as_of=date(2026, 6, 1))
    rng = np.random.default_rng(0)
    dth = post.sample(200, rng) - post.mean
    dev = deviations_for(post, dth, teams[0], teams[1])
    lam, mu, _ = post.rates_for(post.mean + dth, teams[0], teams[1])
    lam0, mu0 = post.expected_goals(teams[0], teams[1])
    assert np.allclose(np.log(lam) - np.log(lam0), dev[:, 0], atol=1e-9)
    assert np.allclose(np.log(mu) - np.log(mu0), dev[:, 1], atol=1e-9)


def test_sigma_struct_recovers_a_known_logit_dispersion():
    rng = np.random.default_rng(5)
    n = 6000
    seasons = np.array(["2019-20", "2020-21", "2021-22"])[rng.integers(0, 3, n)]
    p_ref = rng.uniform(0.15, 0.7, n)
    lg = np.log(p_ref / (1 - p_ref)) + rng.normal(0, 0.30, n)
    p_model = 1 / (1 + np.exp(-lg))
    d = family_dispersion(p_model, p_ref, seasons)
    assert d["status"] == "ESTIMATED" and abs(d["sd_logit_pooled"] - 0.30) < 0.02
    assert set(d["by_season"]) == {"2019-20", "2020-21", "2021-22"}
    d2 = family_dispersion(p_model[:20], p_ref[:20], seasons[:20])
    assert d2["status"] == "INSUFFICIENT"
    # a walk-forward table with the 1X2 columns and an absent totals reference
    p3 = rng.dirichlet([2, 1.5, 1.5], n)
    table = {
        "season": seasons,
        "p_data": p3,
        "p_mkt": np.clip(p3 + rng.normal(0, 0.03, p3.shape), 0.02, 0.96),
        "p_data_o25": rng.uniform(0.3, 0.7, n),
        "p_mkt_o25": np.full(n, np.nan),
    }
    fams = from_table(table)
    assert fams["match_result_3way"]["status"] == "ESTIMATED"
    assert fams["total_goals"]["status"] == "INSUFFICIENT"
    pts = edge_v2_points(fams)
    assert set(pts) == {"match_result_3way"} and 0.0 < pts["match_result_3way"] < 0.2


WIDTH_IN_BAND = 0.05  # in band for seed 11 (see the comment in the test)


def _settled(n, *, width: float, rng, fam="match_result_3way", hz="T-60"):
    """Calibrated fair probabilities with a symmetric interval of the given half-width."""
    rows = []
    for _ in range(n):
        p = rng.uniform(0.2, 0.8)
        y = rng.random() < p
        rows.append(
            {
                "outcome": "yes" if y else "no",
                "model_family": "mf",
                "worlds_version": "worlds_v2",
                "family": fam,
                "horizon": hz,
                "fair_probability_mean": p,
                "fair_probability_low": max(0.0, p - width),
                "fair_probability_high": min(1.0, p + width),
                "entry_yes_mid": min(0.99, max(0.01, p + rng.normal(0, 0.03))),
            }
        )
    return rows


def test_coverage_report_flags_overconfident_cells_and_small_samples():
    # the grouped estimator compares each probability bin's realised rate with the bin's mean interval,
    # so an interval far wider than the bin's sampling error reads as too wide and a hairline interval
    # as too narrow; a half-width near 1.28 x the bin sampling error lands in the band
    rng = np.random.default_rng(11)
    recs = _settled(600, width=WIDTH_IN_BAND, rng=rng)
    recs += _settled(600, width=0.02, rng=rng, fam="total_goals")
    recs += _settled(600, width=0.25, rng=rng, fam="btts")
    recs += _settled(10, width=0.1, rng=rng, fam="handicap")
    recs.append({"outcome": "void", "model_family": "mf", "family": "handicap", "horizon": "T-60"})
    rep = coverage_report(recs, as_of=datetime(2026, 10, 1, tzinfo=UTC))
    cells = {(c["market_family"], c["horizon"]): c for c in rep["cells"]}
    assert cells[("match_result_3way", "any")]["verdict"] == "WITHIN_BAND"
    assert cells[("total_goals", "any")]["verdict"] == "OUTSIDE_BAND"
    assert cells[("total_goals", "any")]["direction"] == "too_narrow"
    assert cells[("total_goals", "any")]["grouped_coverage_80"] < 0.6
    assert cells[("btts", "any")]["direction"] == "too_wide"
    assert cells[("handicap", "any")]["verdict"] == "INSUFFICIENT"
    assert cells[("handicap", "any")]["n_settled"] == 10  # the void record is excluded
    assert rep["verdict_counts"] == {"WITHIN_BAND": 1, "OUTSIDE_BAND": 2, "INSUFFICIENT": 1}
    assert cells[("match_result_3way", "T-60")]["market_mid_inside_share"] is not None
