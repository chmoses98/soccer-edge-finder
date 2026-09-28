"""Runner-side probe of ESPN soccer endpoints and free xG sources. Writes trimmed samples (no full
payload dumps) to data/samples/ so the structure can be studied from a container without egress.
Read-only; no credentials."""

from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime, timedelta
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


TEAM_LIST_LEAGUES = [
    "eng.1",
    "eng.2",
    "esp.1",
    "ger.1",
    "ita.1",
    "fra.1",
    "ned.1",
    "por.1",
    "usa.1",
    "mex.1",
    "bra.1",
    "arg.1",
    "uefa.champions",
    "uefa.europa",
    "uefa.europa.conf",
    "uefa.nations",
    "fifa.friendly",
    "concacaf.nations.league",
    "usa.nwsl",
    "eng.w.1",
    "sco.1",
    "tur.1",
    "ksa.1",
]
CANDIDATE_SLUGS = [
    "concacaf.nations.league",
    "eng.3",
    "eng.4",
    "eng.5",
    "usa.usl.1",
    "bra.2",
    "fifa.wwc",
    "fifa.world",
    "fifa.worldq.uefa",
    "fifa.worldq.conmebol",
    "fifa.worldq.concacaf",
    "fifa.worldq.afc",
    "fifa.worldq.caf",
    "uefa.euro",
    "uefa.euroq",
    "conmebol.libertadores",
    "conmebol.sudamericana",
    "concacaf.champions",
    "concacaf.gold",
    "afc.champions",
    "eng.fa",
    "eng.league_cup",
    "esp.copa_del_rey",
    "ger.dfb_pokal",
    "ita.coppa_italia",
    "fra.coupe_de_france",
    "ned.1",
    "por.1",
    "bel.1",
    "sco.1",
    "tur.1",
    "ksa.1",
    "bra.1",
    "arg.1",
    "col.1",
    "chi.1",
    "per.1",
    "uru.1",
    "jpn.1",
    "kor.1",
    "chn.1",
    "aus.1",
    "isr.1",
    "den.1",
    "swe.1",
    "nor.1",
    "pol.1",
    "esp.2",
    "ger.2",
    "ita.2",
    "fra.2",
    "uefa.wchampions",
    "fifa.cwc",
    "fifa.olympics",
    "eng.w.1",
    "esp.w.1",
]


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
        pre_match_ids: list[tuple[str, str, str]] = []
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
            # per-day queries for the next 3 days (the range form of `dates` returned 400 on 2026-09-28)
            start = datetime.now(UTC)
            per_day = []
            pre_ids: list[tuple[str, str, str]] = []
            for i in range(1, 4):
                d = start + timedelta(days=i)
                r3 = get(c, f"{ESPN}/{lg}/scoreboard", dates=f"{d:%Y%m%d}")
                b3 = r3.get("body") or {}
                evs3 = b3.get("events") or []
                per_day.append(
                    {"date": f"{d:%Y-%m-%d}", "status": r3.get("status"), "events": len(evs3)}
                )
                for ev in evs3:
                    st = ((ev.get("competitions") or [{}])[0].get("status") or {}).get("type") or {}
                    if st.get("state") == "pre" and len(pre_ids) < 2:
                        pre_ids.append((lg, ev["id"], ev.get("date")))
            report["espn"][lg]["per_day_next3"] = per_day
            report["espn"][lg]["window_query_status"] = "per-day"
            report["espn"][lg]["events_next_window"] = sum(x["events"] for x in per_day)
            # range form, recorded for the audit
            r4 = get(
                c,
                f"{ESPN}/{lg}/scoreboard",
                dates=f"{start:%Y%m%d}-{(start + timedelta(days=7)):%Y%m%d}",
            )
            report["espn"][lg]["range_query_status"] = r4.get("status")
            report["espn"][lg]["range_query_events"] = len(
                (r4.get("body") or {}).get("events") or []
            )
            pre_match_ids.extend(pre_ids)
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
        # --- ESPN team lists (compact, FULL lists) for identity mapping by exact alias resolution offline
        report["espn"]["team_lists"] = {}
        for lg in TEAM_LIST_LEAGUES:
            r = get(c, f"{ESPN}/{lg}/teams")
            body = r.get("body") or {}
            teams = []
            for sp in body.get("sports") or []:
                for L in sp.get("leagues") or []:
                    for t in L.get("teams") or []:
                        tm = t.get("team") or t
                        teams.append(
                            {
                                "id": str(tm.get("id")),
                                "abbreviation": tm.get("abbreviation"),
                                "displayName": tm.get("displayName"),
                                "shortDisplayName": tm.get("shortDisplayName"),
                                "name": tm.get("name"),
                                "location": tm.get("location"),
                            }
                        )
            report["espn"]["team_lists"][lg] = {
                "status": r.get("status"),
                "n": len(teams),
                "teams": teams,
            }
        # --- candidate league slugs (status + today's event count only)
        report["espn"]["slug_probe"] = {}
        for lg in CANDIDATE_SLUGS:
            r = get(c, f"{ESPN}/{lg}/scoreboard")
            body = r.get("body") or {}
            lgm = (body.get("leagues") or [{}])[0]
            report["espn"]["slug_probe"][lg] = {
                "status": r.get("status"),
                "events_today": len(body.get("events") or []),
                "name": lgm.get("name"),
                "slug": lgm.get("slug"),
            }
        # --- PRE-MATCH summary probe: are rosters/lineups exposed before kickoff, and how long before?
        report["espn"]["pre_match_summaries"] = []
        for lg, eid, ko in pre_match_ids[:8]:
            r = get(c, f"{ESPN}/{lg}/summary", event=eid)
            body = r.get("body") or {}
            rosters = body.get("rosters") or []
            report["espn"]["pre_match_summaries"].append(
                {
                    "league": lg,
                    "event": eid,
                    "kickoff": ko,
                    "hours_to_kickoff": round(
                        (
                            datetime.strptime(ko, "%Y-%m-%dT%H:%MZ").replace(tzinfo=UTC)
                            - datetime.now(UTC)
                        ).total_seconds()
                        / 3600,
                        2,
                    )
                    if ko
                    else None,
                    "status": r.get("status"),
                    "top_keys": sorted(body.keys()),
                    "rosters_present": bool(rosters),
                    "rosters": [
                        {
                            "homeAway": ro.get("homeAway"),
                            "formation": ro.get("formation"),
                            "n_roster": len(ro.get("roster") or []),
                            "n_starters": sum(
                                1 for e in (ro.get("roster") or []) if e.get("starter")
                            ),
                        }
                        for ro in rosters
                    ],
                    "injuries_present": bool(body.get("injuries")),
                    "injuries_sample": str(body.get("injuries"))[:400],
                    "odds_present": bool(body.get("odds") or body.get("pickcenter")),
                }
            )
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
            "football_data_couk_SP1_2627": (
                "https://www.football-data.co.uk/mmz4281/2627/SP1.csv",
                "csv",
            ),
            "football_data_couk_D1_2627": (
                "https://www.football-data.co.uk/mmz4281/2627/D1.csv",
                "csv",
            ),
            "football_data_couk_I1_2627": (
                "https://www.football-data.co.uk/mmz4281/2627/I1.csv",
                "csv",
            ),
            "football_data_couk_F1_2627": (
                "https://www.football-data.co.uk/mmz4281/2627/F1.csv",
                "csv",
            ),
            "football_data_couk_E1_2627": (
                "https://www.football-data.co.uk/mmz4281/2627/E1.csv",
                "csv",
            ),
            "football_data_couk_N1_2627": (
                "https://www.football-data.co.uk/mmz4281/2627/N1.csv",
                "csv",
            ),
            "football_data_couk_P1_2627": (
                "https://www.football-data.co.uk/mmz4281/2627/P1.csv",
                "csv",
            ),
            "football_data_couk_notes_2627": ("https://www.football-data.co.uk/notes.txt", "text"),
            "understat_league_json_probe": ("https://understat.com/league/EPL/2026", "html"),
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
