"""Append-only JSONL ledger under one root: `<root>/wagers/<YYYY>.jsonl`, `<root>/settlements/<YYYY>.jsonl`.

Rules that make the router's idempotency proof (`git write-tree` unchanged after a second
identical import) hold by construction:

* a file is only ever appended to; existing bytes are copied verbatim into a temp file in the
  same directory, the new lines are added, and the temp file is renamed over the original;
* nothing is sorted, reformatted or re-serialised on the way through;
* when a run has nothing to append to a file, that file is not opened for writing at all.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

WAGERS_DIR = "wagers"
SETTLEMENTS_DIR = "settlements"
_YEAR_FILE_RE = re.compile(r"^(?P<year>20\d{2})\.jsonl$")


@dataclass(frozen=True)
class LedgerPaths:
    root: Path

    @property
    def wagers(self) -> Path:
        return self.root / WAGERS_DIR

    @property
    def settlements(self) -> Path:
        return self.root / SETTLEMENTS_DIR

    def wager_file(self, year: int) -> Path:
        return self.wagers / f"{year}.jsonl"

    def settlement_file(self, year: int) -> Path:
        return self.settlements / f"{year}.jsonl"

    def year_files(self, directory: Path) -> list[Path]:
        if not directory.is_dir():
            return []
        return sorted(p for p in directory.iterdir() if p.is_file() and _YEAR_FILE_RE.match(p.name))


def year_of_file(path: Path) -> int | None:
    match = _YEAR_FILE_RE.match(path.name)
    return int(match["year"]) if match else None


def iter_records(path: Path) -> Iterable[tuple[int, dict]]:
    """Yield `(line_number, record)`; blank lines skipped; a bad line raises `ValueError`."""
    if not path.exists():
        return
    with path.open(encoding="utf-8") as fh:
        for number, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {number}: not decodable JSON") from exc
            if not isinstance(record, dict):
                raise ValueError(f"line {number}: not a JSON object")
            yield number, record


def append_lines(path: Path, lines: list[str]) -> None:
    """Append pre-serialised lines atomically. A no-op (file untouched) when `lines` is empty."""
    if not lines:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_bytes() if path.exists() else b""
    if existing and not existing.endswith(b"\n"):
        existing += b"\n"
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        with tmp.open("wb") as fh:
            fh.write(existing)
            for line in lines:
                fh.write(line.encode("utf-8"))
                fh.write(b"\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
