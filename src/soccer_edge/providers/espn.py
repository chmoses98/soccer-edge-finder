"""ESPN public site API adapter: fixtures, point-in-time lineups, rosters, formations.

Verified 2026-09-28 (data/samples/espn_xg_probe.json, fetched runner-side):
  GET {BASE}/{league}/scoreboard?dates=YYYYMMDD      -> events[] (id, date, status.type.state pre|in|post,
                                                       competitors[home/away].team{id,abbreviation,displayName},
                                                       venue, neutralSite)
  GET {BASE}/{league}/summary?event={id}            -> rosters[] per side: formation, roster[] entries with
                                                       starter, formationPlace, jersey, position, subbedIn/Out,
                                                       athlete{id, displayName}; also gameInfo, header, odds
  GET {BASE}/{league}/teams                         -> sports[0].leagues[0].teams[].team{id, abbreviation, ...}
Unverified: pre-kickoff availability timing of rosters (we record the ESPN status state with every snapshot so
the prospective archive answers it). No key, no ToS-restricted bulk use: a few GETs per fixture per run.

Identity: ESPN team ids map to canonical team ids ONLY through the explicit table in
data/mappings/espn_map.json (competition slugs and team ids). Nothing is fuzzy-matched; an unmapped team is
reported (fail loud) and the fixture is skipped. `propose_team_map` helps a human extend the table by exact
alias resolution against the canonical registry and writes proposals, never the table itself.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from soccer_edge.core.serialization import content_hash
from soccer_edge.core.time import ensure_utc, utc_now
from soccer_edge.identity.models import Fixture, FixtureStatus, Gender
from soccer_edge.identity.registry import AliasRegistry, AmbiguousAliasError, UnknownAliasError
from soccer_edge.providers.base import Observation, Provenance, QualityFlag
from soccer_edge.providers.http import CachedFetcher
from soccer_edge.providers.interfaces import MatchResult

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
PROVIDER_ID = "espn_site_api"
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MAP_PATH = (
    REPO_ROOT / "data" / "mappings" / "espn_map.json"
)  # NOT under data/registry (the registry loader reads every *.json there)

_STATE_TO_STATUS = {
    "pre": FixtureStatus.SCHEDULED,
    "in": FixtureStatus.LIVE,
    "post": FixtureStatus.FINISHED,
}
_STATUS_NAME_OVERRIDES = {
    "STATUS_POSTPONED": FixtureStatus.POSTPONED,
    "STATUS_CANCELED": FixtureStatus.CANCELLED,
    "STATUS_CANCELLED": FixtureStatus.CANCELLED,
    "STATUS_ABANDONED": FixtureStatus.ABANDONED,
}


@dataclass(frozen=True)
class EspnMap:
    """Explicit ESPN -> canonical identity table (no inference)."""

    leagues: dict[str, str]  # espn league slug -> competition_id
    teams: dict[str, str]  # espn team id -> canonical team_id
    version: str = "0"

    @classmethod
    def load(cls, path: Path = DEFAULT_MAP_PATH) -> EspnMap:
        d = json.loads(path.read_text())
        return cls(
            leagues=dict(d["leagues"]),
            teams={str(k): v for k, v in d["teams"].items()},
            version=str(d.get("version", "0")),
        )

    @property
    def competition_to_league(self) -> dict[str, str]:
        return {v: k for k, v in self.leagues.items()}


@dataclass(frozen=True)
class EspnEvent:
    espn_event_id: str
    league: str
    kickoff_utc: datetime
    state: str  # pre | in | post
    status_name: str
    home_espn_id: str
    away_espn_id: str
    home_name: str
    away_name: str
    home_abbr: str
    away_abbr: str
    venue: str | None
    neutral_site: bool
    home_score: int | None
    away_score: int | None
    season_year: int | None
    season_slug: str | None
    venue_city: str | None = None
    venue_country: str | None = None
    goal_events: tuple[GoalEvent, ...] = ()
    home_shootout: int | None = None
    away_shootout: int | None = None


@dataclass(frozen=True)
class GoalEvent:
    """A scoring play from the scoreboard `competitions[0].details` list."""

    team_espn_id: str
    minute: int  # base minute as displayed (45 for "45'+2'")
    stoppage: int  # added-time minutes (2 for "45'+2'")
    own_goal: bool
    penalty: bool
    shootout: bool

    @property
    def period(self) -> str:
        if self.minute <= 45:
            return "first_half"
        if self.minute <= 90:
            return "second_half"
        return "extra_time"


_MINUTE_RE = re.compile(r"^\s*(\d+)'?(?:\s*\+\s*(\d+)'?)?")


def parse_goal_events(details: list[dict[str, Any]]) -> tuple[list[GoalEvent], bool]:
    """(goal events in order, complete) where complete=False when any scoring play lacks a parsable clock."""
    out: list[GoalEvent] = []
    complete = True
    for d in details or []:
        if not d.get("scoringPlay"):
            continue
        disp = ((d.get("clock") or {}).get("displayValue")) or ""
        m = _MINUTE_RE.match(str(disp))
        team = (d.get("team") or {}).get("id")
        if m is None or team is None:
            complete = False
            continue
        out.append(
            GoalEvent(
                team_espn_id=str(team),
                minute=int(m.group(1)),
                stoppage=int(m.group(2) or 0),
                own_goal=bool(d.get("ownGoal")),
                penalty=bool(d.get("penaltyKick")),
                shootout=bool(d.get("shootout")),
            )
        )
    return out, complete


@dataclass(frozen=True)
class LineupPlayer:
    espn_athlete_id: str
    name: str
    jersey: str | None
    position: str | None
    starter: bool
    formation_place: str | None
    subbed_in: bool
    subbed_out: bool
    active: bool | None


@dataclass(frozen=True)
class LineupSnapshot:
    """Point-in-time lineup observation. `event_state` at capture tells backward-leakage checks whether the
    XI was known before kickoff ('pre') or is a post-hoc team sheet ('in'/'post')."""

    espn_event_id: str
    league: str
    captured_at: datetime
    event_state: str
    kickoff_utc: datetime | None
    home_espn_id: str | None
    away_espn_id: str | None
    home_formation: str | None
    away_formation: str | None
    home: tuple[LineupPlayer, ...]
    away: tuple[LineupPlayer, ...]
    source_url: str
    content_hash: str

    @property
    def published(self) -> bool:
        return (
            bool(self.home)
            and bool(self.away)
            and any(p.starter for p in self.home)
            and any(p.starter for p in self.away)
        )

    @property
    def lineup_state(self) -> str:
        """CONFIRMED only when an XI is published AND was captured before kickoff (no backward leakage).
        ESPN can still report state 'pre' after the scheduled kickoff (late start or slow feed), so the capture
        time is checked against kickoff too; without a kickoff time a sheet cannot be proven pre-match."""
        if not self.published:
            return "unconfirmed"
        if self.event_state != "pre" or self.kickoff_utc is None:
            return "post_hoc"
        return "confirmed" if self.captured_at < self.kickoff_utc else "post_hoc"

    def to_record(self) -> dict[str, Any]:
        def _p(p: LineupPlayer) -> dict[str, Any]:
            return {
                "athlete_id": p.espn_athlete_id,
                "name": p.name,
                "jersey": p.jersey,
                "position": p.position,
                "starter": p.starter,
                "formation_place": p.formation_place,
                "subbed_in": p.subbed_in,
                "subbed_out": p.subbed_out,
                "active": p.active,
            }

        return {
            "schema": "espn_lineup_snapshot_v1",
            "provider": PROVIDER_ID,
            "espn_event_id": self.espn_event_id,
            "league": self.league,
            "captured_at": self.captured_at.isoformat(),
            "event_state": self.event_state,
            "kickoff_utc": self.kickoff_utc.isoformat() if self.kickoff_utc else None,
            "lineup_state": self.lineup_state,
            "published": self.published,
            "home_espn_id": self.home_espn_id,
            "away_espn_id": self.away_espn_id,
            "home_formation": self.home_formation,
            "away_formation": self.away_formation,
            "home": [_p(p) for p in self.home],
            "away": [_p(p) for p in self.away],
            "source_url": self.source_url,
            "content_hash": self.content_hash,
        }


# ---------------------------------------------------------------- pure parsers (offline-testable)


INTERNATIONAL_LEAGUE_PREFIXES = (
    "fifa.",
    "uefa.nations",
    "uefa.euro",
    "concacaf.nations",
    "concacaf.gold",
    "conmebol.america",
    "afc.asian",
    "caf.nations",
)
# ESPN venue country vs national-team display name: accepted equivalences (never inferred beyond this list)
_COUNTRY_ALIASES: dict[str, set[str]] = {
    "united states": {"usa", "united states of america"},
    "republic of ireland": {"ireland"},
    "czech republic": {"czechia"},
    "turkey": {"turkiye", "türkiye"},
    "south korea": {"korea republic", "korea", "republic of korea"},
    "north korea": {"korea dpr", "dpr korea"},
    "iran": {"ir iran", "islamic republic of iran"},
    "china": {"china pr", "people's republic of china"},
    "ivory coast": {"cote d'ivoire", "côte d'ivoire"},
    "bosnia and herzegovina": {"bosnia-herzegovina", "bosnia & herzegovina"},
    "cape verde": {"cabo verde"},
    "eswatini": {"swaziland"},
    "north macedonia": {"macedonia", "fyr macedonia"},
    "united arab emirates": {"uae"},
    "england": {"united kingdom"},
    "scotland": {"united kingdom"},
    "wales": {"united kingdom"},
    "northern ireland": {"united kingdom"},
    "netherlands": {"holland"},
    "trinidad and tobago": {"trinidad & tobago"},
    "dr congo": {
        "congo dr",
        "democratic republic of the congo",
        "congo, democratic republic of the",
    },
}


def _country_key(name: str) -> str:
    return re.sub(r"[^a-z' &]", "", (name or "").strip().lower())


def infer_neutral_site(
    league: str, espn_flag: bool, home_name: str, venue_country: str | None
) -> tuple[bool, str]:
    """(neutral, source). ESPN's `neutralSite` flag is honoured when set. For international competitions,
    a venue country that is not the home team's country (after the explicit alias list) marks the match
    neutral (audit B7: the flag was never set on 1,014 archived international results while ~36% of
    such matches are neutral). Club competitions never infer neutrality from the venue."""
    if espn_flag:
        return True, "espn_flag"
    if not league.startswith(INTERNATIONAL_LEAGUE_PREFIXES) or not venue_country:
        return False, "unknown" if league.startswith(INTERNATIONAL_LEAGUE_PREFIXES) else "club"
    h, v = _country_key(home_name), _country_key(venue_country)
    if h == v or v in _COUNTRY_ALIASES.get(h, set()) or h in _COUNTRY_ALIASES.get(v, set()):
        return False, "venue_country_matches_home"
    return True, "venue_country_mismatch"


def parse_scoreboard(league: str, body: dict[str, Any]) -> list[EspnEvent]:
    out: list[EspnEvent] = []
    for ev in body.get("events") or []:
        comp = (ev.get("competitions") or [{}])[0]
        competitors = comp.get("competitors") or ev.get("competitors") or []
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if home is None or away is None:
            continue
        st = comp.get("status") or ev.get("status") or {}
        st_type = st.get("type") or st
        state = st_type.get("state") or "pre"
        status_name = st_type.get("name") or ""
        season = ev.get("season") or {}
        ko = (
            datetime.strptime(ev["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=UTC)
            if ev.get("date")
            else None
        )
        if ko is None:
            continue

        def _score(c: dict[str, Any], key: str = "score") -> int | None:
            s = c.get(key)
            try:
                return int(s) if s not in (None, "") else None
            except (TypeError, ValueError):
                return None

        goals, goals_complete = parse_goal_events(comp.get("details") or [])
        out.append(
            EspnEvent(
                espn_event_id=str(ev["id"]),
                league=league,
                kickoff_utc=ko,
                state=state,
                status_name=status_name,
                home_espn_id=str(home["team"]["id"]),
                away_espn_id=str(away["team"]["id"]),
                home_name=home["team"].get("displayName") or home["team"].get("name") or "",
                away_name=away["team"].get("displayName") or away["team"].get("name") or "",
                home_abbr=home["team"].get("abbreviation") or "",
                away_abbr=away["team"].get("abbreviation") or "",
                venue=((comp.get("venue") or ev.get("venue") or {}).get("fullName")),
                neutral_site=infer_neutral_site(
                    league,
                    bool(comp.get("neutralSite") or ev.get("neutralSite") or False),
                    home["team"].get("displayName") or home["team"].get("name") or "",
                    ((comp.get("venue") or ev.get("venue") or {}).get("address") or {}).get(
                        "country"
                    ),
                )[0],
                home_score=_score(home),
                away_score=_score(away),
                season_year=season.get("year"),
                season_slug=season.get("slug"),
                venue_city=((comp.get("venue") or ev.get("venue") or {}).get("address") or {}).get(
                    "city"
                ),
                venue_country=(
                    (comp.get("venue") or ev.get("venue") or {}).get("address") or {}
                ).get("country"),
                goal_events=tuple(goals) if goals_complete else (),
                home_shootout=_score(home, "shootoutScore"),
                away_shootout=_score(away, "shootoutScore"),
            )
        )
    return out


def parse_summary_lineups(
    league: str, event_id: str, body: dict[str, Any], *, captured_at: datetime, source_url: str
) -> LineupSnapshot:
    rosters = body.get("rosters") or []
    header = body.get("header") or {}
    comps = header.get("competitions") or []
    state = "pre"
    ko: datetime | None = None
    home_id = away_id = None
    if comps:
        c0 = comps[0]
        state = ((c0.get("status") or {}).get("type") or {}).get("state") or state
        if c0.get("date"):
            try:
                ko = datetime.strptime(c0["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=UTC)
            except ValueError:
                ko = None
        for c in c0.get("competitors") or []:
            if c.get("homeAway") == "home":
                home_id = str((c.get("team") or {}).get("id") or c.get("id"))
            elif c.get("homeAway") == "away":
                away_id = str((c.get("team") or {}).get("id") or c.get("id"))

    def _side(which: str) -> tuple[str | None, tuple[LineupPlayer, ...], str | None]:
        r = next((x for x in rosters if x.get("homeAway") == which), None)
        if r is None:
            return None, (), None
        players = []
        for e in r.get("roster") or []:
            ath = e.get("athlete") or {}
            players.append(
                LineupPlayer(
                    espn_athlete_id=str(ath.get("id") or ""),
                    name=ath.get("displayName") or ath.get("fullName") or "",
                    jersey=str(e["jersey"]) if e.get("jersey") not in (None, "") else None,
                    position=(e.get("position") or {}).get("abbreviation")
                    if isinstance(e.get("position"), dict)
                    else e.get("position"),
                    starter=bool(e.get("starter")),
                    formation_place=str(e["formationPlace"])
                    if e.get("formationPlace") not in (None, "")
                    else None,
                    subbed_in=bool(e.get("subbedIn")),
                    subbed_out=bool(e.get("subbedOut")),
                    active=e.get("active") if isinstance(e.get("active"), bool) else None,
                )
            )
        tid = (
            str((r.get("team") or {}).get("id"))
            if isinstance(r.get("team"), dict) and (r.get("team") or {}).get("id")
            else None
        )
        return r.get("formation"), tuple(players), tid

    hf, hp, htid = _side("home")
    af, ap, atid = _side("away")
    return LineupSnapshot(
        espn_event_id=str(event_id),
        league=league,
        captured_at=ensure_utc(captured_at),
        event_state=state,
        kickoff_utc=ko,
        home_espn_id=home_id or htid,
        away_espn_id=away_id or atid,
        home_formation=hf,
        away_formation=af,
        home=hp,
        away=ap,
        source_url=source_url,
        content_hash=content_hash({"r": rosters, "s": state}),
    )


def parse_teams(body: dict[str, Any]) -> list[dict[str, str]]:
    out = []
    for sp in body.get("sports") or []:
        for lg in sp.get("leagues") or []:
            for t in lg.get("teams") or []:
                team = t.get("team") or t
                out.append(
                    {
                        "id": str(team.get("id")),
                        "abbreviation": team.get("abbreviation") or "",
                        "displayName": team.get("displayName") or "",
                        "shortDisplayName": team.get("shortDisplayName") or "",
                        "name": team.get("name") or "",
                        "location": team.get("location") or "",
                    }
                )
    return out


# ---------------------------------------------------------------- mapping to canonical identities


@dataclass
class MappingReport:
    mapped: int = 0
    unmapped_team_ids: dict[str, str] = field(default_factory=dict)  # espn id -> display name
    unmapped_leagues: set[str] = field(default_factory=set)
    skipped_events: int = 0
    espn_event_by_fixture: dict[str, str] = field(default_factory=dict)
    results: dict[str, tuple[int, int]] = field(
        default_factory=dict
    )  # finished fixtures' FT scores

    def to_json(self) -> dict[str, Any]:
        return {
            "mapped": self.mapped,
            "skipped_events": self.skipped_events,
            "unmapped_team_ids": dict(sorted(self.unmapped_team_ids.items())),
            "unmapped_leagues": sorted(self.unmapped_leagues),
        }


def season_id_for(league: str, ev: EspnEvent) -> str:
    """Canonical season id. European leagues span years ('2026-27'); calendar-season leagues use the year."""
    y = ev.season_year or ev.kickoff_utc.year
    if league in (
        "usa.1",
        "usa.nwsl",
        "mex.1",
        "bra.1",
        "arg.1",
        "fifa.friendly",
        "fifa.world",
        "conmebol.libertadores",
    ):
        return str(y)
    slug = ev.season_slug or ""
    if slug[:4].isdigit() and "-" in slug[:8]:
        return slug[:7]
    return f"{y}-{str(y + 1)[-2:]}"


def events_to_fixtures(
    events: list[EspnEvent], emap: EspnMap, report: MappingReport | None = None
) -> list[Fixture]:
    report = report if report is not None else MappingReport()
    out: list[Fixture] = []
    for ev in events:
        comp = emap.leagues.get(ev.league)
        if comp is None:
            report.unmapped_leagues.add(ev.league)
            report.skipped_events += 1
            continue
        h, a = emap.teams.get(ev.home_espn_id), emap.teams.get(ev.away_espn_id)
        if h is None:
            report.unmapped_team_ids[ev.home_espn_id] = ev.home_name
        if a is None:
            report.unmapped_team_ids[ev.away_espn_id] = ev.away_name
        if h is None or a is None:
            report.skipped_events += 1
            continue
        status = _STATUS_NAME_OVERRIDES.get(
            ev.status_name, _STATE_TO_STATUS.get(ev.state, FixtureStatus.SCHEDULED)
        )
        season = season_id_for(ev.league, ev)
        fid = Fixture.make_id(comp, season, h, a)
        out.append(
            Fixture(
                fixture_id=fid,
                competition_id=comp,
                season_id=season,
                home_team_id=h,
                away_team_id=a,
                kickoff_utc=ev.kickoff_utc,
                kickoff_date=ev.kickoff_utc.date().isoformat(),
                status=status,
                neutral_site=ev.neutral_site,
            )
        )
        report.espn_event_by_fixture[fid] = ev.espn_event_id
        if (
            status is FixtureStatus.FINISHED
            and ev.home_score is not None
            and ev.away_score is not None
        ):
            report.results[fid] = (ev.home_score, ev.away_score)
        report.mapped += 1
    return out


def propose_team_map(
    teams: list[dict[str, str]],
    registry: AliasRegistry,
    *,
    country: str | None,
    existing: dict[str, str],
    gender: Gender = Gender.MEN,
) -> dict[str, Any]:
    """Exact alias resolution only (registry aliases, weak forms disabled). Ambiguity is reported, not resolved."""
    proposals: dict[str, str] = {}
    unresolved: dict[str, str] = {}
    ambiguous: dict[str, str] = {}
    for t in teams:
        if t["id"] in existing:
            continue
        hit = None
        for cand in (t["displayName"], t["name"], t["shortDisplayName"], t["location"]):
            if not cand:
                continue
            try:
                hit = registry.resolve_team(
                    cand, country=country, gender=gender, allow_weak=False
                ).team_id
                break
            except UnknownAliasError:
                continue
            except AmbiguousAliasError as exc:
                ambiguous[t["id"]] = f"{t['displayName']}: {exc}"
                break
        if hit:
            proposals[t["id"]] = hit
        elif t["id"] not in ambiguous:
            unresolved[t["id"]] = t["displayName"]
    return {"proposed": proposals, "unresolved": unresolved, "ambiguous": ambiguous}


# ---------------------------------------------------------------- network provider


class EspnProvider:
    provider_id = PROVIDER_ID

    def __init__(
        self,
        fetcher: CachedFetcher | None = None,
        emap: EspnMap | None = None,
        base: str = ESPN_BASE,
    ) -> None:
        self.fetcher = fetcher or CachedFetcher(max_age=timedelta(minutes=10))
        self.map = emap or EspnMap.load()
        self.base = base

    def _get_json(self, url: str) -> tuple[dict[str, Any], Provenance]:
        f = self.fetcher.fetch(
            url,
            source=PROVIDER_ID,
            license_note="ESPN public site API; personal/research use; no redistribution of bulk data",
        )
        return json.loads(f.content.decode("utf-8")), f.provenance

    def scoreboard(self, league: str, day: date) -> Observation[list[EspnEvent]]:
        url = f"{self.base}/{league}/scoreboard?dates={day:%Y%m%d}"
        body, prov = self._get_json(url)
        return Observation(payload=parse_scoreboard(league, body), provenance=prov)

    def fixtures_window(
        self, leagues: list[str], start: date, days: int
    ) -> tuple[list[EspnEvent], list[str]]:
        """Per-day queries (the range form of `dates` returned 400 in the probe)."""
        events: list[EspnEvent] = []
        failures: list[str] = []
        seen: set[str] = set()
        for lg in leagues:
            for i in range(days):
                d = start + timedelta(days=i)
                try:
                    obs = self.scoreboard(lg, d)
                except Exception as exc:
                    failures.append(f"{lg} {d}: {str(exc)[:100]}")
                    continue
                for ev in obs.payload:
                    if ev.espn_event_id not in seen:
                        seen.add(ev.espn_event_id)
                        events.append(ev)
        return events, failures

    def lineup(self, league: str, espn_event_id: str) -> Observation[LineupSnapshot]:
        url = f"{self.base}/{league}/summary?event={espn_event_id}"
        body, prov = self._get_json(url)
        snap = parse_summary_lineups(
            league, espn_event_id, body, captured_at=prov.observed_at, source_url=url
        )
        flags = (QualityFlag.OK,) if snap.published else (QualityFlag.UNVERIFIED,)
        return Observation(
            payload=snap,
            provenance=prov,
            flags=flags,
            notes=() if snap.published else ("no published XI at capture",),
        )

    def teams(self, league: str) -> Observation[list[dict[str, str]]]:
        url = f"{self.base}/{league}/teams"
        body, prov = self._get_json(url)
        return Observation(payload=parse_teams(body), provenance=prov)


def capture_lineups(
    provider: EspnProvider,
    events: list[EspnEvent],
    out_dir: Path,
    *,
    as_of: datetime | None = None,
    max_events: int = 200,
) -> dict[str, Any]:
    """Prospective lineup capture: one JSONL row per (event, capture) — appended, never rewritten. Change-suppressed
    by content hash per event (data/lineups/<date>/<league>.jsonl + last_hashes.json)."""
    from soccer_edge.core.serialization import append_jsonl, read_json_or, write_json

    as_of = as_of or utc_now()
    hp = out_dir / "last_hashes.json"
    last = read_json_or(hp, {})
    stats = {
        "events": 0,
        "captured": 0,
        "unchanged": 0,
        "published_pre_kickoff": 0,
        "published_post": 0,
        "unpublished": 0,
        "failures": [],
    }
    for ev in events[:max_events]:
        stats["events"] += 1
        try:
            obs = provider.lineup(ev.league, ev.espn_event_id)
        except Exception as exc:
            stats["failures"].append(f"{ev.league}/{ev.espn_event_id}: {str(exc)[:100]}")
            continue
        snap = obs.payload
        if snap.lineup_state == "confirmed":
            stats["published_pre_kickoff"] += 1
        elif snap.lineup_state == "post_hoc":
            stats["published_post"] += 1
        else:
            stats["unpublished"] += 1
        if last.get(ev.espn_event_id) == snap.content_hash:
            stats["unchanged"] += 1
            continue
        last[ev.espn_event_id] = snap.content_hash
        append_jsonl(out_dir / f"{as_of:%Y-%m-%d}" / f"{ev.league}.jsonl", snap.to_record())
        stats["captured"] += 1
    write_json(hp, last)
    return stats


# ---------------------------------------------------------------- competitions fed by ESPN (fixtures + FT results)

# competition_id -> ESPN league slugs whose matches form the RESULTS POOL used to fit that competition's strengths.
# National-team competitions pool all men's international matches (form travels across NL / WCQ / friendlies).
INTERNATIONAL_POOL = (
    "uefa.nations",
    "fifa.friendly",
    "fifa.worldq.uefa",
    "fifa.worldq.conmebol",
    "fifa.worldq.concacaf",
    "fifa.worldq.afc",
    "fifa.worldq.caf",
    "uefa.euroq",
    "concacaf.nations.league",
)
ESPN_POOLS: dict[str, tuple[str, ...]] = {
    "usa.mls": ("usa.1",),
    "mex.liga_mx": ("mex.1",),
    "bra.serie_a": ("bra.1",),
    "arg.primera": ("arg.1",),
    "uefa.nations_league": INTERNATIONAL_POOL,
    "fifa.friendly": INTERNATIONAL_POOL,
    "concacaf.nations_league": INTERNATIONAL_POOL,
    "fifa.world_cup_qualifiers": INTERNATIONAL_POOL,
    "uefa.euro_qualifiers": INTERNATIONAL_POOL,
}


def results_from_events(
    events: list[EspnEvent], emap: EspnMap, report: MappingReport | None = None
) -> list[MatchResult]:
    """Finished events with both scores -> MatchResult rows (competition = the ESPN league's competition)."""
    report = report if report is not None else MappingReport()
    out: list[MatchResult] = []
    for ev in events:
        if ev.state != "post" or ev.home_score is None or ev.away_score is None:
            continue
        if ev.status_name in _STATUS_NAME_OVERRIDES:  # postponed/abandoned never count as results
            continue
        comp = emap.leagues.get(ev.league)
        h, a = emap.teams.get(ev.home_espn_id), emap.teams.get(ev.away_espn_id)
        if comp is None or h is None or a is None:
            if comp is None:
                report.unmapped_leagues.add(ev.league)
            if h is None:
                report.unmapped_team_ids[ev.home_espn_id] = ev.home_name
            if a is None:
                report.unmapped_team_ids[ev.away_espn_id] = ev.away_name
            report.skipped_events += 1
            continue
        season = season_id_for(ev.league, ev)
        out.append(
            MatchResult(
                fixture_id=Fixture.make_id(comp, season, h, a),
                competition_id=comp,
                season_id=season,
                match_date=ev.kickoff_utc.date().isoformat(),
                home_team_id=h,
                away_team_id=a,
                home_goals=ev.home_score,
                away_goals=ev.away_score,
                neutral_site=ev.neutral_site,
                **result_evidence(ev),
            )
        )
    return out


def result_evidence(ev: EspnEvent) -> dict[str, Any]:
    """Settlement evidence derived from the scoreboard: status token, kickoff, timed goal split, shootout.

    Fails closed: when the timed goal events do not reproduce the reported score, no split is emitted and
    the settlement engine will refuse contracts that need one.
    """
    name = ev.status_name or ""
    et_status = "AET" in name or "EXTRA" in name
    pen_status = "PEN" in name and "PENDING" not in name
    out: dict[str, Any] = {
        "status_name": name or None,
        "kickoff_utc": ev.kickoff_utc.isoformat().replace("+00:00", "Z"),
        "home_shootout": ev.home_shootout,
        "away_shootout": ev.away_shootout,
        "result_source": PROVIDER_ID,
    }
    pens = ev.home_shootout is not None and ev.away_shootout is not None
    if pens:
        out["decided_on_penalties"] = True
        if ev.home_shootout != ev.away_shootout:
            out["winner_after_penalties"] = (
                "home" if ev.home_shootout > ev.away_shootout else "away"
            )
    elif pen_status:
        out["decided_on_penalties"] = True
    goals = [g for g in ev.goal_events if not g.shootout]
    if goals or name == "STATUS_FULL_TIME":
        # own goals are credited to the opponent of the team ESPN lists on the play
        def _side(g: GoalEvent) -> str | None:
            if g.team_espn_id == ev.home_espn_id:
                s = "home"
            elif g.team_espn_id == ev.away_espn_id:
                s = "away"
            else:
                return None
            if g.own_goal:
                s = "away" if s == "home" else "home"
            return s

        sides = [_side(g) for g in goals]
        if all(sd is not None for sd in sides):
            reg = [(sd, g) for sd, g in zip(sides, goals) if g.period != "extra_time"]
            ht = [(sd, g) for sd, g in zip(sides, goals) if g.period == "first_half"]
            et = [(sd, g) for sd, g in zip(sides, goals) if g.period == "extra_time"]
            h_reg = sum(1 for sd, _ in reg if sd == "home")
            a_reg = sum(1 for sd, _ in reg if sd == "away")
            h_et = sum(1 for sd, _ in et if sd == "home")
            a_et = sum(1 for sd, _ in et if sd == "away")
            consistent = (h_reg + h_et == ev.home_score) and (a_reg + a_et == ev.away_score)
            if consistent:
                out.update(
                    {
                        "home_goals_regulation": h_reg,
                        "away_goals_regulation": a_reg,
                        "home_goals_ht": sum(1 for sd, _ in ht if sd == "home"),
                        "away_goals_ht": sum(1 for sd, _ in ht if sd == "away"),
                        "home_goals_et": h_et,
                        "away_goals_et": a_et,
                        "extra_time_played": bool(et) or et_status or pens,
                        "goal_events_source": "espn_scoreboard_details",
                    }
                )
                if sides:
                    # first scorer: an own goal as the first goal is credited per the rule above
                    out["first_scorer_team"] = sides[0]
                elif name == "STATUS_FULL_TIME":
                    out["first_scorer_team"] = None
    if name == "STATUS_FULL_TIME" and "home_goals_regulation" not in out:
        # full time with no goal detail: the reported score is the regulation score
        out["home_goals_regulation"] = ev.home_score
        out["away_goals_regulation"] = ev.away_score
        out["extra_time_played"] = False
    return out


def result_record(r: MatchResult, espn_event_id: str, league: str) -> dict[str, Any]:
    return {
        "schema": "espn_result_v1",
        "espn_event_id": espn_event_id,
        "league": league,
        **r.model_dump(mode="json"),
    }


def _result_row_upgrades(prev: dict[str, Any], new: dict[str, Any]) -> bool:
    """A later scoreboard read may carry settlement evidence the archived row lacks (status token, timed
    goal split, shootout). The file stays append-only: the richer row is appended and `results()` keeps the
    last row per event. A row never 'upgrades' to a different final score."""
    if (prev.get("home_goals"), prev.get("away_goals")) != (
        new.get("home_goals"),
        new.get("away_goals"),
    ):
        return False
    for key in (
        "status_name",
        "home_goals_regulation",
        "winner_after_penalties",
        "first_scorer_team",
    ):
        if prev.get(key) is None and new.get(key) is not None:
            return True
    return False


class EspnArchive:
    """Offline view of what the runner-side jobs archived: results/espn/<league>.jsonl (append-only, one row per
    ESPN event, last row wins) and fixtures/espn/<date>/*.json (latest file wins)."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    # -- results
    def results_path(self, league: str) -> Path:
        return self.root / "results" / "espn" / f"{league}.jsonl"

    def known_event_ids(self, league: str) -> set[str]:
        from soccer_edge.core.serialization import read_jsonl

        pth = self.results_path(league)
        return {r["espn_event_id"] for r in read_jsonl(pth)} if pth.exists() else set()

    def append_results(self, league: str, rows: list[dict[str, Any]]) -> int:
        from soccer_edge.core.serialization import append_jsonl, read_jsonl

        pth = self.results_path(league)
        latest: dict[str, dict[str, Any]] = {}
        if pth.exists():
            for r in read_jsonl(pth):
                latest[r["espn_event_id"]] = r
        n = 0
        for r in rows:
            prev = latest.get(r["espn_event_id"])
            if prev is not None and not _result_row_upgrades(prev, r):
                continue
            append_jsonl(pth, r)
            latest[r["espn_event_id"]] = r
            n += 1
        return n

    def results(self, leagues: tuple[str, ...]) -> list[MatchResult]:
        from soccer_edge.core.serialization import read_jsonl

        by_event: dict[str, dict[str, Any]] = {}
        for lg in leagues:
            pth = self.results_path(lg)
            if not pth.exists():
                continue
            for r in read_jsonl(pth):
                by_event[r["espn_event_id"]] = r
        out = []
        for r in by_event.values():
            out.append(
                MatchResult(
                    **{k: v for k, v in r.items() if k not in ("schema", "espn_event_id", "league")}
                )
            )
        return out

    # -- fixtures
    def latest_fixtures(self) -> tuple[list[Fixture], dict[str, str], datetime | None]:
        from soccer_edge.core.serialization import read_json

        files = sorted((self.root / "fixtures" / "espn").glob("*/*.json"))
        if not files:
            return [], {}, None
        doc = read_json(files[-1])
        fixtures: list[Fixture] = []
        eid_by_fixture: dict[str, str] = {}
        for row in doc.get("fixtures", []):
            eid = row.pop("espn_event_id", None)
            fx = Fixture(**row)
            fixtures.append(fx)
            if eid:
                eid_by_fixture[fx.fixture_id] = eid
        return (
            fixtures,
            eid_by_fixture,
            datetime.fromisoformat(doc["as_of"]) if doc.get("as_of") else None,
        )
