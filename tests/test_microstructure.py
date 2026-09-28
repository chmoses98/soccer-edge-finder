from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from soccer_edge.cli import main
from soccer_edge.core.serialization import canonical_json
from soccer_edge.kalshi.fees import FeeRegime, taker_fee
from soccer_edge.kalshi.microstructure import (
    HORIZON_BUCKETS,
    build_summary,
    derive_row,
    horizon_bucket,
    load_rows,
)

T0 = datetime(2026, 9, 27, 18, 0, tzinfo=UTC)
A = "KXEPLTOTAL-26SEP28ARSCHE-3"  # total_goals / EPL
B = "KXUCLGAME-26SEP30MUNSBH-MUN"  # match_result_3way / UCL
C = "KXMLSSPREAD-26SEP29SJMIN-SJ2"  # handicap / MLS


def _row(ticker: str, at: datetime, **kw) -> dict:
    base = {
        "ticker": ticker,
        "event_ticker": ticker.rsplit("-", 1)[0],
        "series_ticker": ticker.split("-", maxsplit=1)[0],
        "captured_at": at.isoformat().replace("+00:00", "Z"),
        "status": "active",
        "yes_bid": "0.48",
        "yes_ask": "0.52",
        "no_bid": "0.48",
        "no_ask": "0.52",
        "yes_bid_size": "120",
        "yes_ask_size": "80",
        "no_bid_size": "60",
        "no_ask_size": "90",
        "last_price": "0.50",
        "volume": "1000",
        "open_interest": "400",
        "close_time": None,
        "expected_expiration_time": None,
        "fee_type": "quadratic",
        "fee_multiplier": "1",
        "rules_primary_hash": None,
        "price_unit": "dollars",
        "horizon": "T-24h",
        "minutes_to_kickoff": 2000.0,
        "orderbook": None,
        "batch_id": "cap-x",
        "discovery_run_id": "disc-x",
    }
    base.update(kw)
    return base


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical_json(r) + "\n" for r in rows))


def make_snapshots(root: Path) -> list[dict]:
    m = timedelta(minutes=1)
    rows_a = [
        _row(A, T0, minutes_to_kickoff=2000.0),  # T-24h+
        _row(A, T0 + 10 * m, minutes_to_kickoff=600.0, yes_bid="0.40", yes_ask="0.50"),  # T-6h..24h
        _row(A, T0 + 30 * m, minutes_to_kickoff=120.0, yes_bid="0.45", yes_ask="0.47"),  # T-1h..6h
        _row(A, T0 + 90 * m, minutes_to_kickoff=30.0, yes_bid="0.46", yes_ask="0.47"),  # T-10m..1h
    ]
    rows_b = [
        # one-sided: no bid (sentinel 0), ask present
        _row(B, T0, yes_bid="0", yes_ask="0.60", no_bid="0.40", no_ask="1", minutes_to_kickoff=5.0),
        # all prices None, no kickoff info
        _row(
            B,
            T0 + 45 * m,
            yes_bid=None,
            yes_ask=None,
            no_bid=None,
            no_ask=None,
            yes_bid_size=None,
            yes_ask_size=None,
            no_bid_size=None,
            no_ask_size=None,
            volume=None,
            open_interest=None,
            minutes_to_kickoff=None,
            horizon="adhoc",
        ),
    ]
    rows_c = [
        _row(
            C,
            T0,
            fee_type="quadratic_with_maker_fees",
            yes_bid="0.20",
            yes_ask="0.30",
            no_bid="0.70",
            no_ask="0.80",
        ),
        _row(C, T0 + 15 * m, fee_type=None, fee_multiplier=None),  # fee regime unknown
        _row(
            C,
            T0 + 30 * m,
            yes_bid="0.10",
            yes_ask="0.12",
            no_bid="0.88",
            no_ask="0.90",
            minutes_to_kickoff=-3.0,
        ),
    ]
    _write(root / "2026-09-27" / "cap-1.jsonl", rows_a[:2] + rows_b[:1] + rows_c[:2])
    _write(root / "2026-09-27" / "cap-2.jsonl", rows_a[2:] + rows_b[1:] + rows_c[2:])
    return rows_a + rows_b + rows_c


def test_horizon_bucketing():
    assert [
        horizon_bucket(x) for x in (5000, 1440, 1439, 360, 359, 60, 59, 10, 9, 0, -5, None)
    ] == [
        "T-24h+",
        "T-24h+",
        "T-6h..24h",
        "T-6h..24h",
        "T-1h..6h",
        "T-1h..6h",
        "T-10m..1h",
        "T-10m..1h",
        "<10m",
        "<10m",
        "<10m",
        "unknown",
    ]
    assert tuple(HORIZON_BUCKETS) == (
        "T-24h+",
        "T-6h..24h",
        "T-1h..6h",
        "T-10m..1h",
        "<10m",
        "unknown",
    )


def test_derive_row_spread_fee_and_flags():
    r = derive_row(_row(A, T0))
    assert r is not None
    assert r.family == "total_goals" and r.competition == "EPL"
    assert r.quote_state == "two_sided"
    assert r.spread_yes == Decimal("0.04") and r.mid == Decimal("0.50")
    assert r.exec_yes == Decimal("0.52") and r.exec_no == Decimal("0.52")
    assert r.gap_yes == Decimal("0.02") and r.gap_no == Decimal("0.02")
    regime = FeeRegime("quadratic", Decimal(1))
    fee = taker_fee(Decimal("0.52"), 1, regime)
    assert r.fee_yes == fee and r.fee_impact_yes == fee / Decimal("0.52")
    assert r.fee_status == "ok"
    # 3c edge erased? half-spread 0.02 + fee 0.017472 = 0.037472 >= 0.03 -> yes; 5c -> no
    assert r.erased("yes", Decimal("0.03")) is True
    assert r.erased("yes", Decimal("0.05")) is False


def test_one_sided_none_prices_and_unknown_fee_do_not_crash():
    one = derive_row(_row(B, T0, yes_bid="0", yes_ask="0.60", no_ask="1"))
    assert one.quote_state == "one_sided" and one.spread_yes is None and one.mid is None
    assert one.exec_yes == Decimal("0.60") and one.exec_no is None
    assert one.fee_yes is not None and one.fee_no is None
    assert one.erased("yes", Decimal("0.03")) is None

    none = derive_row(
        _row(B, T0, yes_bid=None, yes_ask=None, no_bid=None, no_ask=None, minutes_to_kickoff=None)
    )
    assert none.quote_state == "no_quote" and none.bucket == "unknown"
    assert none.fee_status == "not_computable" and none.fee_impact_yes is None

    unk = derive_row(_row(C, T0, fee_type=None))
    assert unk.fee_status == "unverified_regime" and unk.fee_yes is None
    bad = derive_row(_row(C, T0, fee_type="flat"))
    assert bad.fee_status == "unverified_regime"

    maker = derive_row(
        _row(C, T0, fee_type="quadratic_with_maker_fees", yes_ask="0.30", no_ask="0.80")
    )
    assert maker.fee_yes == taker_fee(Decimal("0.30"), 1, FeeRegime("quadratic_with_maker_fees"))
    assert maker.fee_no == taker_fee(Decimal("0.80"), 1, FeeRegime("quadratic_with_maker_fees"))

    assert derive_row({"ticker": A}) is None
    assert derive_row({"captured_at": "2026-09-27T00:00:00Z"}) is None


def test_summary_counts_groups_and_cadence(tmp_path: Path):
    snaps = tmp_path / "snapshots"
    all_rows = make_snapshots(snaps)
    rows, counters = load_rows(snaps)
    assert counters == {"files": 2, "rows_read": 9, "rows_skipped": 0, "rows_before_since": 0}
    assert len(rows) == len(all_rows) == 9

    s = build_summary(snaps)
    assert s["schema"] == "microstructure_summary_v1"
    assert s["rows"] == 9 and s["tickers"] == 3
    assert s["date_range"] == {
        "first_captured_at": "2026-09-27T18:00:00Z",
        "last_captured_at": "2026-09-27T19:30:00Z",
    }
    qs = s["quote_state"]
    assert (qs["two_sided"], qs["one_sided"], qs["no_quote"]) == (7, 1, 1)
    assert qs["two_sided_share"] == round(7 / 9, 6)

    # spreads of the 7 two-sided rows
    spreads = sorted([0.04, 0.10, 0.02, 0.01, 0.10, 0.04, 0.02])
    assert s["spread_yes"]["n"] == 7
    assert s["spread_yes"]["median"] == 0.04
    assert s["spread_yes"]["min"] == 0.01 and s["spread_yes"]["max"] == 0.10
    assert s["spread_yes"]["mean"] == round(sum(spreads) / 7, 6)

    # fee impact on YES side: every executable ask with a verified regime (8 rows: 9 minus None-prices minus unknown fee)
    assert s["fee_impact"]["yes"]["n"] == 7
    q = FeeRegime("quadratic")
    exp = float(taker_fee(Decimal("0.52"), 1, q) / Decimal("0.52"))
    # only A's first row sits in total_goals x T-24h+, so the cell median is that row's fee impact
    assert s["by_family_horizon"]["total_goals|T-24h+"]["fee_impact_yes"]["median"] == round(exp, 6)
    # the bucket as a whole also holds C's maker-regime row (0.30 ask) -> higher median
    exp_c = float(
        taker_fee(Decimal("0.30"), 1, FeeRegime("quadratic_with_maker_fees")) / Decimal("0.30")
    )
    assert s["by_horizon_bucket"]["T-24h+"]["fee_impact_yes"]["n"] == 2
    assert s["by_horizon_bucket"]["T-24h+"]["fee_impact_yes"]["median"] == round(
        (exp + exp_c) / 2, 6
    )

    # groups
    assert set(s["by_family"]) == {"total_goals", "match_result_3way", "handicap"}
    assert set(s["by_competition"]) == {"EPL", "UCL", "MLS"}
    assert s["by_family"]["total_goals"]["rows"] == 4
    assert s["by_family"]["match_result_3way"]["quote_state"]["two_sided"] == 0
    assert s["by_horizon_bucket"]["T-24h+"]["rows"] == 3  # A row 1 + C rows 1,2 (default 2000 min)
    assert s["by_horizon_bucket"]["unknown"]["rows"] == 1
    assert s["by_horizon_bucket"]["<10m"]["rows"] == 2  # B one-sided (5m) and C in-play (-3m)
    assert [t["bucket"] for t in s["toward_kickoff"]] == [
        "T-24h+",
        "T-6h..24h",
        "T-1h..6h",
        "T-10m..1h",
        "<10m",
        "unknown",
    ]
    assert "total_goals|T-1h..6h" in s["by_family_horizon"]

    # erased-edge share over executable sides (two-sided rows with verified fee -> 6 rows x 2 sides)
    assert s["mid_edge_erased_sides_n"] == 12
    assert 0.0 <= s["mid_edge_erased_share_3c"] <= 1.0
    assert s["mid_edge_erased_share_5c"] <= s["mid_edge_erased_share_3c"]

    # volume / OI use the last row per ticker: A=1000, B=None (last row), C=1000
    voi = s["volume_open_interest_by_family"]
    assert voi["total_goals"]["volume_total_last_row"] == 1000.0
    assert voi["match_result_3way"]["volume_total_last_row"] == 0.0

    # capture completeness: A gaps 10,20,60 -> median 20 max 60 ; C gaps 15,15 ; B has only 2 rows
    cad = s["capture_cadence"]
    assert cad["tickers_total"] == 3 and cad["tickers_with_3plus_rows"] == 2
    assert cad["gap_minutes_per_ticker_median"]["min"] == 15.0
    assert cad["gap_minutes_per_ticker_median"]["max"] == 20.0
    assert cad["gap_minutes_per_ticker_median"]["median"] == 17.5
    assert cad["gap_minutes_per_ticker_max"]["max"] == 60.0
    cov = s["capture_coverage"]
    assert cov["rows_by_utc_hour"]["18"] == 8 and cov["rows_by_utc_hour"]["19"] == 1
    assert cov["distinct_capture_timestamps"] == 6
    assert cov["rows_by_day"] == {"2026-09-27": 9}

    # stored labels vs recomputed (the 2026-09-27 mislabel lesson)
    hl = s["horizon_labels"]
    assert hl["stored_label_histogram"]["T-24h"] == 8
    assert hl["stored_vs_recomputed_mismatch_rows"] > 0

    # determinism: same input -> identical output apart from generated_at
    s2 = build_summary(snaps)
    s.pop("generated_at"), s2.pop("generated_at")
    assert canonical_json(s) == canonical_json(s2)


def test_since_filter_and_cli(tmp_path: Path):
    snaps = tmp_path / "snapshots"
    make_snapshots(snaps)
    # a second day, later
    later = [_row(A, T0 + timedelta(days=2))]
    _write(snaps / "2026-09-29" / "cap-9.jsonl", later)
    out = tmp_path / "micro.json"
    rc = main(
        [
            "microstructure",
            "--snapshots-dir",
            str(snaps),
            "--out",
            str(out),
            "--since",
            "2026-09-29",
        ]
    )
    assert rc == 0
    doc = json.loads(out.read_text())
    assert (
        doc["rows"] == 1 and doc["input"]["rows_before_since"] == 9 and doc["since"] == "2026-09-29"
    )
    assert doc["schema"] == "microstructure_summary_v1"


def test_missing_dir_is_empty_not_error(tmp_path: Path):
    s = build_summary(tmp_path / "nope")
    assert s["rows"] == 0 and s["tickers"] == 0 and s["spread_yes"]["n"] == 0
    assert s["quote_state"]["two_sided_share"] is None
    assert s["capture_cadence"]["tickers_with_3plus_rows"] == 0
