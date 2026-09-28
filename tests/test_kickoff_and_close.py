"""Kickoff dispatcher horizons (phase 6), reference source quality (phase 7), close capture v2 (phase 8)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from soccer_edge.dispatch.horizons import (
    HORIZON_WINDOWS,
    REQUIRED_HORIZONS,
    HorizonRow,
    ScheduledFixture,
    append_log,
    build_schedule,
    delivered_rows,
    diagnostics,
    horizon_for_minutes,
    load_log,
    minutes_until_next_window,
    plan,
)
from soccer_edge.reference.close import (
    CloseClassV2,
    book_is_valid,
    classify_kalshi_close,
    classify_reference_close,
    close_completeness,
    kalshi_close_for,
    reference_close_for,
    side_probability,
)
from soccer_edge.reference.quality import (
    REFERENCE_PROVIDERS,
    SourceQuality,
    live_sharp_reference_available,
    quality_for_bookmaker,
)

KO = datetime(2026, 10, 3, 19, 0, tzinfo=UTC)


def _fx(fid="fx:a", ko=KO):
    return ScheduledFixture(fid, ko, "eng.premier_league", "run_output", 40)


# ------------------------------------------------------------------ dispatcher


def test_windows_cover_the_final_130_minutes_without_overlap():
    prev_lo = None
    for h in REQUIRED_HORIZONS:
        lo, hi = HORIZON_WINDOWS[h]
        assert lo < h <= hi
        if prev_lo is not None:
            assert (
                hi >= prev_lo
            )  # no gap: the next window opens before (early tolerance) the previous closes
        prev_lo = lo
    assert horizon_for_minutes(125) == 120 and horizon_for_minutes(47) == 60
    assert (
        horizon_for_minutes(3) == 5
        and horizon_for_minutes(0) is None
        and horizon_for_minutes(200) is None
    )


def test_plan_due_missed_upcoming_and_catch_up():
    fx = _fx()
    # T-125: only the 120 horizon is due; others upcoming
    due, missed, upcoming = plan([fx], [], now=KO - timedelta(minutes=125))
    assert [d.horizon for d in due] == [120] and missed == []
    assert [u.horizon for u in upcoming] == [60, 30, 15, 5]
    assert minutes_until_next_window(upcoming) == 125 - 66
    # a missed 120 tick: at T-50 the 120 window is closed (missed) and 60 is due (catch-up inside its window)
    due, missed, upcoming = plan([fx], [], now=KO - timedelta(minutes=50))
    assert [d.horizon for d in due] == [60]
    assert [(m.horizon, m.status) for m in missed] == [(120, "missed")]
    # once logged, neither the delivered nor the missed horizon is reported again
    log = missed + delivered_rows(due, now=KO - timedelta(minutes=50), batch_id="b1", actions=["x"])
    due2, missed2, _ = plan([fx], log, now=KO - timedelta(minutes=49))
    assert due2 == [] and missed2 == []
    # after kickoff every undelivered horizon is missed exactly once
    _, missed3, up3 = plan([fx], log, now=KO + timedelta(minutes=1))
    assert sorted(m.horizon for m in missed3) == [5, 15, 30] and up3 == []


def test_delivered_rows_record_achieved_and_lateness():
    fx = _fx()
    due, _, _ = plan([fx], [], now=KO - timedelta(minutes=47))
    (row,) = delivered_rows(
        due, now=KO - timedelta(minutes=47), batch_id="kd-1", actions=["kalshi_capture:ok"]
    )
    assert row.horizon == 60 and row.achieved_minutes == 47.0 and row.lateness_minutes == 13.0
    assert row.status == "delivered" and row.actions == ["kalshi_capture:ok"]


def test_log_round_trip_and_diagnostics(tmp_path):
    fx = _fx()
    p = tmp_path / "dispatch" / "horizons.jsonl"
    rows = [
        HorizonRow(
            "fx:a",
            "2026-10-03T19:00:00Z",
            120,
            "delivered",
            "t",
            achieved_minutes=118.0,
            lateness_minutes=2.0,
        ),
        HorizonRow("fx:a", "2026-10-03T19:00:00Z", 60, "missed", "t"),
        HorizonRow(
            "fx:b",
            "2026-10-03T19:00:00Z",
            60,
            "delivered",
            "t",
            achieved_minutes=40.0,
            lateness_minutes=20.0,
        ),
    ]
    append_log(p, rows)
    assert [r.horizon for r in load_log(p)] == [120, 60, 60]
    d = diagnostics(load_log(p), [fx], now=KO - timedelta(minutes=30))
    assert d["delivered_total"] == 2 and d["missed_total"] == 1 and d["fixtures_tracked"] == 2
    assert (
        d["by_horizon"]["60"]["delivery_rate"] == 0.5
        and d["by_horizon"]["60"]["lateness_minutes_max"] == 20.0
    )
    assert d["by_horizon"]["120"]["achieved_minutes_median"] == 118.0
    assert d["n_pending_fixtures"] == 1  # fx:a still has 30/15/5 open


def test_build_schedule_merges_run_events_and_espn_fixtures():
    now = KO - timedelta(hours=5)
    run_out = {
        "events": [
            {
                "event_id": "fx:a",
                "start_time": KO.isoformat(),
                "league_id": "eng.premier_league",
                "markets_discovered": 40,
            }
        ]
    }
    espn = [
        {
            "fixture_id": "fx:a",
            "kickoff_utc": KO.isoformat(),
            "competition_id": "eng.premier_league",
        },  # duplicate
        {
            "fixture_id": "fx:c",
            "kickoff_utc": (KO + timedelta(hours=2)).isoformat(),
            "competition_id": "usa.mls",
        },
        {
            "fixture_id": "fx:d",
            "kickoff_utc": (KO + timedelta(hours=2)).isoformat(),
            "competition_id": "xyz.not_priced",
        },
        {
            "fixture_id": "fx:e",
            "kickoff_utc": (KO - timedelta(days=2)).isoformat(),
            "competition_id": "usa.mls",
        },  # past
    ]
    doc = build_schedule(
        run_output=run_out,
        espn_fixtures=espn,
        priced_competitions={"eng.premier_league", "usa.mls"},
        now=now,
    )
    ids = [f["fixture_id"] for f in doc["fixtures"]]
    assert ids == ["fx:a", "fx:c"]
    assert doc["fixtures"][0]["source"] == "run_output" and doc["fixtures"][1]["source"] == "espn"


# ------------------------------------------------------------------ reference quality


def test_bookmaker_quality_and_no_live_sharp_source():
    assert quality_for_bookmaker("pinnacle") is SourceQuality.SHARP_REFERENCE
    assert quality_for_bookmaker("bet365") is SourceQuality.SECONDARY_REFERENCE
    assert quality_for_bookmaker("consensus") is SourceQuality.SECONDARY_REFERENCE
    assert quality_for_bookmaker("kalshi") is SourceQuality.KALSHI_ONLY
    assert quality_for_bookmaker("someshop") is SourceQuality.UNAVAILABLE
    ok, why = live_sharp_reference_available()
    assert ok is False and "blocked" in why
    # the only near-kickoff sharp providers require credentials; Kalshi is never a sharp reference
    for spec in REFERENCE_PROVIDERS.values():
        if spec.best_quality is SourceQuality.KALSHI_ONLY:
            assert spec.provider_id == "kalshi_public"
        if spec.live and spec.near_kickoff and spec.best_quality is SourceQuality.SHARP_REFERENCE:
            assert spec.credentials_required


# ------------------------------------------------------------------ close v2


def test_close_class_matrix_edges():
    assert classify_reference_close(0) is CloseClassV2.TRUE_CLOSE
    assert classify_reference_close(15) is CloseClassV2.TRUE_CLOSE
    assert classify_reference_close(15.01) is CloseClassV2.NEAR_CLOSE
    assert classify_reference_close(120) is CloseClassV2.NEAR_CLOSE
    assert classify_reference_close(120.5) is CloseClassV2.STALE
    assert (
        classify_reference_close(None) is CloseClassV2.NONE
        and classify_reference_close(-1) is CloseClassV2.NONE
    )
    assert classify_kalshi_close(30, valid=True) is CloseClassV2.KALSHI_CLOSE
    assert classify_kalshi_close(31, valid=True) is CloseClassV2.STALE
    assert classify_kalshi_close(5, valid=False) is CloseClassV2.NONE


def test_book_validity():
    assert book_is_valid("active", "0.40", "0.45")[0]
    assert not book_is_valid("suspended", "0.40", "0.45")[0]
    assert not book_is_valid("active", "0", "1")[0]  # sentinel empty book
    assert not book_is_valid("active", None, "0.45")[0]  # one-sided
    assert not book_is_valid("active", "0.30", "0.45")[0]  # 15c spread
    assert not book_is_valid("active", "0.50", "0.45")[0]  # crossed


def _snap(minutes_before, bid, ask, status="active"):
    return {
        "captured_at": (KO - timedelta(minutes=minutes_before)).isoformat().replace("+00:00", "Z"),
        "yes_bid": bid,
        "yes_ask": ask,
        "status": status,
    }


def test_kalshi_close_steps_back_over_invalid_books():
    rows = [
        _snap(90, "0.40", "0.44"),
        _snap(25, "0.42", "0.46"),
        _snap(10, "0", "1"),
        _snap(4, "0.45", "0.50", status="suspended"),
    ]
    kc = kalshi_close_for(rows, KO)
    assert (
        kc.close_class is CloseClassV2.KALSHI_CLOSE
        and kc.minutes_before_kickoff == 25
        and kc.yes_bid == Decimal("0.42")
    )
    assert kc.snapshots_in_window == 3 and kc.invalid_in_window == 2
    j = kc.to_json()
    assert j["yes_mid"] == 0.44 and j["no_executable"] == "0.58"
    # only invalid books in the window and a valid one earlier -> STALE with the earlier book
    kc2 = kalshi_close_for([_snap(90, "0.40", "0.44"), _snap(10, "0", "1")], KO)
    assert kc2.close_class is CloseClassV2.STALE and kc2.minutes_before_kickoff == 90
    # nothing valid at all; and a post-kickoff row is ignored
    kc3 = kalshi_close_for([_snap(10, "0", "1"), _snap(-5, "0.5", "0.52")], KO)
    assert kc3.close_class is CloseClassV2.NONE and not kc3.valid


def _ref(minutes_before, bookmaker, p):
    return {
        "captured_at": (KO - timedelta(minutes=minutes_before)).isoformat().replace("+00:00", "Z"),
        "bookmaker": bookmaker,
        "devigged_probability": p,
        "devig_method": "proportional",
    }


def test_reference_close_prefers_sharp_then_latest():
    rows = [
        _ref(200, "consensus", 0.50),
        _ref(100, "bet365", 0.52),
        _ref(110, "pinnacle", 0.55),
        _ref(-3, "pinnacle", 0.60),
    ]
    rc = reference_close_for(rows, KO)
    assert (
        rc.bookmaker == "pinnacle"
        and rc.probability_yes == 0.55
        and rc.close_class is CloseClassV2.NEAR_CLOSE
    )
    assert rc.source_quality is SourceQuality.SHARP_REFERENCE and rc.minutes_before_kickoff == 110
    rc2 = reference_close_for([_ref(10, "bet365", 0.52), _ref(12, "bet365", 0.51)], KO)
    assert (
        rc2.close_class is CloseClassV2.TRUE_CLOSE
        and rc2.probability_yes == 0.52
        and rc2.source_quality is SourceQuality.SECONDARY_REFERENCE
    )
    assert reference_close_for([], KO).close_class is CloseClassV2.NONE
    assert reference_close_for([_ref(300, "bet365", 0.5)], KO).close_class is CloseClassV2.STALE


def test_side_probability_and_completeness():
    assert side_probability(0.3, "no") == 0.7 and side_probability(None, "yes") is None
    recs = [
        {
            "close_v2": {
                "reference": {"close_class": "TRUE_CLOSE"},
                "kalshi": {"close_class": "KALSHI_CLOSE"},
            }
        },
        {
            "close_v2": {
                "reference": {"close_class": "NEAR_CLOSE"},
                "kalshi": {"close_class": "NONE"},
            }
        },
        {"close_v2": {"reference": {"close_class": "NONE"}, "kalshi": {"close_class": "STALE"}}},
        {},
    ]
    c = close_completeness(recs)
    assert (
        c["records"] == 3 and c["true_close_share"] == 1 / 3 and c["reference_close_share"] == 2 / 3
    )
    assert c["kalshi_close_share"] == pytest.approx(1 / 3)
    assert c["missing_reference_close_rate"] == pytest.approx(1 / 3)


def test_settlement_rows_carry_close_v2(tmp_path):
    from soccer_edge.archive.ledger import PredictionLedger
    from soccer_edge.core.serialization import append_jsonl
    from soccer_edge.providers.interfaces import MatchResult
    from soccer_edge.run.settle import build_result_index, settle_ledger
    from soccer_edge.settlement.resolve import CoverageRows

    ko = KO
    rec = {
        "schema": "prediction_record_v1",
        "run_id": "run-x",
        "as_of": (ko - timedelta(hours=5)).isoformat().replace("+00:00", "Z"),
        "ticker": "T1",
        "fixture_id": "fx:eng.premier_league:2026-27:eng.a:eng.b",
        "competition_id": "eng.premier_league",
        "kickoff_utc": ko.isoformat().replace("+00:00", "Z"),
        "family": "match_result_3way",
        "semantics": {
            "side": "home",
            "line": None,
            "period": "regulation",
            "k": None,
            "description": "",
        },
        "model_family": "data_only.world_sim_v1",
        "probability": {
            "fair_probability_mean": 0.5,
            "fair_probability_low": 0.4,
            "fair_probability_high": 0.6,
        },
        "market": {"yes_bid": "0.40", "yes_ask": "0.45", "no_bid": "0.55", "no_ask": "0.60"},
        "market_as_of": (ko - timedelta(hours=5)).isoformat().replace("+00:00", "Z"),
        "fee_regime": {"fee_type": "quadratic", "fee_multiplier": "1"},
        "reference": {
            "bookmaker": "consensus",
            "probability_yes": 0.48,
            "observed_at": None,
            "kalshi_mid_yes": 0.425,
        },
        "recommendation": {},
    }
    led = PredictionLedger(tmp_path / "pred")
    led.append(rec, when=ko - timedelta(hours=5))
    snaps = tmp_path / "snaps" / "2026-10-03"
    append_jsonl(snaps / "cap-1.jsonl", {"ticker": "T1", **_snap(20, "0.50", "0.54")})
    append_jsonl(snaps / "cap-1.jsonl", {"ticker": "T1", **_snap(8, "0", "1")})
    ref = tmp_path / "ref" / "2026-10-03"
    append_jsonl(
        ref / "ref-1.jsonl",
        {
            "fixture_id": rec["fixture_id"],
            "market": "1x2",
            "selection": "home",
            "line": None,
            **_ref(12, "pinnacle", 0.56),
        },
    )
    res = MatchResult(
        fixture_id=rec["fixture_id"],
        competition_id="eng.premier_league",
        season_id="2026-27",
        match_date="2026-10-03",
        home_team_id="eng.a",
        away_team_id="eng.b",
        home_goals=1,
        away_goals=0,
        status_name="STATUS_FULL_TIME",
    )
    rows = CoverageRows()
    written = settle_ledger(
        led,
        build_result_index({"espn_site_api": [res]}),
        tmp_path / "snaps",
        PredictionLedger(tmp_path / "stl"),
        as_of=ko + timedelta(hours=6),
        reference_dir=tmp_path / "ref",
        et_possible_for={"eng.premier_league": False},
        coverage_rows=rows,
    )
    cv = written[0]["close_v2"]
    assert (
        cv["kalshi"]["close_class"] == "KALSHI_CLOSE"
        and cv["kalshi"]["minutes_before_kickoff"] == 20
    )
    assert (
        cv["reference"]["close_class"] == "TRUE_CLOSE"
        and cv["reference"]["probability_yes"] == 0.56
        and cv["reference"]["probability_no"] == 0.44
    )
    assert cv["entry"]["kalshi"] == {
        "yes": "0.45",
        "no": "0.60",
        "captured_at": rec["market_as_of"],
    }
    assert cv["entry"]["reference"]["probability_yes"] == 0.48 and cv["complete"] == {
        "reference_close": True,
        "kalshi_close": True,
    }
    assert rows.close_completeness["true_close_share"] == 1.0
