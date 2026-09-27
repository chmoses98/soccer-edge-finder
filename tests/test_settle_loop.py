from __future__ import annotations

from datetime import date, timedelta

from soccer_edge.archive.ledger import PredictionLedger
from soccer_edge.authority.policy import AuthorityMatrix
from soccer_edge.core.serialization import append_jsonl
from soccer_edge.kalshi.client import KalshiPublicClient
from soccer_edge.kalshi.discovery import discover
from soccer_edge.kalshi.fake import FakeKalshi
from soccer_edge.providers.interfaces import MatchResult
from soccer_edge.run.pipeline import RunConfig, run
from soccer_edge.run.settle import model_health, settle_ledger
from tests.test_run_pipeline import _inputs


def test_prospective_loop_settles_and_reports(registry, epl_fixtures, tmp_path):
    fake = FakeKalshi(
        epl_fixtures,
        registry,
        fair=lambda f: {"home": 0.45, "draw": 0.27, "away": 0.28, "mean_total": 2.6},
    )
    disc = discover(KalshiPublicClient(transport=fake.transport))
    led = PredictionLedger(tmp_path / "ledger")
    art = run(
        _inputs(registry, epl_fixtures, disc),
        RunConfig(run_date=date(2026, 10, 10), n_worlds=80, draws_per_world=40),
        ledger=led,
    )
    assert len(art.prediction_record_ids) == 36
    # a 'close' snapshot before kickoff and one after (must be ignored)
    snaps = tmp_path / "snapshots"
    ko = epl_fixtures[0].kickoff_utc
    for tk in disc.markets:
        append_jsonl(
            snaps / "2026-10-10" / "cap-a.jsonl",
            {
                "ticker": tk,
                "captured_at": (ko - timedelta(minutes=20)).isoformat(),
                "yes_bid": "0.50",
                "yes_ask": "0.52",
                "no_ask": "0.50",
            },
        )
        append_jsonl(
            snaps / "2026-10-10" / "cap-b.jsonl",
            {
                "ticker": tk,
                "captured_at": (ko + timedelta(minutes=20)).isoformat(),
                "yes_bid": "0.90",
                "yes_ask": "0.92",
                "no_ask": "0.10",
            },
        )
    results = {
        f.fixture_id: MatchResult(
            fixture_id=f.fixture_id,
            competition_id=f.competition_id,
            season_id=f.season_id,
            match_date=f.kickoff_date,
            home_team_id=f.home_team_id,
            away_team_id=f.away_team_id,
            home_goals=2,
            away_goals=1,
            home_goals_ht=1,
            away_goals_ht=0,
        )
        for f in epl_fixtures
    }
    stl = PredictionLedger(tmp_path / "settlements")
    too_early = settle_ledger(led, results, snaps, stl, as_of=ko + timedelta(hours=1))
    assert too_early == []
    written = settle_ledger(led, results, snaps, stl, as_of=ko + timedelta(hours=4))
    assert len(written) == 36
    assert {w["outcome"] for w in written} <= {"yes", "no"}
    home_win = [
        w for w in written if w["family"] == "match_result_3way" and w["ticker"].endswith("-ARS")
    ]
    assert home_win and home_win[0]["outcome"] == "yes"
    assert all(w["close_yes_mid"] == 0.51 for w in written)  # post-kickoff snapshot ignored
    # idempotent
    assert settle_ledger(led, results, snaps, stl, as_of=ko + timedelta(hours=5)) == []
    rows, proposals = model_health(stl, AuthorityMatrix(), as_of=ko + timedelta(hours=5))
    assert rows and all(r.authority == "RESEARCH_ONLY" for r in rows)
    assert proposals["proposals"] == {}  # 36 settled contracts cannot promote anything
    total = next(r for r in rows if r.market_family == "total_goals" and r.horizon == "any")
    assert total.n_settled == 15 and total.log_loss is not None
