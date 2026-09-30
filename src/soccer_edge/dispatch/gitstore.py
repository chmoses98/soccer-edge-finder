"""Durable, race-safe writes to the data-archive branch (stdlib only).

Two uses:

* ArchiveAppender: append a heartbeat row (and rewrite the reliability summary) with a fetch / apply /
  commit / push loop. A rejected push means someone else pushed first: the loop starts again from the new
  tip, so concurrent writers never lose rows and never conflict.
* ClaimStore: an atomic "first writer wins" claim for an idempotency identity, made BEFORE a paid provider
  call. Each identity is one file at a deterministic path; two dispatchers that race for the same identity
  both try to add that file on top of the same tip and only one push can succeed. The loser refetches, sees
  the file, and drops the identity. If the claim cannot be recorded at all, nothing is claimed and the
  caller must not spend (fail closed).

Only these paths are ever written here: dispatch/heartbeats/, dispatch/reliability.json, claims/. The
append-only publisher (scripts/archive_publish.sh) never writes them, so the two paths cannot conflict.
Credentials live only in the remote URL and are redacted from every error message.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from soccer_edge.dispatch.wake import redact

BRANCH = "data-archive"
CLAIMS_DIR = "claims"


class GitStoreError(RuntimeError):
    pass


def github_remote_url(repository: str | None = None, token: str | None = None) -> str | None:
    """Authenticated HTTPS remote for the workflow token (never printed)."""
    repository = repository or os.environ.get("GITHUB_REPOSITORY")
    token = token if token is not None else os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        return None
    return f"https://x-access-token:{token}@github.com/{repository}.git"


class _SparseArchive:
    def __init__(
        self,
        remote_url: str,
        *,
        branch: str = BRANCH,
        workdir: Path | None = None,
        paths: Iterable[str] = ("dispatch", CLAIMS_DIR),
        max_attempts: int = 8,
    ) -> None:
        self._remote = remote_url
        self.branch = branch
        self.dir = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="archive-sparse-"))
        self.paths = tuple(paths)
        self.max_attempts = max_attempts
        self._ready = False

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        p = subprocess.run(
            ["git", *args],
            cwd=self.dir,
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
            check=False,
        )
        if check and p.returncode != 0:
            raise GitStoreError(redact(f"git {args[0]} failed: {p.stderr.strip()[-400:]}"))
        return p

    def _ensure(self) -> None:
        if self._ready:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        if not (self.dir / ".git").exists():
            self._git("init", "-q")
            self._git("remote", "add", "origin", self._remote)
            self._git("config", "user.name", "soccer-edge-bot")
            self._git("config", "user.email", "soccer-edge-bot@users.noreply.github.com")
            self._git("sparse-checkout", "init", "--cone")
            self._git("sparse-checkout", "set", *self.paths)
        self._ready = True

    def _sync(self) -> None:
        # partial + shallow: only the tip commit, and only the blobs the sparse paths need (~KBs)
        self._git("fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", self.branch)
        self._git("checkout", "-q", "-B", "work", "--force", "FETCH_HEAD")
        self._git("clean", "-qfd")

    def commit_push(self, mutate: Callable[[Path], bool], message: str) -> bool:
        """Apply `mutate` on a fresh tip and push; retry from the new tip on rejection.
        Returns True when the change is on the remote (or `mutate` decided nothing needs writing)."""
        self._ensure()
        for attempt in range(self.max_attempts):
            self._sync()
            if not mutate(self.dir):
                return True
            self._git("add", "-A", "--", *self.paths)
            if not self._git("diff", "--cached", "--quiet", check=False).returncode:
                return True
            self._git("commit", "-q", "-m", message)
            if (
                self._git("push", "-q", "origin", f"HEAD:{self.branch}", check=False).returncode
                == 0
            ):
                return True
            time.sleep(min(8.0, 0.5 * (2**attempt)) * (0.5 + random.random()))
        return False


class ArchiveAppender(_SparseArchive):
    def append_heartbeat(
        self, row: dict[str, Any], *, day: str, reliability: Callable[[Path], dict] | None = None
    ) -> bool:
        line = json.dumps(row, sort_keys=True, separators=(",", ":"))

        def mutate(root: Path) -> bool:
            p = root / "dispatch" / "heartbeats" / f"{day}.jsonl"
            p.parent.mkdir(parents=True, exist_ok=True)
            existing = p.read_text(encoding="utf-8") if p.exists() else ""
            if line in existing.splitlines():
                return False  # idempotent: this exact row is already recorded
            if existing and not existing.endswith("\n"):
                existing += "\n"
            p.write_text(existing + line + "\n", encoding="utf-8")
            if reliability is not None:
                rel = reliability(root)
                (root / "dispatch" / "reliability.json").write_text(
                    json.dumps(rel, indent=1, sort_keys=True) + "\n", encoding="utf-8"
                )
            return True

        return self.commit_push(mutate, f"heartbeat {row.get('phase')} {row.get('run_id')} {day}")


def claim_path(identity: str, namespace: str = "odds_api") -> str:
    h = hashlib.sha256(identity.encode()).hexdigest()[:32]
    return f"{CLAIMS_DIR}/{namespace}/{h[:2]}/{h}.json"


CALLS_DIR = f"{CLAIMS_DIR}/odds_api_calls"


def _calls_spent(root: Path, days: list[str]) -> int:
    """Credits reserved by durable call records for these UTC days (expected cost per paid call)."""
    total = 0
    for day in days:
        d = root / CALLS_DIR / day
        if not d.is_dir():
            continue
        for p in d.glob("*.json"):
            try:
                total += int(json.loads(p.read_text(encoding="utf-8")).get("expected_cost") or 0)
            except (OSError, ValueError):
                total += 3  # unreadable record: count it at the design cost, never as zero
    return total


class ClaimStore(_SparseArchive):
    """First-writer-wins claims on data-archive (see module docstring).

    With `call_record` + `caps`, the claim commit ALSO writes one durable record for the paid call it
    authorises and refuses (claims nothing) when the records already on the tip, plus this one, would
    exceed the daily or rolling 30-day credit cap. The check and the write happen in one commit on the
    fresh tip, so neither a stale local ledger, nor a restarted dispatcher, nor any number of parallel
    runs can spend past the caps: this layer does not depend on the scheduler being correct."""

    def __init__(self, remote_url: str, **kw: Any) -> None:
        kw.setdefault("paths", (CLAIMS_DIR,))
        super().__init__(remote_url, **kw)
        self.last_reason: str | None = None

    def claim(
        self,
        identities: list[str],
        meta: dict[str, Any],
        namespace: str = "odds_api",
        *,
        call_record: dict[str, Any] | None = None,
        caps: dict[str, int] | None = None,
    ) -> set[str]:
        """Claim every identity not yet claimed; return the identities this caller now owns.
        On any failure to record the claim, or a durable cap refusal, returns an empty set (no spend)."""
        won: set[str] = set()
        self.last_reason = None

        def mutate(root: Path) -> bool:
            won.clear()
            self.last_reason = None
            fresh = [i for i in identities if not (root / claim_path(i, namespace)).exists()]
            if not fresh:
                self.last_reason = "ALREADY_CLAIMED"
                return False
            if call_record is not None:
                day = call_record["day"]
                cost = int(call_record.get("expected_cost") or 3)
                d0 = datetime.strptime(day, "%Y-%m-%d")
                last30 = [(d0 - timedelta(days=k)).strftime("%Y-%m-%d") for k in range(30)]
                today = _calls_spent(root, [day])
                month = _calls_spent(root, last30)
                caps_ = caps or {}
                if "daily" in caps_ and today + cost > caps_["daily"]:
                    self.last_reason = f"DURABLE_DAILY_CAP ({today}+{cost}>{caps_['daily']})"
                    return False
                if "rolling_30d" in caps_ and month + cost > caps_["rolling_30d"]:
                    self.last_reason = f"DURABLE_30D_CAP ({month}+{cost}>{caps_['rolling_30d']})"
                    return False
                rec = root / CALLS_DIR / day / f"{call_record['call_id']}.json"
                if rec.exists():
                    self.last_reason = "CALL_RECORD_EXISTS"
                    return False
                rec.parent.mkdir(parents=True, exist_ok=True)
                rec.write_text(
                    json.dumps({**call_record, **meta, "identities": fresh}, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
            for ident in fresh:
                p = root / claim_path(ident, namespace)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(
                    json.dumps({"identity": ident, **meta}, sort_keys=True) + "\n", encoding="utf-8"
                )
                won.add(ident)
            return True

        try:
            ok = self.commit_push(
                mutate, f"claim {namespace} {meta.get('batch_id', '')} ({len(identities)})"
            )
        except GitStoreError as exc:
            self.last_reason = f"CLAIM_UNAVAILABLE: {exc}"[:200]
            return set()
        if not ok:
            self.last_reason = self.last_reason or "CLAIM_PUSH_FAILED"
            return set()
        return set(won)


LEASE_FILE = "dispatch/chain_lease.json"


class ChainLease(_SparseArchive):
    """At most one bounded capture link at a time. Acquire = compare-and-set of dispatch/chain_lease.json
    on the fresh tip (a lease held by another run and not yet expired refuses). The holder releases it at
    the end; a crashed holder's lease simply expires."""

    def __init__(self, remote_url: str, **kw: Any) -> None:
        kw.setdefault("paths", ("dispatch",))
        super().__init__(remote_url, **kw)
        self.holder: dict[str, Any] | None = None

    def _write(self, fn: Callable[[dict[str, Any] | None], dict[str, Any] | None]) -> bool:
        decided: dict[str, bool] = {"ok": False}

        def mutate(root: Path) -> bool:
            p = root / LEASE_FILE
            cur = None
            if p.exists():
                try:
                    cur = json.loads(p.read_text(encoding="utf-8"))
                except ValueError:
                    cur = None
            self.holder = cur
            new = fn(cur)
            decided["ok"] = new is not None
            if new is None:
                return False
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(new, sort_keys=True) + "\n", encoding="utf-8")
            return True

        try:
            pushed = self.commit_push(mutate, "chain lease")
        except GitStoreError:
            return False
        return pushed and decided["ok"]

    def acquire(self, run_id: str, *, now: datetime, minutes: float) -> bool:
        def fn(cur):
            if cur and cur.get("run_id") != run_id and cur.get("expires_at", "") > _z(now):
                return None
            return {
                "run_id": run_id,
                "acquired_at": _z(now),
                "expires_at": _z(now + timedelta(minutes=minutes)),
            }

        return self._write(fn)

    def release(self, run_id: str, *, now: datetime) -> bool:
        def fn(cur):
            if not cur or cur.get("run_id") != run_id:
                return None
            return {**cur, "expires_at": _z(now), "released_at": _z(now)}

        return self._write(fn)


def _z(d: datetime) -> str:
    return d.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
