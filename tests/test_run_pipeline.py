from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from soccer_edge.archive.ledger import PredictionLedger
from soccer_edge.authority.policy import Authority, AuthorityMatrix
from soccer_edge.core.errors import FreshnessError
from soccer_edge.kalshi.client import KalshiPublicClient
from soccer_edge.kalshi.discovery import discover
from soccer_edge.kalshi.fake import FakeKalshi
from soccer_edge.model.strength import DixonColesFitter, MatchRow
from soccer_edge.run.modeling import CompetitionModel
from soccer_edge.run.pipeline import RunConfig, RunInputs, run, write_outputs
from soccer_edge.run.simcache import SimCache

AS_OF = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


def _epl_model(fixtures):
    rng = np.random.default_rng(0)
    teams = sorted(
        {f.home_team_id for f in fixtures}
        | {f.away_team_id for f in fixtures}
        | {"eng.everton", "eng.fulham"}
    )
    rows = []
    d = date(2025, 8, 10)
    for k in range(60):
        for i in range(0, len(teams) - 1, 2):
            h, a = teams[(i + k) % len(teams)], teams[(i + k + 1) % len(teams)]
            rows.append(
                MatchRow(
                    d + timedelta(days=7 * (k % 40)),
                    h,
                    a,
                    int(rng.poisson(1.5)),
                    int(rng.poisson(1.1)),
                )
            )
    post = DixonColesFitter().fit(rows, as_of=date(2026, 10, 9))
    return CompetitionModel(
        "eng.premier_league", post, AS_OF - timedelta(hours=1), len(rows), date(2026, 10, 4), []
    )


def _inputs(registry, fixtures, disc, authority=None):
    return RunInputs(
        registry=registry,
        fixtures=fixtures,
        fixtures_observed_at=AS_OF - timedelta(hours=2),
        models={"eng.premier_league": _epl_model(fixtures)},
        results_observed_at=AS_OF - timedelta(days=1),
        discovery=disc,
        market_observed_at=AS_OF - timedelta(minutes=5),
        authority=authority or AuthorityMatrix(),
        as_of=AS_OF,
    )


@pytest.fixture
def disc(registry, epl_fixtures):
    fake = FakeKalshi(
        epl_fixtures,
        registry,
        fair=lambda f: {"home": 0.45, "draw": 0.27, "away": 0.28, "mean_total": 2.6},
    )
    return discover(KalshiPublicClient(transport=fake.transport))


def test_end_to_end_coverage_and_outputs(registry, epl_fixtures, disc, tmp_path):
    cfg = RunConfig(run_date=date(2026, 10, 10), n_worlds=150, draws_per_world=60)
    led = PredictionLedger(tmp_path / "ledger")
    art = run(
        _inputs(registry, epl_fixtures, disc),
        cfg,
        ledger=led,
        sim_cache=SimCache(tmp_path / "cache"),
    )
    out = art.output
    assert out.coverage.unaccounted_contracts == 0
    assert out.coverage.contracts_discovered == 42
    assert out.coverage.by_disposition["unknown_family"] == 3
    assert out.coverage.by_disposition["unsupported_family"] == 3  # player props: no lineup layer
    assert out.coverage.contracts_evaluated == 36
    assert out.no_bets  # everything RESEARCH_ONLY by default
    assert len(art.prediction_record_ids) == 36 and led.verify() == []
    paths = write_outputs(art, tmp_path / "out")
    assert paths["json"].exists() and "unaccounted contracts: 0" in art.markdown
    assert len(art.fixtures_simulated) == 3


def test_market_refresh_reuses_simulation(registry, epl_fixtures, disc, tmp_path):
    cfg = RunConfig(run_date=date(2026, 10, 10), n_worlds=100, draws_per_world=50)
    cache = SimCache(tmp_path / "cache")
    a = run(_inputs(registry, epl_fixtures, disc), cfg, sim_cache=cache)
    assert a.fixtures_simulated and not a.fixtures_repriced
    # move quotes only
    for tk, m in list(disc.markets.items()):
        disc.markets[tk] = m.model_copy(update={"yes_ask": (m.yes_ask or 0) + 0})
    b = run(_inputs(registry, epl_fixtures, disc), cfg, sim_cache=cache)
    assert b.fixtures_repriced and not b.fixtures_simulated
    # change model inputs -> resimulate
    c = run(
        _inputs(registry, epl_fixtures, disc),
        RunConfig(run_date=date(2026, 10, 10), n_worlds=100, draws_per_world=50, seed=1),
        sim_cache=cache,
    )
    assert c.fixtures_simulated


def test_freshness_gate_fails_closed(registry, epl_fixtures, disc):
    inp = _inputs(registry, epl_fixtures, disc)
    inp.market_observed_at = AS_OF - timedelta(hours=5)
    with pytest.raises(FreshnessError):
        run(inp, RunConfig(run_date=date(2026, 10, 10), n_worlds=50, draws_per_world=20))
    art = run(
        inp,
        RunConfig(
            run_date=date(2026, 10, 10), n_worlds=50, draws_per_world=20, enforce_freshness=False
        ),
    )
    assert any("freshness" in w for w in art.output.warnings)


def test_incomplete_discovery_never_recommends(registry, epl_fixtures):
    fake = FakeKalshi(
        epl_fixtures,
        registry,
        fail_on={"/markets:KXEPLSPREAD"},
        fair=lambda f: {"home": 0.2, "draw": 0.2, "away": 0.6, "mean_total": 1.0},
    )
    disc = discover(KalshiPublicClient(transport=fake.transport, max_retries=0))
    trusted = AuthorityMatrix({"data_only.world_sim_v1|any|any": Authority.TRUSTED})
    art = run(
        _inputs(registry, epl_fixtures, disc, trusted),
        RunConfig(run_date=date(2026, 10, 10), n_worlds=100, draws_per_world=40),
    )
    assert not art.output.coverage.discovery_complete
    assert art.output.no_bets and art.output.shadow_recommendations  # edges exist but are withheld
    assert art.output.coverage.unaccounted_contracts == 0


def test_trusted_authority_surfaces_recommendations(registry, epl_fixtures):
    fake = FakeKalshi(
        epl_fixtures,
        registry,
        fair=lambda f: {"home": 0.2, "draw": 0.2, "away": 0.6, "mean_total": 1.0},
    )
    disc = discover(KalshiPublicClient(transport=fake.transport))
    trusted = AuthorityMatrix({"data_only.world_sim_v1|any|any": Authority.TRUSTED})
    art = run(
        _inputs(registry, epl_fixtures, disc, trusted),
        RunConfig(run_date=date(2026, 10, 10), n_worlds=150, draws_per_world=40),
    )
    assert not art.output.no_bets
    r = art.output.recommendations[0]
    assert (
        r.authority == "TRUSTED"
        and r.fee_adjusted_edge > 0
        and r.correlation_group.startswith("fx:")
    )
    groups = [r.correlation_group for r in art.output.recommendations]
    assert len(groups) == len(set(groups))  # one expression per correlation group


def test_started_and_window_dispositions(registry, epl_fixtures, disc):
    inp = _inputs(registry, epl_fixtures, disc)
    inp.as_of = datetime(2026, 10, 10, 15, 0, tzinfo=UTC)  # after kickoff
    inp.market_observed_at = inp.as_of
    inp.fixtures_observed_at = inp.as_of
    inp.results_observed_at = inp.as_of
    inp.models["eng.premier_league"].fitted_at = inp.as_of
    art = run(inp, RunConfig(run_date=date(2026, 10, 10), n_worlds=20, draws_per_world=10))
    assert (
        art.output.coverage.by_disposition["started"] == 39
    )  # everything mapped, incl. player props
    inp.as_of = AS_OF - timedelta(days=10)
    for k in ("market_observed_at", "fixtures_observed_at", "results_observed_at"):
        setattr(inp, k, inp.as_of)
    inp.models["eng.premier_league"].fitted_at = inp.as_of
    art = run(
        inp, RunConfig(run_date=date(2026, 9, 29), n_worlds=20, draws_per_world=10, window_hours=24)
    )
    assert art.output.coverage.by_disposition["out_of_window"] == 39
