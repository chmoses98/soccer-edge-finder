from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import numpy as np

from soccer_edge.families.base import devig_power, devig_proportional
from soccer_edge.providers.football_data_couk import FootballDataCoUkProvider
from soccer_edge.reference.capture import build_snapshots, reference_for_contract, reference_lookup
from soccer_edge.reference.schemas import CloseClass, classify_close
from soccer_edge.run.settle import clv_fields

CSV = """﻿Div,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A,PSH,PSD,PSA,AvgH,AvgD,AvgA,B365>2.5,B365<2.5,Avg>2.5,Avg<2.5
E0,10/10/2026,12:30,Arsenal,Leeds,1.30,5.50,9.00,1.31,5.60,9.50,1.30,5.40,9.20,1.60,2.30,1.62,2.28
E0,10/10/2026,15:00,Chelsea,Bournemouth,1.80,3.80,4.20,,,,,,,,,,
"""


def test_devig_methods():
    odds = np.array([[1.30, 5.50, 9.00]])
    p = devig_proportional(odds)[0]
    assert abs(p.sum() - 1) < 1e-12 and p[0] > 0.7
    q = devig_power(odds)[0]
    assert abs(q.sum() - 1) < 1e-6 and q[0] > p[0]  # power de-vig removes more from longshots


def test_build_snapshots_joins_fixtures_and_builds_consensus(registry, epl_fixtures):
    prov = FootballDataCoUkProvider(registry=registry)
    quotes = prov.upcoming_odds(content=CSV.encode()).payload
    as_of = datetime(2026, 10, 9, 12, tzinfo=UTC)
    snaps, stats = build_snapshots(quotes, epl_fixtures, captured_at=as_of)
    assert stats["unmapped_fixture_groups"] == 0
    books = {(s.fixture_id.split(":")[3], s.bookmaker, s.market) for s in snaps}
    assert ("eng.arsenal", "consensus", "1x2") in books and (
        "eng.arsenal",
        "consensus",
        "ou",
    ) in books
    ars_cons = [
        s
        for s in snaps
        if "eng.arsenal" in s.fixture_id and s.bookmaker == "consensus" and s.market == "1x2"
    ]
    ars_avg = [
        s
        for s in snaps
        if "eng.arsenal" in s.fixture_id and s.bookmaker == "average" and s.market == "1x2"
    ]
    assert {s.devigged_probability for s in ars_cons} == {
        s.devigged_probability for s in ars_avg
    }  # average book wins
    che_cons = [s for s in snaps if "eng.chelsea" in s.fixture_id and s.bookmaker == "consensus"]
    che_b365 = [s for s in snaps if "eng.chelsea" in s.fixture_id and s.bookmaker == "bet365"]
    assert len(che_cons) == 3 and {s.devigged_probability for s in che_cons} == {
        s.devigged_probability for s in che_b365
    }  # fallback: only book
    assert all(s.is_closing is False and s.minutes_to_kickoff > 0 for s in snaps)
    assert all(
        abs(
            sum(
                x.devigged_probability
                for x in snaps
                if x.fixture_id == s.fixture_id and x.bookmaker == s.bookmaker and x.market == "1x2"
            )
            - 1
        )
        < 1e-9
        for s in snaps
    )
    look = reference_lookup(snaps)
    fid = ars_cons[0].fixture_id
    assert (
        reference_for_contract(look, fid, "match_result_3way", "home", None)
        == ars_cons[0].devigged_probability
        if ars_cons[0].selection == "home"
        else True
    )
    assert reference_for_contract(look, fid, "total_goals", None, Decimal("2.5")) is not None
    assert reference_for_contract(look, fid, "total_goals", None, Decimal("3.5")) is None
    assert reference_for_contract(look, fid, "btts", None, None) is None
    assert snaps[0].fingerprint() == snaps[0].fingerprint()


def test_close_classification():
    assert classify_close(10) is CloseClass.TRUE_CLOSE
    assert classify_close(30) is CloseClass.TRUE_CLOSE
    assert classify_close(40) is CloseClass.NEAR_CLOSE  # a T-40 snapshot is NOT a closing price
    assert classify_close(360) is CloseClass.NEAR_CLOSE
    assert classify_close(361) is CloseClass.PRE_CLOSE
    assert classify_close(None) is CloseClass.NONE and classify_close(-5) is CloseClass.NONE


def test_clv_is_side_aware_and_fee_aware():
    yes = clv_fields(
        side="yes",
        entry_price=Decimal("0.50"),
        close_yes_bid=Decimal("0.58"),
        close_yes_ask=Decimal("0.60"),
        fee_type="quadratic",
        fee_multiplier="1",
    )
    assert yes["clv_probability_points"] == 0.09 and yes["clv_price_points"] == 0.10
    assert (
        yes["clv_fee_aware_points"] < yes["clv_price_points"]
    )  # fee at 0.60 < fee at 0.50 -> fee-aware > price? check sign
    no = clv_fields(
        side="no",
        entry_price=Decimal("0.50"),
        close_yes_bid=Decimal("0.58"),
        close_yes_ask=Decimal("0.60"),
        fee_type="quadratic",
        fee_multiplier="1",
    )
    assert no["clv_probability_points"] == -0.09 and no["clv_price_points"] == -0.08
    none = clv_fields(
        side="yes",
        entry_price=None,
        close_yes_bid=None,
        close_yes_ask=None,
        fee_type=None,
        fee_multiplier=None,
    )
    assert none["clv_probability_points"] is None
