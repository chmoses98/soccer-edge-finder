"""Synthetic two-league world for the hierarchical multi-league model (RESEARCH_ONLY)."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from soccer_edge.model.analytic import outcome_probs, score_matrix
from soccer_edge.model.multi_league import (
    LeagueMatchRow,
    MultiLeagueConfig,
    MultiLeagueFitter,
    fit_elo_mapping,
    integrated_outcome_probs,
)

AS_OF = date(2026, 6, 1)


def _world(
    seed: int = 3,
    n_per_league: int = 12,
    rounds: int = 22,
    gap: float = 0.35,
    n_cross: int = 60,
    start: date = date(2025, 8, 1),
):
    """Two closed leagues A (strong) and B (weak): true absolute team totals differ by ``gap``
    on the log-rate scale. Optionally ``n_cross`` neutral cross-league matches."""
    rng = np.random.default_rng(seed)
    teams = {
        "A": [f"a{i:02d}" for i in range(n_per_league)],
        "B": [f"b{i:02d}" for i in range(n_per_league)],
    }
    att, dfn = {}, {}
    for lg, off in (("A", gap / 2), ("B", -gap / 2)):
        for t in teams[lg]:
            att[t] = off + rng.normal(0, 0.2)
            dfn[t] = off + rng.normal(0, 0.2)
    rows = []

    def play(h, a, d, league, neutral=False):
        lam = np.exp(att[h] - dfn[a] + (0.0 if neutral else 0.25))
        mu = np.exp(att[a] - dfn[h])
        rows.append(
            LeagueMatchRow(d, h, a, int(rng.poisson(lam)), int(rng.poisson(mu)), league, neutral)
        )

    for lg in ("A", "B"):
        for rnd in range(rounds):
            order = list(range(n_per_league))
            rng.shuffle(order)
            for i in range(0, n_per_league, 2):
                play(
                    teams[lg][order[i]],
                    teams[lg][order[i + 1]],
                    start + timedelta(days=7 * rnd),
                    lg,
                )
    for c in range(n_cross):
        h = teams["A"][rng.integers(n_per_league)]
        a = teams["B"][rng.integers(n_per_league)]
        if c % 2:
            h, a = a, h
        play(h, a, start + timedelta(days=3 + 7 * (c % rounds)), None)
    return teams, att, dfn, rows


def test_recovers_known_offset_with_cross_play():
    _, att, dfn, rows = _world(gap=0.35, n_cross=80)
    post = MultiLeagueFitter().fit(rows, as_of=AS_OF)
    diff, sd = post.offset_difference("A", "B")
    assert abs(diff - 0.35) < 0.15, (diff, sd)
    # posterior sd is finite and well inside the prior (sqrt(2) * 0.30 for a difference), and the
    # truth is within ~2 sd (a two-league world with 12 teams each: the league mean itself carries
    # ~0.35/sqrt(24) of hierarchical uncertainty per league on top of the cross-play evidence)
    assert sd < 0.25
    assert abs(diff - 0.35) / sd < 2.5
    # team totals are recovered on an absolute scale across both leagues
    est = np.array(
        [post.mean[post.idx_attack(t)] + post.mean[post.idx_defence(t)] for t in post.teams]
    )
    tru = np.array([att[t] + dfn[t] for t in post.teams])
    assert np.corrcoef(est, tru)[0, 1] > 0.85


def test_offset_uncertainty_wider_without_cross_play():
    _, _, _, rows_cross = _world(gap=0.35, n_cross=80)
    _, _, _, rows_closed = _world(gap=0.35, n_cross=0)
    cfg = MultiLeagueConfig()
    p_cross = MultiLeagueFitter(cfg).fit(rows_cross, as_of=AS_OF)
    p_closed = MultiLeagueFitter(cfg).fit(rows_closed, as_of=AS_OF)
    _, sd_cross = p_cross.offset_difference("A", "B")
    d_closed, sd_closed = p_closed.offset_difference("A", "B")
    assert sd_closed > 2 * sd_cross
    # with no evidence the offsets stay at the prior: near 0, sd near the prior sd
    assert abs(d_closed) < 0.1
    for lg in ("A", "B"):
        assert 0.15 < p_closed.league_offsets()[lg]["sd"] <= cfg.prior_sd_league + 0.05
        assert p_closed.cross_play_by_league[lg] == 0.0
        assert p_cross.cross_play_by_league[lg] > 0


def test_promoted_team_carries_strength_and_identifies_gap():
    """A team plays half a season in B, then moves to A. With no other cross-play, its own
    continuity is the only evidence of the gap, and the gap should still be recovered."""
    rng = np.random.default_rng(7)
    gap = 0.4
    n = 12
    teams_a = [f"a{i:02d}" for i in range(n)]
    teams_b = [f"b{i:02d}" for i in range(n)]
    att = {t: gap / 2 + rng.normal(0, 0.15) for t in teams_a}
    dfn = {t: gap / 2 + rng.normal(0, 0.15) for t in teams_a}
    att.update({t: -gap / 2 + rng.normal(0, 0.15) for t in teams_b})
    dfn.update({t: -gap / 2 + rng.normal(0, 0.15) for t in teams_b})
    mover = "b00"  # a good B side: true strength sits at the A mean
    att[mover] = gap / 2
    dfn[mover] = gap / 2
    rows = []
    start = date(2025, 8, 1)

    def play(h, a, d, league):
        lam = np.exp(att[h] - dfn[a] + 0.25)
        mu = np.exp(att[a] - dfn[h])
        rows.append(LeagueMatchRow(d, h, a, int(rng.poisson(lam)), int(rng.poisson(mu)), league))

    # phase 1 (weeks 0-15): mover in B, A closed
    for rnd in range(16):
        d = start + timedelta(days=7 * rnd)
        for lg, ts in (("A", teams_a), ("B", teams_b)):
            order = list(range(n))
            rng.shuffle(order)
            for i in range(0, n, 2):
                play(ts[order[i]], ts[order[i + 1]], d, lg)
    # phase 2 (weeks 16-31): mover joins A (A has 13 teams; one sits out each round)
    a2 = teams_a + [mover]
    b2 = [t for t in teams_b if t != mover]
    for rnd in range(16, 32):
        d = start + timedelta(days=7 * rnd)
        order = list(range(len(a2)))
        rng.shuffle(order)
        for i in range(0, len(a2) - 1, 2):
            play(a2[order[i]], a2[order[i + 1]], d, "A")
        order = list(range(len(b2)))
        rng.shuffle(order)
        for i in range(0, len(b2) - 1, 2):
            play(b2[order[i]], b2[order[i + 1]], d, "B")
    post = MultiLeagueFitter().fit(rows, as_of=AS_OF)
    assert post.league_of[mover] == "A"
    diff, sd = post.offset_difference("A", "B")
    assert diff > 0.15, (diff, sd)  # sign and a good part of the magnitude recovered
    assert sd < MultiLeagueConfig().prior_sd_league  # tighter than the prior: evidence used
    # the mover is a single parameter vector: one team, one strength, across both leagues
    assert post.teams.count(mover) == 1
    total = post.mean[post.idx_attack(mover)] + post.mean[post.idx_defence(mover)]
    b_mean = np.mean([post.mean[post.idx_attack(t)] + post.mean[post.idx_defence(t)] for t in b2])
    assert total > b_mean + 0.2


def test_neutral_flag_and_prediction_interface():
    _, _, _, rows = _world(gap=0.3, n_cross=40)
    post = MultiLeagueFitter().fit(rows, as_of=AS_OF)
    lam_h, mu_h = post.expected_goals("a00", "b00")
    lam_n, mu_n = post.expected_goals("a00", "b00", neutral=True)
    assert lam_h > lam_n and mu_h == pytest.approx(mu_n)
    rng = np.random.default_rng(0)
    lam, mu, rho = post.sample_rates(200, rng, "a00", "b00")
    p, over = integrated_outcome_probs(lam, mu, rho)
    assert p.sum() == pytest.approx(1.0, abs=1e-9)
    assert 0 < over < 1
    # vectorised integrator agrees with the analytic score matrix at a point
    m = score_matrix(1.4, 1.1, -0.05)
    op = outcome_probs(m)
    p1, _ = integrated_outcome_probs(np.array([1.4]), np.array([1.1]), np.array([-0.05]))
    assert p1[0] == pytest.approx(op["home"], abs=1e-9)
    assert p1[1] == pytest.approx(op["draw"], abs=1e-9)
    assert len(post.param_hash()) > 10
    assert set(post.league_offsets()) == {"A", "B"}


def test_elo_mapping_and_elo_prior_variant():
    rng = np.random.default_rng(11)
    n = 4000
    gamma_true = 0.0018
    he = rng.normal(1700, 100, n)
    ae = rng.normal(1700, 100, n)
    lam = np.exp(0.1 + 0.25 + gamma_true * (he - ae))
    mu = np.exp(0.1 - gamma_true * (he - ae))
    hg, ag = rng.poisson(lam), rng.poisson(mu)
    fit = fit_elo_mapping(he, ae, hg, ag)
    assert fit["poisson_gamma_log_rate_per_elo_point"] == pytest.approx(gamma_true, abs=4e-4)
    assert fit["ols_goal_diff_per_elo_point"] > 0
    # Elo prior variant: a brand-new team with a high Elo gets a higher prior mean
    _, _, _, rows = _world(gap=0.3, n_cross=40)
    elo = {t: 1600.0 for r in rows for t in (r.home, r.away)}
    newcomer = LeagueMatchRow(date(2026, 5, 20), "a_new", "a01", 1, 1, "A")
    rows = rows + [newcomer]
    cfg = MultiLeagueConfig(elo_gamma=0.002, version="multi_league_v1_elo_prior")
    post_hi = MultiLeagueFitter(cfg).fit(rows, as_of=AS_OF, elo={**elo, "a_new": 1900.0})
    post_lo = MultiLeagueFitter(cfg).fit(rows, as_of=AS_OF, elo={**elo, "a_new": 1300.0})
    assert (
        post_hi.team_summary("a_new")["total_mean"]
        > post_lo.team_summary("a_new")["total_mean"] + 0.3
    )
