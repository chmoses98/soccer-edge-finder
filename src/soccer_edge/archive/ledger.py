"""Append-only, content-hashed prediction ledger.

Rules
-----
* A record's id is derived from its content hash; writing an identical record is a NO_OP.
* Writing a *different* record under an existing id is a CONFLICT and raises.
* Records are never edited. Corrections are new records with `supersedes=<old id>` and a reason.
* Every record carries: input snapshot hash, model version + parameter hash, world/sim hashes,
  data_as_of, market_as_of, lineup state, probability + uncertainty outputs, market snapshot,
  recommendation flag and exclusion reason.
* Files are JSONL, one directory per UTC day. `archive/manifest.py` records byte-prefix hashes and one row per
  record so that deletion and rewriting are detected (`soccer archive verify`).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from soccer_edge.core.errors import ArchiveImmutabilityError
from soccer_edge.core.serialization import canonical_json, content_hash
from soccer_edge.core.time import ensure_utc, iso_utc, utc_now


class WriteStatus(str, Enum):
    WRITTEN = "written"
    NO_OP = "no_op"


class PredictionLedger:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def record_id(record: dict[str, Any]) -> str:
        body = {k: v for k, v in record.items() if k not in ("record_id", "archived_at")}
        return "pred_" + hashlib.sha256(canonical_json(body).encode()).hexdigest()[:24]

    def _day_file(self, when: datetime) -> Path:
        d = ensure_utc(when)
        return self.root / f"{d:%Y-%m-%d}" / "predictions.jsonl"

    def _index(self) -> dict[str, str]:
        idx_path = self.root / "index.json"
        if idx_path.exists():
            return json.loads(idx_path.read_text())
        return {}

    def _save_index(self, idx: dict[str, str]) -> None:
        (self.root / "index.json").write_text(json.dumps(idx, sort_keys=True, indent=0) + "\n")

    def append(
        self, record: dict[str, Any], *, when: datetime | None = None
    ) -> tuple[str, WriteStatus]:
        when = when or utc_now()
        rid = self.record_id(record)
        idx = self._index()
        if rid in idx:
            if not (self.root / idx[rid]).exists():
                # A restored ledger may carry the archive's index without its day files (the run-soccer
                # workflow restores only index.json). The id is a content hash of the body, so an identical
                # id means an identical record: nothing to write, and nothing that could conflict.
                return rid, WriteStatus.NO_OP
            existing = self.get(rid)
            if existing is None:
                raise ArchiveImmutabilityError(f"index lists {rid} but file is missing")
            body_old = {k: v for k, v in existing.items() if k not in ("record_id", "archived_at")}
            body_new = {k: v for k, v in record.items() if k not in ("record_id", "archived_at")}
            if content_hash(body_old) != content_hash(body_new):
                raise ArchiveImmutabilityError(f"conflict: {rid} exists with different content")
            return rid, WriteStatus.NO_OP
        full = {**record, "record_id": rid, "archived_at": iso_utc(when)}
        path = self._day_file(when)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(canonical_json(full) + "\n")
        idx[rid] = str(path.relative_to(self.root))
        self._save_index(idx)
        return rid, WriteStatus.WRITTEN

    def get(self, rid: str) -> dict[str, Any] | None:
        idx = self._index()
        rel = idx.get(rid)
        if rel is None:
            return None
        with (self.root / rel).open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rec = json.loads(line)
                    if rec.get("record_id") == rid:
                        return rec
        return None

    def iter_records(self):
        for path in sorted(self.root.glob("*/predictions.jsonl")):
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        yield json.loads(line)

    def verify(self) -> list[str]:
        """Recompute every record id; report tampering."""
        problems = []
        for rec in self.iter_records():
            if self.record_id(rec) != rec.get("record_id"):
                problems.append(f"record {rec.get('record_id')} hash mismatch")
        return problems

    def supersede(
        self, old_id: str, new_record: dict[str, Any], reason: str
    ) -> tuple[str, WriteStatus]:
        if self.get(old_id) is None:
            raise ArchiveImmutabilityError(f"cannot supersede unknown record {old_id}")
        return self.append({**new_record, "supersedes": old_id, "supersede_reason": reason})
