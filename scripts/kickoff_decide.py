"""Stdlib-only decide step for the kickoff dispatcher (no pip install; runs in seconds).

Reads the published dispatch schedule and delivery log straight from the data-archive branch (public
raw URLs) and prints GitHub-output lines:

    due=true|false      a capture batch is needed now (or the schedule could not be read)
    n_due=<int>         (fixture, horizon) pairs satisfiable now
    n_missed=<int>      windows that closed without a capture since the last tick (logged by the tick job)
    next_window_minutes=<float|none>
    reason=<text>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soccer_edge.dispatch.horizons import (  # noqa: E402  (stdlib-only module)
    SCHEDULE_FILE,
    STATE_LOG,
    HorizonRow,
    ScheduledFixture,
    minutes_until_next_window,
    plan,
)


def _fetch(url: str) -> bytes | None:
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.read()
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--repo", default=os.environ.get("GITHUB_REPOSITORY", "chmoses98/soccer-edge-finder")
    )
    ap.add_argument("--branch", default="data-archive")
    a = ap.parse_args()
    base = f"https://raw.githubusercontent.com/{a.repo}/{a.branch}"
    now = datetime.now(UTC)
    sched_raw = _fetch(f"{base}/{SCHEDULE_FILE}")
    if sched_raw is None:
        print("due=true")
        print("n_due=0")
        print("n_missed=0")
        print("next_window_minutes=none")
        print("reason=no schedule readable; tick job will build one")
        return 0
    schedule = [ScheduledFixture.from_json(d) for d in json.loads(sched_raw).get("fixtures", [])]
    log_raw = _fetch(f"{base}/{STATE_LOG}") or b""
    log = []
    for ln in log_raw.decode("utf-8", errors="replace").splitlines():
        if ln.strip():
            d = json.loads(ln)
            log.append(HorizonRow(**{k: d.get(k) for k in HorizonRow.__dataclass_fields__}))
    due, missed, upcoming = plan(schedule, log, now=now)
    nxt = minutes_until_next_window(upcoming)
    go = bool(due) or bool(missed)
    print(f"due={'true' if go else 'false'}")
    print(f"n_due={len(due)}")
    print(f"n_missed={len(missed)}")
    print(f"next_window_minutes={'none' if nxt is None else round(nxt, 1)}")
    print(
        f"reason=scheduled={len(schedule)} due={[(d.fixture.fixture_id[-40:], d.horizon) for d in due][:6]} missed={len(missed)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
