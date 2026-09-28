"""Durable archive manifest + verifier for the append-only `data-archive` tree.

Why
---
The prediction ledger's `verify()` re-hashes the rows that survive; it cannot see a row that was deleted
(audit B1/B13: 830 prediction rows of one run were overwritten by the next publish and nothing noticed).
This module records what the archive *should* contain so that deletion, rewriting and dangling references
fail loudly.

Design
------
Every archived file is append-only (jsonl day files) or immutable (run outputs, fixture dumps, recovery
manifests). For an append-only file the manifest stores the byte length and the sha256 of that byte prefix
at manifest time; the file may only grow, so a later verification re-hashes the same prefix. Any deleted,
edited or reordered line inside the manifested prefix changes the prefix hash. For an immutable file the
whole content hash must match exactly. A day file whose UTC day is older than the closing grace is
*closed*: its length must equal the manifested length (nothing may be appended to a closed day except
through a recorded recovery, which updates the manifest entry and names the recovery manifest).

Evidence records (predictions, settlements, lineups, weather) additionally get one manifest row each:

    record_id, record_type, run_id, captured_at, content_hash, archive_path, schema_version

so the verifier can name exactly which record is missing, rewritten or duplicated, check that every
prediction id in `predictions/index.json` has a row, and that every prediction's `run_id` has an archived
run output and every settlement's `prediction_record_id` has a prediction.

Layout (relative to the archive root):

    manifest/files.json              file table (mutable, rewritten by `archive manifest`)
    manifest/records/<day>.jsonl     append-only record rows, one file per archive day (or `undated`)

Mutable pointer files (`index.json`, `last_*.json`, `STATUS.json`, `latest.*`, `evaluation/*`, caches)
are deliberately not manifested: they are rebuildable and are checked for *consistency* instead.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from soccer_edge.archive.ledger import PredictionLedger
from soccer_edge.core.serialization import canonical_json, read_json_or, write_json
from soccer_edge.core.time import iso_utc, utc_now

MANIFEST_VERSION = 1
FILES_PATH = "manifest/files.json"
RECORDS_DIR = "manifest/records"
CLOSE_GRACE_DAYS = 2  # a day file older than this (UTC) is closed: no more appends
CONTENT_HASH_HEX = 24  # 96 bits of the sha256 of the raw line bytes

_DAY_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

# (glob, record_type, record_level, immutable)
_RULES: tuple[tuple[str, str, bool, bool], ...] = (
    ("predictions/*/predictions.jsonl", "prediction", True, False),
    ("settlements/*/predictions.jsonl", "settlement", True, False),
    ("lineups/*/*.jsonl", "lineup", True, False),
    ("weather/*.jsonl", "weather", True, False),
    ("results/espn/*.jsonl", "result", False, False),
    ("snapshots/*/*.jsonl", "kalshi_snapshot", False, False),
    ("reference/*/*.jsonl", "reference", False, False),
    ("runs/*/*/*.json", "run_output", False, True),
    ("runs/*/*/*.md", "run_output", False, True),
    ("fixtures/espn/*/*.json", "espn_fixtures", False, True),
    ("recovery/*.json", "recovery_manifest", False, True),
)

_MUTABLE_GLOBS = (
    "*/index.json",
    "*/last_*.json",
    "*/STATUS.json",
    "*/BACKFILL_STATUS.json",
    "*/reconcile.json",
    "runs/latest.*",
    "runs/LATEST_*",
    "evaluation/*",
    "weather/geocode_cache.json",
    "README.md",
    "manifest/*",
    "manifest/*/*",
)


def line_hash(raw: bytes) -> str:
    return hashlib.sha256(raw.rstrip(b"\r\n")).hexdigest()[:CONTENT_HASH_HEX]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def classify_path(rel: str) -> tuple[str, bool, bool] | None:
    """(record_type, record_level, immutable) for an archive path, or None when the path is mutable /
    unknown and therefore not manifested."""
    for g in _MUTABLE_GLOBS:
        if fnmatch.fnmatch(rel, g):
            return None
    for g, rtype, rec_level, immutable in _RULES:
        if fnmatch.fnmatch(rel, g):
            return rtype, rec_level, immutable
    return None


def path_day(rel: str) -> str | None:
    m = _DAY_RE.search(rel)
    return m.group(1) if m else None


def _record_fields(
    rtype: str, rec: dict[str, Any]
) -> tuple[str | None, str | None, str | None, str | None]:
    """(record_id, run_id, captured_at, schema_version) for an evidence row."""
    if rtype == "prediction":
        return rec.get("record_id"), rec.get("run_id"), rec.get("as_of"), rec.get("schema")
    if rtype == "settlement":
        return (
            rec.get("record_id"),
            rec.get("prediction_record_id"),
            rec.get("settled_at"),
            rec.get("schema"),
        )
    if rtype in ("lineup", "weather"):
        return None, None, rec.get("captured_at"), rec.get("schema")
    return None, None, None, rec.get("schema")


@dataclass
class VerifyReport:
    archive_root: str
    verified_at: str
    manifest_present: bool
    files_checked: int = 0
    records_checked: int = 0
    unmanifested_files: list[str] = field(default_factory=list)
    problems: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def problem(self, kind: str, path: str, **detail: Any) -> None:
        self.problems.append({"kind": kind, "path": path, **detail})

    def warn(self, kind: str, path: str, **detail: Any) -> None:
        self.warnings.append({"kind": kind, "path": path, **detail})

    def to_json(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for p in self.problems:
            counts[p["kind"]] = counts.get(p["kind"], 0) + 1
        return {
            "archive_root": self.archive_root,
            "verified_at": self.verified_at,
            "manifest_present": self.manifest_present,
            "ok": self.ok,
            "files_checked": self.files_checked,
            "records_checked": self.records_checked,
            "problem_counts": counts,
            "problems": self.problems[:500],
            "n_problems": len(self.problems),
            "warnings": self.warnings[:200],
            "n_warnings": len(self.warnings),
            "unmanifested_files": self.unmanifested_files[:200],
            "n_unmanifested_files": len(self.unmanifested_files),
        }


class ArchiveManifest:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    # ------------------------------------------------------------------ storage
    @property
    def files_path(self) -> Path:
        return self.root / FILES_PATH

    def exists(self) -> bool:
        return self.files_path.exists()

    def load_files(self) -> dict[str, Any]:
        doc = read_json_or(self.files_path, None)
        if doc is None:
            return {"manifest_version": MANIFEST_VERSION, "updated_at": None, "files": {}}
        return doc

    def _save_files(self, doc: dict[str, Any]) -> None:
        doc["manifest_version"] = MANIFEST_VERSION
        doc["updated_at"] = iso_utc(utc_now())
        doc["files"] = dict(sorted(doc["files"].items()))
        write_json(self.files_path, doc)

    def _records_file(self, day: str | None) -> Path:
        return self.root / RECORDS_DIR / f"{day or 'undated'}.jsonl"

    def iter_record_rows(self):
        d = self.root / RECORDS_DIR
        if not d.exists():
            return
        for p in sorted(d.glob("*.jsonl")):
            with p.open("rb") as fh:
                for raw in fh:
                    if raw.strip():
                        yield json.loads(raw)

    # ------------------------------------------------------------------ scanning
    def archive_files(self) -> list[str]:
        out = []
        for p in sorted(self.root.rglob("*")):
            if p.is_file() and ".git" not in p.parts:
                out.append(p.relative_to(self.root).as_posix())
        return out

    @staticmethod
    def is_closed(day: str | None, *, today: date) -> bool:
        if day is None:
            return False
        try:
            d = date.fromisoformat(day)
        except ValueError:
            return False
        return d < today - timedelta(days=CLOSE_GRACE_DAYS)

    # ------------------------------------------------------------------ update
    def update(
        self,
        *,
        today: date | None = None,
        init: bool = False,
        recovery_id: str | None = None,
        recovered_paths: set[str] | None = None,
    ) -> dict[str, Any]:
        """Extend the manifest to cover the current archive state.

        Refuses (raises `ArchiveManifestError`) when the existing manifest does not verify: a corrupt
        archive must never be re-manifested as if it were healthy. With `recovery_id`, the named paths may
        grow even when closed (a recorded recovery), and the entries record the recovery id.
        """
        today = today or utc_now().date()
        if not self.exists() and not init:
            raise ArchiveManifestError("no manifest present; run with init=True to bootstrap")
        doc = self.load_files()
        if self.exists():
            rep = self.verify(today=today, allow_recovered=recovered_paths or set())
            if not rep.ok:
                raise ArchiveManifestError(
                    f"refusing to update a manifest that does not verify: {rep.to_json()['problem_counts']}"
                )
        files = doc["files"]
        added_files = 0
        extended_files = 0
        added_records = 0
        new_rows_by_day: dict[str | None, list[dict[str, Any]]] = {}
        for rel in self.archive_files():
            cls = classify_path(rel)
            if cls is None:
                continue
            rtype, rec_level, immutable = cls
            data = (self.root / rel).read_bytes()
            entry = files.get(rel)
            day = path_day(rel)
            if entry is None:
                start = 0
                added_files += 1
            else:
                start = int(entry["byte_length"])
                if len(data) == start:
                    # unchanged: only the closed flag may move
                    entry["closed"] = immutable or self.is_closed(day, today=today)
                    continue
                extended_files += 1
            if rec_level:
                rows = self._record_rows(rel, rtype, data, start)
                new_rows_by_day.setdefault(day, []).extend(rows)
                added_records += len(rows)
            files[rel] = {
                "record_type": rtype,
                "record_level": rec_level,
                "immutable": immutable,
                "day": day,
                "byte_length": len(data),
                "sha256_prefix": _sha256_bytes(data),
                "line_count": sum(1 for ln in data.split(b"\n") if ln.strip())
                if rel.endswith(".jsonl")
                else None,
                "closed": immutable or self.is_closed(day, today=today),
                "first_manifested_at": (entry or {}).get("first_manifested_at")
                or iso_utc(utc_now()),
                "recovery_id": recovery_id
                if (recovered_paths and rel in recovered_paths)
                else (entry or {}).get("recovery_id"),
            }
        for day, rows in new_rows_by_day.items():
            p = self._records_file(day)
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("a", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(canonical_json(r) + "\n")
        self._save_files(doc)
        return {
            "files_added": added_files,
            "files_extended": extended_files,
            "records_added": added_records,
            "files_total": len(files),
        }

    @staticmethod
    def _record_rows(rel: str, rtype: str, data: bytes, start: int) -> list[dict[str, Any]]:
        rows = []
        for raw in data[start:].split(b"\n"):
            if not raw.strip():
                continue
            rec = json.loads(raw)
            rid, run_id, captured_at, schema = _record_fields(rtype, rec)
            h = line_hash(raw)
            rows.append(
                {
                    "record_id": rid or f"{rtype}_{h}",
                    "record_type": rtype,
                    "run_id": run_id,
                    "captured_at": captured_at,
                    "content_hash": h,
                    "archive_path": rel,
                    "schema_version": schema,
                }
            )
        return rows

    # ------------------------------------------------------------------ verify
    def verify(
        self, *, today: date | None = None, allow_recovered: set[str] | None = None
    ) -> VerifyReport:
        today = today or utc_now().date()
        allow_recovered = allow_recovered or set()
        rep = VerifyReport(str(self.root), iso_utc(utc_now()), manifest_present=self.exists())
        doc = self.load_files()
        files = doc["files"]
        present = set(self.archive_files())
        # 1. file table: existence, prefix integrity, closed-day immutability
        for rel, entry in files.items():
            rep.files_checked += 1
            if rel not in present:
                rep.problem("missing_file", rel, record_type=entry.get("record_type"))
                continue
            data = (self.root / rel).read_bytes()
            n = int(entry["byte_length"])
            if len(data) < n:
                rep.problem("file_shrunk", rel, manifested_bytes=n, current_bytes=len(data))
                continue
            if _sha256_bytes(data[:n]) != entry["sha256_prefix"]:
                rep.problem("file_prefix_rewritten", rel, manifested_bytes=n)
                continue
            if (
                len(data) > n
                and (entry.get("immutable") or entry.get("closed"))
                and rel not in allow_recovered
            ):
                rep.problem(
                    "closed_file_appended", rel, manifested_bytes=n, current_bytes=len(data)
                )
        # 2. unmanifested files (informational unless the archive is expected to be complete)
        for rel in sorted(present):
            if classify_path(rel) is not None and rel not in files:
                rep.unmanifested_files.append(rel)
        # 3. record-level consistency
        manifest_rows = list(self.iter_record_rows()) if rep.manifest_present else []
        self._verify_records(rep, files, manifest_rows)
        return rep

    def _verify_records(
        self, rep: VerifyReport, files: dict[str, Any], manifest_rows: list[dict[str, Any]]
    ) -> None:
        # read every record-level file that exists (manifested or not) once
        by_path_hashes: dict[str, set[str]] = {}
        ids_seen: dict[str, dict[str, str]] = {}  # record_type -> id -> line hash
        predictions_by_id: dict[str, tuple[str, dict[str, Any]]] = {}
        settlement_refs: list[tuple[str, str]] = []
        run_ids: dict[str, str] = {}
        for rel in self.archive_files():
            cls = classify_path(rel)
            if cls is None or not cls[1]:
                continue
            rtype = cls[0]
            hashes: set[str] = set()
            with (self.root / rel).open("rb") as fh:
                for raw in fh:
                    if not raw.strip():
                        continue
                    try:
                        rec = json.loads(raw)
                    except ValueError:
                        rep.problem("unparsable_line", rel, content_hash=line_hash(raw))
                        continue
                    h = line_hash(raw)
                    if h in hashes:
                        rep.warn("duplicate_line", rel, content_hash=h)
                    hashes.add(h)
                    rid, run_id, _, _ = _record_fields(rtype, rec)
                    if rtype in ("prediction", "settlement"):
                        if rid is None:
                            rep.problem("record_without_id", rel, content_hash=h)
                            continue
                        if PredictionLedger.record_id(rec) != rid:
                            rep.problem("record_rewritten", rel, record_id=rid)
                        prev = ids_seen.setdefault(rtype, {}).get(rid)
                        if prev is not None and prev != h:
                            rep.problem("duplicate_id_conflict", rel, record_id=rid)
                        ids_seen[rtype][rid] = h
                        if rtype == "prediction":
                            predictions_by_id[rid] = (rel, rec)
                            if run_id:
                                run_ids[run_id] = rel
                        else:
                            settlement_refs.append((rid, rec.get("prediction_record_id")))
            by_path_hashes[rel] = hashes
        # manifest rows must all still be present
        for row in manifest_rows:
            rep.records_checked += 1
            rel = row["archive_path"]
            hashes = by_path_hashes.get(rel)
            if hashes is None:
                if rel not in files or rel not in set(self.archive_files()):
                    continue  # already reported as missing_file
                hashes = set()
            if row["content_hash"] not in hashes:
                rep.problem(
                    "record_missing",
                    rel,
                    record_id=row["record_id"],
                    record_type=row["record_type"],
                )
        # predictions index consistency (index is mutable; it must agree with the files)
        idx_path = self.root / "predictions" / "index.json"
        if idx_path.exists():
            idx = read_json_or(idx_path, {})
            for rid, rel in idx.items():
                if rid not in predictions_by_id:
                    rep.problem("index_dangling", f"predictions/{rel}", record_id=rid)
            for rid, (rel, _) in predictions_by_id.items():
                if rid not in idx:
                    rep.problem("index_missing_record", rel, record_id=rid)
        # run references
        runs_root = self.root / "runs"
        run_dirs = (
            {p.parent.name for p in runs_root.glob("*/*/run_output.v1.json")}
            if runs_root.exists()
            else set()
        )
        for run_id, rel in run_ids.items():
            if run_id not in run_dirs:
                rep.problem("run_reference_broken", rel, run_id=run_id)
        for sid, pid in settlement_refs:
            if pid not in predictions_by_id:
                rep.problem(
                    "prediction_reference_broken",
                    "settlements",
                    settlement_record_id=sid,
                    prediction_record_id=pid,
                )


class ArchiveManifestError(Exception):
    pass


def verify_archive(
    root: Path, *, require_manifest: bool = True, today: date | None = None
) -> tuple[int, dict[str, Any]]:
    """Return (exit_code, report). exit 0 = ok; 1 = corruption; 2 = no manifest (when required)."""
    man = ArchiveManifest(root)
    if not man.exists():
        if require_manifest:
            return 2, {"ok": False, "manifest_present": False, "error": "no manifest present"}
        rep = man.verify(today=today)
        j = rep.to_json()
        j["note"] = (
            "no manifest present: intrinsic record checks only, reported but NOT enforced (UNVERIFIED); "
            "bootstrap the manifest (archive-recover.yml init_manifest) to make verification strict"
        )
        return 0, j
    rep = man.verify(today=today)
    return (0 if rep.ok else 1), rep.to_json()


def utc_today_from(dt: datetime) -> date:
    return dt.date()
