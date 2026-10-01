"""Stdlib-only decision job for RUN SOCCER: is there any relevant soccer fixture inside the window?

RUN SOCCER produces the Kalshi listing (runs/latest.run_output.v1.json) behind the kickoff dispatcher's
schedule. The paid-reference guard refuses to spend on a listing older than 36 h, so the listing must be
refreshed whenever ANY relevant fixture is coming, not only top-five-league ones (2026-10-01: during the
international break the old top-five-only check skipped every run and the listing aged past 36 h while
MLS and other Kalshi-listed fixtures existed).

Sources, any one of which makes the run go:

* dispatch/schedule.json on data-archive: every fixture of the dispatcher's schedule, any competition,
  rebuilt by each capture link from the latest Kalshi run output plus ESPN fixtures of every competition
  the system prices (top five, MLS, Liga MX, Brasileirão, Argentina, UEFA and international pools);
* openfootball top-five fixtures (the original source, kept so a missing schedule never stops a run).

Nothing in the window from any readable source -> no run. Every source unreadable -> run anyway and let
the run fail loudly. This job makes no Odds API request; RUN SOCCER itself makes none either.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import UTC, datetime, timedelta

FILES = ["en.1", "es.1", "de.1", "it.1", "fr.1"]
PAST_GRACE = timedelta(hours=3)


def _get(url: str):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def schedule_fixtures_in_window(doc: dict, start: datetime, end: datetime) -> list[dict]:
    out = []
    for f in (doc or {}).get("fixtures", []):
        try:
            ko = datetime.fromisoformat(str(f["kickoff_utc"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if start - PAST_GRACE <= ko <= end:
            out.append(f)
    return out


def openfootball_count(data_by_file: list[dict], start: datetime, end: datetime) -> int:
    count = 0
    for data in data_by_file:
        for m in data.get("matches", []):
            if "score" in m:
                continue
            try:
                d = datetime.fromisoformat(
                    m["date"] + "T" + (m.get("time") or "12:00") + ":00"
                ).replace(tzinfo=UTC)
            except (KeyError, ValueError):
                continue
            if start - PAST_GRACE <= d <= end:
                count += 1
    return count


def decide(
    *, schedule_doc: dict | None, openfootball: list[dict] | None, start: datetime, end: datetime
) -> tuple[bool, str]:
    """(go, reason). `None` means that source could not be read."""
    sched = (
        schedule_fixtures_in_window(schedule_doc, start, end) if schedule_doc is not None else []
    )
    of = openfootball_count(openfootball, start, end) if openfootball is not None else 0
    comps = sorted({f.get("competition_id", "?") for f in sched})
    if sched or of:
        return True, f"schedule_fixtures={len(sched)} competitions={comps} top5_openfootball={of}"
    if schedule_doc is None and openfootball is None:
        return True, "every fixture source unreadable: running anyway (fails loudly)"
    return False, "no relevant fixture in window"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-hours", type=int, default=48)
    ap.add_argument("--date", default="")
    ap.add_argument(
        "--repo", default=os.environ.get("GITHUB_REPOSITORY", "chmoses98/soccer-edge-finder")
    )
    a = ap.parse_args()
    now = datetime.now(UTC)
    start = datetime.fromisoformat(a.date).replace(tzinfo=UTC) if a.date else now
    end = start + timedelta(hours=a.window_hours)
    try:
        schedule_doc = _get(
            f"https://raw.githubusercontent.com/{a.repo}/data-archive/dispatch/schedule.json"
        )
    except Exception:
        schedule_doc = None
    season_start = start.year if start.month >= 7 else start.year - 1
    season = f"{season_start}-{str(season_start + 1)[2:]}"
    files = []
    for f in FILES:
        try:
            files.append(
                _get(
                    f"https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{f}.json"
                )
            )
        except Exception:
            continue
    go, reason = decide(schedule_doc=schedule_doc, openfootball=files or None, start=start, end=end)
    print(f"go={'true' if go else 'false'}")
    print(f"reason={reason}"[:900])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
