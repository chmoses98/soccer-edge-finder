from __future__ import annotations

from decimal import Decimal

import numpy as np
import pytest

from soccer_edge.archive.ledger import PredictionLedger, WriteStatus
from soccer_edge.authority.policy import (
    Authority,
    AuthorityKey,
    AuthorityMatrix,
    Evidence,
    recommend_state,
)
from soccer_edge.core.errors import ArchiveImmutabilityError
from soccer_edge.evaluation.metrics import (
    brier,
    clv_points,
    expected_calibration_error,
    interval_calibration,
    log_loss,
    reliability,
)
from soccer_edge.identity.models import FixtureStatus
from soccer_edge.kalshi.taxonomy import MarketFamily, Period
from soccer_edge.pricing.semantics import Semantics
from soccer_edge.settlement.engine import OfficialResult, SettlementOutcome, settle


def test_ledger_append_only(tmp_path):
    led = PredictionLedger(tmp_path)
    rec = {"ticker": "A", "p": 0.5}
    rid, st = led.append(rec)
    assert st is WriteStatus.WRITTEN
    rid2, st2 = led.append(dict(rec))
    assert rid2 == rid and st2 is WriteStatus.NO_OP
    assert led.verify() == []
    # attempting to change content under the same id is impossible (id is content-derived)
    rid3, _ = led.append({"ticker": "A", "p": 0.6})
    assert rid3 != rid
    with pytest.raises(ArchiveImmutabilityError):
        led.supersede("pred_missing", {"x": 1}, "bug")
    rid4, _ = led.supersede(rid, {"ticker": "A", "p": 0.55}, "replayed after semantics fix")
    assert led.get(rid4)["supersedes"] == rid and led.get(rid)["p"] == 0.5


def test_ledger_detects_tampering(tmp_path):
    led = PredictionLedger(tmp_path)
    led.append({"ticker": "A", "p": 0.5})
    f = next(tmp_path.glob("*/predictions.jsonl"))
    f.write_text(f.read_text().replace("0.5", "0.9"))
    assert led.verify()


def _res(**kw):
    base = {
        "fixture_id": "fx",
        "status": FixtureStatus.FINISHED,
        "home_ft": 2,
        "away_ft": 1,
        "home_ht": 1,
        "away_ht": 1,
    }
    base.update(kw)
    return OfficialResult(**base)


def test_settlement_semantics():
    s = lambda fam, side=None, line=None, period=Period.REGULATION, k=None: Semantics(
        "T", fam, period, side, Decimal(str(line)) if line is not None else None, k
    )
    assert settle(s(MarketFamily.TOTAL_GOALS, line=2.5), _res()).outcome is SettlementOutcome.YES
    assert settle(s(MarketFamily.TOTAL_GOALS, line=3.5), _res()).outcome is SettlementOutcome.NO
    assert settle(s(MarketFamily.HANDICAP, "home", 0.5), _res()).outcome is SettlementOutcome.YES
    assert settle(s(MarketFamily.HANDICAP, "home", 1.5), _res()).outcome is SettlementOutcome.NO
    assert (
        settle(s(MarketFamily.MATCH_RESULT_3WAY, "draw", period=Period.FIRST_HALF), _res()).outcome
        is SettlementOutcome.YES
    )
    assert (
        settle(
            s(MarketFamily.MATCH_RESULT_3WAY, "draw", period=Period.FIRST_HALF), _res(home_ht=None)
        ).outcome
        is SettlementOutcome.REFUSED_MISSING_PERIOD_DATA
    )
    assert settle(s(MarketFamily.BTTS), _res(away_ft=0)).outcome is SettlementOutcome.NO
    assert (
        settle(s(MarketFamily.DRAW_NO_BET, "home"), _res(away_ft=2)).outcome
        is SettlementOutcome.VOID
    )
    assert (
        settle(s(MarketFamily.TOTAL_GOALS, line=2.5), _res(status=FixtureStatus.ABANDONED)).outcome
        is SettlementOutcome.REFUSED_ABANDONED
    )
    # extra time inclusive market counts ET goals; regulation market does not
    r = _res(home_ft=1, away_ft=1, home_et=1, away_et=0, winner_after_pens="home")
    assert settle(s(MarketFamily.TOTAL_GOALS, line=2.5), r).outcome is SettlementOutcome.NO
    assert (
        settle(s(MarketFamily.TOTAL_GOALS, line=2.5, period=Period.INCLUDING_ET), r).outcome
        is SettlementOutcome.YES
    )
    assert settle(s(MarketFamily.MATCH_WINNER_2WAY, "home"), r).outcome is SettlementOutcome.YES
    # kalshi cross-check recorded
    st = settle(s(MarketFamily.TOTAL_GOALS, line=2.5), _res(), kalshi_result="no")
    assert st.agrees_with_kalshi is False


def test_metrics_basic():
    p = np.array([0.9, 0.8, 0.2, 0.1])
    y = np.array([1, 1, 0, 0])
    assert brier(p, y) < 0.05 and log_loss(p, y) < 0.25
    assert expected_calibration_error(p, y) < 0.2
    assert len(reliability(p, y, 5)) == 5
    clv = clv_points(np.array([0.5, 0.5]), np.array([0.55, 0.45]), np.array([True, False]))
    assert np.allclose(clv, [0.05, 0.05])


def test_interval_calibration_reports_coverage():
    rng = np.random.default_rng(0)
    p = rng.uniform(0.2, 0.8, 5000)
    y = (rng.random(5000) < p).astype(int)
    d = interval_calibration(p, p - 0.05, p + 0.05, y, level=0.8)
    assert 0.5 <= d["weighted_bin_coverage"] <= 1.0
    assert d["mean_width"] == pytest.approx(0.10)


def test_authority_no_leapfrog_and_default_research_only(tmp_path):
    m = AuthorityMatrix()
    assert (
        m.get(AuthorityKey("data_only.world_sim_v1", "total_goals", "T-30m"))
        is Authority.RESEARCH_ONLY
    )
    strong = Evidence(
        n_settled=5000,
        model_logloss=0.60,
        market_logloss=0.62,
        clv_points_mean=0.01,
        ece=0.02,
        interval_coverage_80=0.80,
    )
    state, notes = recommend_state(strong, Authority.RESEARCH_ONLY)
    assert state is Authority.SHADOW  # one step at a time
    weak = Evidence(
        n_settled=50,
        model_logloss=0.65,
        market_logloss=0.62,
        clv_points_mean=-0.02,
        ece=0.1,
        interval_coverage_80=None,
    )
    assert recommend_state(weak, Authority.RESEARCH_ONLY)[0] is Authority.RESEARCH_ONLY
