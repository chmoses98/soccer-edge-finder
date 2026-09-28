"""Archive compaction (phase 22): gzip closed day files without losing evidence or verification."""

from __future__ import annotations

import gzip
from datetime import UTC, date, datetime

import pytest

from soccer_edge.archive.compact import compact, plan, read_jsonl_any
from soccer_edge.archive.ledger import PredictionLedger
from soccer_edge.archive.manifest import ArchiveManifest, ArchiveManifestError
from soccer_edge.core.serialization import write_json

TODAY = date(2026, 10, 10)


def _seed(root):
    led = PredictionLedger(root / "predictions")
    ids = []
    for i in range(4):
        rid, _ = led.append(
            {
                "schema": "prediction_record_v1",
                "run_id": "run-1",
                "as_of": "2026-09-28T12:00:00Z",
                "ticker": f"T{i}",
            },
            when=datetime(2026, 9, 28, 12, tzinfo=UTC),
        )
        ids.append(rid)
    led.append(
        {
            "schema": "prediction_record_v1",
            "run_id": "run-1",
            "as_of": "2026-10-09T12:00:00Z",
            "ticker": "open",
        },
        when=datetime(2026, 10, 9, 12, tzinfo=UTC),
    )
    write_json(root / "runs" / "2026-09-28" / "run-1" / "run_output.v1.json", {"run_id": "run-1"})
    return ids


def test_compaction_keeps_verification_and_readers_working(tmp_path):
    ids = _seed(tmp_path)
    man = ArchiveManifest(tmp_path)
    man.update(init=True, today=TODAY)
    cands = plan(tmp_path, today=TODAY)
    assert [c.path for c in cands] == [
        "predictions/2026-09-28/predictions.jsonl"
    ]  # 10-09 is still open
    rep = compact(tmp_path, cands, today=TODAY)
    assert (
        rep["files"][0]["gzip_bytes"] < rep["files"][0]["bytes"]
        and rep["policy"]["deletes_evidence"] is False
    )
    assert not (tmp_path / "predictions/2026-09-28/predictions.jsonl").exists()
    gz = tmp_path / "predictions/2026-09-28/predictions.jsonl.gz"
    assert gz.exists()
    # manifest verifies the compacted file through its gzip twin, and the record-level checks still run
    v = man.verify(today=TODAY)
    assert v.ok, v.problems
    assert v.records_checked == 5
    # readers accept both forms
    rows = read_jsonl_any(tmp_path / "predictions/2026-09-28/predictions.jsonl")
    assert [r["record_id"] for r in rows] == ids
    # a second plan finds nothing; manifest update is a no-op on the compacted entry
    assert plan(tmp_path, today=TODAY) == []
    assert man.update(today=TODAY)["files_extended"] == 0


def test_tampering_with_a_compacted_file_is_detected(tmp_path):
    _seed(tmp_path)
    man = ArchiveManifest(tmp_path)
    man.update(init=True, today=TODAY)
    compact(tmp_path, plan(tmp_path, today=TODAY), today=TODAY)
    gz = tmp_path / "predictions/2026-09-28/predictions.jsonl.gz"
    data = gzip.decompress(gz.read_bytes()).decode().splitlines()
    gz.write_bytes(gzip.compress(("\n".join(data[:-1]) + "\n").encode()))
    kinds = {p["kind"] for p in man.verify(today=TODAY).problems}
    assert "compacted_file_rewritten" in kinds
    # and the index now dangles for the dropped record
    assert "index_dangling" in kinds


def test_compaction_refuses_without_manifest_or_on_corruption(tmp_path):
    _seed(tmp_path)
    with pytest.raises(ArchiveManifestError):
        plan(tmp_path, today=TODAY)
    man = ArchiveManifest(tmp_path)
    man.update(init=True, today=TODAY)
    f = tmp_path / "predictions/2026-09-28/predictions.jsonl"
    f.write_text("".join(f.read_text().splitlines(keepends=True)[1:]))
    with pytest.raises(ArchiveManifestError):
        compact(tmp_path, plan(tmp_path, today=TODAY), today=TODAY)
