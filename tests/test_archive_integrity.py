"""Archive manifest / verifier / recovery (docs/PRELAUNCH_AUDIT.md B1, B13, §O, §P1)."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from soccer_edge.archive.ledger import PredictionLedger, WriteStatus
from soccer_edge.archive.manifest import (
    ArchiveManifest,
    ArchiveManifestError,
    classify_path,
    verify_archive,
)
from soccer_edge.archive.recover import (
    RecoveryError,
    apply_recovery,
    dry_run_report,
    scan_history,
)
from soccer_edge.core.serialization import canonical_json, write_json

TODAY = date(2026, 10, 1)


def _pred(run_id: str, ticker: str, p: float, day: str = "2026-09-28") -> dict:
    return {
        "schema": "prediction_record_v1",
        "run_id": run_id,
        "as_of": f"{day}T12:00:00Z",
        "ticker": ticker,
        "probability": {"fair_probability_mean": p},
    }


def _seed_archive(
    root: Path, *, day: str = "2026-09-28", run_id: str = "run-1", n: int = 3
) -> list[str]:
    led = PredictionLedger(root / "predictions")
    ids = []
    for i in range(n):
        rid, st = led.append(
            _pred(run_id, f"T{i}", 0.4 + i / 100, day), when=datetime(2026, 9, 28, 12, tzinfo=UTC)
        )
        assert st is WriteStatus.WRITTEN
        ids.append(rid)
    write_json(root / "runs" / day / run_id / "run_output.v1.json", {"run_id": run_id})
    (root / "weather").mkdir(exist_ok=True)
    (root / "weather" / f"{day}.jsonl").write_text(
        canonical_json(
            {
                "schema": "weather_snapshot_v1",
                "espn_event_id": "1",
                "captured_at": "x",
                "forecast_time_utc": "y",
            }
        )
        + "\n"
    )
    return ids


# ---------------------------------------------------------------- classification


def test_classify_paths():
    assert classify_path("predictions/2026-09-28/predictions.jsonl") == ("prediction", True, False)
    assert classify_path("settlements/2026-09-28/predictions.jsonl") == ("settlement", True, False)
    assert classify_path("snapshots/2026-09-28/cap-1.jsonl") == ("kalshi_snapshot", False, False)
    assert classify_path("runs/2026-09-28/run-1/run_output.v1.json") == ("run_output", False, True)
    # mutable pointers are not manifested
    assert classify_path("predictions/index.json") is None
    assert classify_path("runs/latest.run_output.v1.json") is None
    assert classify_path("evaluation/model_health.v1.json") is None
    assert classify_path("manifest/files.json") is None


# ---------------------------------------------------------------- manifest + verify


def test_bootstrap_then_verify_clean(tmp_path):
    _seed_archive(tmp_path)
    man = ArchiveManifest(tmp_path)
    assert not man.exists()
    stats = man.update(init=True, today=TODAY)
    assert stats["files_added"] == 3 and stats["records_added"] == 4
    rep = man.verify(today=TODAY)
    assert rep.ok and rep.records_checked == 4 and rep.unmanifested_files == []
    code, j = verify_archive(tmp_path, today=TODAY)
    assert code == 0 and j["ok"]


def test_verify_requires_manifest_by_default(tmp_path):
    _seed_archive(tmp_path)
    code, j = verify_archive(tmp_path, today=TODAY)
    assert code == 2 and not j["manifest_present"]
    code, j = verify_archive(tmp_path, require_manifest=False, today=TODAY)
    assert code == 0 and "UNVERIFIED" in j["note"]
    # without a manifest, intrinsic problems are reported but do not fail (nothing to enforce against yet)
    (tmp_path / "predictions" / "index.json").write_text(
        '{"pred_ghost": "2026-09-28/predictions.jsonl"}'
    )
    code, j = verify_archive(tmp_path, require_manifest=False, today=TODAY)
    assert code == 0 and j["problem_counts"] == {"index_dangling": 1, "index_missing_record": 3}


def test_deleting_a_prediction_line_fails_verify(tmp_path):
    ids = _seed_archive(tmp_path)
    ArchiveManifest(tmp_path).update(init=True, today=TODAY)
    f = tmp_path / "predictions" / "2026-09-28" / "predictions.jsonl"
    lines = f.read_text().splitlines()
    f.write_text("\n".join(lines[:1] + lines[2:]) + "\n")
    rep = ArchiveManifest(tmp_path).verify(today=TODAY)
    kinds = {p["kind"] for p in rep.problems}
    assert {"file_shrunk", "record_missing", "index_dangling"} <= kinds
    assert any(p.get("record_id") == ids[1] for p in rep.problems if p["kind"] == "record_missing")
    # a corrupt archive can never be re-manifested as healthy
    with pytest.raises(ArchiveManifestError):
        ArchiveManifest(tmp_path).update(today=TODAY)


def test_rewriting_a_record_in_place_fails_verify(tmp_path):
    _seed_archive(tmp_path)
    ArchiveManifest(tmp_path).update(init=True, today=TODAY)
    f = tmp_path / "predictions" / "2026-09-28" / "predictions.jsonl"
    f.write_text(f.read_text().replace("0.41", "0.91"))
    rep = ArchiveManifest(tmp_path).verify(today=TODAY)
    kinds = {p["kind"] for p in rep.problems}
    assert "file_prefix_rewritten" in kinds
    assert "record_rewritten" in kinds  # the id no longer re-hashes


def test_appending_to_an_open_day_is_allowed_and_manifest_extends(tmp_path):
    _seed_archive(tmp_path)
    man = ArchiveManifest(tmp_path)
    man.update(init=True, today=date(2026, 9, 28))
    led = PredictionLedger(tmp_path / "predictions")
    led.append(_pred("run-1", "T9", 0.7), when=datetime(2026, 9, 28, 13, tzinfo=UTC))
    assert man.verify(today=date(2026, 9, 28)).ok
    stats = man.update(today=date(2026, 9, 28))
    assert stats["files_extended"] == 1 and stats["records_added"] == 1
    assert man.verify(today=date(2026, 9, 28)).records_checked == 5


def test_appending_to_a_closed_day_fails_unless_recorded_recovery(tmp_path):
    _seed_archive(tmp_path)
    man = ArchiveManifest(tmp_path)
    man.update(init=True, today=TODAY)  # 2026-09-28 is closed on 2026-10-01
    f = tmp_path / "weather" / "2026-09-28.jsonl"
    f.write_text(
        f.read_text()
        + canonical_json(
            {
                "schema": "weather_snapshot_v1",
                "espn_event_id": "2",
                "captured_at": "x",
                "forecast_time_utc": "y",
            }
        )
        + "\n"
    )
    rep = man.verify(today=TODAY)
    assert [p["kind"] for p in rep.problems] == ["closed_file_appended"]
    # a recorded recovery may extend the closed file and the entry names the recovery id
    stats = man.update(
        today=TODAY, recovery_id="rec-x", recovered_paths={"weather/2026-09-28.jsonl"}
    )
    assert stats["files_extended"] == 1
    assert man.load_files()["files"]["weather/2026-09-28.jsonl"]["recovery_id"] == "rec-x"
    assert man.verify(today=TODAY).ok


def test_immutable_run_output_modification_fails(tmp_path):
    _seed_archive(tmp_path)
    man = ArchiveManifest(tmp_path)
    man.update(init=True, today=TODAY)
    p = tmp_path / "runs" / "2026-09-28" / "run-1" / "run_output.v1.json"
    p.write_text(p.read_text() + " ")
    assert [x["kind"] for x in man.verify(today=TODAY).problems] == ["closed_file_appended"]
    p.write_text(p.read_text().replace("run-1", "run-X"))  # same length, different bytes
    assert "file_prefix_rewritten" in {x["kind"] for x in man.verify(today=TODAY).problems}


def test_broken_references_are_reported(tmp_path):
    ids = _seed_archive(tmp_path)
    # a settlement pointing at an unknown prediction; a prediction whose run output is gone
    stl = PredictionLedger(tmp_path / "settlements")
    stl.append(
        {"schema": "settlement_record_v1", "prediction_record_id": "pred_nope", "settled_at": "x"}
    )
    stl.append(
        {"schema": "settlement_record_v1", "prediction_record_id": ids[0], "settled_at": "x"}
    )
    man = ArchiveManifest(tmp_path)
    man.update(init=True, today=TODAY)
    assert "prediction_reference_broken" in {p["kind"] for p in man.verify(today=TODAY).problems}
    (tmp_path / "runs" / "2026-09-28" / "run-1" / "run_output.v1.json").unlink()
    kinds = {p["kind"] for p in man.verify(today=TODAY).problems}
    assert {"run_reference_broken", "missing_file"} <= kinds


def test_duplicate_id_with_different_payload_is_a_conflict(tmp_path):
    _seed_archive(tmp_path)
    f = tmp_path / "predictions" / "2026-09-28" / "predictions.jsonl"
    first = json.loads(f.read_text().splitlines()[0])
    forged = {
        **first,
        "probability": {"fair_probability_mean": 0.99},
    }  # same record_id, different body
    f.write_text(f.read_text() + canonical_json(forged) + "\n")
    rep = ArchiveManifest(tmp_path).verify(today=TODAY)
    kinds = {p["kind"] for p in rep.problems}
    assert "duplicate_id_conflict" in kinds and "record_rewritten" in kinds


def test_ledger_tolerates_index_without_day_file(tmp_path):
    led = PredictionLedger(tmp_path)
    rid, _ = led.append({"ticker": "A", "p": 0.5}, when=datetime(2026, 9, 28, tzinfo=UTC))
    # simulate the run-soccer restore: index kept, day file not restored
    (tmp_path / "2026-09-28" / "predictions.jsonl").unlink()
    rid2, st = led.append({"ticker": "A", "p": 0.5}, when=datetime(2026, 9, 28, tzinfo=UTC))
    assert rid2 == rid and st is WriteStatus.NO_OP


# ---------------------------------------------------------------- recovery from git history


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True)


def _commit(repo: Path, msg: str) -> None:
    _git(repo, "add", "-A")
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", msg],
        check=True,
    )


@pytest.fixture
def history(tmp_path):
    """An archive branch whose second publish overwrote the first run's rows (the B1 pattern)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "data-archive")
    day = repo / "predictions" / "2026-09-28"
    day.mkdir(parents=True)
    run1 = [_pred("run-1", f"A{i}", 0.3 + i / 100) for i in range(4)]
    rows1 = [
        {**r, "record_id": PredictionLedger.record_id(r), "archived_at": r["as_of"]} for r in run1
    ]
    (day / "predictions.jsonl").write_text("".join(canonical_json(r) + "\n" for r in rows1))
    write_json(repo / "runs" / "2026-09-28" / "run-1" / "run_output.v1.json", {"run_id": "run-1"})
    _commit(repo, "run-1")
    run2 = [_pred("run-2", f"B{i}", 0.5 + i / 100) for i in range(2)]
    rows2 = [
        {**r, "record_id": PredictionLedger.record_id(r), "archived_at": r["as_of"]} for r in run2
    ]
    (day / "predictions.jsonl").write_text(
        "".join(canonical_json(r) + "\n" for r in rows2)
    )  # overwrite!
    write_json(repo / "runs" / "2026-09-28" / "run-2" / "run_output.v1.json", {"run_id": "run-2"})
    idx = {r["record_id"]: "2026-09-28/predictions.jsonl" for r in rows1 + rows2}
    (repo / "predictions" / "index.json").write_text(json.dumps(idx, sort_keys=True))
    _commit(repo, "run-2 (overwrote run-1)")
    return repo, rows1, rows2


def test_recovery_dry_run_counts_and_origins(history):
    repo, rows1, rows2 = history
    recs = scan_history(repo, "data-archive")
    report = dry_run_report(recs, repo=repo, branch="data-archive")
    assert not report["refused"] and report["recoverable_lines_total"] == 4
    (pth,) = report["paths"]
    assert pth["union_lines"] == 6 and pth["tip_lines"] == 2 and pth["recoverable_lines"] == 4
    (grp,) = pth["groups"]
    assert grp["run_ids"] == ["run-1"] and grp["n_lines"] == 4
    assert grp["origin_commit"] == _git(repo, "rev-list", "--max-parents=0", "data-archive").strip()


def test_recovery_apply_appends_and_never_overwrites(history):
    repo, rows1, rows2 = history
    wt = repo  # apply into the working tree of the tip
    recs = scan_history(repo, "data-archive", tip_root=wt)
    report = dry_run_report(recs, repo=repo, branch="data-archive")
    manifest = apply_recovery(recs, archive_root=wt, report=report)
    f = wt / "predictions" / "2026-09-28" / "predictions.jsonl"
    lines = [json.loads(ln) for ln in f.read_text().splitlines()]
    # surviving rows first and untouched, recovered rows appended in original order with original bytes
    assert [r["ticker"] for r in lines] == ["B0", "B1", "A0", "A1", "A2", "A3"]
    assert lines[2:] == rows1
    assert (
        manifest["lines_appended_total"] == 4
        and manifest["policy"]["recomputed_probabilities"] is False
    )
    (rec_manifest,) = list((wt / "recovery").glob("*.json"))
    assert json.loads(rec_manifest.read_text())["groups"][0]["origin_blob"]
    # idempotent: a second scan finds nothing to recover
    again = dry_run_report(
        scan_history(repo, "data-archive", tip_root=wt), repo=repo, branch="data-archive"
    )
    assert again["recoverable_lines_total"] == 0
    # and the recovered tree verifies once manifested
    man = ArchiveManifest(wt)
    man.update(init=True, today=TODAY)
    assert man.verify(today=TODAY).ok


def test_recovery_refuses_on_conflicting_identity(history):
    repo, rows1, rows2 = history
    # forge history: same record_id as a run-1 row but a different payload, in a third commit
    forged = {**rows1[0], "probability": {"fair_probability_mean": 0.99}}
    f = repo / "predictions" / "2026-09-28" / "predictions.jsonl"
    f.write_text(f.read_text() + canonical_json(forged) + "\n")
    _commit(repo, "forged")
    recs = scan_history(repo, "data-archive")
    report = dry_run_report(recs, repo=repo, branch="data-archive")
    assert report["refused"] and report["unverifiable_total"] == 1  # forged row does not re-hash
    with pytest.raises(RecoveryError):
        apply_recovery(recs, archive_root=repo, report=report)
    # genuine conflict: two self-verifying rows can only differ in archived_at
    f.write_text(
        "".join(canonical_json(r) + "\n" for r in rows2)
        + canonical_json({**rows1[0], "archived_at": "2026-09-28T13:00:00Z"})
        + "\n"
    )
    _commit(repo, "conflict")
    report = dry_run_report(scan_history(repo, "data-archive"), repo=repo, branch="data-archive")
    assert report["refused"] and report["conflicts_total"] == 1
