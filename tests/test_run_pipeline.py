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


def _epl_rows(fixtures):
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
    return rows


def _epl_model(fixtures, as_of: date = date(2026, 10, 9)):
    rows = _epl_rows(fixtures)
    rows = [r for r in rows if r.date < as_of]
    post = DixonColesFitter().fit(rows, as_of=as_of, strict_point_in_time=True)
    fitted_at = datetime(as_of.year, as_of.month, as_of.day, 11, tzinfo=UTC)
    return CompetitionModel(
        "eng.premier_league", post, fitted_at, len(rows), max(r.date for r in rows), []
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
    # point-in-time: the model used at this earlier decision time must not have seen later results
    inp.models["eng.premier_league"] = _epl_model(epl_fixtures, as_of=inp.as_of.date())
    art = run(
        inp, RunConfig(run_date=date(2026, 9, 29), n_worlds=20, draws_per_world=10, window_hours=24)
    )
    assert art.output.coverage.by_disposition["out_of_window"] == 39


def test_international_pool_competitions_use_distinct_model_family():
    from soccer_edge.run.pipeline import INTL_POOL_FAMILY_ID, MODEL_FAMILY_ID, model_family_for

    assert model_family_for("eng.premier_league") == MODEL_FAMILY_ID
    assert model_family_for("uefa.nations_league") == INTL_POOL_FAMILY_ID
    assert INTL_POOL_FAMILY_ID != MODEL_FAMILY_ID and INTL_POOL_FAMILY_ID.startswith(
        MODEL_FAMILY_ID
    )


def test_temporal_guard_fails_closed_on_future_input(registry, epl_fixtures, disc):
    from soccer_edge.core.temporal import FutureInformationError

    inp = _inputs(registry, epl_fixtures, disc)
    inp.results_observed_at = inp.as_of + timedelta(seconds=1)
    with pytest.raises(FutureInformationError):
        run(
            inp,
            RunConfig(
                run_date=AS_OF.date(), n_worlds=50, draws_per_world=10, enforce_freshness=False
            ),
        )
    inp.results_observed_at = inp.as_of - timedelta(days=1)
    inp.fixtures_observed_at = inp.as_of + timedelta(minutes=1)
    with pytest.raises(FutureInformationError):
        run(
            inp,
            RunConfig(
                run_date=AS_OF.date(), n_worlds=50, draws_per_world=10, enforce_freshness=False
            ),
        )


def test_temporal_guard_report_is_in_the_run_output(registry, epl_fixtures, disc):
    inp = _inputs(registry, epl_fixtures, disc)
    art = run(
        inp,
        RunConfig(run_date=AS_OF.date(), n_worlds=50, draws_per_world=10, enforce_freshness=False),
    )
    tg = art.output.freshness["temporal_guard"]
    assert tg["ok"] is True and tg["violations"] == []
    assert {"fixtures", "results", "market_snapshots"} <= set(tg["checked"])


def test_pipeline_runs_end_to_end_on_world_sim_v2(registry, epl_fixtures, disc, tmp_path):
    from soccer_edge.model.strength_v2 import DixonColesFitterV2
    from soccer_edge.run.pipeline import ENGINE_V2

    inp = _inputs(registry, epl_fixtures, disc)
    v1_model = inp.models["eng.premier_league"]
    rows = _epl_rows(epl_fixtures)
    post2 = DixonColesFitterV2().fit(rows, as_of=date(2026, 10, 9), strict_point_in_time=True)
    inp.models["eng.premier_league"] = CompetitionModel(
        "eng.premier_league", post2, v1_model.fitted_at, len(rows), max(r.date for r in rows), []
    )
    led = PredictionLedger(tmp_path / "ledger")
    art = run(
        inp,
        RunConfig(
            run_date=date(2026, 10, 10), n_worlds=60, draws_per_world=20, engine_version=ENGINE_V2
        ),
        ledger=led,
    )
    assert (
        art.output.coverage.unaccounted_contracts == 0
        and art.output.coverage.contracts_evaluated > 0
    )
    recs = list(led.iter_records())
    assert recs and all(r["model_version"] == "dc_laplace_v2" for r in recs)
    assert all(r["engine_version"] == "world_sim_v2" for r in recs)
    assert all(r["model_family"].startswith("data_only.world_sim_v2") for r in recs)
    ft = [r for r in recs if r["family"] == "match_result_3way"]
    assert ft and all(r["probability"]["mc_standard_error"] == 0.0 for r in ft)  # analytic
    assert led.verify() == []
