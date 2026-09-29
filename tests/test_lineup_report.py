"""Lineup capture reliability report (phase 18)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from soccer_edge.evaluation.lineups import lead_time_report

KO = datetime(2026, 10, 3, 19, 0, tzinfo=UTC)


def _row(eid, minutes_before, published, state="unconfirmed", league="eng.1"):
    return {
        "schema": "espn_lineup_snapshot_v1",
        "provider": "espn_site_api",
        "espn_event_id": eid,
        "league": league,
        "kickoff_utc": KO.isoformat(),
        "captured_at": (KO - timedelta(minutes=minutes_before)).isoformat(),
        "published": published,
        "lineup_state": state,
    }


def test_lead_time_report_counts_and_distribution():
    rows = [
        _row("1", 600, False),
        _row("1", 75, True, "confirmed"),  # first XI 75 min before kickoff
        _row("1", 30, True, "confirmed"),
        _row("2", 400, False),
        _row("2", -1, True, "post_hoc"),  # first XI one minute AFTER kickoff
        _row("3", 200, False),  # never published
        _row("4", 25, True, "confirmed", league="usa.1"),
    ]
    rep = lead_time_report(rows, as_of=KO + timedelta(hours=3))
    assert rep["fixtures_tracked"] == 4 and rep["fixtures_kickoff_passed"] == 4
    assert (
        rep["with_any_xi"] == 3
        and rep["with_pre_kickoff_xi"] == 2
        and rep["post_kickoff_first_xi"] == 1
    )
    assert rep["with_xi_ge_20min_before_kickoff"] == 2 and rep["share_xi_ge_20min"] == 0.5
    assert (
        rep["lead_time_minutes"]["n"] == 2
        and rep["lead_time_minutes"]["min"] == 25
        and rep["lead_time_minutes"]["max"] == 75
    )
    f1 = next(f for f in rep["fixtures"] if f["espn_event_id"] == "1")
    assert (
        f1["capture_attempts"] == 3
        and f1["lead_time_seconds"] == 75 * 60
        and f1["observed_before_kickoff"]
    )
    assert rep["by_competition"]["usa.1"]["with_xi_ge_20min"] == 1
    # fixtures whose kickoff has not passed are tracked but not scored
    rep2 = lead_time_report(rows, as_of=KO - timedelta(hours=1))
    assert rep2["fixtures_kickoff_passed"] == 0 and rep2["fixtures_tracked"] == 4


def test_backfilled_history_rows_are_not_capture_attempts(tmp_path):
    import json

    from soccer_edge.evaluation.lineups import lineup_rows

    live = tmp_path / "lineups" / "2026-10-10"
    live.mkdir(parents=True)
    hist = tmp_path / "lineups" / "history"
    hist.mkdir()
    row = {"schema": "espn_lineup_snapshot_v1", "espn_event_id": "1", "league": "eng.1"}
    (live / "eng.1.jsonl").write_text(json.dumps(row) + "\n")
    (hist / "eng.1.jsonl").write_text(
        json.dumps({**row, "espn_event_id": "2", "backfill": True, "lineup_state": "post_hoc"})
        + "\n"
    )
    (live / "esp.1.jsonl").write_text(
        json.dumps({**row, "espn_event_id": "3", "backfill": True, "league": "esp.1"}) + "\n"
    )
    assert [r["espn_event_id"] for r in lineup_rows(tmp_path)] == ["1"]
    assert len(lineup_rows(tmp_path, include_backfill=True)) == 3
