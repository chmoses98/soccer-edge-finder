"""Stdlib-only decision job: are there fixtures with kickoff inside the window? (no pip install)."""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import UTC, datetime, timedelta

FILES = ["en.1", "es.1", "de.1", "it.1", "fr.1"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-hours", type=int, default=48)
    ap.add_argument("--date", default="")
    a = ap.parse_args()
    now = datetime.now(UTC)
    start = datetime.fromisoformat(a.date).replace(tzinfo=UTC) if a.date else now
    end = start + timedelta(hours=a.window_hours)
    season = f"{start.year if start.month >= 7 else start.year - 1}-{str((start.year if start.month >= 7 else start.year - 1) + 1)[2:]}"
    count = 0
    errors = 0
    for f in FILES:
        url = (
            f"https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{f}.json"
        )
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                data = json.load(r)
        except Exception:
            errors += 1
            continue
        for m in data.get("matches", []):
            if "score" in m:
                continue
            d = datetime.fromisoformat(
                m["date"] + "T" + (m.get("time") or "12:00") + ":00"
            ).replace(tzinfo=UTC)
            if start - timedelta(hours=3) <= d <= end:
                count += 1
    go = count > 0 or errors == len(
        FILES
    )  # if every fetch failed, run anyway and let the run fail loudly
    print(f"go={'true' if go else 'false'}")
    print(f"reason=fixtures_in_window={count} fetch_errors={errors}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
