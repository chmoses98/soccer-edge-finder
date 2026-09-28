"""Regression tests from the pre-launch statistical audit (docs/PRELAUNCH_AUDIT.md).

The first group pins bugs fixed by the audit. The `xfail(strict=True)` group pins *known model defects* that
the audit did not fix (they need versioned model families): when a versioned fix lands, the test starts
passing, strict xfail turns that into a failure, and the marker must be removed deliberately.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import numpy as np
import pytest

from soccer_edge.kalshi.executable import top_of_book
from soccer_edge.kalshi.schemas import RawMarket
from soccer_edge.model.analytic import outcome_probs, score_matrix
from soccer_edge.model.context import MatchContext
from soccer_edge.model.strength import DixonColesFitter, MatchRow
from soccer_edge.model.worlds import WorldConfig, WorldSet
from soccer_edge.pricing.pricer import PricedProbability
from soccer_edge.providers.espn import parse_summary_lineups
from soccer_edge.run.settle import clv_fields, model_signed_clv
from soccer_edge.run.simcache import compact, expand_world_probs
from soccer_edge.sim.engine import SimConfig, simulate
from tests.test_espn_provider import _summary_body

# ---- fixed bugs ------------------------------------------------------------------------------------------


def test_no_side_depth_comes_from_yes_bid_size():
    # Kalshi returns no no_ask_size; the NO ask is 1 - yes_bid, so its depth is the YES bid size
    m = RawMarket.from_api(
        {
            "ticker": "T-1-1",
            "event_ticker": "T-1",
            "yes_bid_dollars": "0.40",
            "yes_ask_dollars": "0.46",
            "no_bid_dollars": "0.54",
            "no_ask_dollars": "0.60",
            "yes_bid_size_fp": "37",
            "yes_ask_size_fp": "10",
        }
    )
    q = top_of_book(m, "no")
    assert q.price == Decimal("0.60") and q.size == Decimal("37") and q.is_quote


def test_clv_ignores_empty_book_sentinels():
    # close book with no bids (yes_bid 0): no mid, and no executable NO close (1 - 0 = 1 is not a price)
    no = clv_fields(
        side="no",
        entry_price=Decimal("0.80"),
        close_yes_bid=Decimal("0"),
        close_yes_ask=Decimal("0.30"),
        fee_type="quadratic",
        fee_multiplier="1",
    )
    assert no == {
        "clv_probability_points": None,
        "clv_price_points": None,
        "clv_fee_aware_points": None,
    }
    # no asks (yes_ask 1): YES side has no executable close and no mid
    yes = clv_fields(
        side="yes",
        entry_price=Decimal("0.40"),
        close_yes_bid=Decimal("0.35"),
        close_yes_ask=Decimal("1"),
        fee_type="quadratic",
        fee_multiplier="1",
    )
    assert yes["clv_price_points"] is None and yes["clv_probability_points"] is None
    # a real two-sided close still works
    ok = clv_fields(
        side="yes",
        entry_price=Decimal("0.40"),
        close_yes_bid=Decimal("0.44"),
        close_yes_ask=Decimal("0.46"),
        fee_type="quadratic",
        fee_multiplier="1",
    )
    assert ok["clv_price_points"] == pytest.approx(0.06) and ok["clv_probability_points"] == (
        pytest.approx(0.05)
    )


def test_authority_clv_is_signed_by_model_side():
    # model above the entry mid and the market rises: good; model below and the market rises: bad
    up = {"clv_yes_points": 0.03, "entry_yes_mid": 0.40, "fair_probability_mean": 0.50}
    down = {"clv_yes_points": 0.03, "entry_yes_mid": 0.40, "fair_probability_mean": 0.30}
    assert model_signed_clv(up) == pytest.approx(0.03)
    assert model_signed_clv(down) == pytest.approx(-0.03)
    assert model_signed_clv({"clv_yes_points": None, "entry_yes_mid": 0.4}) is None


def test_lineup_captured_after_kickoff_is_never_confirmed():
    # ESPN can still say 'pre' a minute after the scheduled 13:00 kickoff; that sheet is post-hoc
    late = parse_summary_lineups(
        "eng.1",
        "401879276",
        _summary_body("pre"),
        captured_at=datetime(2026, 9, 20, 13, 1, tzinfo=UTC),
        source_url="u",
    )
    assert late.published and late.lineup_state == "post_hoc"


def test_sim_cache_keeps_exact_world_probabilities():
    rng = np.random.default_rng(3)
    wp = np.clip(rng.normal(0.30, 0.04, 1000), 0, 1)
    p = PricedProbability(
        "T",
        float(wp.mean()),
        float(np.median(wp)),
        0.25,
        0.35,
        0.8,
        0.04,
        0.001,
        1000,
        100,
        100000,
        wp,
        "d",
    )
    back = expand_world_probs(compact(p))
    # P(edge>0) at a 0.27 break-even must not move (the 20-bin histogram moved it from 0.76 to 0.89)
    assert (back > 0.27).mean() == pytest.approx((wp > 0.27).mean(), abs=1e-9)


def test_cached_repricing_reproduces_draw_level_payoffs(registry, epl_fixtures, tmp_path):
    from soccer_edge.authority.policy import Authority, AuthorityMatrix
    from soccer_edge.kalshi.client import KalshiPublicClient
    from soccer_edge.kalshi.discovery import discover
    from soccer_edge.kalshi.fake import FakeKalshi
    from soccer_edge.run.pipeline import RunConfig, run
    from soccer_edge.run.simcache import SimCache
    from tests.test_run_pipeline import _inputs

    fake = FakeKalshi(
        epl_fixtures,
        registry,
        fair=lambda f: {"home": 0.2, "draw": 0.2, "away": 0.6, "mean_total": 1.0},
    )
    disc = discover(KalshiPublicClient(transport=fake.transport))
    trusted = AuthorityMatrix({"data_only.world_sim_v1|any|any": Authority.TRUSTED})
    cfg = RunConfig(run_date=date(2026, 10, 10), n_worlds=120, draws_per_world=40)
    cache = SimCache(tmp_path / "cache")
    a = run(_inputs(registry, epl_fixtures, disc, trusted), cfg, sim_cache=cache)
    b = run(_inputs(registry, epl_fixtures, disc, trusted), cfg, sim_cache=cache)
    assert a.fixtures_simulated and b.fixtures_repriced and not b.fixtures_simulated

    def expr(art):
        return {r["ticker"]: r["expression"] for r in art.per_contract}

    # same candidates, same correlation groups and correlations: the cache is invisible to the reducer
    assert expr(a) == expr(b)
    assert [r.market_ticker for r in a.output.recommendations] == [
        r.market_ticker for r in b.output.recommendations
    ]


def test_market_age_is_measured_from_the_start_of_the_sweep():
    from soccer_edge.kalshi.discovery import DiscoveryRun
    from soccer_edge.run.inputs import AssembledData, build_inputs

    t0 = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
    disc = DiscoveryRun(run_id="d", started_at=t0, finished_at=t0 + timedelta(minutes=13))
    data = AssembledData([], t0, {}, t0, {}, [])
    inp = build_inputs(None, data, disc, as_of=t0 + timedelta(minutes=14))  # type: ignore[arg-type]
    assert inp.market_observed_at == t0


# ---- known model defects (not fixed by the audit; versioned fixes required) --------------------------------


def _league(seed: int, home_rate: float = 1.55, away_rate: float = 1.25):
    rng = np.random.default_rng(seed)
    n = 20
    teams = [f"t{i:02d}" for i in range(n)]
    att, dfn = rng.normal(0, 0.2, n), rng.normal(0, 0.2, n)
    rows, start = [], date(2025, 8, 1)
    for rnd in range(38):
        order = rng.permutation(n)
        for i in range(0, n, 2):
            h, a = order[i], order[i + 1]
            lam = home_rate * np.exp(att[h] - dfn[a])
            mu = away_rate * np.exp(att[a] - dfn[h])
            rows.append(
                MatchRow(
                    start + timedelta(days=7 * rnd),
                    teams[h],
                    teams[a],
                    int(rng.poisson(lam)),
                    int(rng.poisson(mu)),
                )
            )
    return teams, rows


@pytest.mark.xfail(
    strict=True,
    reason="dc_laplace_v1 has no scoring intercept: the sum-to-zero penalty pins the away level near exp(0) "
    "(docs/RESEARCH_HOME_BIAS.md H8; docs/PRELAUNCH_AUDIT.md §D)",
)
def test_fitted_away_level_matches_training_away_level():
    teams, rows = _league(11)
    post = DixonColesFitter().fit(rows, as_of=date(2026, 7, 1))
    pred_away = np.mean([post.expected_goals(r.home, r.away)[1] for r in rows])
    obs_away = np.mean([r.away_goals for r in rows])
    assert abs(pred_away / obs_away - 1) < 0.05


@pytest.mark.xfail(
    strict=True,
    reason="minute_engine_v1 never reads worlds.rho, so the fitted Dixon-Coles low-score correction is dropped "
    "at pricing (docs/PRELAUNCH_AUDIT.md §B2)",
)
def test_engine_honours_dixon_coles_rho():
    W = 400
    cfg = WorldConfig(red_card_mean_per_team=0.0, trailing_attack_mult=1.0, leading_attack_mult=1.0)
    ws = WorldSet(
        W,
        np.full(W, 1.3),
        np.full(W, 1.1),
        np.full(W, -0.12),
        np.zeros(W),
        np.zeros(W),
        np.ones(W),
        np.ones(W),
        config=cfg,
    )
    ctx = MatchContext("f", "c", "H", "A", datetime(2026, 1, 1, tzinfo=UTC))
    out = simulate(ws, ctx, SimConfig(draws_per_world=200, allocate_player_goals=False), seed=5)
    draw_sim = float((out.home_ft == out.away_ft).mean())
    draw_dc = outcome_probs(score_matrix(1.3, 1.1, -0.12))["draw"]
    assert abs(draw_sim - draw_dc) < 0.006
