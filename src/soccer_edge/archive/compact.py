"""Archive compaction (remediation phase 22; audit §O).

Growth drivers measured by the audit: `priced_contracts.json` (~5.7 MB per run, duplicates the prediction
ledger), `coverage_diagnostics.json` (~0.9 MB per run, reconstructible), `latest.*` copies,
`last_fingerprints.json` rewritten per capture. Projection: 2.5-3.5 GB/year of git history.

This module does two things, both manifest-aware and both leaving the evidence intact:

1. `plan()` / `compact()` gzip the CLOSED day files (`.jsonl` -> `.jsonl.gz`, deterministic gzip) and
   record the change in the manifest: the entry keeps the pre-compaction byte length and prefix hash of
   the *uncompressed* content (verified by decompressing), plus the gzip file's own hash. Readers
   (`read_jsonl_any`) accept both forms, so settlement, recovery and verification keep working.
2. Nothing is deleted: a compacted file replaces its uncompressed twin in the same commit, and the
   manifest names the compaction id.

What is NOT done here, by design: git history is not rewritten. Deleting or compressing files only slows
future growth; the ~35 MB already in history stays. docs/ARCHIVE_COMPACTION.md records the implications
and the point at which a non-git backend is warranted.

The publishing workflows stop committing the redundant per-run copies (`priced_contracts.json`,
`coverage_diagnostics.json`, `runs/latest.*`) - they remain in the 14-day Actions artifact - which is the
larger saving (~70% of daily growth).
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from soccer_edge.archive.manifest import ArchiveManifest, ArchiveManifestError
from soccer_edge.core.serialization import write_json
from soccer_edge.core.time import iso_utc, utc_now


def gzip_bytes(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0) as fh:
        fh.write(data)
    return buf.getvalue()


def read_jsonl_any(path: Path) -> list[dict[str, Any]]:
    """Read `<name>.jsonl` or its compacted `<name>.jsonl.gz` twin (whichever exists)."""
    gz = path.with_suffix(path.suffix + ".gz") if path.suffix == ".jsonl" else path
    if path.exists():
        raw = path.read_bytes()
    elif gz.exists():
        raw = gzip.decompress(gz.read_bytes())
    else:
        return []
    return [json.loads(ln) for ln in raw.decode("utf-8").splitlines() if ln.strip()]


@dataclass(frozen=True)
class CompactionCandidate:
    path: str
    bytes_uncompressed: int
    day: str | None


def plan(root: Path, *, today: date | None = None) -> list[CompactionCandidate]:
    """Closed day `.jsonl` files (per the manifest's closed flag) that are still uncompressed."""
    man = ArchiveManifest(root)
    if not man.exists():
        raise ArchiveManifestError("compaction requires a manifest (verify + manifest first)")
    doc = man.load_files()
    out = []
    for rel, entry in doc["files"].items():
        if not rel.endswith(".jsonl") or not entry.get("closed") or entry.get("compacted"):
            continue
        if not (root / rel).exists():
            continue
        out.append(CompactionCandidate(rel, int(entry["byte_length"]), entry.get("day")))
    return out


def compact(
    root: Path, candidates: list[CompactionCandidate], *, today: date | None = None
) -> dict[str, Any]:
    """Gzip each candidate, verify the round trip against the manifest prefix, update the manifest entry,
    write `recovery/<compaction_id>.json`. Refuses when the archive does not verify first."""
    man = ArchiveManifest(root)
    rep = man.verify(today=today)
    if not rep.ok:
        raise ArchiveManifestError(
            f"refusing to compact an archive that does not verify: {rep.to_json()['problem_counts']}"
        )
    doc = man.load_files()
    files = doc["files"]
    compaction_id = "cmp-" + utc_now().strftime("%Y%m%dT%H%M%SZ")
    done = []
    saved = 0
    for c in candidates:
        src = root / c.path
        data = src.read_bytes()
        entry = files[c.path]
        if (
            len(data) != int(entry["byte_length"])
            or hashlib.sha256(data).hexdigest() != entry["sha256_prefix"]
        ):
            raise ArchiveManifestError(
                f"{c.path} does not match its manifest entry; not compacting"
            )
        gz = gzip_bytes(data)
        if gzip.decompress(gz) != data:
            raise ArchiveManifestError(f"{c.path}: gzip round trip failed")
        dst = src.with_suffix(src.suffix + ".gz")
        dst.write_bytes(gz)
        src.unlink()
        entry.update(
            {
                "compacted": True,
                "compaction_id": compaction_id,
                "compacted_path": c.path + ".gz",
                "gzip_sha256": hashlib.sha256(gz).hexdigest(),
                "gzip_bytes": len(gz),
            }
        )
        done.append({"path": c.path, "bytes": len(data), "gzip_bytes": len(gz)})
        saved += len(data) - len(gz)
    man._save_files(doc)
    manifest = {
        "schema": "archive_compaction_manifest_v1",
        "compaction_id": compaction_id,
        "applied_at": iso_utc(utc_now()),
        "files": done,
        "bytes_saved": saved,
        "policy": {"deletes_evidence": False, "rewrites_history": False, "readers_accept_gz": True},
    }
    write_json(root / "recovery" / f"{compaction_id}.json", manifest)
    return manifest
