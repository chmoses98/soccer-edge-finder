"""Probe free soccer data sources for reachability + basic payload sanity. Read-only.

Run from a GitHub-hosted runner (workflow probe-sources.yml). Results feed docs/DATA_SOURCE_AUDIT.md.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

UA = "soccer-edge-finder/0.1 (+https://github.com/chmoses98/soccer-edge-finder; source probe)"

PROBES = [
    (
        "openfootball_json_epl_2026_27",
        "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/en.1.json",
        "json",
    ),
    (
        "openfootball_json_laliga_2026_27",
        "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/es.1.json",
        "json",
    ),
    (
        "openfootball_json_ligue1_2026_27",
        "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/fr.1.json",
        "json",
    ),
    (
        "openfootball_txt_ucl_2026_27",
        "https://raw.githubusercontent.com/openfootball/champions-league/master/2026-27/cl.txt",
        "text",
    ),
    (
        "club_football_match_data",
        "https://raw.githubusercontent.com/xgabora/Club-Football-Match-Data-2000-2025/main/data/Matches.csv",
        "csv-head",
    ),
    (
        "football_data_couk_E0_2627",
        "https://www.football-data.co.uk/mmz4281/2627/E0.csv",
        "csv-head",
    ),
    ("football_data_couk_fixtures", "https://www.football-data.co.uk/fixtures.csv", "csv-head"),
    (
        "football_data_org_PL_matches",
        "https://api.football-data.org/v4/competitions/PL/matches?status=SCHEDULED",
        "json",
    ),
    (
        "espn_epl_scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
        "json",
    ),
    (
        "espn_ucl_scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard",
        "json",
    ),
    ("clubelo_api", "http://api.clubelo.com/Arsenal", "csv-head"),
    ("understat_epl", "https://understat.com/league/EPL/2026", "text"),
    ("fbref_epl", "https://fbref.com/en/comps/9/Premier-League-Stats", "text"),
    ("fotmob_league", "https://www.fotmob.com/api/leagues?id=47", "json"),
    (
        "sofascore_events",
        f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{datetime.now(UTC):%Y-%m-%d}",
        "json",
    ),
    ("the_odds_api_sports", "https://api.the-odds-api.com/v4/sports/", "json"),
    (
        "open_meteo",
        "https://api.open-meteo.com/v1/forecast?latitude=51.55&longitude=-0.11&hourly=temperature_2m,precipitation,wind_speed_10m&forecast_days=2",
        "json",
    ),
    (
        "kalshi_series_sports",
        "https://api.elections.kalshi.com/trade-api/v2/series?limit=5&category=Sports",
        "json",
    ),
    (
        "kalshi_milestones_soccer",
        "https://api.elections.kalshi.com/trade-api/v2/milestones?limit=5&type=soccer_tournament_multi_leg",
        "json",
    ),
    (
        "kalshi_markets_epl",
        "https://api.elections.kalshi.com/trade-api/v2/markets?limit=5&series_ticker=KXEPLTOTAL",
        "json",
    ),
]


def probe(name: str, url: str, kind: str) -> dict:
    t0 = time.monotonic()
    rec = {"name": name, "url": url, "ok": False}
    try:
        with httpx.Client(timeout=30, headers={"User-Agent": UA}, follow_redirects=True) as c:
            r = c.get(url)
        rec["status"] = r.status_code
        rec["bytes"] = len(r.content)
        rec["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
        rec["content_type"] = r.headers.get("content-type", "")
        if r.status_code == 200:
            if kind == "json":
                body = r.json()
                rec["ok"] = True
                rec["keys"] = list(body)[:10] if isinstance(body, dict) else f"list[{len(body)}]"
            elif kind == "csv-head":
                head = r.text.splitlines()[:1]
                rec["ok"] = bool(head)
                rec["header"] = head[0][:300] if head else ""
            else:
                rec["ok"] = len(r.text) > 500
                rec["snippet"] = r.text[:120].replace("\n", " ")
        else:
            rec["error"] = r.text[:160]
    except Exception as exc:
        rec["error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--md", required=True)
    a = ap.parse_args()
    results = [probe(*p) for p in PROBES]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(
        json.dumps({"probed_at": datetime.now(UTC).isoformat(), "results": results}, indent=1)
        + "\n"
    )
    lines = [
        f"# Source probe {datetime.now(UTC):%Y-%m-%d %H:%M}Z",
        "",
        "| source | ok | status | bytes | ms | note |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        note = r.get("header") or r.get("keys") or r.get("snippet") or r.get("error") or ""
        lines.append(
            f"| {r['name']} | {'✅' if r['ok'] else '❌'} | {r.get('status', '-')} | {r.get('bytes', '-')} | {r.get('elapsed_ms', '-')} | {str(note)[:90].replace('|', '/')} |"
        )
    Path(a.md).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
