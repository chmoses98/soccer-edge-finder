"""Runner-side probe of ESPN soccer endpoints and free xG sources. Writes trimmed samples (no full
payload dumps) to data/samples/ so the structure can be studied from a container without egress.
Read-only; no credentials."""

from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

UA = "soccer-edge-finder/0.1 (+https://github.com/chmoses98/soccer-edge-finder; probe)"
OUT = Path("data/samples")
ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer"
ESPN_LEAGUES = {
    "eng.1": "EPL",
    "esp.1": "La Liga",
    "ger.1": "Bundesliga",
    "ita.1": "Serie A",
    "fra.1": "Ligue 1",
    "usa.1": "MLS",
    "uefa.champions": "UCL",
    "uefa.europa": "UEL",
    "uefa.europa.conf": "UECL",
    "fifa.friendly": "Intl friendlies",
    "uefa.nations": "Nations League",
    "eng.2": "Championship",
    "mex.1": "Liga MX",
    "usa.nwsl": "NWSL",
}


def get(client: httpx.Client, url: str, **params):
    t0 = time.monotonic()
    try:
        r = client.get(url, params=params)
        body = (
            r.json() if r.headers.get("content-type", "").startswith("application/json") else None
        )
        return {
            "status": r.status_code,
            "ms": int((time.monotonic() - t0) * 1000),
            "bytes": len(r.content),
            "body": body,
            "text": None if body is not None else r.text[:300],
        }
    except Exception as exc:
        return {"status": 0, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


def trim_event(ev: dict) -> dict:
    comp = (ev.get("competitions") or [{}])[0]
    return {
        "id": ev.get("id"),
        "uid": ev.get("uid"),
        "date": ev.get("date"),
        "name": ev.get("name"),
        "shortName": ev.get("shortName"),
        "season": ev.get("season"),
        "status": (ev.get("status") or {}).get("type"),
        "venue": comp.get("venue"),
        "neutralSite": comp.get("neutralSite"),
        "attendance": comp.get("attendance"),
        "competitors": [
            {k: c.get(k) for k in ("id", "homeAway", "winner", "score", "form")}
            | {
                "team": {
                    k: (c.get("team") or {}).get(k)
                    for k in (
                        "id",
                        "uid",
                        "abbreviation",
                        "displayName",
                        "shortDisplayName",
                        "name",
                        "location",
                    )
                }
            }
            for c in comp.get("competitors", [])
        ],
        "odds": comp.get("odds"),
        "details_count": len(comp.get("details") or []),
        "details_sample": (comp.get("details") or [])[:3],
        "keys": sorted(comp.keys()),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {"probed_at": datetime.now(UTC).isoformat(), "espn": {}, "xg": {}}
    with httpx.Client(timeout=30, headers={"User-Agent": UA}, follow_redirects=True) as c:
        # --- ESPN scoreboards per league (today +/- a week window via dates param)
        sample_event_ids: list[tuple[str, str]] = []
        for lg, name in ESPN_LEAGUES.items():
            r2 = get(c, f"{ESPN}/{lg}/scoreboard")
            body = r2.get("body") or {}
            evs = body.get("events") or []
            report["espn"][lg] = {
                "name": name,
                "status": r2.get("status"),
                "events_today": len(evs),
                "leagues_meta": [
                    {k: L.get(k) for k in ("id", "uid", "name", "abbreviation", "slug", "season")}
                    for L in body.get("leagues", [])
                ][:1],
                "first_event": trim_event(evs[0]) if evs else None,
                "top_keys": sorted(body.keys()),
            }
            for ev in evs[:2]:
                sample_event_ids.append((lg, ev["id"]))
            # date-range query (next 10 days)
            start = datetime.now(UTC)
            r3 = get(
                c,
                f"{ESPN}/{lg}/scoreboard",
                dates=f"{start:%Y%m%d}-{(start.replace(month=start.month + 1 if start.month < 12 else 12, day=5)):%Y%m%d}",
            )
            b3 = r3.get("body") or {}
            report["espn"][lg]["events_next_window"] = len(b3.get("events") or [])
            report["espn"][lg]["window_query_status"] = r3.get("status")
            if b3.get("events") and not sample_event_ids:
                sample_event_ids.append((lg, b3["events"][0]["id"]))
            if b3.get("events"):
                report["espn"][lg]["window_first_event"] = trim_event(b3["events"][0])
        # --- ESPN summary (lineups, rosters, formations) for a few events
        report["espn"]["summaries"] = []
        for lg, eid in sample_event_ids[:6]:
            r = get(c, f"{ESPN}/{lg}/summary", event=eid)
            body = r.get("body") or {}
            rosters = body.get("rosters") or []
            trimmed = {
                "league": lg,
                "event": eid,
                "status": r.get("status"),
                "top_keys": sorted(body.keys()),
                "rosters": [
                    {
                        "homeAway": ro.get("homeAway"),
                        "team": (ro.get("team") or {}).get("displayName"),
                        "formation": ro.get("formation"),
                        "n_roster": len(ro.get("roster") or []),
                        "roster_sample": [
                            {
                                k: p.get(k)
                                for k in (
                                    "starter",
                                    "jersey",
                                    "formationPlace",
                                    "subbedIn",
                                    "subbedOut",
                                )
                            }
                            | {
                                "position": (p.get("position") or {}).get("abbreviation"),
                                "athlete": {
                                    k: (p.get("athlete") or {}).get(k)
                                    for k in ("id", "displayName", "fullName")
                                },
                                "keys": sorted(p.keys()),
                            }
                            for p in (ro.get("roster") or [])[:3]
                        ],
                    }
                    for ro in rosters
                ],
                "keyEvents_sample": [
                    (k.get("type") or {}).get("text") for k in (body.get("keyEvents") or [])[:5]
                ],
                "header_competitions_keys": sorted(
                    ((body.get("header") or {}).get("competitions") or [{}])[0].keys()
                ),
                "gameInfo_keys": sorted((body.get("gameInfo") or {}).keys()),
                "injuries_present": bool(body.get("injuries")),
                "injuries_sample": str(body.get("injuries"))[:300],
                "odds_present": bool(body.get("odds")),
                "odds_sample": str(body.get("odds"))[:300],
            }
            report["espn"]["summaries"].append(trimmed)
        # --- ESPN teams list for identity mapping (one league)
        r = get(c, f"{ESPN}/eng.1/teams")
        teams = (((r.get("body") or {}).get("sports") or [{}])[0].get("leagues") or [{}])[0].get(
            "teams"
        ) or []
        report["espn"]["teams_eng1"] = {
            "status": r.get("status"),
            "n": len(teams),
            "sample": [
                {
                    k: (t.get("team") or {}).get(k)
                    for k in (
                        "id",
                        "abbreviation",
                        "displayName",
                        "shortDisplayName",
                        "location",
                        "name",
                    )
                }
                for t in teams[:25]
            ],
        }
        r = get(c, f"{ESPN}/uefa.champions/teams")
        teams = (((r.get("body") or {}).get("sports") or [{}])[0].get("leagues") or [{}])[0].get(
            "teams"
        ) or []
        report["espn"]["teams_ucl"] = {
            "status": r.get("status"),
            "n": len(teams),
            "sample": [
                {
                    k: (t.get("team") or {}).get(k)
                    for k in ("id", "abbreviation", "displayName", "location")
                }
                for t in teams[:40]
            ],
        }

        # --- xG sources
        xg_probes = {
            "understat_league_page": ("https://understat.com/league/EPL/2025", "html"),
            "understat_match_page": ("https://understat.com/match/26631", "html"),
            "fbref_epl": ("https://fbref.com/en/comps/9/Premier-League-Stats", "html"),
            "football_data_couk_E0_2526_xg_columns": (
                "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
                "csv",
            ),
            "football_data_couk_E0_2425_xg_columns": (
                "https://www.football-data.co.uk/mmz4281/2425/E0.csv",
                "csv",
            ),
            "football_data_couk_E0_2324_xg_columns": (
                "https://www.football-data.co.uk/mmz4281/2324/E0.csv",
                "csv",
            ),
            "football_data_couk_SP1_2526": (
                "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
                "csv",
            ),
            "football_data_couk_D1_2526": (
                "https://www.football-data.co.uk/mmz4281/2526/D1.csv",
                "csv",
            ),
            "football_data_couk_I1_2526": (
                "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
                "csv",
            ),
            "football_data_couk_F1_2526": (
                "https://www.football-data.co.uk/mmz4281/2526/F1.csv",
                "csv",
            ),
            "football_data_couk_E0_2627": (
                "https://www.football-data.co.uk/mmz4281/2627/E0.csv",
                "csv",
            ),
            "statsbomb_open_data_competitions": (
                "https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json",
                "json",
            ),
            "fotmob_match_details": (
                "https://www.fotmob.com/api/matchDetails?matchId=4506263",
                "json",
            ),
            "sofascore_xg": ("https://api.sofascore.com/api/v1/event/12436870/statistics", "json"),
            "whoscored": (
                "https://www.whoscored.com/Regions/252/Tournaments/2/England-Premier-League",
                "html",
            ),
            "kaggle_style_github_understat_mirror_1": (
                "https://raw.githubusercontent.com/danielvicente/understat-data/main/README.md",
                "text",
            ),
            "opta_analyst_xg_page": (
                "https://theanalyst.com/eu/2025/08/premier-league-xg-table",
                "html",
            ),
            "fivethirtyeight_spi_archive": (
                "https://projects.fivethirtyeight.com/soccer-api/club/spi_matches.csv",
                "csv",
            ),
            "footystats_free": ("https://footystats.org/api/league-matches?key=example", "json"),
            "api_football_free": ("https://v3.football.api-sports.io/status", "json"),
        }
        for name, (url, kind) in xg_probes.items():
            r = get(c, url)
            rec = {
                "url": url,
                "status": r.get("status"),
                "bytes": r.get("bytes"),
                "ms": r.get("ms"),
                "error": r.get("error"),
            }
            if r.get("status") == 200:
                if kind == "csv":
                    txt = (r.get("text") or "") if r.get("body") is None else json.dumps(r["body"])
                    # re-fetch text for csv (body parse would have failed -> text present)
                    head = txt.splitlines()[0] if txt else ""
                    rec["header"] = head[:400]
                    rec["has_xg_cols"] = any(k in head for k in ("HxG", "AxG", "xG"))
                    rec["rows"] = txt.count("\n")
                elif kind == "html":
                    txt = r.get("text") or ""
                    full = c.get(url).text if len(txt) < 400 else txt
                    rec["has_embedded_json"] = bool(re.search(r"JSON\.parse\('", full))
                    rec["snippet"] = full[:200].replace("\n", " ")
                    rec["mentions_xg"] = "xG" in full or "xg" in full
                elif kind == "json":
                    body = r.get("body")
                    rec["keys_or_len"] = (
                        list(body)[:8]
                        if isinstance(body, dict)
                        else (f"list[{len(body)}]" if isinstance(body, list) else str(body)[:100])
                    )
                    if name.startswith("statsbomb") and isinstance(body, list):
                        rec["competitions"] = sorted(
                            {(x.get("competition_name"), x.get("season_name")) for x in body}
                        )[:60]
                else:
                    rec["snippet"] = (r.get("text") or "")[:200]
            report["xg"][name] = rec
    (OUT / "espn_xg_probe.json").write_text(
        json.dumps(report, indent=1, default=str)[:900000] + "\n"
    )
    print(
        json.dumps(
            {
                "espn": {
                    k: (v.get("status"), v.get("events_today"), v.get("events_next_window"))
                    for k, v in report["espn"].items()
                    if isinstance(v, dict) and "status" in v
                },
                "summaries": [
                    (
                        s["league"],
                        s["status"],
                        [r["formation"] for r in s["rosters"]],
                        [r["n_roster"] for r in s["rosters"]],
                    )
                    for s in report["espn"]["summaries"]
                ],
                "xg": {
                    k: (v.get("status"), v.get("has_xg_cols"), v.get("has_embedded_json"))
                    for k, v in report["xg"].items()
                },
            },
            indent=1,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
