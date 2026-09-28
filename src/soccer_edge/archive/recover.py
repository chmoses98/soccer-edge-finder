"""One-time recovery of archive rows that a publish overwrote (audit B1, §O1).

The archive branch is append-only by contract, but until audit fix S1 `archive_publish.sh` replaced
`.jsonl` day files instead of merging them. The overwritten rows still exist in earlier commits of the
branch. This module reconstructs them deterministically from git history:

* every historical version (blob) of every `.jsonl` path is read, oldest commit first;
* lines are unioned per path by exact bytes, remembering the first commit/blob that carried each line;
* a line is *recoverable* when it is absent from the current tip of that path;
* identities are checked before anything is written: a prediction row must re-hash to its own
  `record_id` (they are self-verifying), and the same identity must never map to two different payloads
  across history and the tip. Any conflict refuses the whole recovery (exit non-zero, nothing written);
* applying appends the recoverable lines in first-seen order, never touches a surviving line, and writes
  `recovery/<recovery_id>.json` naming the origin commit and blob of every recovered group.

Nothing is recomputed: timestamps, run ids, model versions and probabilities are the original bytes.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from soccer_edge.archive.ledger import PredictionLedger
from soccer_edge.core.serialization import write_json
from soccer_edge.core.time import iso_utc, utc_now


@dataclass
class LineOrigin:
    commit: str
    blob: str
    path: str
    commit_time: str


@dataclass
class PathRecovery:
    path: str
    record_type: str
    union_lines: int
    tip_lines: int
    recoverable: list[bytes]
    origins: dict[bytes, LineOrigin]
    duplicate_line_occurrences: (
        int  # a line seen in more than one historical blob (expected: every carried-forward line)
    )
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    unverifiable: list[dict[str, Any]] = field(default_factory=list)

    def groups(self) -> list[dict[str, Any]]:
        by_origin: dict[tuple[str, str], list[bytes]] = {}
        for ln in self.recoverable:
            o = self.origins[ln]
            by_origin.setdefault((o.commit, o.blob), []).append(ln)
        out = []
        for (commit, blob), lines in by_origin.items():
            o = self.origins[lines[0]]
            run_ids = sorted(
                {_identity_fields(self.record_type, ln).get("run_id") or "" for ln in lines} - {""}
            )
            digest = hashlib.sha256(b"\n".join(sorted(lines))).hexdigest()
            out.append(
                {
                    "path": self.path,
                    "record_type": self.record_type,
                    "origin_commit": commit,
                    "origin_blob": blob,
                    "origin_commit_time": o.commit_time,
                    "n_lines": len(lines),
                    "run_ids": run_ids,
                    "lines_sha256": digest,
                }
            )
        return out


def _git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args])


def _identity_fields(record_type: str, raw: bytes) -> dict[str, Any]:
    try:
        rec = json.loads(raw)
    except ValueError:
        return {"identity": None, "parse_error": True}
    if record_type == "prediction":
        rid = rec.get("record_id")
        return {
            "identity": rid,
            "run_id": rec.get("run_id"),
            "self_verifies": rid is not None and PredictionLedger.record_id(rec) == rid,
        }
    if record_type == "lineup":
        return {
            "identity": (rec.get("espn_event_id"), rec.get("captured_at"), rec.get("content_hash"))
        }
    if record_type == "weather":
        return {
            "identity": (
                rec.get("espn_event_id"),
                rec.get("captured_at"),
                rec.get("forecast_time_utc"),
            )
        }
    if record_type == "result":
        return {"identity": (rec.get("espn_event_id"), rec.get("fixture_id"))}
    return {"identity": hashlib.sha256(raw.rstrip(b"\r\n")).hexdigest()}


def record_type_for(path: str) -> str:
    if path.startswith("predictions/"):
        return "prediction"
    if path.startswith("settlements/"):
        return "settlement"
    if path.startswith("lineups/"):
        return "lineup"
    if path.startswith("weather/"):
        return "weather"
    if path.startswith("results/"):
        return "result"
    if path.startswith("snapshots/"):
        return "kalshi_snapshot"
    if path.startswith("reference/"):
        return "reference"
    return "other"


def _lines(data: bytes) -> list[bytes]:
    return [ln.rstrip(b"\r") for ln in data.split(b"\n") if ln.strip()]


def scan_history(repo: Path, branch: str, *, tip_root: Path | None = None) -> list[PathRecovery]:
    """Union every historical `.jsonl` version on `branch`; compare with the working tip.

    `tip_root` defaults to the branch tip inside the repo; passing a working tree lets the scan compose
    with earlier recoveries or uncommitted appends.
    """
    commits = _git(repo, "rev-list", "--reverse", branch).decode().split()
    if not commits:
        raise RecoveryError(f"branch {branch} has no commits")
    times = dict(
        ln.split(" ", 1)
        for ln in _git(repo, "log", "--reverse", "--format=%H %cI", branch).decode().splitlines()
        if ln
    )
    union: dict[str, dict[bytes, LineOrigin]] = {}
    seen_blobs: set[str] = set()
    dup_occurrences: dict[str, int] = {}
    paths_in_history: set[str] = set()
    for c in commits:
        tree = _git(repo, "ls-tree", "-r", c).decode().splitlines()
        for entry in tree:
            meta, path = entry.split("\t", 1)
            _mode, kind, blob = meta.split()
            if kind != "blob" or not path.endswith(".jsonl") or path.startswith("manifest/"):
                continue
            paths_in_history.add(path)
            key = f"{path}@{blob}"
            if key in seen_blobs:
                continue
            seen_blobs.add(key)
            data = _git(repo, "cat-file", "-p", blob)
            bucket = union.setdefault(path, {})
            for ln in _lines(data):
                if ln in bucket:
                    dup_occurrences[path] = dup_occurrences.get(path, 0) + 1
                else:
                    bucket[ln] = LineOrigin(c, blob, path, times.get(c, ""))
    out: list[PathRecovery] = []
    for path in sorted(paths_in_history):
        if tip_root is not None:
            tip_file = tip_root / path
            tip_lines = _lines(tip_file.read_bytes()) if tip_file.exists() else []
        else:
            try:
                tip_lines = _lines(_git(repo, "show", f"{branch}:{path}"))
            except subprocess.CalledProcessError:
                tip_lines = []
        tip_set = set(tip_lines)
        hist = union.get(path, {})
        rtype = record_type_for(path)
        recoverable = [ln for ln in hist if ln not in tip_set]
        pr = PathRecovery(
            path=path,
            record_type=rtype,
            union_lines=len(hist),
            tip_lines=len(tip_set),
            recoverable=recoverable,
            origins=hist,
            duplicate_line_occurrences=dup_occurrences.get(path, 0),
        )
        # identity checks over union and tip
        ident_to_line: dict[Any, bytes] = {}
        for ln in list(tip_lines) + recoverable:
            f = _identity_fields(rtype, ln)
            if f.get("parse_error"):
                pr.unverifiable.append({"reason": "unparsable", "origin": _origin_json(pr, ln)})
                continue
            if rtype == "prediction" and not f.get("self_verifies"):
                pr.unverifiable.append(
                    {
                        "reason": "record_id does not re-hash",
                        "record_id": f.get("identity"),
                        "origin": _origin_json(pr, ln),
                    }
                )
                continue
            ident = f["identity"]
            prev = ident_to_line.get(ident)
            if prev is not None and prev != ln:
                pr.conflicts.append(
                    {
                        "identity": ident if isinstance(ident, str) else list(ident),
                        "a": _origin_json(pr, prev),
                        "b": _origin_json(pr, ln),
                    }
                )
            else:
                ident_to_line[ident] = ln
        out.append(pr)
    return out


def _origin_json(pr: PathRecovery, ln: bytes) -> dict[str, Any]:
    o = pr.origins.get(ln)
    if o is None:
        return {"where": "tip"}
    return {"commit": o.commit, "blob": o.blob}


def dry_run_report(recs: list[PathRecovery], *, repo: Path, branch: str) -> dict[str, Any]:
    paths = []
    total = 0
    conflicts = 0
    unverifiable = 0
    for pr in recs:
        total += len(pr.recoverable)
        conflicts += len(pr.conflicts)
        unverifiable += len(pr.unverifiable)
        if pr.recoverable or pr.conflicts or pr.unverifiable:
            paths.append(
                {
                    "path": pr.path,
                    "record_type": pr.record_type,
                    "union_lines": pr.union_lines,
                    "tip_lines": pr.tip_lines,
                    "recoverable_lines": len(pr.recoverable),
                    "duplicate_line_occurrences": pr.duplicate_line_occurrences,
                    "conflicts": pr.conflicts,
                    "unverifiable": pr.unverifiable,
                    "groups": pr.groups(),
                }
            )
    return {
        "schema": "archive_recovery_report_v1",
        "generated_at": iso_utc(utc_now()),
        "repo": str(repo),
        "branch": branch,
        "paths_scanned": len(recs),
        "recoverable_lines_total": total,
        "conflicts_total": conflicts,
        "unverifiable_total": unverifiable,
        "refused": conflicts > 0 or unverifiable > 0,
        "paths": paths,
    }


def apply_recovery(
    recs: list[PathRecovery], *, archive_root: Path, report: dict[str, Any]
) -> dict[str, Any]:
    """Append every recoverable line to the working archive; write the recovery manifest.

    Refuses when the report carries conflicts or unverifiable rows. Never removes or rewrites a line.
    """
    if report["refused"]:
        raise RecoveryError("recovery refused: conflicts or unverifiable rows present (see report)")
    recovery_id = (
        "rec-"
        + utc_now().strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + hashlib.sha256(json.dumps(report["paths"], sort_keys=True).encode()).hexdigest()[:8]
    )
    appended: dict[str, int] = {}
    groups: list[dict[str, Any]] = []
    for pr in recs:
        if not pr.recoverable:
            continue
        target = archive_root / pr.path
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = target.read_bytes() if target.exists() else b""
        with target.open("ab") as fh:
            if existing and not existing.endswith(b"\n"):
                fh.write(b"\n")
            for ln in pr.recoverable:
                fh.write(ln + b"\n")
        appended[pr.path] = len(pr.recoverable)
        groups.extend(pr.groups())
        if pr.record_type == "prediction":
            _repair_index(archive_root / "predictions", pr)
    manifest = {
        "schema": "archive_recovery_manifest_v1",
        "recovery_id": recovery_id,
        "applied_at": iso_utc(utc_now()),
        "source_repo_branch": report["branch"],
        "lines_appended": appended,
        "lines_appended_total": sum(appended.values()),
        "groups": groups,
        "policy": {
            "overwrite_surviving_records": False,
            "recomputed_probabilities": False,
            "timestamps_preserved": True,
            "run_ids_preserved": True,
            "model_versions_preserved": True,
        },
    }
    out = archive_root / "recovery" / f"{recovery_id}.json"
    write_json(out, manifest)
    return manifest


def _repair_index(pred_root: Path, pr: PathRecovery) -> None:
    """Add index entries for recovered prediction ids that the (mutable) index does not list."""
    idx_path = pred_root / "index.json"
    if not idx_path.exists():
        return
    idx = json.loads(idx_path.read_text())
    rel = pr.path.split("predictions/", 1)[1]
    changed = False
    for ln in pr.recoverable:
        rid = json.loads(ln).get("record_id")
        if rid and rid not in idx:
            idx[rid] = rel
            changed = True
    if changed:
        idx_path.write_text(json.dumps(idx, sort_keys=True, indent=0) + "\n")


class RecoveryError(Exception):
    pass
