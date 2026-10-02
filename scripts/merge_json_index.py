#!/usr/bin/env python3
"""Union-merge a mutable pointer index (data-archive `predictions/index.json`) into the archived copy.

The index maps record_id -> day file and only ever grows (records are append-only). Publishers restore it
when they start and publish it when they finish; a plain copy therefore REPLACED the archive's index with
the publisher's start-of-run snapshot and dropped every entry another writer added meanwhile. A 5.5 h
kickoff-dispatch link that overlapped a run-soccer publish then failed the manifest check with
`index_missing_record` (runs 36876149810: 2863, 36983392414: 851) and every later batch of that link went
unpublished.

Merge rule: every archived entry is kept; incoming entries are added when absent. On a conflicting value
the archived entry wins and the conflict is reported (archive verify still checks the result). Unreadable
input fails closed (exit 2): a corrupt index is never merged over.

usage: merge_json_index.py <archived_index.json (updated in place)> <incoming_index.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def merge_index(archived: dict[str, str], incoming: dict[str, str]) -> tuple[dict[str, str], dict]:
    merged = dict(archived)
    added = 0
    conflicts: list[str] = []
    for rid, rel in incoming.items():
        if rid not in merged:
            merged[rid] = rel
            added += 1
        elif merged[rid] != rel:
            conflicts.append(rid)
    return merged, {"kept": len(archived), "added": added, "conflicts": len(conflicts)}


def _load(path: Path) -> dict[str, str]:
    doc = json.loads(path.read_text())
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: index is not a JSON object")
    return doc


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    dst, src = Path(argv[0]), Path(argv[1])
    try:
        archived, incoming = _load(dst), _load(src)
    except (OSError, ValueError) as exc:
        print(f"::error::index merge refused: {exc}", file=sys.stderr)
        return 2
    merged, stats = merge_index(archived, incoming)
    if stats["conflicts"]:
        print(f"::warning::index merge: {stats['conflicts']} conflicting entries kept as archived")
    dst.write_text(json.dumps(merged, sort_keys=True, indent=0) + "\n")
    print(f"index merge {dst.name}: {json.dumps(stats)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
