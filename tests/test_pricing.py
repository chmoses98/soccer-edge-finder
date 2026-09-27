from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import numpy as np
import pytest

from soccer_edge.core.errors import CoherenceError
from soccer_edge.kalshi.executable import ExecutableQuote
from soccer_edge.kalshi.fees import FeeRegime
from soccer_edge.kalshi.schemas import RawMarket
from soccer_edge.kalshi.taxonomy import MarketFamily, Period, classify
from soccer_edge.model.context import MatchContext
from soccer_edge.model.worlds import WorldGenerator
from soccer_edge.pricing.coherence import assert_coherent, audit
from soccer_edge.pricing.edge import EdgeConfig, assess
from soccer_edge.pricing.expression import Candidate, payoff_vector, reduce_expressions
from soccer_edge.pricing.portfolio import portfolio_stats
from soccer_edge.pricing.pricer import PricedProbability, price
from soccer_edge.pricing.semantics import Semantics, UnsupportedSemantics, resolve_semantics
from soccer_edge.sim.engine import SimConfig, simulate


@pytest.fixture(scope="module")
def sim(synthetic_posterior):
    post = synthetic_posterior[0]
    ctx = MatchContext("fx", "c", "t00", "t01", datetime(2026, 10, 10, 14, tzinfo=UTC))
    ws = WorldGenerator(post).generate(ctx, 300, np.random.default_rng(3))
    return simulate(ws, ctx, SimConfig(draws_per_world=100), seed=5)


def _sem(fam, side=None, line=None, period=Period.REGULATION, k=None, tk="T"):
    return Semantics(tk, fam, period, side, Decimal(str(line)) if line is not None else None, k)


def test_logical_implications(sim):
    p = {
        "o25": price(_sem(MarketFamily.TOTAL_GOALS, line=2.5), sim).fair_mean,
        "o35": price(_sem(MarketFamily.TOTAL_GOALS, line=3.5), sim).fair_mean,
        "h15": price(_sem(MarketFamily.TEAM_TOTAL, "home", 1.5), sim).fair_mean,
        "h25": price(_sem(MarketFamily.TEAM_TOTAL, "home", 2.5), sim).fair_mean,
        "hw": price(_sem(MarketFamily.MATCH_RESULT_3WAY, "home"), sim).fair_mean,
        "dr": price(_sem(MarketFamily.MATCH_RESULT_3WAY, "draw"), sim).fair_mean,
        "aw": price(_sem(MarketFamily.MATCH_RESULT_3WAY, "away"), sim).fair_mean,
        "hcap05": price(_sem(MarketFamily.HANDICAP, "home", 0.5), sim).fair_mean,
        "hcap15": price(_sem(MarketFamily.HANDICAP, "home", 1.5), sim).fair_mean,
        "btts": price(_sem(MarketFamily.BTTS), sim).fair_mean,
        "cs_home": price(_sem(MarketFamily.CLEAN_SHEET, "home"), sim).fair_mean,
        "a05": price(_sem(MarketFamily.TEAM_TOTAL, "away", 0.5), sim).fair_mean,
        "h1o05": price(
            _sem(MarketFamily.TOTAL_GOALS, line=0.5, period=Period.FIRST_HALF), sim
        ).fair_mean,
        "o05": price(_sem(MarketFamily.TOTAL_GOALS, line=0.5), sim).fair_mean,
    }
    assert p["o35"] <= p["o25"]
    assert p["h25"] <= p["h15"]
    assert abs(p["hw"] + p["dr"] + p["aw"] - 1) < 1e-12
    assert abs(p["hcap05"] - p["hw"]) < 1e-12  # home -0.5 == home win
    assert p["hcap15"] <= p["hcap05"]
    assert abs(p["cs_home"] + p["a05"] - 1) < 1e-12  # clean sheet == away under 0.5
    assert p["h1o05"] <= p["o05"]
    assert p["btts"] <= min(1 - p["cs_home"], p["h15"] + (1 - p["h15"]))


def test_exact_scores_reconcile_with_results(sim):
    s = sim.compact_summary(max_goals=8)
    grid = np.array(s["score_grid"])
    assert abs(np.tril(grid, -1).sum() - s["p_home"]) < 1e-3  # 5-dp rounding + >8 goal cap
    assert abs(np.trace(grid) - s["p_draw"]) < 1e-3


def test_first_half_contracts_use_ht_arrays(sim):
    fh = price(
        _sem(MarketFamily.MATCH_RESULT_3WAY, "draw", period=Period.FIRST_HALF), sim
    ).fair_mean
    ft = price(_sem(MarketFamily.MATCH_RESULT_3WAY, "draw"), sim).fair_mean
    assert fh > ft  # HT draws are more common than FT draws


def test_interval_contains_mean_and_widens_with_uncertainty(sim):
    pp = price(_sem(MarketFamily.TOTAL_GOALS, line=2.5), sim)
    assert pp.p_low <= pp.fair_mean <= pp.p_high
    assert pp.p_high - pp.p_low > 2 * pp.mc_se


def test_player_goal_bounded_by_participation(synthetic_posterior):
    from soccer_edge.model.context import LineupState, PlayerAvailability

    post = synthetic_posterior[0]
    pl = (
        PlayerAvailability("p1", "t00", 0.5, 0.5, importance=0.1, goal_share_if_play=0.4),
        PlayerAvailability("p2", "t00", 1.0, 1.0, importance=0.1, goal_share_if_play=0.6),
    )
    ctx = MatchContext(
        "fx", "c", "t00", "t01", None, lineup_state=LineupState.PROJECTED, home_players=pl
    )
    ws = WorldGenerator(post).generate(ctx, 400, np.random.default_rng(1))
    out = simulate(ws, ctx, SimConfig(draws_per_world=50), seed=1)
    sem = Semantics(
        "T", MarketFamily.PLAYER_GOALS, Period.REGULATION, "home", None, 1, player_slot=("home", 0)
    )
    p = price(sem, out).fair_mean
    p_play = out.home_players_on[:, 0].mean()
    assert p <= p_play + 1e-9


def test_semantics_resolution_refuses_unresolved_side():
    m = RawMarket.from_api(
        {
            "ticker": "KXEPLSPREAD-26OCT10LEEARS-ARS2",
            "event_ticker": "x",
            "title": "Arsenal wins by more than 1.5?",
            "floor_strike": "1.5",
        }
    )
    spec = classify(m)
    with pytest.raises(UnsupportedSemantics):
        resolve_semantics(spec, side_is_home=None)
    sem = resolve_semantics(spec, side_is_home=True)
    assert sem.side == "home" and sem.line == Decimal("1.5")


def test_coherence_audit_catches_broken_ladder():
    bad = [
        (
            _sem(MarketFamily.TOTAL_GOALS, line=2.5, tk="A"),
            PricedProbability(
                "A", 0.5, 0.5, 0.4, 0.6, 0.8, 0.05, 0.001, 10, 100, 100, np.full(10, 0.5)
            ),
        ),
        (
            _sem(MarketFamily.TOTAL_GOALS, line=3.5, tk="B"),
            PricedProbability(
                "B", 0.6, 0.6, 0.5, 0.7, 0.8, 0.05, 0.001, 10, 100, 100, np.full(10, 0.6)
            ),
        ),
    ]
    assert audit(bad)
    with pytest.raises(CoherenceError):
        assert_coherent(bad)


def test_edge_assessment_and_bet_up_to():
    pw = np.clip(np.random.default_rng(0).normal(0.60, 0.03, 500), 0, 1)
    p = PricedProbability(
        "T",
        float(pw.mean()),
        float(np.median(pw)),
        float(np.quantile(pw, 0.1)),
        float(np.quantile(pw, 0.9)),
        0.8,
        float(pw.std()),
        0.001,
        500,
        50000,
        50000,
        pw,
    )
    r = FeeRegime("quadratic")
    good = assess(
        p,
        ExecutableQuote("T", "yes", Decimal("0.50"), Decimal(100), "top_of_book"),
        r,
        EdgeConfig(),
    )
    assert good.robust_positive_ev and good.p_edge_positive > 0.95 and good.fee_adjusted_edge > 0.05
    assert good.bet_up_to_price is not None and Decimal("0.50") < good.bet_up_to_price < Decimal(
        "0.60"
    )
    thin = assess(
        p,
        ExecutableQuote("T", "yes", Decimal("0.59"), Decimal(100), "top_of_book"),
        r,
        EdgeConfig(),
    )
    assert not thin.robust_positive_ev and thin.reasons
    no_side = assess(
        p, ExecutableQuote("T", "no", Decimal("0.42"), Decimal(100), "top_of_book"), r, EdgeConfig()
    )
    assert not no_side.robust_positive_ev and no_side.fair == pytest.approx(1 - p.fair_mean)


def test_p_edge_positive_monotone_in_price():
    pw = np.clip(np.random.default_rng(0).normal(0.55, 0.05, 500), 0, 1)
    p = PricedProbability(
        "T", float(pw.mean()), 0.55, 0.45, 0.65, 0.8, 0.05, 0.001, 500, 50000, 50000, pw
    )
    r = FeeRegime("quadratic")
    vals = [
        assess(
            p, ExecutableQuote("T", "yes", Decimal(c) / 100, Decimal(1), "top_of_book"), r
        ).p_edge_positive
        for c in (40, 45, 50, 55, 60)
    ]
    assert all(a >= b for a, b in zip(vals, vals[1:]))


def test_expression_reducer_collapses_correlated(sim):
    r = FeeRegime("quadratic")
    sems = [
        _sem(MarketFamily.MATCH_RESULT_3WAY, "home", tk="HW"),
        _sem(MarketFamily.HANDICAP, "home", 0.5, tk="H05"),
        _sem(MarketFamily.TOTAL_GOALS, line=2.5, tk="O25"),
    ]
    cands = []
    for s in sems:
        p = price(s, sim)
        q = ExecutableQuote(
            s.ticker,
            "yes",
            Decimal(str(round(max(0.05, p.fair_mean - 0.15), 2))),
            Decimal(100),
            "top_of_book",
        )
        a = assess(p, q, r, EdgeConfig())
        cands.append(
            Candidate(
                "fx",
                a,
                payoff_vector(s.settle(sim), "yes", float(q.price), float(a.fee_per_contract)),
            )
        )
    res = reduce_expressions(cands)
    kept = {c.assessment.ticker for c in res.kept}
    assert len(kept) == 2 and len({"HW", "H05"} & kept) == 1  # HW and H05 are identical exposure
    assert "O25" in kept


def test_portfolio_stats_from_shared_draws(sim):
    a = payoff_vector(_sem(MarketFamily.MATCH_RESULT_3WAY, "home").settle(sim), "yes", 0.4, 0.01)
    b = payoff_vector(_sem(MarketFamily.TEAM_TOTAL, "home", 1.5).settle(sim), "yes", 0.4, 0.01)
    c = payoff_vector(_sem(MarketFamily.MATCH_RESULT_3WAY, "away").settle(sim), "yes", 0.3, 0.01)
    st = portfolio_stats(["hw", "ht", "aw"], [a, b, c])
    assert st.correlation[0, 1] > 0.3 and st.correlation[0, 2] < 0
    assert st.to_json()["staking"].startswith("DISABLED")


def test_exact_score_semantics_and_orientation(sim):
    from soccer_edge.kalshi.schemas import RawMarket

    # leg LEO0JUA0 with event code LEOJUA (home first): Leon 0 - Juarez 0
    spec = classify(
        RawMarket.from_api(
            {
                "ticker": "KXLIGAMXSCORE-26SEP27LEOJUA-LEO0JUA0",
                "event_ticker": "x",
                "title": "Final score Draw 0-0?",
            }
        )
    )
    sem = resolve_semantics(spec, side_is_home=True)
    p00 = price(sem, sim).fair_mean
    grid = np.array(sim.compact_summary()["score_grid"])
    assert abs(p00 - grid[0, 0]) < 1e-3
    # 2-1 to the team named first, which is the AWAY side here -> home 1, away 2
    spec2 = classify(
        RawMarket.from_api(
            {
                "ticker": "KXLIGAMXSCORE-26SEP27LEOJUA-JUA2LEO1",
                "event_ticker": "x",
                "title": "Final score 2-1?",
            }
        )
    )
    sem2 = resolve_semantics(spec2, side_is_home=False)
    assert abs(price(sem2, sim).fair_mean - grid[1, 2]) < 1e-3
    # all exact scores on the grid partition the mass
    tot = 0.0
    for hh in range(9):
        for aa in range(9):
            sem_ = Semantics(
                "T", MarketFamily.EXACT_SCORE, Period.REGULATION, "home", None, hh * 100 + aa
            )
            tot += price(sem_, sim).fair_mean
    assert tot > 0.995
