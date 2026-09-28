from __future__ import annotations

import json
from pathlib import Path

from soccer_edge.cli import main
from soccer_edge.kalshi.reconcile import normalise, reconcile_fast_vs_full

FULL_T = "2026-09-27T23:37:39Z"
FAST_T = "2026-09-28T10:05:00Z"


def _series(ticker: str, *, swept: bool = True, fast_skip: bool = False) -> dict:
    reason = "soccer tag"
    if not swept:
        reason += (
            "; not swept (fast capture: no markets in last full discovery)"
            if fast_skip
            else "; not swept (no soccer wording)"
        )
    return {
        "ticker": ticker,
        "title": ticker,
        "category": "Sports",
        "tags": ["Soccer"],
        "fee_type": "quadratic",
        "fee_multiplier": "1",
        "ownership": "soccer",
        "ownership_reason": reason,
        "market_sweeps_complete": True,
        "event_sweep_complete": True,
        "swept": swept,
        "failures": [],
    }


def _market(
    ticker: str, *, status: str = "active", close_time: str = "2026-10-05T19:00:00Z"
) -> dict:
    return {
        "ticker": ticker,
        "event_ticker": ticker.rsplit("-", 1)[0],
        "status": status,
        "close_time": close_time,
    }


def _catalog(
    series: list[dict], markets: list[dict], *, statuses, finished_at, complete=True
) -> dict:
    return {
        "schema_version": 1,
        "run_id": f"disc-{finished_at}",
        "started_at": finished_at,
        "finished_at": finished_at,
        "statuses": list(statuses),
        "complete": complete,
        "counters": {"complete": complete, "contracts_discovered": len(markets)},
        "series": series,
        "events": [],
        "markets": markets,
        "specs": [],
    }


S1, S2, S3, S4 = "KXEPLTOTAL", "KXEPLBTTS", "KXUCLGAME", "KXNEWSERIES"
M1, M2 = "KXEPLTOTAL-26SEP28ARSCHE-3", "KXEPLTOTAL-26SEP28ARSCHE-2"
M3 = "KXUCLGAME-26SEP27MUNSBH-MUN"  # closes before the fast run
M4 = "KXEPLTOTAL-26OCT03LIVMCI-3"  # unopened in full; fast asks only for open
M5 = "KXNEWSERIES-26SEP29AAABBB-1"  # new since full


def full_catalog() -> dict:
    return _catalog(
        [_series(S1), _series(S2), _series(S3), _series("KXNFLGAME", swept=False)],
        [
            _market(M1),
            _market(M2),
            _market(M3, close_time="2026-09-27T19:00:00Z"),
            _market(M4, status="initialized"),
        ],
        statuses=("open", "unopened"),
        finished_at=FULL_T,
    )


def fast_catalog(markets: list[dict], *, skip: set[str] = frozenset({S2})) -> dict:
    series = [
        _series(S1, swept=S1 not in skip, fast_skip=True),
        _series(S2, swept=S2 not in skip, fast_skip=True),
        _series(S3, swept=S3 not in skip, fast_skip=True),
        _series(S4),
        _series("KXNFLGAME", swept=False),
    ]
    return _catalog(series, markets, statuses=("open",), finished_at=FAST_T)


def test_pass_all_missing_markets_explained():
    rep = reconcile_fast_vs_full(
        fast_catalog([_market(M1), _market(M2), _market(M5)]), full_catalog()
    )
    assert rep["schema"] == "discovery_reconcile_v1"
    assert rep["evidence_level"] == "market"
    assert rep["complete_relative_to_full"] is True
    assert rep["violations"] == []
    assert rep["series"]["skipped_by_fast"] == 1
    assert rep["series"]["skipped_by_fast_with_markets_in_full"] == 0
    assert rep["series"]["new_in_fast"] == 1
    mk = rep["markets"]
    assert mk["full_total"] == 4 and mk["fast_total"] == 3
    assert mk["in_both"] == 2 and mk["in_full_not_fast"] == 2 and mk["in_fast_not_full"] == 1
    assert mk["full_not_fast_breakdown"] == {
        "in_skipped_series": 0,
        "closed_between_runs": 1,
        "status_not_requested": 1,
        "unexplained": 0,
    }


def test_violation_fast_mode_missed_series_with_markets():
    # fast skipped S3 although S3 carried M3 in full (and M3 is even still open here)
    full = full_catalog()
    full["markets"][2]["close_time"] = "2026-10-05T19:00:00Z"
    rep = reconcile_fast_vs_full(fast_catalog([_market(M1), _market(M2)], skip={S2, S3}), full)
    assert rep["complete_relative_to_full"] is False
    kinds = [v["kind"] for v in rep["violations"]]
    assert kinds == ["fast_mode_missed"]
    v = rep["violations"][0]
    assert v["series"] == 1 and v["series_tickers"] == [S3] and v["markets"] == 1
    assert rep["series"]["skipped_by_fast_with_markets_in_full"] == 1
    assert rep["markets"]["full_not_fast_breakdown"]["in_skipped_series"] == 1
    assert rep["markets"]["full_not_fast_breakdown"]["unexplained"] == 0


def test_violation_unexplained_missing_market():
    # S1 swept by fast, but M2 (open, closes next week) is absent
    rep = reconcile_fast_vs_full(fast_catalog([_market(M1)]), full_catalog())
    assert rep["complete_relative_to_full"] is False
    assert [v["kind"] for v in rep["violations"]] == ["unexplained_missing_markets"]
    assert rep["violations"][0]["markets"] == 1
    assert rep["markets"]["full_not_fast_breakdown"]["unexplained"] == 1
    assert rep["markets"]["unexplained_by_series"] == {S1: 1}


def test_closed_status_counts_as_lifecycle_not_violation():
    full = full_catalog()
    full["markets"][1]["status"] = "settled"
    rep = reconcile_fast_vs_full(fast_catalog([_market(M1)]), full)
    assert rep["complete_relative_to_full"] is True
    assert rep["markets"]["full_not_fast_breakdown"]["closed_between_runs"] == 2


def test_index_shaped_full_gives_series_evidence():
    full_idx = {
        "run_id": "disc-x",
        "finished_at": FULL_T,
        "complete": True,
        "counters": {"contracts_discovered": 4},
        "series": [
            {
                k: s[k]
                for k in (
                    "ticker",
                    "title",
                    "tags",
                    "fee_type",
                    "fee_multiplier",
                    "ownership",
                    "ownership_reason",
                )
            }
            for s in full_catalog()["series"]
        ],
        "market_count": 4,
        "series_with_markets": [S1, S3],
    }
    side = normalise(full_idx)
    assert side.kind == "index" and side.markets is None and side.series_with_markets == {S1, S3}
    assert side.series_unswept_other == {"KXNFLGAME"}

    ok = reconcile_fast_vs_full(fast_catalog([_market(M1), _market(M2)]), full_idx)
    assert ok["evidence_level"] == "series" and ok["complete_relative_to_full"] is True
    assert ok["markets"]["in_both"] is None

    bad = reconcile_fast_vs_full(fast_catalog([_market(M1)], skip={S2, S3}), full_idx)
    assert bad["complete_relative_to_full"] is False
    assert [v["kind"] for v in bad["violations"]] == ["fast_mode_missed"]


def test_status_json_only_is_insufficient_and_incomplete_runs_fail():
    status = {
        "batch_id": "cap-1",
        "captured_at": FAST_T,
        "discovery_complete": True,
        "contracts_discovered": 3,
        "snapshots_written": 3,
        "counters": {"complete": True, "series_skipped_fast_mode": 1},
    }
    rep = reconcile_fast_vs_full(status, full_catalog())
    assert rep["evidence_level"] == "insufficient"
    assert rep["complete_relative_to_full"] is False
    assert [v["kind"] for v in rep["violations"]] == ["insufficient_evidence"]

    fast = fast_catalog([_market(M1), _market(M2)])
    fast["complete"] = False
    rep2 = reconcile_fast_vs_full(fast, full_catalog())
    assert [v["kind"] for v in rep2["violations"]] == ["fast_discovery_incomplete"]


def test_cli_exit_codes(tmp_path: Path):
    full_p, fast_p, out = tmp_path / "full.json", tmp_path / "fast.json", tmp_path / "rep.json"
    full_p.write_text(json.dumps(full_catalog()))
    fast_p.write_text(json.dumps(fast_catalog([_market(M1), _market(M2)])))
    assert (
        main(
            ["reconcile-discovery", "--fast", str(fast_p), "--full", str(full_p), "--out", str(out)]
        )
        == 0
    )
    rep = json.loads(out.read_text())
    assert rep["complete_relative_to_full"] is True

    fast_p.write_text(json.dumps(fast_catalog([_market(M1)])))
    assert (
        main(
            ["reconcile-discovery", "--fast", str(fast_p), "--full", str(full_p), "--out", str(out)]
        )
        == 1
    )
    assert json.loads(out.read_text())["complete_relative_to_full"] is False
