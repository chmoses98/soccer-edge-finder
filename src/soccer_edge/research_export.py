"""Research export: the SOCCER data-archive -> the Edge Finder research graph (``app/latest/explorer``).

A pure adapter beside the v1 app export (docs/APP_EXPORT.md, "Research explorer"). It reads the v1
publication it extends (``<app_root>/{manifest,events,markets,model_prices,recommendations}.json``, so
every ``prt_`` / ``evt_`` / ``mkt_`` id is the one the v1 export emitted) plus what the production
pipeline already archives on ``data-archive`` and what ``main`` commits:

* ``snapshots/<day>/cap-*.jsonl[.gz]``          Kalshi quote captures -> per-event market history
* ``predictions/<day>/predictions.jsonl[.gz]``  prediction ledger -> projection history per fixture x ticker
* ``settlements/<day>/predictions.jsonl[.gz]``  settlement ledger -> settled outcomes, CLV (settled events)
* ``evaluation/model_health.v1.json``           calibration cells (model x family x horizon)
* ``results/espn/<league>.jsonl``               ESPN results (goals only) -> game logs, form, head-to-head,
                                                rankings, and a RESEARCH-labelled dc_laplace_v2 refit
* ``lineups/<day>/*``, ``lineups/history/*``    lineup sheets and appearance counts (no minutes, no stats)
* ``weather/<day>.jsonl[.gz]``                  kickoff-hour forecasts and venue
* ``runs/latest.model_board.v1.json``           current board quantiles (latest only)
* ``data/international/results_v1.csv.gz``      national-team Elo history (main; exact intl:->nat. map)
* ``data/registry/*.json``                      team / competition names (main)

Nothing here prices, gates or recommends. Every number is a stored value or simple arithmetic over
stored values (per-game averages, rates, records, trailing means, ranks). The one model fit is the
repository's own ``fit_competition`` with ``StrengthConfigV2`` on committed ESPN results, as the audit
recommends; its output is labelled RESEARCH and is never presented as the production posterior.

Failure policy: any exception leaves the previous ``explorer/`` tree untouched (``publish_explorer``
is atomic) and the process exits 1. The v1 payload is never touched.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import math
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

_CONTRACT_DIR = Path(__file__).resolve().parents[2] / "contract"
try:
    import edge_finder_contract  # noqa: F401
except ImportError:  # pragma: no cover - only outside pytest/CI, which put contract/ on the path
    if (_CONTRACT_DIR / "edge_finder_contract").is_dir():
        sys.path.insert(0, str(_CONTRACT_DIR))

from edge_finder_contract import build, ids, timeutil  # noqa: E402
from edge_finder_contract import freshness as fr  # noqa: E402
from edge_finder_contract import research as R  # noqa: E402, N812
from edge_finder_contract.publish import dumps  # noqa: E402

from soccer_edge import __version__  # noqa: E402
from soccer_edge.gamescript.presentation import script_engine_payload  # noqa: E402
from soccer_edge.identity.registry import AliasRegistry  # noqa: E402
from soccer_edge.model.strength_v2 import StrengthConfigV2  # noqa: E402
from soccer_edge.providers.interfaces import MatchResult  # noqa: E402
from soccer_edge.providers.international_results import team_id as intl_team_id  # noqa: E402
from soccer_edge.run.modeling import fit_competition  # noqa: E402

SPORT = "SOCCER"
AUDIT_DATE = "2026-10-03"
REPO_ROOT = Path(__file__).resolve().parents[2]
METHODOLOGY_VERSION = f"soccer_edge {__version__} research_export v1"

SNAPSHOTS_DIR = "snapshots"
PREDICTIONS_DIR = "predictions"
SETTLEMENTS_DIR = "settlements"
RESULTS_DIR = "results/espn"
LINEUPS_DIR = "lineups"
WEATHER_DIR = "weather"
BOARD_FILE = "runs/latest.model_board.v1.json"
SLATE_FILE = "runs/latest.actionable_slate.v1.json"
# the soccer script-engine payload (event_research.extensions.soccer_script_engine) gets this share of the
# per-event budget before projection history; beyond it the payload trims deep evidence (recorded in `trimmed`)
SCRIPT_ENGINE_MAX_BYTES = 75_000
MODEL_HEALTH_FILE = "evaluation/model_health.v1.json"
REGISTRY_DIR = REPO_ROOT / "data" / "registry"
INTL_RESULTS_FILE = REPO_ROOT / "data" / "international" / "results_v1.csv.gz"
INTL_MANIFEST_FILE = REPO_ROOT / "data" / "international" / "MANIFEST.json"

#: Competitions priced from the pooled international results archive (run/pipeline.py
#: INTL_POOL_COMPETITIONS, copied so the export does not import the run pipeline).
INTL_POOL_COMPETITIONS = frozenset(
    {
        "uefa.nations_league",
        "fifa.friendly",
        "concacaf.nations_league",
        "fifa.world_cup_qualifiers",
        "uefa.euro_qualifiers",
        "uefa.euro",
        "fifa.world_cup",
        "conmebol.copa_america",
        "concacaf.gold_cup",
    }
)
INTL_POOL = "intl"
INTL_POOL_LABEL = (
    "national teams, ESPN international archive (Nations Leagues, WC qualifiers, friendlies)"
)

# budgets (ADAPTER_SPEC hard rules)
SETTLED_WINDOW_DAYS = 7
PROFILE_GAMES_CAP = 40
GAME_SERIES_CAP = 40
ELO_SERIES_CAP = 100
MARKET_HISTORY_TICKER_CAP = 200
MARKET_HISTORY_MAX_BYTES = 380_000
PROJECTION_HISTORY_MAX_BYTES = 60_000
EVENT_MAX_BYTES = (
    145_000  # the per-event budget is 150 KB; the projection history table shrinks to fit
)
DEFAULT_NEW_TEAM_EFFECTIVE = StrengthConfigV2().new_team_weighted_matches
CLUB_SEASON_MIN_GAMES = 3
LAST_N_WINDOWS = (5, 10)
INTL_MIN_GAMES = 5
QUANTILE_INDEXES = (0, 10, 25, 49, 50, 74, 89, 99)  # stored levels (i + 0.5) / 100

RESULTS_FRESH = fr.Thresholds(3 * 86400, 7 * 86400)
MODEL_FRESH = fr.Thresholds(12 * 3600, 36 * 3600)
MARKET_FRESH = fr.Thresholds(20 * 60, 60 * 60)

HORIZON_MINUTES = {
    "T-24h": 1440,
    "T-12h": 720,
    "T-6h": 360,
    "T-2h": 120,
    "T-90m": 90,
    "T-60m": 60,
    "T-30m": 30,
    "T-15m": 15,
    "T-10m": 10,
    "close": 0,
}

_SECRET_MARKERS = ("PRIVATE KEY", "ghp_", "github_pat_", "Bearer ", "AIRTABLE")

# ---- verbatim audit limitations (scratchpad/phase2/audit_soccer.md, 2026-10-03) -------------------------
LIM_RESULTS = [
    "ESPN results carry goals only (HT split 3 %, shots/corners/cards/xG 0 %)",
    "results/espn covers 14 ESPN leagues from 2024-07-01; club top-5 league history is not in the repo "
    "(fetched at run time into a gitignored cache)",
    "207 duplicated fixture_ids (Liga MX Apertura/Clausura share season 2024) and 85 duplicated espn_event_ids: "
    "deduplicated by espn_event_id (last row wins); repeated fixture ids get the repo's :occN suffix",
]
LIM_ELO = [
    "national-team history needs an intl: -> nat. map; only teams mapped exactly from registry names/aliases are published",
    "data/international/results_v1.csv.gz is a frozen snapshot (date_max 2026-08-26); Elo is the pre-match rating "
    "of each archived match (post-match ratings are not stored)",
]
LIM_DC = [
    "team-level ratings are never persisted by production (only a parameter_hash is archived)",
    "refit by the research export with the repo's own fit_competition + StrengthConfigV2 (dc_laplace_v2) on "
    "results/espn per competition; NOT the production posterior (production prices with dc_laplace_v1)",
    "club top-5 cannot be refit from committed data (history lives in the runtime cache)",
]
LIM_MARKET_HISTORY = [
    "change-suppressed: a snapshot row is written only when the quote changed, so no point between two captures "
    "means unchanged or not captured",
    "the stored horizon / minutes_to_kickoff fields are unreliable (computed from the market close, not the fixture "
    "kickoff) and are not published; time to kickoff = event start_time_utc - captured_at",
    "orderbook depth is never captured (null on every row)",
]
LIM_PROJECTIONS = [
    "the model is RESEARCH_ONLY everywhere (walk-forward log loss 1.0010 vs Bet365 0.9732)",
    "the international pool (model_family *.intl_pool) is explicitly not validated (docs/KNOWN_LIMITATIONS.md #26)",
    "production runs dc_laplace_v1 on 100 % of ledger rows",
]
LIM_DISTRIBUTIONS = [
    "board quantiles are the current board only (overwritten each run; not archived across runs)",
    "realisations are never stored",
]
LIM_LINEUPS = [
    "lineup sheets carry ids, names, positions and starter/sub flags only: no minutes, no stats",
    "about 50 % of passed fixtures had a pre-kickoff XI (median lead 37 min)",
    "no canonical player registry (data/registry players: 0); ESPN athlete ids only",
]
LIM_WEATHER = [
    "Open-Meteo kickoff-hour forecasts joined by espn_event_id (weather rows carry no fixture_id)",
    "weather STATUS health DEGRADED (geocode failures)",
]
LIM_CONTEXT = [
    "rest/congestion features (rest days, matches in 14/28 d) are point-in-time but research found "
    "≈ no signal (congestion ≈ -0.001 log loss, rest nothing)",
    "no L3/L5 goal form is stored by the repo; "
    "the L5/L10 windows here are arithmetic over results/espn",
]
LIM_CLV = [
    "sharp reference almost never present (Pinnacle TRUE_CLOSE 3.95 %)",
    "clv_yes_points non-null on 7,872 / 10,874 settled records",
]
LIM_CALIBRATION = ["95 % of the evaluated mass is the unvalidated international pool"]


class ResearchExportError(Exception):
    pass


# ----------------------------------------------------------------------------- small helpers
def _f(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _r(value: Any, nd: int = 4) -> float | None:
    v = _f(value)
    return None if v is None else round(v, nd)


def _ts(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return timeutil.parse_ts(value)
    except (ValueError, TypeError):
        return None


def _iso(value: Any) -> str | None:
    d = _ts(value)
    return timeutil.to_iso(d) if d else None


def _day_ts(day: str) -> str:
    return f"{day}T00:00:00Z"


def _open(path: Path):
    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open(encoding="utf-8")


def _jsonl(path: Path):
    with _open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield line


def _quick_field(line: str, key: str) -> str | None:
    """The string value of a top-level-ish key without parsing the line (compact JSON); None if absent."""
    for pat in (f'"{key}":"', f'"{key}": "'):
        i = line.find(pat)
        if i >= 0:
            j = line.find('"', i + len(pat))
            return line[i + len(pat) : j]
    return None


def _day_files(root: Path, sub: str, pattern: str) -> list[Path]:
    d = root / sub
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob(f"*/{pattern}") if p.is_file())


def _team_participant(team_id: str, name: str) -> dict[str, Any]:
    """The same call the v1 export makes (app_export._team), so participant ids match."""
    return build.participant(
        sport=SPORT,
        participant_type="TEAM",
        source="team_id",
        source_id=team_id,
        display_name=name,
        short_name=None,
    )


def _pid(team_id: str) -> str:
    return ids.participant_id(SPORT, "TEAM", "team_id", team_id)


def _eid(fixture_id: str) -> str:
    return ids.event_id(SPORT, "fixture_id", fixture_id)


def _parse_fixture_id(fixture_id: str) -> tuple[str | None, str | None, str | None, str | None]:
    parts = fixture_id.split(":")
    if len(parts) >= 5 and parts[0] == "fx":
        return parts[1], parts[2], parts[3], parts[4]
    return None, None, None, None


def _pool_of(competition_id: str | None) -> str | None:
    if not competition_id:
        return None
    return INTL_POOL if competition_id in INTL_POOL_COMPETITIONS else competition_id


# ----------------------------------------------------------------------------- inputs
@dataclass
class ResearchInputs:
    now: datetime
    manifest: dict[str, Any]
    events: list[dict[str, Any]]
    markets: list[dict[str, Any]]
    model_prices: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    wagers: list[dict[str, Any]]
    team_names: dict[str, str]
    team_aliases: dict[str, list[str]]
    team_meta: dict[str, dict[str, Any]]
    competition_names: dict[str, str]
    results: list[dict[str, Any]]
    predictions: list[dict[str, Any]]
    settlements: list[dict[str, Any]]
    snapshots: dict[str, list[dict[str, Any]]]
    lineups: list[dict[str, Any]]
    appearances: dict[str, dict[str, Any]]
    weather: dict[str, dict[str, Any]]
    board: dict[str, Any]
    model_health: list[dict[str, Any]]
    intl_rows: list[dict[str, Any]]
    intl_date_max: str | None
    espn_team_map: dict[str, str]
    sources: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    # latest actionable slate (price-time script survivability; gamescript/presentation.py)
    slate: dict[str, Any] = field(default_factory=dict)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _v1_items(app_root: Path, kind: str) -> list[dict[str, Any]]:
    path = app_root / f"{kind}.json"
    return list(_read_json(path)["items"]) if path.exists() else []


def _load_results(root: Path, now: datetime) -> list[dict[str, Any]]:
    """Deduplicated by espn_event_id, last row wins (EspnArchive.results semantics); match_date <= now."""
    d = root / RESULTS_DIR
    by_event: dict[str, dict[str, Any]] = {}
    files = sorted(p for p in d.glob("*.jsonl*") if p.is_file()) if d.is_dir() else []
    for path in files:
        for line in _jsonl(path):
            row = json.loads(line)
            if (
                row.get("espn_event_id") is None
                or row.get("home_goals") is None
                or row.get("away_goals") is None
            ):
                continue
            by_event[str(row["espn_event_id"])] = row
    today = now.date().isoformat()
    rows = [r for r in by_event.values() if str(r.get("match_date", "")) <= today]
    rows.sort(key=lambda r: (r["match_date"], r.get("kickoff_utc") or "", str(r["espn_event_id"])))
    # Liga MX / Argentina: Apertura and Clausura share a season id, so fixture ids repeat. Give the
    # 2nd.. occurrence the repo's own ":occN" suffix (identity/models.py Fixture.make_id) so every game
    # has a distinct event id; the first occurrence keeps the plain fixture id.
    seen: dict[str, int] = defaultdict(int)
    for r in rows:
        seen[r["fixture_id"]] += 1
        n = seen[r["fixture_id"]]
        r["_game_fixture_id"] = r["fixture_id"] if n == 1 else f"{r['fixture_id']}:occ{n}"
    return rows


def _load_settlements(root: Path, now: datetime) -> list[dict[str, Any]]:
    lo = now - timedelta(days=SETTLED_WINDOW_DAYS)
    out = []
    for path in _day_files(root, SETTLEMENTS_DIR, "predictions.jsonl*"):
        for line in _jsonl(path):
            row = json.loads(line)
            at = _ts(row.get("settled_at"))
            if at is None or not (lo <= at <= now):
                continue
            clv = row.get("clv") or {}
            kal = (row.get("close_v2") or {}).get("kalshi") or {}
            out.append(
                {
                    "record_id": row.get("record_id"),
                    "prediction_record_id": row.get("prediction_record_id"),
                    "fixture_id": row.get("fixture_id"),
                    "ticker": row.get("ticker"),
                    "family": row.get("family"),
                    "model_family": row.get("model_family"),
                    "horizon": row.get("horizon"),
                    "outcome": row.get("outcome"),
                    "fair_mean": _f(row.get("fair_probability_mean")),
                    "fair_low": _f(row.get("fair_probability_low")),
                    "fair_high": _f(row.get("fair_probability_high")),
                    "entry_yes_ask": _f(row.get("entry_yes_ask")),
                    "entry_yes_mid": _f(row.get("entry_yes_mid")),
                    "close_yes_mid": _f(row.get("close_yes_mid")),
                    "close_class": row.get("close_class"),
                    "kalshi_close_class": kal.get("close_class"),
                    "clv_yes_points": _f(row.get("clv_yes_points")),
                    "clv_model_signed_points": _f(row.get("clv_model_signed_points")),
                    "clv_fee_aware_yes": _f((clv.get("yes") or {}).get("clv_fee_aware_points")),
                    "clv_fee_aware_no": _f((clv.get("no") or {}).get("clv_fee_aware_points")),
                    "evidence": row.get("evidence") or {},
                    "settled_at": timeutil.to_iso(at),
                    "source": f"{path.parent.parent.name}/{path.parent.name}/{path.name}",
                }
            )
    return out


def _load_predictions(root: Path, now: datetime, fixtures: set[str]) -> list[dict[str, Any]]:
    out = []
    for path in _day_files(root, PREDICTIONS_DIR, "predictions.jsonl*"):
        for line in _jsonl(path):
            fid = _quick_field(line, "fixture_id")
            if fid is not None and fid not in fixtures:
                continue
            row = json.loads(line)
            if row.get("fixture_id") not in fixtures:
                continue
            at = _ts(row.get("as_of"))
            if at is None or at > now:
                continue
            prob = row.get("probability") or {}
            mkt = row.get("market") or {}
            sem = row.get("semantics") or {}
            out.append(
                {
                    "record_id": row.get("record_id"),
                    "run_id": row.get("run_id"),
                    "as_of": timeutil.to_iso(at),
                    "fixture_id": row["fixture_id"],
                    "competition_id": row.get("competition_id"),
                    "kickoff_utc": _iso(row.get("kickoff_utc")),
                    "ticker": row.get("ticker"),
                    "family": row.get("family"),
                    "description": sem.get("description") or prob.get("description"),
                    "mean": _f(prob.get("fair_probability_mean")),
                    "low": _f(prob.get("fair_probability_low")),
                    "high": _f(prob.get("fair_probability_high")),
                    "n_worlds": prob.get("n_worlds"),
                    "yes_ask": _f(mkt.get("yes_ask")),
                    "model_family": row.get("model_family"),
                    "model_version": row.get("model_version"),
                    "engine_version": row.get("engine_version"),
                    "context": row.get("context") or {},
                    "lineup_state": row.get("lineup_state"),
                    "source": f"{path.parent.parent.name}/{path.parent.name}/{path.name}",
                }
            )
    out.sort(key=lambda r: (r["fixture_id"], r["ticker"] or "", r["as_of"], r["record_id"] or ""))
    return out


def _load_snapshots(
    root: Path, now: datetime, tickers: set[str]
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in _day_files(root, SNAPSHOTS_DIR, "cap-*.jsonl*"):
        for line in _jsonl(path):
            tk = _quick_field(line, "ticker")
            if tk is not None and tk not in tickers:
                continue
            row = json.loads(line)
            tk = row.get("ticker")
            if tk not in tickers:
                continue
            at = _ts(row.get("captured_at"))
            if at is None or at > now:
                continue
            out[tk].append(
                {
                    "captured_at": at,
                    "yes_bid": _f(row.get("yes_bid")),
                    "yes_ask": _f(row.get("yes_ask")),
                    "last_price": _f(row.get("last_price")),
                    "volume": _f(row.get("volume")),
                    "open_interest": _f(row.get("open_interest")),
                    "source": f"kalshi:{row.get('batch_id') or path.name.split('.')[0]}",
                }
            )
    for rows in out.values():
        rows.sort(key=lambda r: (r["captured_at"], r["source"]))
    return dict(out)


def _load_lineups(
    root: Path, now: datetime, wanted_espn: set[str]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """(daily sheets for the published events, appearance counts per athlete over every stored sheet)."""
    sheets: list[dict[str, Any]] = []
    counts: dict[str, dict[str, Any]] = {}
    base = root / LINEUPS_DIR
    if not base.is_dir():
        return sheets, counts
    files = sorted(p for p in base.glob("*/*.jsonl*") if p.is_file())
    latest_by_event: dict[str, dict[str, Any]] = {}
    for path in files:
        for line in _jsonl(path):
            row = json.loads(line)
            at = _ts(row.get("captured_at"))
            if at is None or at > now:
                continue
            row["_source"] = f"{LINEUPS_DIR}/{path.parent.name}/{path.name}"
            eid = str(row.get("espn_event_id"))
            if row.get("home") or row.get("away"):
                prev = latest_by_event.get(eid)
                if prev is None or timeutil.to_iso(at) >= prev["_at"]:
                    row["_at"] = timeutil.to_iso(at)
                    latest_by_event[eid] = row
            if eid in wanted_espn:
                row["_at"] = timeutil.to_iso(at)
                sheets.append(row)
    # appearance counts: one count per (event, athlete) from the newest sheet with players for that event
    for row in latest_by_event.values():
        day = (row.get("kickoff_utc") or row["_at"])[:10]
        for side in ("home", "away"):
            for p in row.get(side) or []:
                aid = str(p.get("athlete_id") or "")
                if not aid:
                    continue
                c = counts.setdefault(
                    aid,
                    {
                        "sheets": 0,
                        "starts": 0,
                        "sub_appearances": 0,
                        "unused_bench": 0,
                        "first_seen": day,
                        "last_seen": day,
                    },
                )
                c["sheets"] += 1
                if p.get("starter"):
                    c["starts"] += 1
                elif p.get("subbed_in"):
                    c["sub_appearances"] += 1
                else:
                    c["unused_bench"] += 1
                c["first_seen"] = min(c["first_seen"], day)
                c["last_seen"] = max(c["last_seen"], day)
    sheets.sort(key=lambda r: (str(r.get("espn_event_id")), r["_at"], r.get("content_hash") or ""))
    return sheets, counts


def _load_weather(root: Path, now: datetime, wanted_espn: set[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    d = root / WEATHER_DIR
    if not d.is_dir():
        return out
    revisions: dict[str, int] = defaultdict(int)
    for path in sorted(p for p in d.glob("*.jsonl*") if p.is_file()):
        for line in _jsonl(path):
            row = json.loads(line)
            eid = str(row.get("espn_event_id"))
            at = _ts(row.get("captured_at"))
            if eid not in wanted_espn or at is None or at > now:
                continue
            revisions[eid] += 1
            row["_at"] = timeutil.to_iso(at)
            row["_source"] = f"{WEATHER_DIR}/{path.name}"
            if eid not in out or row["_at"] >= out[eid]["_at"]:
                out[eid] = row
    for eid, row in out.items():
        row["_revisions"] = revisions[eid]
    return out


def _load_intl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with gzip.open(path, "rb") as fh:
        text = fh.read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    rows.sort(key=lambda r: (r["date"], r["home_id"], r["away_id"]))
    return rows


def load_inputs(
    *, data_root: Path, app_root: Path, now: datetime | None = None, repo_root: Path = REPO_ROOT
) -> ResearchInputs:
    data_root, app_root = Path(data_root), Path(app_root)
    manifest_path = app_root / "manifest.json"
    if not manifest_path.exists():
        raise ResearchExportError(f"no v1 manifest at {manifest_path}: run app-export first")
    manifest = _read_json(manifest_path)
    if now is None:
        now = timeutil.parse_ts(manifest["generated_at"])
    events = _v1_items(app_root, "events")
    markets = _v1_items(app_root, "markets")
    warnings: list[str] = []

    reg = AliasRegistry.from_directory(repo_root / "data" / "registry")
    team_names = {tid: t.name for tid, t in reg.teams.items()}
    team_aliases = {tid: sorted(set(t.aliases)) for tid, t in reg.teams.items()}
    team_meta = {
        tid: {
            "country": t.country,
            "kind": getattr(t.kind, "value", str(t.kind)),
            "gender": getattr(t.gender, "value", str(t.gender)),
        }
        for tid, t in reg.teams.items()
    }
    competition_names = {cid: c.name for cid, c in reg.competitions.items()}
    espn_map_path = repo_root / "data" / "mappings" / "espn_map.json"
    espn_team_map = (
        dict(_read_json(espn_map_path).get("teams", {})) if espn_map_path.exists() else {}
    )

    settlements = _load_settlements(data_root, now)
    v1_fixtures = {
        e["source_ids"].get("fixture_id")
        for e in events
        if e.get("source_ids", {}).get("fixture_id")
    }
    fixtures = v1_fixtures | {s["fixture_id"] for s in settlements if s.get("fixture_id")}
    predictions = _load_predictions(data_root, now, fixtures)
    tickers = {m["kalshi_ticker"] for m in markets if m.get("event_id")} | {
        s["ticker"] for s in settlements if s.get("ticker")
    }
    snapshots = _load_snapshots(data_root, now, tickers)
    results = _load_results(data_root, now)
    wanted_espn = {
        str(e["source_ids"]["espn_event_id"])
        for e in events
        if e.get("source_ids", {}).get("espn_event_id")
    }
    by_fixture = defaultdict(list)
    for r in results:
        by_fixture[r["fixture_id"]].append(r)
    for fid in fixtures - v1_fixtures:
        for r in by_fixture.get(fid, []):
            wanted_espn.add(str(r["espn_event_id"]))
    lineups, appearances = _load_lineups(data_root, now, wanted_espn)
    weather = _load_weather(data_root, now, wanted_espn)
    board_path = data_root / BOARD_FILE
    board = _read_json(board_path) if board_path.exists() else {}
    slate_path = data_root / SLATE_FILE
    slate = _read_json(slate_path) if slate_path.exists() else {}
    mh_path = data_root / MODEL_HEALTH_FILE
    mh = _read_json(mh_path) if mh_path.exists() else []
    if isinstance(
        mh, list
    ):  # point-in-time: a cell evaluated after the publication instant is not shown
        mh = [
            c for c in mh if isinstance(c, dict) and (_ts(c.get("last_evaluated_at")) or now) <= now
        ]
    intl_path = repo_root / "data" / "international" / "results_v1.csv.gz"
    intl_rows = _load_intl(intl_path)
    intl_manifest = repo_root / "data" / "international" / "MANIFEST.json"
    intl_date_max = _read_json(intl_manifest).get("date_max") if intl_manifest.exists() else None
    for what, ok in (
        ("snapshots", snapshots),
        ("predictions", predictions),
        ("results/espn", results),
        ("model board", board),
        ("international results", intl_rows),
    ):
        if not ok:
            warnings.append(f"{what}: nothing read")
    return ResearchInputs(
        now=now,
        manifest=manifest,
        events=events,
        markets=markets,
        model_prices=_v1_items(app_root, "model_prices"),
        recommendations=_v1_items(app_root, "recommendations"),
        wagers=_v1_items(app_root, "wagers"),
        team_names=team_names,
        team_aliases=team_aliases,
        team_meta=team_meta,
        competition_names=competition_names,
        results=results,
        predictions=predictions,
        settlements=settlements,
        snapshots=snapshots,
        lineups=lineups,
        appearances=appearances,
        weather=weather,
        board=board,
        model_health=mh if isinstance(mh, list) else [],
        intl_rows=intl_rows,
        intl_date_max=intl_date_max,
        espn_team_map=espn_team_map,
        warnings=warnings,
        slate=slate if isinstance(slate, dict) else {},
    )


# ----------------------------------------------------------------------------- team aggregates
@dataclass
class Game:
    """One archived ESPN result from one team's point of view."""

    event_id: str
    fixture_id: str
    competition_id: str
    season_id: str
    match_date: str
    t: str
    team_id: str
    opponent_id: str
    home_away: str
    gf: int
    ga: int
    espn_event_id: str

    @property
    def points(self) -> int:
        return 3 if self.gf > self.ga else 1 if self.gf == self.ga else 0

    @property
    def outcome(self) -> str:
        return "W" if self.gf > self.ga else "T" if self.gf == self.ga else "L"


def _games_by_team(results: list[dict[str, Any]]) -> dict[str, list[Game]]:
    out: dict[str, list[Game]] = defaultdict(list)
    for r in results:
        eid = _eid(r["_game_fixture_id"])
        t = _iso(r.get("kickoff_utc")) or _day_ts(r["match_date"])
        neutral = bool(r.get("neutral_site"))
        for side, other in (("home", "away"), ("away", "home")):
            out[r[f"{side}_team_id"]].append(
                Game(
                    event_id=eid,
                    fixture_id=r["_game_fixture_id"],
                    competition_id=r["competition_id"],
                    season_id=str(r.get("season_id")),
                    match_date=r["match_date"],
                    t=t,
                    team_id=r[f"{side}_team_id"],
                    opponent_id=r[f"{other}_team_id"],
                    home_away="NEUTRAL" if neutral else side.upper(),
                    gf=int(r[f"{side}_goals"]),
                    ga=int(r[f"{other}_goals"]),
                    espn_event_id=str(r["espn_event_id"]),
                )
            )
    for games in out.values():
        games.sort(key=lambda g: (g.t, g.event_id))
    return dict(out)


def _rates(games: list[Game]) -> dict[str, float | None]:
    n = len(games)
    if not n:
        return {}
    w = sum(1 for g in games if g.gf > g.ga)
    d = sum(1 for g in games if g.gf == g.ga)
    return {
        "goals_for_per_game": round(sum(g.gf for g in games) / n, 4),
        "goals_against_per_game": round(sum(g.ga for g in games) / n, 4),
        "goal_difference_per_game": round(sum(g.gf - g.ga for g in games) / n, 4),
        "points_per_game": round(sum(g.points for g in games) / n, 4),
        "clean_sheet_rate": round(100.0 * sum(1 for g in games if g.ga == 0) / n, 2),
        "btts_rate": round(100.0 * sum(1 for g in games if g.gf > 0 and g.ga > 0) / n, 2),
        "over_2_5_rate": round(100.0 * sum(1 for g in games if g.gf + g.ga >= 3) / n, 2),
        "_record": f"{w}-{d}-{n - w - d}",
    }


@dataclass(frozen=True)
class MetricDef:
    slug: str
    name: str
    short: str
    description: str
    stat_type: str
    unit: str | None
    higher_is_better: bool | None
    category: str
    splits: bool = False


FORM_METRICS = (
    MetricDef(
        "points_per_game",
        "Points per game",
        "PPG",
        "League points per game (3 win / 1 draw / 0 loss) from the "
        "stored final score of each archived ESPN result; display value is the W-D-L record.",
        "RATE",
        "points",
        True,
        "results",
        True,
    ),
    MetricDef(
        "goals_for_per_game",
        "Goals scored per game",
        "GF/G",
        "Mean goals scored per archived ESPN result "
        "(final score as stored; includes extra time where played).",
        "RATE",
        "goals",
        True,
        "attack",
        True,
    ),
    MetricDef(
        "goals_against_per_game",
        "Goals conceded per game",
        "GA/G",
        "Mean goals conceded per archived ESPN result.",
        "RATE",
        "goals",
        False,
        "defence",
        True,
    ),
    MetricDef(
        "goal_difference_per_game",
        "Goal difference per game",
        "GD/G",
        "Mean (goals scored - goals conceded) per archived ESPN result.",
        "RATE",
        "goals",
        True,
        "results",
    ),
    MetricDef(
        "clean_sheet_rate",
        "Clean-sheet rate",
        "CS%",
        "Share of archived ESPN results with zero goals conceded, in percent.",
        "PERCENT",
        "%",
        True,
        "defence",
    ),
    MetricDef(
        "btts_rate",
        "Both-teams-to-score rate",
        "BTTS%",
        "Share of archived ESPN results in which both sides "
        "scored, in percent (context for btts markets; neither direction is better).",
        "PERCENT",
        "%",
        None,
        "game_state",
    ),
    MetricDef(
        "over_2_5_rate",
        "Over 2.5 goals rate",
        "O2.5%",
        "Share of archived ESPN results with three or more "
        "total goals, in percent (context for total_goals markets; neither direction is better).",
        "PERCENT",
        "%",
        None,
        "game_state",
    ),
)
SPLIT_SLUGS = tuple(m.slug for m in FORM_METRICS if m.splits)


@dataclass
class Pool:
    key: str
    label: str
    competitions: set[str]
    windows: list[dict[str, Any]]
    primary_window: dict[str, Any]
    season: str | None
    teams: set[str] = field(default_factory=set)


def _pool_label(key: str, names: dict[str, str]) -> str:
    return INTL_POOL_LABEL if key == INTL_POOL else f"{names.get(key, key)} teams"


def _window_games(pool: Pool, games: list[Game], window: dict[str, Any]) -> list[Game]:
    mine = [g for g in games if _pool_of(g.competition_id) == pool.key]
    if window["kind"] == "SEASON":
        return [g for g in mine if g.season_id == pool.season]
    return mine[-int(window["n"]) :]


def _window_ok(pool: Pool, n_games: int, window: dict[str, Any]) -> bool:
    if window["kind"] == "SEASON":
        return n_games >= CLUB_SEASON_MIN_GAMES
    if pool.key == INTL_POOL:
        return n_games >= INTL_MIN_GAMES
    return n_games >= int(window["n"])


def _window_filter(pool: Pool, window: dict[str, Any]) -> str:
    if window["kind"] == "SEASON":
        return f"teams with >= {CLUB_SEASON_MIN_GAMES} archived {pool.season} games in this competition"
    if pool.key == INTL_POOL:
        return f"national teams with >= {INTL_MIN_GAMES} archived internationals (window = their last {window['n']})"
    return f"teams with >= {window['n']} archived games in this competition (window = their last {window['n']})"


# ----------------------------------------------------------------------------- Elo (international dataset)
def _intl_map(inputs: ResearchInputs) -> dict[str, str]:
    """nat.<code> -> intl:<slug>, exact name/alias matches only; anything ambiguous is dropped."""
    present = {r["home_id"] for r in inputs.intl_rows} | {r["away_id"] for r in inputs.intl_rows}
    claims: dict[str, set[str]] = defaultdict(set)
    for tid, meta in inputs.team_meta.items():
        if meta.get("kind") != "national" or meta.get("gender") != "men":
            continue
        cands = {intl_team_id(inputs.team_names[tid])} | {
            intl_team_id(a) for a in inputs.team_aliases.get(tid, [])
        }
        hits = cands & present
        if len(hits) == 1:
            claims[next(iter(hits))].add(tid)
    return {next(iter(tids)): iid for iid, tids in claims.items() if len(tids) == 1}


def _intl_by_team(inputs: ResearchInputs) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in inputs.intl_rows:
        out[r["home_id"]].append(r)
        if r["away_id"] != r["home_id"]:
            out[r["away_id"]].append(r)
    return out


def _elo_history(by_team: dict[str, list[dict[str, Any]]], intl_id: str) -> list[dict[str, Any]]:
    out = []
    for r in by_team.get(intl_id, []):
        home = r["home_id"] == intl_id
        out.append(
            {
                "date": r["date"],
                "elo": _f(r["home_elo_pre" if home else "away_elo_pre"]),
                "opponent_intl": r["away_id"] if home else r["home_id"],
                "opponent_name": r["away_team"] if home else r["home_team"],
                "gf": int(r["home_goals" if home else "away_goals"]),
                "ga": int(r["away_goals" if home else "home_goals"]),
                "tournament": r["tournament"],
                "neutral": r.get("neutral") == "1",
                "home": home,
            }
        )
    return out


# ----------------------------------------------------------------------------- the build
@dataclass
class Ctx:
    inputs: ResearchInputs
    run_id: str
    now: datetime
    v1_events: dict[str, dict[str, Any]]  # fixture_id -> v1 event
    events: dict[str, dict[str, Any]]  # event_id -> event object (v1 or built)
    event_fixture: dict[str, str]  # event_id -> fixture_id
    settled_by_fixture: dict[str, list[dict[str, Any]]]
    preds_by_fixture: dict[str, list[dict[str, Any]]]
    games: dict[str, list[Game]]
    pools: dict[str, Pool]
    team_pool: dict[str, str]
    profile_teams: set[str]
    names: dict[str, str]
    intl_map: dict[str, str]
    metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    rankings: dict[tuple[str, str, str], dict[str, Any]] = field(default_factory=dict)
    obs: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    split_obs: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    primary_obs: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    team_series: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    dc_fits: dict[str, dict[str, Any]] = field(default_factory=dict)
    elo_latest: dict[str, dict[str, Any]] = field(default_factory=dict)
    profile_pids: set[str] = field(default_factory=set)
    intl_by_team: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    caps_notes: list[str] = field(default_factory=list)


def _q(
    status: str,
    source: str,
    ctx: Ctx,
    *,
    production: bool = True,
    data_as_of: Any = None,
    coverage: Any = None,
    sample_size: Any = None,
    limitations: list[str] | None = None,
    source_version: Any = None,
) -> dict[str, Any]:
    return R.quality(
        status=status,
        source=source,
        generated_at=ctx.now,
        production=production,
        data_as_of=data_as_of,
        source_version=source_version,
        methodology_version=METHODOLOGY_VERSION,
        coverage=coverage,
        sample_size=sample_size,
        limitations=limitations,
    )


def _team_name(ctx: Ctx, team_id: str) -> str:
    return ctx.names.get(team_id) or ctx.inputs.team_names.get(team_id) or team_id


def _profile_path(ctx: Ctx, team_id: str) -> str | None:
    return R.team_path(_pid(team_id)) if team_id in ctx.profile_teams else None


def _event_path(ctx: Ctx, event_id: str) -> str | None:
    return R.event_path(event_id) if event_id in ctx.events else None


def _build_context(inputs: ResearchInputs, run_id: str) -> Ctx:
    now = inputs.now
    v1_events = {
        e["source_ids"]["fixture_id"]: e
        for e in inputs.events
        if e.get("source_ids", {}).get("fixture_id")
    }
    names: dict[str, str] = {}
    for e in inputs.events:
        for p in e["participants"]:
            tid = (p.get("source_ids") or {}).get("team_id")
            if tid:
                names[tid] = p["display_name"]
    settled_by_fixture: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in inputs.settlements:
        settled_by_fixture[s["fixture_id"]].append(s)
    preds_by_fixture: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in inputs.predictions:
        preds_by_fixture[p["fixture_id"]].append(p)
    events: dict[str, dict[str, Any]] = {}
    event_fixture: dict[str, str] = {}
    for fid, e in v1_events.items():
        events[e["event_id"]] = e
        event_fixture[e["event_id"]] = fid
    games = _games_by_team(inputs.results)
    results_by_fixture: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in inputs.results:
        results_by_fixture[r["fixture_id"]].append(r)
    for fid in sorted(settled_by_fixture):
        if fid in v1_events:
            continue
        comp, season, home, away = _parse_fixture_id(fid)
        if not home or not away:
            continue
        preds = preds_by_fixture.get(fid, [])
        kickoff = next((p["kickoff_utc"] for p in preds if p.get("kickoff_utc")), None)
        res = results_by_fixture.get(fid, [])
        if kickoff is None and res:
            kickoff = _iso(res[-1].get("kickoff_utc")) or _day_ts(res[-1]["match_date"])
        if kickoff is None:
            continue
        espn = None
        if res:
            ko_day = kickoff[:10]
            best = min(
                res,
                key=lambda r: abs(
                    (date.fromisoformat(r["match_date"]) - date.fromisoformat(ko_day)).days
                ),
            )
            espn = str(best["espn_event_id"])
        h = _team_participant(home, names.get(home) or inputs.team_names.get(home, home))
        a = _team_participant(away, names.get(away) or inputs.team_names.get(away, away))
        last = max(s["settled_at"] for s in settled_by_fixture[fid])
        ev = build.event(
            sport=SPORT,
            source="fixture_id",
            source_id=fid,
            start_time_utc=kickoff,
            participants=[h, a],
            home_participant=h["participant_id"],
            away_participant=a["participant_id"],
            league=comp,
            season=season,
            competition=inputs.competition_names.get(comp or "", comp),
            status="FINAL",
            start_time_source="predictions_ledger",
            start_time_confidence="SCHEDULED",
            source_ids={"espn_event_id": espn} if espn else None,
            last_updated_at=last,
            extensions={"settled_only": True},
        )
        events[ev["event_id"]] = ev
        event_fixture[ev["event_id"]] = fid
    # pools: every competition pool a published event belongs to
    pools: dict[str, Pool] = {}
    for ev in events.values():
        key = _pool_of(ev.get("league"))
        if key and key not in pools:
            comps = set(INTL_POOL_COMPETITIONS) if key == INTL_POOL else {key}
            pool_rows = [r for r in inputs.results if r["competition_id"] in comps]
            season = None
            if key != INTL_POOL and pool_rows:
                season = str(pool_rows[-1].get("season_id"))
            windows = (
                [R.window("LAST_N", n=n) for n in LAST_N_WINDOWS]
                if key == INTL_POOL
                else [R.window("SEASON"), R.window("LAST_N", n=LAST_N_WINDOWS[0])]
            )
            primary = windows[-1] if key == INTL_POOL else windows[0]
            pools[key] = Pool(
                key=key,
                label=_pool_label(key, inputs.competition_names),
                competitions=comps,
                windows=windows,
                primary_window=primary,
                season=season,
            )
            for r in pool_rows:
                pools[key].teams.update((r["home_team_id"], r["away_team_id"]))
    profile_teams: set[str] = set()
    for ev in events.values():
        for p in ev["participants"]:
            tid = (p.get("source_ids") or {}).get("team_id")
            if tid:
                profile_teams.add(tid)
    team_pool: dict[str, str] = {}
    for pool in pools.values():
        profile_teams |= pool.teams
    for tid in profile_teams:
        counts: dict[str, int] = defaultdict(int)
        for g in games.get(tid, []):
            k = _pool_of(g.competition_id)
            if k in pools:
                counts[k] += 1
        if counts:
            team_pool[tid] = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    for ev in (
        events.values()
    ):  # a published team with no archived game still belongs to its event's pool
        key = _pool_of(ev.get("league"))
        for p in ev["participants"]:
            tid = (p.get("source_ids") or {}).get("team_id")
            if tid and tid not in team_pool and key in pools:
                team_pool[tid] = key
    return Ctx(
        inputs=inputs,
        run_id=run_id,
        now=now,
        v1_events=v1_events,
        events=events,
        event_fixture=event_fixture,
        settled_by_fixture=dict(settled_by_fixture),
        preds_by_fixture=dict(preds_by_fixture),
        games=games,
        pools=pools,
        team_pool=team_pool,
        profile_teams=profile_teams,
        names=names,
        intl_map=_intl_map(inputs),
        profile_pids={_pid(t) for t in profile_teams},
        intl_by_team=_intl_by_team(inputs),
    )


def _register_metrics(ctx: Ctx) -> None:
    inputs = ctx.inputs
    newest_result = max((r["match_date"] for r in inputs.results), default=None)
    res_as_of = _day_ts(newest_result) if newest_result else None
    res_fresh = (
        fr.classify(fr.age_seconds(res_as_of, ctx.now), RESULTS_FRESH) if res_as_of else "UNKNOWN"
    )
    oldest = min((r["match_date"] for r in inputs.results), default=None)
    n_res = len(inputs.results)
    q_res = _q(
        "PARTIAL",
        "results/espn/<league>.jsonl (ESPN results, espn_result_v1)",
        ctx,
        data_as_of=res_as_of,
        coverage=f"{n_res} deduplicated ESPN results, {oldest} -> {newest_result}",
        sample_size=n_res,
        limitations=LIM_RESULTS,
    )
    windows = sorted({w["label"] for p in ctx.pools.values() for w in p.windows})
    for m in FORM_METRICS:
        ctx.metrics[m.slug] = R.metric(
            sport=SPORT,
            slug=m.slug,
            name=m.name,
            short_name=m.short,
            description=m.description,
            entity_type="TEAM",
            category=m.category,
            stat_type=m.stat_type,
            unit=m.unit,
            source="results/espn (ESPN results archive)",
            quality=q_res,
            freshness=res_fresh,
            higher_is_better=m.higher_is_better,
            comparison_universe="per competition pool: one club league per season, or the pooled national-team archive",
            supports=R.supports(
                rank=True,
                percentile=True,
                time_series=m.slug in ("goals_for_per_game", "goals_against_per_game"),
                windows=True,
                splits=m.splits,
                home_away=m.splits,
            ),
            windows=windows,
            splits=["home_away"] if m.splits else [],
            methodology_version=METHODOLOGY_VERSION,
            historical_start=oldest,
            update_frequency="every 2 h (espn-lineups appends results)",
            known_limitations=LIM_RESULTS,
            extensions={"window_note": "club pools: SEASON + L5; national teams: L10 + L5"},
        )
    if inputs.intl_rows:
        q_elo = _q(
            "PARTIAL",
            "data/international/results_v1.csv.gz (martj42 CC0, point-in-time Elo)",
            ctx,
            data_as_of=_day_ts(inputs.intl_date_max) if inputs.intl_date_max else None,
            coverage=f"{len(inputs.intl_rows)} internationals {inputs.intl_rows[0]['date']} -> {inputs.intl_rows[-1]['date']}",
            sample_size=len(inputs.intl_rows),
            limitations=LIM_ELO,
            production=False,
        )
        elo_fresh = fr.classify(
            fr.age_seconds(_day_ts(inputs.intl_rows[-1]["date"]), ctx.now), RESULTS_FRESH
        )
        ctx.metrics["elo_rating"] = R.metric(
            sport=SPORT,
            slug="elo_rating",
            name="International Elo (pre-match)",
            short_name="Elo",
            description="World-Football-Elo-style rating computed in date order by the repo's dataset builder "
            "(providers/international_results.py compute_point_in_time_elo, start 1500, home +100, "
            "tournament-weighted K). The value is the PRE-match rating of the team's latest archived match.",
            entity_type="TEAM",
            category="rating",
            stat_type="RATING",
            unit="Elo points",
            higher_is_better=True,
            source="data/international/results_v1.csv.gz",
            quality=q_elo,
            freshness=elo_fresh,
            comparison_universe="registry national teams mapped exactly to the international dataset",
            supports=R.supports(rank=True, percentile=True, time_series=True),
            windows=["LATEST"],
            methodology_version=METHODOLOGY_VERSION,
            historical_start=inputs.intl_rows[0]["date"],
            update_frequency="frozen snapshot (MANIFEST.json date_max)",
            known_limitations=LIM_ELO,
        )
    q_dc = _q(
        "RESEARCH",
        "fit_competition + StrengthConfigV2 refit on results/espn (research export)",
        ctx,
        production=False,
        data_as_of=res_as_of,
        limitations=LIM_DC,
        source_version="dc_laplace_v2",
    )
    for slug, name, short, desc in (
        (
            "dc_attack",
            "Attack rating (DC v2 refit)",
            "ATT",
            "Dixon-Coles attack parameter a_i from a dc_laplace_v2 "
            "MAP fit (sum-to-zero within the competition pool, intercept kappa, 730-day lookback, decay 0.0065/day). "
            "Opponent-adjusted by construction. Higher = scores more against an average defence.",
        ),
        (
            "dc_defence",
            "Defence rating (DC v2 refit)",
            "DEF",
            "Dixon-Coles defence parameter d_i from the same "
            "dc_laplace_v2 refit (mu_away = exp(kappa + a_away - d_home)). Opponent-adjusted by construction. "
            "Higher = concedes fewer against an average attack.",
        ),
    ):
        ctx.metrics[slug] = R.metric(
            sport=SPORT,
            slug=slug,
            name=name,
            short_name=short,
            description=desc,
            entity_type="TEAM",
            category="rating",
            stat_type="RATING",
            unit="log goals",
            higher_is_better=True,
            source="research export refit of results/espn",
            quality=q_dc,
            freshness=res_fresh,
            comparison_universe="teams in the competition-pool fit",
            supports=R.supports(rank=True, percentile=True, opponent_adjustment=True),
            windows=["FIT_730D"],
            source_version="dc_laplace_v2",
            methodology_version=METHODOLOGY_VERSION,
            update_frequency="every research export",
            known_limitations=LIM_DC,
            related_metrics=[
                ids.metric_id(SPORT, "goals_for_per_game"),
                ids.metric_id(SPORT, "goals_against_per_game"),
            ],
        )
    proj_as_of = max((p["as_of"] for p in inputs.predictions), default=None)
    q_proj = _q(
        "VERIFIED",
        "predictions/<day>/predictions.jsonl (append-only prediction ledger)",
        ctx,
        data_as_of=proj_as_of,
        coverage=f"{len(inputs.predictions)} ledger rows for the published fixtures",
        sample_size=len(inputs.predictions),
        limitations=LIM_PROJECTIONS,
    )
    ctx.metrics["model_fair_probability"] = R.metric(
        sport=SPORT,
        slug="model_fair_probability",
        name="Model fair P(YES) per run",
        short_name="P(model)",
        description="fair_probability_mean of the prediction ledger row for one Kalshi ticker at each RUN SOCCER run "
        "(DATA_ONLY Dixon-Coles + world simulation). Evidence, never a bet: authority RESEARCH_ONLY.",
        entity_type="MARKET",
        category="projection",
        stat_type="PROBABILITY",
        unit="probability",
        source="predictions ledger",
        quality=q_proj,
        freshness=fr.classify(fr.age_seconds(proj_as_of, ctx.now), MODEL_FRESH)
        if proj_as_of
        else "UNKNOWN",
        supports=R.supports(time_series=True),
        windows=["RUN"],
        methodology_version=METHODOLOGY_VERSION,
        historical_start=min((p["as_of"] for p in inputs.predictions), default=None),
        update_frequency="each run (4x/day + kickoff chain)",
        known_limitations=LIM_PROJECTIONS,
    )


def _form_rankings(ctx: Ctx) -> list[dict[str, Any]]:
    docs = []
    q = ctx.metrics["points_per_game"]["quality"]
    for pool in sorted(ctx.pools.values(), key=lambda p: p.key):
        members = sorted(t for t, k in ctx.team_pool.items() if k == pool.key)
        for window in pool.windows:
            per_team = {}
            for tid in members:
                gs = _window_games(pool, ctx.games.get(tid, []), window)
                if gs:
                    per_team[tid] = (gs, _rates(gs))
            for m in FORM_METRICS:
                mid = ids.metric_id(SPORT, m.slug)
                values = [
                    {
                        "entity_id": _pid(tid),
                        "display_name": _team_name(ctx, tid),
                        "value": rates[m.slug] if _window_ok(pool, len(gs), window) else None,
                        "sample_size": len(gs),
                    }
                    for tid, (gs, rates) in sorted(per_team.items())
                ]
                rk = None
                if sum(1 for v in values if v["value"] is not None) >= 2:
                    rk = R.ranking(
                        sport=SPORT,
                        metric_id=mid,
                        universe_label=pool.label,
                        entity_type="TEAM",
                        window=window,
                        as_of=ctx.metrics[m.slug]["quality"]["data_as_of"] or ctx.now,
                        higher_is_better=m.higher_is_better,
                        values=values,
                        run_id=ctx.run_id,
                        generated_at=ctx.now,
                        quality=q,
                        season=pool.season,
                        universe_filter=_window_filter(pool, window),
                        path_for=lambda e: _path_for_pid(ctx, e),
                    )
                    ctx.rankings[(m.slug, pool.key, window["label"])] = rk
                    docs.append(rk)
                for tid, (gs, rates) in sorted(per_team.items()):
                    pid = _pid(tid)
                    o = R.observation(
                        sport=SPORT,
                        metric_id=mid,
                        entity_id=pid,
                        entity_type="TEAM",
                        value=rates[m.slug],
                        window=window,
                        as_of=gs[-1].t,
                        source="results/espn",
                        quality_status="PARTIAL",
                        unit=m.unit,
                        display_value=rates["_record"] if m.slug == "points_per_game" else None,
                        sample_size=len(gs),
                        season=pool.season if window["kind"] == "SEASON" else None,
                        context=R.context_from_ranking(rk, pid) if rk else None,
                        extensions={
                            "pool": pool.label,
                            "first_game": gs[0].match_date,
                            "last_game": gs[-1].match_date,
                        },
                    )
                    ctx.obs[tid].append(o)
                    if window["label"] == pool.primary_window["label"]:
                        ctx.primary_obs[(tid, m.slug)] = o
            # home/away splits over the primary window (no ranking: sample sizes are small; context null)
            if window["label"] == pool.primary_window["label"]:
                for tid in members:
                    gs_all = _window_games(pool, ctx.games.get(tid, []), window)
                    for side in ("HOME", "AWAY"):
                        gs = [g for g in gs_all if g.home_away == side]
                        if not gs:
                            continue
                        rates = _rates(gs)
                        for slug in SPLIT_SLUGS:
                            ctx.split_obs[tid].append(
                                R.observation(
                                    sport=SPORT,
                                    metric_id=ids.metric_id(SPORT, slug),
                                    entity_id=_pid(tid),
                                    entity_type="TEAM",
                                    value=rates[slug],
                                    window=window,
                                    as_of=gs[-1].t,
                                    source="results/espn",
                                    quality_status="PARTIAL",
                                    split=R.split("home_away", side),
                                    sample_size=len(gs),
                                    season=pool.season if window["kind"] == "SEASON" else None,
                                    display_value=rates["_record"]
                                    if slug == "points_per_game"
                                    else None,
                                )
                            )
    return docs


def _path_for_pid(ctx: Ctx, pid: str) -> str | None:
    return R.team_path(pid) if pid in ctx.profile_pids else None


def _dc_rankings(ctx: Ctx) -> list[dict[str, Any]]:
    docs = []
    as_of = ctx.now.date()
    for pool in sorted(ctx.pools.values(), key=lambda p: p.key):
        rows = [r for r in ctx.inputs.results if r["competition_id"] in pool.competitions]
        results = [
            MatchResult(**{k: v for k, v in r.items() if k in MatchResult.model_fields})
            for r in rows
        ]
        if len(results) < 50:  # the production rule: competitions with < 50 results are not fitted
            continue
        model = fit_competition(pool.key, results, as_of=as_of, config=StrengthConfigV2())
        post = model.posterior
        mean, cov = post.mean, post.cov
        fit = {
            "fitted_through": str(post.fitted_through),
            "n_matches": int(post.n_matches),
            "home_advantage": round(float(mean[post.idx_home]), 4),
            "rho": round(float(mean[post.idx_rho]), 4),
            "intercept": round(float(mean[post.idx_intercept]), 4),
            "parameter_hash": post.param_hash(),
            "version": post.version,
            "lookback_days": 730,
            "results_used": model.results_used,
        }
        ctx.dc_fits[pool.key] = fit
        window = R.window("CUSTOM", label="FIT_730D", end=_day_ts(fit["fitted_through"]))
        for slug, idx in (("dc_attack", post.idx_attack), ("dc_defence", post.idx_defence)):
            mid = ids.metric_id(SPORT, slug)
            per = {}
            for tid in post.teams:
                i = idx(tid)
                eff = float(post.effective_matches.get(tid, 0.0))
                per[tid] = (
                    round(float(mean[i]), 4),
                    round(float(math.sqrt(max(cov[i, i], 0.0))), 4),
                    eff,
                )
            values = [
                {
                    "entity_id": _pid(t),
                    "display_name": _team_name(ctx, t),
                    "value": v if eff >= DEFAULT_NEW_TEAM_EFFECTIVE else None,
                    "sample_size": round(eff),
                }
                for t, (v, _sd, eff) in sorted(per.items())
            ]
            rk = R.ranking(
                sport=SPORT,
                metric_id=mid,
                universe_label=pool.label,
                entity_type="TEAM",
                window=window,
                as_of=_day_ts(fit["fitted_through"]),
                higher_is_better=True,
                values=values,
                run_id=ctx.run_id,
                generated_at=ctx.now,
                quality=ctx.metrics[slug]["quality"],
                universe_filter=f"teams in the {pool.key} fit with >= {DEFAULT_NEW_TEAM_EFFECTIVE:g} effective "
                "(decayed) matches (below that the new-team prior dominates)",
                path_for=lambda e: _path_for_pid(ctx, e),
            )
            ctx.rankings[(slug, pool.key, "FIT_730D")] = rk
            docs.append(rk)
            for tid, (v, sd, eff) in sorted(per.items()):
                if tid not in ctx.profile_teams or ctx.team_pool.get(tid) != pool.key:
                    continue
                o = R.observation(
                    sport=SPORT,
                    metric_id=mid,
                    entity_id=_pid(tid),
                    entity_type="TEAM",
                    value=v,
                    window=window,
                    as_of=_day_ts(fit["fitted_through"]),
                    source="research export dc_laplace_v2 refit",
                    quality_status="RESEARCH",
                    unit="log goals",
                    sample_size=round(eff),
                    context=R.context_from_ranking(rk, _pid(tid)),
                    extensions={
                        "sd": sd,
                        "effective_matches": round(eff, 2),
                        "home_advantage": fit["home_advantage"],
                        "intercept": fit["intercept"],
                        "parameter_hash": fit["parameter_hash"],
                        "not_production_posterior": True,
                    },
                )
                ctx.obs[tid].append(o)
                ctx.primary_obs[(tid, slug)] = o
    return docs


def _elo(ctx: Ctx) -> list[dict[str, Any]]:
    if "elo_rating" not in ctx.metrics:
        return []
    mid = ids.metric_id(SPORT, "elo_rating")
    q = ctx.metrics["elo_rating"]["quality"]
    window = R.window("CUSTOM", label="LATEST")
    values = []
    for nat, iid in sorted(ctx.intl_map.items()):
        hist = _elo_history(ctx.intl_by_team, iid)
        if not hist or hist[-1]["elo"] is None:
            continue
        ctx.elo_latest[nat] = {
            "elo": round(hist[-1]["elo"], 2),
            "date": hist[-1]["date"],
            "intl_id": iid,
            "matches": len(hist),
            "history": hist,
        }
        values.append(
            {
                "entity_id": _pid(nat),
                "display_name": _team_name(ctx, nat),
                "value": round(hist[-1]["elo"], 2),
                "sample_size": len(hist),
            }
        )
    if len(values) < 2:
        return []
    as_of = _day_ts(ctx.inputs.intl_rows[-1]["date"])
    rk = R.ranking(
        sport=SPORT,
        metric_id=mid,
        universe_label="national teams (registry, exact intl map)",
        entity_type="TEAM",
        window=window,
        as_of=as_of,
        higher_is_better=True,
        values=values,
        run_id=ctx.run_id,
        generated_at=ctx.now,
        quality=q,
        universe_filter="registry men's national teams whose name or alias maps to exactly one "
        "intl: id (and no other registry team claims it)",
        path_for=lambda e: _path_for_pid(ctx, e),
    )
    ctx.rankings[("elo_rating", "nat", "LATEST")] = rk
    for nat, info in sorted(ctx.elo_latest.items()):
        if nat not in ctx.profile_teams:
            continue
        o = R.observation(
            sport=SPORT,
            metric_id=mid,
            entity_id=_pid(nat),
            entity_type="TEAM",
            value=info["elo"],
            window=window,
            as_of=_day_ts(info["date"]),
            source="data/international/results_v1.csv.gz",
            quality_status="PARTIAL",
            unit="Elo points",
            sample_size=info["matches"],
            context=R.context_from_ranking(rk, _pid(nat)),
            extensions={
                "intl_id": info["intl_id"],
                "rating_kind": "pre-match",
                "match_date": info["date"],
            },
        )
        ctx.obs[nat].append(o)
        ctx.primary_obs[(nat, "elo_rating")] = o
    return [rk]


def _series_for_team(ctx: Ctx, tid: str) -> list[dict[str, Any]]:
    docs = []
    pid = _pid(tid)
    team_link = R.link(
        rel="TEAM",
        target_kind="entity_profile",
        label=_team_name(ctx, tid),
        target_id=pid,
        path=R.team_path(pid),
    )
    games = ctx.games.get(tid, [])[-GAME_SERIES_CAP:]
    if games:
        q = _q(
            "PARTIAL",
            "results/espn",
            ctx,
            data_as_of=games[-1].t,
            sample_size=len(games),
            coverage=f"last {len(games)} archived ESPN games ({games[0].match_date} -> {games[-1].match_date})",
            limitations=[*LIM_RESULTS, f"capped at the last {GAME_SERIES_CAP} games"],
        )
        for slug, key in (("goals_for_per_game", "gf"), ("goals_against_per_game", "ga")):
            pts = [
                R.point(
                    x=f"{g.match_date} {'vs' if g.home_away != 'AWAY' else '@'} {g.opponent_id}",
                    t=g.t,
                    value=getattr(g, key),
                    quality_status="PARTIAL",
                    event_id=g.event_id,
                    opponent_id=_pid(g.opponent_id),
                    sample_size=1,
                    source=f"results/espn ({g.competition_id})",
                    path=_event_path(ctx, g.event_id),
                )
                for g in games
            ]
            docs.append(
                R.time_series(
                    sport=SPORT,
                    metric_id=ids.metric_id(SPORT, slug),
                    entity_id=pid,
                    entity_type="TEAM",
                    x_axis="GAME",
                    points=R.rolling(pts, 5),
                    as_of=games[-1].t,
                    run_id=ctx.run_id,
                    generated_at=ctx.now,
                    quality=q,
                    unit="goals",
                    rolling_window=5,
                    links=[team_link],
                )
            )
    info = ctx.elo_latest.get(tid)
    if info:
        hist = info["history"][-ELO_SERIES_CAP:]
        inv = {v: k for k, v in ctx.intl_map.items()}
        q = _q(
            "PARTIAL",
            "data/international/results_v1.csv.gz",
            ctx,
            production=False,
            data_as_of=_day_ts(hist[-1]["date"]),
            sample_size=len(hist),
            coverage=f"last {len(hist)} of {info['matches']} internationals ({hist[0]['date']} -> {hist[-1]['date']})",
            limitations=[*LIM_ELO, f"capped at the last {ELO_SERIES_CAP} matches"],
        )
        pts = [
            R.point(
                x=f"{h['date']} {'vs' if h['home'] else '@'} {h['opponent_name']} ({h['gf']}-{h['ga']}, {h['tournament']})",
                t=_day_ts(h["date"]),
                value=_r(h["elo"], 2),
                quality_status="PARTIAL",
                opponent_id=_pid(inv[h["opponent_intl"]]) if h["opponent_intl"] in inv else None,
                source="data/international/results_v1.csv.gz",
            )
            for h in hist
        ]
        docs.append(
            R.time_series(
                sport=SPORT,
                metric_id=ids.metric_id(SPORT, "elo_rating"),
                entity_id=pid,
                entity_type="TEAM",
                x_axis="GAME",
                points=R.rolling(pts, 5),
                as_of=_day_ts(hist[-1]["date"]),
                run_id=ctx.run_id,
                generated_at=ctx.now,
                quality=q,
                unit="Elo points",
                rolling_window=5,
                links=[team_link],
            )
        )
    ctx.team_series[tid] = docs
    return docs


# ----------------------------------------------------------------------------- events
def _participants(ev: dict[str, Any]) -> tuple[str | None, str | None]:
    by = {
        p["participant_id"]: (p.get("source_ids") or {}).get("team_id") for p in ev["participants"]
    }
    return by.get(ev.get("home_participant")), by.get(ev.get("away_participant"))


def _model_family_of(mp: dict[str, Any]) -> str | None:
    return (mp.get("extensions") or {}).get("model_family")


def _calibration_cells(
    ctx: Ctx, families: set[str], market_families: set[str]
) -> list[dict[str, Any]]:
    out = []
    for c in ctx.inputs.model_health:
        if (
            c.get("model_family") in families
            and c.get("market_family") in market_families
            and c.get("horizon") == "any"
        ):
            out.append(
                {
                    "model_family": c["model_family"],
                    "market_family": c["market_family"],
                    "horizon": "any",
                    "n_settled": c.get("n_settled"),
                    "log_loss": c.get("log_loss"),
                    "market_log_loss": c.get("market_log_loss"),
                    "brier": c.get("brier"),
                    "ece": c.get("ece"),
                    "interval_coverage_80": c.get("interval_coverage_80"),
                    "clv_points_mean": c.get("clv_points_mean"),
                    "authority": c.get("authority"),
                    "validated": not str(c["model_family"]).endswith(".intl_pool"),
                    "last_evaluated_at": _iso(c.get("last_evaluated_at")),
                }
            )
    out.sort(key=lambda c: (c["model_family"], c["market_family"]))
    return out


def _projection_history(
    ctx: Ctx, preds: list[dict[str, Any]], max_bytes: int = PROJECTION_HISTORY_MAX_BYTES
) -> tuple[dict[str, Any], dict[str, Any]]:
    by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in preds:
        if p.get("ticker"):
            by_ticker[p["ticker"]].append(p)
    table = {}
    for tk in sorted(by_ticker):
        rows = sorted(by_ticker[tk], key=lambda p: (p["as_of"], p["record_id"] or ""))
        fams = sorted({p["model_family"] for p in rows if p.get("model_family")})
        table[tk] = {
            "family": rows[-1]["family"],
            "description": rows[-1]["description"],
            "model_family": "|".join(fams),
            "rows": [
                [
                    p["as_of"],
                    _r(p["mean"]),
                    _r(p["low"]),
                    _r(p["high"]),
                    _r(p["yes_ask"]),
                    p["run_id"],
                ]
                for p in rows
            ],
        }
    meta = {
        "columns": [
            "as_of",
            "fair_mean",
            "fair_low_80",
            "fair_high_80",
            "kalshi_yes_ask_at_run",
            "ledger_run_id",
        ],
        "source": "predictions/<day>/predictions.jsonl",
        "authority": "RESEARCH_ONLY",
        "capped_rows_per_ticker": None,
    }
    size = len(json.dumps(table, separators=(",", ":")))
    if size > max_bytes:
        k = max(len(v["rows"]) for v in table.values())
        while k > 1 and len(json.dumps(table, separators=(",", ":"))) > max_bytes:
            k -= 1
            for v in table.values():
                v["rows"] = v["rows"][-k:]
        meta["capped_rows_per_ticker"] = k
    return table, meta


def _market_history(
    ctx: Ctx, ev: dict[str, Any], tickers: list[str]
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    start = timeutil.parse_ts(ev["start_time_utc"])
    raw: dict[str, list[dict[str, Any]]] = {}
    capped_tickers = 0
    for tk in sorted(set(tickers)):
        pts = ctx.inputs.snapshots.get(tk) or []
        if len(pts) > MARKET_HISTORY_TICKER_CAP:
            capped_tickers += 1
            pts = pts[-MARKET_HISTORY_TICKER_CAP:]
        if pts:
            # the contract's price_point, built once per capture (validated once, in market_history)
            raw[tk] = [
                R.price_point(
                    captured_at=p["captured_at"],
                    yes_bid=p["yes_bid"],
                    yes_ask=p["yes_ask"],
                    last_price=p["last_price"],
                    volume=p["volume"],
                    open_interest=p["open_interest"],
                    source=p["source"],
                )
                for p in pts
            ]
    summary: dict[str, Any] = {"tickers": len(set(tickers)), "tickers_with_captures": len(raw)}
    if not raw:
        return None, summary

    def thin(pts: list[dict[str, Any]], k: int | None) -> list[dict[str, Any]]:
        return pts if k is None or len(pts) <= k else [pts[0], *pts[-(k - 1) :]]

    def series_for(k: int | None) -> list[dict[str, Any]]:
        return [
            {"market_id": ids.market_id(tk), "kalshi_ticker": tk, "points": thin(pts, k)}
            for tk, pts in raw.items()
        ]

    def size(k: int | None) -> int:
        return (
            len(
                json.dumps(series_for(k), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            )
            + 4_000
        )

    cap = None
    if size(None) > MARKET_HISTORY_MAX_BYTES:
        lo, hi = 2, max(len(p) for p in raw.values())
        while lo < hi:  # the largest k that fits
            mid = (lo + hi + 1) // 2
            if size(mid) <= MARKET_HISTORY_MAX_BYTES:
                lo = mid
            else:
                hi = mid - 1
        cap = lo
    series = series_for(cap)
    last = max(p["captured_at"] for pts in raw.values() for p in pts)
    first = min(p["captured_at"] for pts in raw.values() for p in pts)
    lims = list(LIM_MARKET_HISTORY)
    if capped_tickers:
        lims.append(f"capped at the latest {MARKET_HISTORY_TICKER_CAP} captures per ticker")
    if cap:
        lims.append(
            f"capped at the opening capture + the latest {cap - 1} captures per ticker to stay under the per-event size budget"
        )
    n_pub = sum(len(s["points"]) for s in series)
    q = _q(
        "VERIFIED",
        "snapshots/<day>/cap-*.jsonl (Kalshi quote captures)",
        ctx,
        data_as_of=last,
        sample_size=n_pub,
        limitations=lims,
        coverage=f"{len(series)} tickers, {n_pub} captures",
    )
    doc = R.market_history(
        sport=SPORT,
        run_id=ctx.run_id,
        generated_at=ctx.now,
        event_id=ev["event_id"],
        as_of=last,
        series=series,
        quality=q,
        links=[
            R.link(
                rel="EVENT_RESEARCH",
                target_kind="event_research",
                label="event research",
                target_id=ev["event_id"],
                path=R.event_path(ev["event_id"]),
            )
        ],
    )
    t_first, t_last = timeutil.parse_ts(first), timeutil.parse_ts(last)
    summary.update(
        {
            "points_published": n_pub,
            "points_stored": sum(len(ctx.inputs.snapshots.get(tk) or []) for tk in raw),
            "first_capture": first,
            "last_capture": last,
            "minutes_before_kickoff_first": round((start - t_first).total_seconds() / 60, 1),
            "minutes_before_kickoff_last": round((start - t_last).total_seconds() / 60, 1),
            "capped_points_per_ticker": cap,
            "time_to_kickoff_rule": "event start_time_utc - captured_at (the stored horizon fields are not used)",
            "change_suppressed": True,
        }
    )
    return doc, summary


def _lineup_context(
    ctx: Ctx, espn_id: str | None, home: str | None, away: str | None
) -> list[dict[str, Any]]:
    if not espn_id:
        return []
    rows = [r for r in ctx.inputs.lineups if str(r.get("espn_event_id")) == espn_id]
    if not rows:
        return []
    with_players = [r for r in rows if r.get("home") or r.get("away")]
    row = (with_players or rows)[-1]
    sides = {}
    for side, tid in (("home", home), ("away", away)):
        espn_team = row.get(f"{side}_espn_id")
        mapped = ctx.inputs.espn_team_map.get(str(espn_team)) if espn_team else None
        players = []
        for p in row.get(side) or []:
            aid = str(p.get("athlete_id") or "")
            c = ctx.inputs.appearances.get(aid, {})
            players.append(
                {
                    "athlete_id": aid,
                    "name": p.get("name"),
                    "position": p.get("position"),
                    "jersey": p.get("jersey"),
                    "starter": bool(p.get("starter")),
                    "subbed_in": bool(p.get("subbed_in")),
                    "subbed_out": bool(p.get("subbed_out")),
                    "stored_sheets": c.get("sheets", 0),
                    "stored_starts": c.get("starts", 0),
                    "stored_sub_appearances": c.get("sub_appearances", 0),
                }
            )
        sides[side] = {
            "team_id": mapped or tid,
            "participant_id": _pid(mapped or tid) if (mapped or tid) else None,
            "espn_team_id": espn_team,
            "formation": row.get(f"{side}_formation"),
            "players": players,
        }
    return [
        {
            "espn_event_id": espn_id,
            "captured_at": row["_at"],
            "lineup_state": row.get("lineup_state"),
            "event_state": row.get("event_state"),
            "kickoff_utc": _iso(row.get("kickoff_utc")),
            "sheets_stored_for_event": len(rows),
            "source": row.get("_source"),
            "home": sides["home"],
            "away": sides["away"],
            "note": "ESPN lineup sheet: ids, names, positions, starter/sub flags only (no minutes, no stats). "
            "stored_* counts are appearances across every stored sheet (lineups/history + daily), not season totals.",
        }
    ]


def _weather_context(
    ctx: Ctx, espn_id: str | None
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    row = ctx.inputs.weather.get(espn_id or "")
    if not row:
        return None, None
    w = {
        k: row.get(k)
        for k in (
            "forecast_time_utc",
            "temperature_2m",
            "precipitation",
            "precipitation_probability",
            "wind_speed_10m",
            "wind_gusts_10m",
            "relative_humidity_2m",
            "weather_code",
            "provider",
        )
    }
    w.update(
        {
            "captured_at": row["_at"],
            "kickoff_utc": _iso(row.get("kickoff_utc")),
            "revisions_stored": row["_revisions"],
            "source": row["_source"],
            "units": {"temperature_2m": "C", "precipitation": "mm", "wind_speed_10m": "km/h"},
        }
    )
    v = {
        "name": row.get("venue"),
        "city": row.get("venue_city"),
        "country": row.get("venue_country"),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "source": row["_source"],
    }
    return w, v


def _rest_context(preds: list[dict[str, Any]]) -> dict[str, Any] | None:
    rows = [p for p in preds if p.get("context")]
    if not rows:
        return None
    p = max(rows, key=lambda r: (r["as_of"], r["record_id"] or ""))
    c = p["context"]
    return {
        "home": {
            "rest_days": c.get("rest_days_home"),
            "matches_14d": c.get("matches_14d_home"),
            "matches_28d": c.get("matches_28d_home"),
        },
        "away": {
            "rest_days": c.get("rest_days_away"),
            "matches_14d": c.get("matches_14d_away"),
            "matches_28d": c.get("matches_28d_away"),
        },
        "rest_gap_days": c.get("rest_gap_days"),
        "as_of": p["as_of"],
        "ledger_run_id": p["run_id"],
        "source": "prediction ledger context (run/context_features.py)",
        "quality_status": "PARTIAL",
    }


def _head_to_head(ctx: Ctx, home: str | None, away: str | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not home or not away:
        return out
    meetings = [g for g in ctx.games.get(home, []) if g.opponent_id == away]
    if meetings:
        out["espn"] = {
            "source": "results/espn",
            "n": len(meetings),
            "home_team_w": sum(1 for g in meetings if g.gf > g.ga),
            "draws": sum(1 for g in meetings if g.gf == g.ga),
            "away_team_w": sum(1 for g in meetings if g.gf < g.ga),
            "home_team_goals": sum(g.gf for g in meetings),
            "away_team_goals": sum(g.ga for g in meetings),
            "recent": [
                {
                    "date": g.match_date,
                    "competition": g.competition_id,
                    "venue_side": g.home_away,
                    "score": f"{g.gf}-{g.ga}",
                    "event_id": g.event_id,
                }
                for g in meetings[-5:]
            ],
        }
    ih, ia = ctx.intl_map.get(home), ctx.intl_map.get(away)
    if ih and ia:
        rows = [r for r in ctx.intl_by_team.get(ih, []) if {r["home_id"], r["away_id"]} == {ih, ia}]
        if rows:

            def gf_ga(r: dict[str, Any]) -> tuple[int, int]:
                hg, ag = int(r["home_goals"]), int(r["away_goals"])
                return (hg, ag) if r["home_id"] == ih else (ag, hg)

            scores = [gf_ga(r) for r in rows]
            out["international_results"] = {
                "source": "data/international/results_v1.csv.gz",
                "n": len(rows),
                "since": rows[0]["date"],
                "home_team_w": sum(1 for a, b in scores if a > b),
                "draws": sum(1 for a, b in scores if a == b),
                "away_team_w": sum(1 for a, b in scores if a < b),
                "home_team_goals": sum(a for a, _ in scores),
                "away_team_goals": sum(b for _, b in scores),
                "recent": [
                    {
                        "date": r["date"],
                        "tournament": r["tournament"],
                        "score": "{}-{}".format(*gf_ga(r)),
                        "neutral": r.get("neutral") == "1",
                    }
                    for r in rows[-5:]
                ],
            }
    return out


def _settlement_block(ctx: Ctx, fid: str, preds: list[dict[str, Any]]) -> dict[str, Any] | None:
    rows = ctx.settled_by_fixture.get(fid)
    if not rows:
        return None
    desc = {p["record_id"]: p.get("description") for p in preds}
    by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in rows:
        by_ticker[s["ticker"]].append(s)
    tickers = []
    for tk in sorted(by_ticker):
        rs = sorted(
            by_ticker[tk],
            key=lambda s: (HORIZON_MINUTES.get(s["horizon"], 9999) * -1, s["record_id"] or ""),
        )
        s = rs[-1]  # the record closest to kickoff
        tickers.append(
            {
                "ticker": tk,
                "market_id": ids.market_id(tk),
                "family": s["family"],
                "description": desc.get(s["prediction_record_id"]),
                "outcome": s["outcome"],
                "horizon": s["horizon"],
                "fair_mean": _r(s["fair_mean"]),
                "fair_low": _r(s["fair_low"]),
                "fair_high": _r(s["fair_high"]),
                "entry_yes_ask": _r(s["entry_yes_ask"]),
                "entry_yes_mid": _r(s["entry_yes_mid"]),
                "close_yes_mid": _r(s["close_yes_mid"]),
                "close_class": s["close_class"],
                "clv_yes_points": _r(s["clv_yes_points"]),
                "clv_model_signed_points": _r(s["clv_model_signed_points"]),
                "clv_fee_aware_yes": _r(s["clv_fee_aware_yes"]),
                "clv_fee_aware_no": _r(s["clv_fee_aware_no"]),
                "model_family": s["model_family"],
                "records": len(rs),
            }
        )

    def scores(key: str) -> tuple[float | None, float | None, int]:
        pairs = [
            (t[key], 1.0 if t["outcome"] == "yes" else 0.0)
            for t in tickers
            if t[key] is not None and t["outcome"] in ("yes", "no")
        ]
        if not pairs:
            return None, None, 0
        brier = statistics.fmean((p - y) ** 2 for p, y in pairs)
        ll = statistics.fmean(-math.log(min(max(p if y else 1 - p, 1e-6), 1.0)) for p, y in pairs)
        return round(brier, 5), round(ll, 5), len(pairs)

    ev0 = rows[0]["evidence"]
    clvs = [t["clv_yes_points"] for t in tickers if t["clv_yes_points"] is not None]
    summary = {
        "tickers": len(tickers),
        "records": len(rows),
        "settled_at_latest": max(s["settled_at"] for s in rows),
        "result": {
            "home": ev0.get("home"),
            "away": ev0.get("away"),
            "period": ev0.get("period"),
            "status": ev0.get("status"),
            "source": ev0.get("source"),
        },
        "clv_yes_points_mean": round(statistics.fmean(clvs), 5) if clvs else None,
        "clv_n": len(clvs),
    }
    for key, label in (
        ("fair_mean", "model"),
        ("entry_yes_mid", "entry_mid"),
        ("close_yes_mid", "close_mid"),
    ):
        b, ll, n = scores(key)
        summary[f"brier_{label}"], summary[f"log_loss_{label}"], summary[f"n_{label}"] = b, ll, n
    return {
        "summary": summary,
        "tickers": tickers,
        "method": "one row per ticker: the settled record closest to kickoff; Brier / log loss are arithmetic over "
        "those rows (log loss clipped at 1e-6); CLV fields are the settlement ledger's own",
        "source": "settlements/<day>/predictions.jsonl (settlement_record_v1)",
        "quality_status": "VERIFIED",
    }


def _event_docs(ctx: Ctx) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    stats: dict[str, Any] = {
        "lineup_events": [],
        "weather_events": [],
        "distribution_events": [],
        "settled_events": [],
        "mh_events": [],
        "projection_series": [],
        "capped_mh": 0,
        "mh_points": 0,
        "mh_tickers": 0,
        "calibration_events": [],
        "rest_events": [],
        "projection_events": [],
    }
    inputs = ctx.inputs
    rec_auth = {
        r["market_id"]: (bool(r["research_only"]), r["authority"]) for r in inputs.recommendations
    }
    board_fx = (inputs.board or {}).get("fixtures", {}) if isinstance(inputs.board, dict) else {}
    slate = inputs.slate or {}
    slate_fx_by = {f.get("fixture_id"): f for f in slate.get("fixtures") or []}
    slate_rows_by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in slate.get("contracts") or []:
        slate_rows_by[c.get("fixture_id")].append(c)
    slate_meta = {"slate_id": slate.get("slate_id"), "kalshi": slate.get("kalshi") or {}}
    for eid in sorted(ctx.events):
        ev = ctx.events[eid]
        fid = ctx.event_fixture[eid]
        is_v1 = fid in ctx.v1_events
        home, away = _participants(ev)
        preds = ctx.preds_by_fixture.get(fid, [])
        mkts = sorted(
            (m for m in inputs.markets if m.get("event_id") == eid),
            key=lambda m: m["kalshi_ticker"],
        )
        mps = sorted(
            (mp for mp in inputs.model_prices if mp.get("event_id") == eid),
            key=lambda mp: mp["market_id"],
        )
        notes: list[str] = []
        links = []
        participants = []
        for tid, side in ((home, "HOME"), (away, "AWAY")):
            if not tid:
                continue
            pid = _pid(tid)
            participants.append(
                {
                    "participant_id": pid,
                    "display_name": _team_name(ctx, tid),
                    "home_away": side,
                    "path": R.team_path(pid),
                }
            )
            links.append(
                R.link(
                    rel="TEAM",
                    target_kind="entity_profile",
                    label=_team_name(ctx, tid),
                    target_id=pid,
                    path=R.team_path(pid),
                )
            )
        # matchup rows: the same metric for both sides (each side's own primary window)
        matchup = []
        for slug in [m.slug for m in FORM_METRICS] + ["elo_rating", "dc_attack", "dc_defence"]:
            if slug not in ctx.metrics:
                continue
            ho, ao = ctx.primary_obs.get((home, slug)), ctx.primary_obs.get((away, slug))
            if ho is None and ao is None:
                continue
            note = None
            if slug in ("dc_attack", "dc_defence"):
                note = "RESEARCH refit (dc_laplace_v2), not the production posterior"
            elif slug == "elo_rating":
                note = "pre-match Elo of each team's latest archived international (dataset frozen at its date_max)"
            elif ho and ao and ho["window"]["label"] != ao["window"]["label"]:
                note = "sides use different windows"
            matchup.append(
                {
                    "metric_id": ids.metric_id(SPORT, slug),
                    "name": ctx.metrics[slug]["name"],
                    "home": ho,
                    "away": ao,
                    "note": note,
                }
            )
        # projections (v1 model prices) + distributions (board quantiles)
        families = {f for f in (_model_family_of(mp) for mp in mps) if f} | {
            p["model_family"] for p in preds if p.get("model_family")
        }
        intl = any(f.endswith(".intl_pool") for f in families)
        projections = []
        for mp in mps:
            ro, auth = rec_auth.get(mp["market_id"], (True, "RESEARCH_ONLY"))
            fam = _model_family_of(mp) or ""
            projections.append(
                R.projection_ref(
                    mp,
                    research_only=ro,
                    authority=auth,
                    quality_status="RESEARCH" if fam.endswith(".intl_pool") else "VERIFIED",
                    metric_id=ids.metric_id(SPORT, "model_fair_probability"),
                )
            )
        distributions = []
        bf = board_fx.get(fid) if is_v1 else None
        if bf:
            v1_tickers = {m["kalshi_ticker"]: m for m in mkts}
            fam = (bf.get("inputs") or {}).get("model_family") or ""
            for tk in sorted(bf.get("contracts", {})):
                c = bf["contracts"][tk]
                q = c.get("q") or []
                if tk not in v1_tickers or len(q) != 100:
                    continue
                distributions.append(
                    {
                        "market_id": ids.market_id(tk),
                        "metric_id": ids.metric_id(SPORT, "model_fair_probability"),
                        "entity_id": None,
                        "label": f"P(YES) parameter-uncertainty quantiles: {c.get('description') or tk}",
                        "quantiles": {
                            f"p{(i + 0.5):g}": round(float(q[i]), 5) for i in QUANTILE_INDEXES
                        },
                        "mean": _r(c.get("p"), 6),
                        "stdev": _r(c.get("param_sd"), 6),
                        "samples": c.get("n_worlds"),
                        "run_id": None,
                        "generated_at": _iso(bf.get("model_generated_at")) or ctx.now,
                        "source": f"{BOARD_FILE} (source_run_id {bf.get('source_run_id')})",
                        "quality_status": "RESEARCH" if fam.endswith(".intl_pool") else "PARTIAL",
                    }
                )
            if distributions:
                stats["distribution_events"].append(eid)
            s = bf.get("summary") or {}
            if s:
                notes.append(
                    "Model board (RESEARCH_ONLY): mean goals home {} / away {}; P(home/draw/away) {}/{}/{}; "
                    "P(btts) {}; P(over 2.5) {}.".format(
                        *(
                            s.get(k)
                            for k in (
                                "mean_home_goals",
                                "mean_away_goals",
                                "p_home",
                                "p_draw",
                                "p_away",
                                "p_btts",
                                "p_over_2_5",
                            )
                        )
                    )
                )
        # context
        espn_id = (ev.get("source_ids") or {}).get("espn_event_id")
        lineups = _lineup_context(ctx, espn_id, home, away)
        if any(lu["home"]["players"] or lu["away"]["players"] for lu in lineups):
            stats["lineup_events"].append(eid)
        weather, venue = _weather_context(ctx, espn_id)
        if weather:
            stats["weather_events"].append(eid)
        if venue is None and ev.get("venue"):
            venue = {"name": ev["venue"], "source": "v1 event"}
        rest = _rest_context(preds)
        if rest:
            stats["rest_events"].append(eid)
            notes.append(
                "Rest/congestion (ledger context, PARTIAL; research found ≈ no signal): home rest {} d, {} matches "
                "in 14 d; away rest {} d, {} matches in 14 d.".format(
                    rest["home"]["rest_days"],
                    rest["home"]["matches_14d"],
                    rest["away"]["rest_days"],
                    rest["away"]["matches_14d"],
                )
            )
        h2h = _head_to_head(ctx, home, away)
        for key, label in (
            ("espn", "ESPN archive"),
            ("international_results", "international results since {since}"),
        ):
            if key in h2h:
                h = h2h[key]
                notes.append(
                    f"Head-to-head ({label.format(**h)}): {h['n']} meetings, home side {h['home_team_w']}W "
                    f"{h['draws']}D {h['away_team_w']}L, goals {h['home_team_goals']}-{h['away_team_goals']}."
                )
        cells = _calibration_cells(
            ctx,
            families,
            {m["market_family"] for m in mkts} | {p["family"] for p in preds if p.get("family")},
        )
        if cells:
            stats["calibration_events"].append(eid)
            mr = next((c for c in cells if c["market_family"] == "match_result_3way"), cells[0])
            notes.append(
                f"Model calibration to date ({mr['model_family']}, {mr['market_family']}, all horizons): n {mr['n_settled']}, "
                f"log loss {mr['log_loss']} vs market {mr['market_log_loss']}, ECE {mr['ece']}, mean CLV {mr['clv_points_mean']}; "
                f"authority {mr['authority']}."
            )
        if intl:
            notes.append(
                "International pool model: NOT VALIDATED (docs/KNOWN_LIMITATIONS.md #26); projections are RESEARCH."
            )
        notes.append("Every model number here is RESEARCH_ONLY evidence, not a bet.")
        settlement = _settlement_block(ctx, fid, preds)
        if settlement:
            stats["settled_events"].append(eid)
            sm = settlement["summary"]
            notes.append(
                f"Settled: {sm['result']['home']}-{sm['result']['away']} ({sm['result']['period']}); {sm['tickers']} tickers; "
                f"model Brier {sm['brier_model']} vs close-mid Brier {sm['brier_close_mid']}; mean CLV (yes, points) "
                f"{sm['clv_yes_points_mean']}."
            )
        # market history + projection history
        tickers = (
            [m["kalshi_ticker"] for m in mkts]
            if is_v1
            else sorted({s["ticker"] for s in ctx.settled_by_fixture.get(fid, [])})
        )
        mh, mh_summary = _market_history(ctx, ev, tickers)
        if mh is not None:
            docs.append(mh)
            stats["mh_events"].append(eid)
            stats["mh_points"] += mh_summary["points_published"]
            stats["mh_tickers"] += mh_summary["tickers_with_captures"]
            stats["capped_mh"] += 1 if mh_summary.get("capped_points_per_ticker") else 0
            links.append(
                R.link(
                    rel="MARKET_HISTORY",
                    target_kind="market_history",
                    label="Kalshi price history",
                    target_id=eid,
                    path=R.market_history_path(eid),
                )
            )
        proj_table, proj_meta = _projection_history(ctx, preds)
        if proj_table:
            stats["projection_events"].append(eid)
        # RUN series for the 3-way result tickers of a live (v1) event
        if is_v1:
            for m in mkts:
                if m["market_family"] != "match_result_3way":
                    continue
                rows = [
                    p for p in preds if p["ticker"] == m["kalshi_ticker"] and p["mean"] is not None
                ]
                if not rows:
                    continue
                fam_intl = any(str(p.get("model_family", "")).endswith(".intl_pool") for p in rows)
                status = "RESEARCH" if fam_intl else "VERIFIED"
                pts = [
                    R.point(
                        x=p["run_id"] or p["as_of"],
                        t=p["as_of"],
                        value=_r(p["mean"], 6),
                        quality_status=status,
                        event_id=eid,
                        sample_size=p["n_worlds"],
                        source=f"predictions ledger · {p['model_family']} · {p['model_version']}",
                        path=R.event_path(eid),
                    )
                    for p in rows
                ]
                lims = list(LIM_PROJECTIONS)
                q = _q(
                    status,
                    "predictions/<day>/predictions.jsonl",
                    ctx,
                    data_as_of=rows[-1]["as_of"],
                    sample_size=len(rows),
                    coverage=f"{len(rows)} runs {rows[0]['as_of']} -> {rows[-1]['as_of']}",
                    limitations=lims,
                )
                ser = R.time_series(
                    sport=SPORT,
                    metric_id=ids.metric_id(SPORT, "model_fair_probability"),
                    entity_id=m["market_id"],
                    entity_type="MARKET",
                    x_axis="RUN",
                    points=pts,
                    as_of=rows[-1]["as_of"],
                    run_id=ctx.run_id,
                    generated_at=ctx.now,
                    quality=q,
                    unit="probability",
                    links=[
                        R.link(
                            rel="EVENT_RESEARCH",
                            target_kind="event_research",
                            label="event",
                            target_id=eid,
                            path=R.event_path(eid),
                        ),
                        R.link(
                            rel="MARKET",
                            target_kind="markets",
                            label=m["yes_description"],
                            target_id=m["market_id"],
                            path=None,
                        ),
                    ],
                )
                docs.append(ser)
                stats["projection_series"].append(ser["series_id"])
                links.append(
                    R.link(
                        rel="SERIES",
                        target_kind="time_series",
                        label=f"model P(YES) by run: {m['yes_description']}",
                        target_id=ser["series_id"],
                        path=R.series_path(ser["series_id"]),
                    )
                )
        links.append(
            R.link(
                rel="CAPABILITIES",
                target_kind="capability_manifest",
                label="what SOCCER can show",
                path=R.app_path(R.CAPABILITIES_NAME),
            )
        )
        ext: dict[str, Any] = {
            "fixture_id": fid,
            "espn_event_id": espn_id,
            "published_as": "v1_event" if is_v1 else "settled_event",
            "model_families": sorted(families),
            "international_pool": intl,
            "market_history_summary": mh_summary,
            "projection_history": proj_table,
            "projection_history_meta": proj_meta,
            "calibration": cells,
            "head_to_head": h2h,
        }
        if bf and bf.get("summary"):
            ext["board_summary"] = dict(
                bf["summary"],
                source=BOARD_FILE,
                model_generated_at=_iso(bf.get("model_generated_at")),
                quality_status="RESEARCH" if intl else "PARTIAL",
            )
        if is_v1:
            ext["soccer_script_engine"] = _fit_script_payload(
                script_engine_payload(
                    bf,
                    slate_fx_by.get(fid),
                    slate_rows_by.get(fid, []),
                    intl_pool=intl,
                    slate_meta=slate_meta,
                )
            )
            stats.setdefault("script_engine_events", []).append(
                {"fixture_id": fid, "status": ext["soccer_script_engine"].get("status")}
            )
        if rest:
            ext["rest_congestion"] = rest
        if settlement:
            ext["settlement"] = settlement
        lims = (
            ["model outputs are RESEARCH_ONLY; the international pool is not validated"]
            if intl
            else []
        )
        q = _q(
            "VERIFIED",
            "v1 app export + data-archive ledgers" if is_v1 else "settlement ledger + data-archive",
            ctx,
            data_as_of=mh["as_of"] if mh else None,
            limitations=lims or None,
            coverage=f"{len(mkts)} v1 markets, {len(projections)} projections"
            if is_v1
            else f"settled fixture {fid}",
        )
        budget = PROJECTION_HISTORY_MAX_BYTES
        while True:
            doc = R.event_research(
                sport=SPORT,
                run_id=ctx.run_id,
                generated_at=ctx.now,
                event=ev,
                quality=q,
                participants=participants,
                matchup=matchup,
                projections=projections,
                distributions=distributions,
                markets=[R.market_ref(m) for m in mkts],
                market_history_path=R.market_history_path(eid) if mh is not None else None,
                context={
                    "lineups": lineups,
                    "weather": weather,
                    "venue": venue,
                    "notes": notes,
                    "injuries": [],
                },
                wagers=sorted(w["wager_id"] for w in inputs.wagers if w.get("event_id") == eid),
                links=links,
                extensions=ext,
            )
            over = len(dumps(doc)) - EVENT_MAX_BYTES
            if over <= 0 or not ext["projection_history"]:
                break
            budget = max(0, budget - over - 2_000)
            if budget < 2_000:
                ext["projection_history"] = {}
                ext["projection_history_meta"] = dict(proj_meta, omitted="per-event size budget")
                continue
            ext["projection_history"], ext["projection_history_meta"] = _projection_history(
                ctx, preds, budget
            )
        docs.append(doc)
    return docs, stats


def _fit_script_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep the script-engine payload inside SCRIPT_ENGINE_MAX_BYTES by trimming deep evidence in a fixed
    order; what was trimmed is recorded (never silently)."""
    trimmed: list[str] = []

    def size() -> int:
        return len(dumps(payload))

    steps = [
        (
            "matrix.low_high",
            lambda: [r.__setitem__(slice(5, 7), [None, None]) for r in payload["matrix"]["rows"]],
        ),
        ("cards.temporal", lambda: [c.pop("temporal", None) for c in payload["scripts"]["cards"]]),
        (
            "survivability.rows>25",
            lambda: payload["survivability"].__setitem__(
                "rows", payload["survivability"]["rows"][:25]
            ),
        ),
        ("cards.profile", lambda: [c.pop("profile", None) for c in payload["scripts"]["cards"]]),
        (
            "matrix.exact_score_rows",
            lambda: payload["matrix"].__setitem__(
                "rows",
                [
                    r
                    for r in payload["matrix"]["rows"]
                    if r[1] not in ("exact_score", "first_half_exact_score")
                ],
            ),
        ),
    ]
    if payload.get("status") != "OK":
        return payload
    for name, fn in steps:
        if size() <= SCRIPT_ENGINE_MAX_BYTES:
            break
        fn()
        trimmed.append(name)
    if trimmed:
        payload["trimmed"] = trimmed
    return payload


# ----------------------------------------------------------------------------- profiles
def _profiles(ctx: Ctx) -> list[dict[str, Any]]:
    docs = []
    v1_parts = {}
    for e in ctx.inputs.events:
        for p in e["participants"]:
            v1_parts[p["participant_id"]] = p
    upcoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for eid, ev in ctx.events.items():
        for p in ev["participants"]:
            tid = (p.get("source_ids") or {}).get("team_id")
            if tid:
                upcoming[tid].append(ev)
    q_prof = _q(
        "PARTIAL",
        "results/espn + data/registry + data-archive ledgers",
        ctx,
        limitations=LIM_RESULTS,
    )
    for tid in sorted(ctx.profile_teams):
        pid = _pid(tid)
        entity = v1_parts.get(pid) or _team_participant(tid, _team_name(ctx, tid))
        pool_key = ctx.team_pool.get(tid)
        pool = ctx.pools.get(pool_key) if pool_key else None
        all_games = ctx.games.get(tid, [])
        games = []
        for g in all_games[-PROFILE_GAMES_CAP:]:
            games.append(
                R.game_ref(
                    event_id=g.event_id,
                    start_time_utc=g.t,
                    status="FINAL",
                    opponent_id=_pid(g.opponent_id),
                    opponent_name=_team_name(ctx, g.opponent_id),
                    home_away=g.home_away,
                    result={"for": float(g.gf), "against": float(g.ga), "outcome": g.outcome},
                    competition=g.competition_id,
                    path=_event_path(ctx, g.event_id),
                )
            )
        seen_games = {g["event_id"] for g in games}
        for ev in sorted(upcoming.get(tid, []), key=lambda e: e["start_time_utc"]):
            if ev["event_id"] in seen_games:
                continue
            home, away = _participants(ev)
            opp = away if home == tid else home
            games.append(
                R.game_ref(
                    event_id=ev["event_id"],
                    start_time_utc=ev["start_time_utc"],
                    status=ev["status"],
                    opponent_id=_pid(opp) if opp else None,
                    opponent_name=_team_name(ctx, opp) if opp else None,
                    home_away="HOME" if home == tid else "AWAY",
                    competition=ev.get("league"),
                    path=R.event_path(ev["event_id"]),
                )
            )
        opp_events: dict[str, list[str]] = defaultdict(list)
        h2h: dict[str, dict[str, Any]] = {}
        for g in all_games:
            opp_events[g.opponent_id].append(g.event_id)
            h = h2h.setdefault(
                _pid(g.opponent_id),
                {"n": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "last": None},
            )
            h["n"] += 1
            h["w" if g.gf > g.ga else "d" if g.gf == g.ga else "l"] += 1
            h["gf"] += g.gf
            h["ga"] += g.ga
            h["last"] = g.match_date
        opponents = [
            {
                "participant_id": _pid(o),
                "display_name": _team_name(ctx, o),
                "event_ids": sorted(set(evs)),
                "path": _profile_path(ctx, o),
            }
            for o, evs in sorted(opp_events.items())
        ]
        series_docs = ctx.team_series.get(tid, [])
        series_refs = [
            {
                "series_id": s["series_id"],
                "metric_id": s["metric_id"],
                "x_axis": s["x_axis"],
                "split": None,
                "path": R.series_path(s["series_id"]),
            }
            for s in series_docs
        ]
        metrics = sorted(ctx.obs.get(tid, []), key=lambda o: (o["metric_id"], o["window"]["label"]))
        rankings = []
        for o in metrics:
            c = o.get("context")
            if c and c.get("ranking_id"):
                rankings.append(
                    {
                        "ranking_id": c["ranking_id"],
                        "metric_id": o["metric_id"],
                        "window_label": o["window"]["label"],
                        "split": None,
                        "path": R.ranking_path(c["ranking_id"]),
                    }
                )
        splits = {
            "home_away": sorted(
                ctx.split_obs.get(tid, []), key=lambda o: (o["metric_id"], o["split"]["value"])
            )
        }
        if not splits["home_away"]:
            splits = {}
        team_markets = [m for m in ctx.inputs.markets if m.get("participant_id") == pid]
        market_ids = {m["market_id"] for m in team_markets}
        rec_auth = {
            r["market_id"]: (bool(r["research_only"]), r["authority"])
            for r in ctx.inputs.recommendations
        }
        projections = []
        for mp in sorted(
            (mp for mp in ctx.inputs.model_prices if mp["market_id"] in market_ids),
            key=lambda mp: mp["market_id"],
        ):
            ro, auth = rec_auth.get(mp["market_id"], (True, "RESEARCH_ONLY"))
            projections.append(
                R.projection_ref(
                    mp,
                    research_only=ro,
                    authority=auth,
                    quality_status="RESEARCH"
                    if (_model_family_of(mp) or "").endswith(".intl_pool")
                    else "VERIFIED",
                    metric_id=ids.metric_id(SPORT, "model_fair_probability"),
                )
            )
        links = [
            R.link(
                rel="EVENT",
                target_kind="event_research",
                label=f"{ev.get('competition') or ev.get('league')} {ev['start_time_utc'][:10]}",
                target_id=ev["event_id"],
                path=R.event_path(ev["event_id"]),
            )
            for ev in sorted(
                upcoming.get(tid, []), key=lambda e: (e["start_time_utc"], e["event_id"])
            )
        ]
        links += [
            R.link(
                rel="SERIES",
                target_kind="time_series",
                label=ctx.metrics[s["metric_id"].split(".", 1)[1]]["name"],
                target_id=s["series_id"],
                path=R.series_path(s["series_id"]),
            )
            for s in series_docs
        ]
        meta = ctx.inputs.team_meta.get(tid, {})
        ext = {
            "team_id": tid,
            "pool": pool.label if pool else None,
            "country": meta.get("country"),
            "kind": meta.get("kind"),
            "gender": meta.get("gender"),
            "games_archived": len(all_games),
            "games_listed_cap": PROFILE_GAMES_CAP,
            "head_to_head": h2h,
            "registry_aliases": ctx.inputs.team_aliases.get(tid, []),
        }
        if tid in ctx.intl_map:
            ext["intl_id"] = ctx.intl_map[tid]
        if pool_key in ctx.dc_fits:
            ext["dc_fit"] = dict(
                ctx.dc_fits[pool_key], quality_status="RESEARCH", not_production_posterior=True
            )
        docs.append(
            R.entity_profile(
                sport=SPORT,
                run_id=ctx.run_id,
                generated_at=ctx.now,
                entity=entity,
                entity_type="TEAM",
                quality=q_prof,
                season=pool.season if pool else None,
                league=pool_key,
                metrics=metrics,
                splits=splits,
                series=series_refs,
                rankings=rankings,
                games=games,
                opponents=opponents,
                markets=[R.market_ref(m) for m in team_markets],
                projections=projections,
                links=links,
                extensions=ext,
            )
        )
    return docs


# ----------------------------------------------------------------------------- capabilities + search
def _cap(**kw: Any) -> dict[str, Any]:
    return R.capability(**kw)


def _evidence_or_unavailable(
    capability: str,
    status: str,
    summary: str,
    evidence: list[str],
    *,
    limitations: list[str] | None = None,
    reason_if_none: str,
    **kw: Any,
) -> dict[str, Any]:
    if evidence:
        return _cap(
            capability=capability,
            status=status,
            summary=summary,
            evidence=evidence[:3],
            limitations=limitations,
            **kw,
        )
    return _cap(
        capability=capability, status="UNAVAILABLE", summary=summary, reasons=[reason_if_none]
    )


def _capabilities(
    ctx: Ctx,
    stats: dict[str, Any],
    profile_paths: list[str],
    ranking_docs: list[dict[str, Any]],
    series_docs: list[dict[str, Any]],
) -> dict[str, Any]:
    inputs = ctx.inputs
    v1_paths = [
        R.event_path(e["event_id"]) for e in sorted(inputs.events, key=lambda e: e["event_id"])
    ]
    first_team = profile_paths[:2]
    res_since = min((r["match_date"] for r in inputs.results), default=None)
    snap_since = min(
        (p["captured_at"] for pts in inputs.snapshots.values() for p in pts), default=None
    )
    pred_since = min((p["as_of"] for p in inputs.predictions), default=None)
    form_ids = [ids.metric_id(SPORT, m.slug) for m in FORM_METRICS]
    teams_with_obs = sum(1 for t in ctx.profile_teams if ctx.obs.get(t))
    nat_series = [s for s in series_docs if s["metric_id"] == ids.metric_id(SPORT, "elo_rating")]
    game_series = [
        s
        for s in series_docs
        if s["entity_type"] == "TEAM" and s["metric_id"] != ids.metric_id(SPORT, "elo_rating")
    ]
    proj_series = [s for s in series_docs if s["entity_type"] == "MARKET"]
    settled = [R.event_path(e) for e in stats["settled_events"]]
    mh_paths = [R.market_history_path(e) for e in stats["mh_events"]]
    window_labels = sorted({w["label"] for p in ctx.pools.values() for w in p.windows})
    caps = [
        _cap(
            capability="team_profiles",
            status="PARTIAL",
            entity_types=["TEAM"],
            evidence=first_team,
            summary=f"{len(ctx.profile_teams)} team profiles: every team of the published events plus every team of their "
            "competition pools (game logs, form, head-to-head, rankings)",
            limitations=LIM_RESULTS
            + [
                "team-level ratings are never persisted by production; the dc_* ratings are a RESEARCH refit"
            ],
            coverage=f"{len(ctx.profile_teams)} teams ({teams_with_obs} with ranked metrics), pools: {', '.join(sorted(ctx.pools))}",
            since=res_since,
        ),
        _cap(
            capability="player_profiles",
            status="UNAVAILABLE",
            entity_types=["PLAYER"],
            summary="no player profiles",
            reasons=[
                "no canonical player identity: data/registry has players: 0; ESPN athlete ids appear only on lineup sheets",
                "player metrics are UNAVAILABLE (no minutes, goals, xG per player); lineup sheets and appearance "
                "counts are published inside event research context.lineups instead",
            ],
        ),
        _cap(
            capability="event_research",
            status="VERIFIED",
            entity_types=["EVENT"],
            evidence=v1_paths[:2] + settled[:1],
            summary=f"{len(inputs.events)} v1 events + {len(ctx.events) - len(inputs.events)} settled events (last "
            f"{SETTLED_WINDOW_DAYS} days): markets, projections, distributions, matchup, context, settlement",
            coverage=f"{len(ctx.events)} events",
            limitations=["the matchup / context parts carry their own PARTIAL / RESEARCH statuses"],
        ),
        _cap(
            capability="team_metrics",
            status="PARTIAL",
            entity_types=["TEAM"],
            evidence=first_team,
            metrics=form_ids,
            summary="goals-based form (PPG, GF/GA per game, clean sheets, BTTS, over 2.5) per competition pool",
            limitations=LIM_RESULTS,
            windows=window_labels,
            since=res_since,
            coverage=f"{len(inputs.results)} deduplicated ESPN results",
        ),
        _cap(
            capability="player_metrics",
            status="UNAVAILABLE",
            entity_types=["PLAYER"],
            summary="no player metrics",
            reasons=[
                "only ESPN lineup sheets exist (ids, names, positions, starter/sub flags); no minutes, goals, xG "
                "(PlayerMatchStats protocol only, providers/interfaces.py)"
            ],
        ),
        _cap(
            capability="team_game_logs",
            status="PARTIAL",
            entity_types=["TEAM"],
            evidence=first_team,
            summary=f"per-team ESPN game logs (last {PROFILE_GAMES_CAP} in the profile; per-game GF/GA series for event teams)",
            limitations=LIM_RESULTS
            + [f"profiles list the last {PROFILE_GAMES_CAP} games; series cap {GAME_SERIES_CAP}"],
            since=res_since,
            coverage=f"{len(inputs.results)} results across {len({r['competition_id'] for r in inputs.results})} competitions",
        ),
        _evidence_or_unavailable(
            "player_game_logs",
            "PARTIAL",
            "appearance counts per player on the published lineup sheets",
            [R.event_path(e) for e in stats["lineup_events"]],
            entity_types=["PLAYER"],
            limitations=LIM_LINEUPS,
            reason_if_none="no published event has a stored lineup sheet with players in this publication",
        ),
        _cap(
            capability="historical_results",
            status="PARTIAL",
            entity_types=["TEAM"],
            evidence=first_team + [R.series_path(s["series_id"]) for s in nat_series[:1]],
            summary="ESPN results 2024-07 onward (goals only) and the international results archive since 1872 (Elo series)",
            limitations=LIM_RESULTS + LIM_ELO,
            since=res_since,
        ),
        _cap(
            capability="opponents",
            status="PARTIAL",
            entity_types=["TEAM"],
            evidence=first_team + v1_paths[:1],
            summary="opponent lists with event ids and head-to-head records (ESPN archive; international archive for mapped nations)",
            limitations=LIM_RESULTS + LIM_ELO,
        ),
        _evidence_or_unavailable(
            "opponent_adjustment",
            "PARTIAL",
            "Dixon-Coles attack/defence ratings (opponent-adjusted by construction), "
            "refit by the research export per competition pool",
            first_team if ctx.dc_fits else [],
            entity_types=["TEAM"],
            limitations=LIM_DC,
            metrics=[ids.metric_id(SPORT, "dc_attack"), ids.metric_id(SPORT, "dc_defence")],
            reason_if_none="no competition pool had >= 50 archived results to refit",
        ),
        _cap(
            capability="schedule_strength",
            status="UNAVAILABLE",
            summary="no schedule-strength metric",
            reasons=[
                "implicit in Dixon-Coles only; ratings are not persisted, so no schedule-strength series exists"
            ],
        ),
        _evidence_or_unavailable(
            "recent_form_windows",
            "PARTIAL",
            "L5 / L10 form windows and per-fixture rest/congestion context",
            first_team if any(len(p.windows) > 1 for p in ctx.pools.values()) else [],
            limitations=LIM_CONTEXT,
            windows=window_labels,
            reason_if_none="no form windows were computed",
        ),
        _cap(
            capability="usage",
            status="UNAVAILABLE",
            summary="no minutes / usage",
            reasons=[
                "ESPN summary has no minutes; only lineup priors (model/lineups.py 80/15 min) exist"
            ],
        ),
        _evidence_or_unavailable(
            "lineups",
            "PARTIAL",
            "latest stored ESPN lineup sheet per published event (formation, XI, bench)",
            [R.event_path(e) for e in stats["lineup_events"]],
            limitations=LIM_LINEUPS,
            reason_if_none="no published event has a stored lineup sheet with players in this publication",
        ),
        _cap(
            capability="injuries",
            status="UNAVAILABLE",
            summary="no injury data",
            reasons=["InjuryProvider is unimplemented"],
        ),
        _cap(
            capability="matchup_metrics",
            status="UNAVAILABLE",
            summary="no matchup-specific metrics",
            reasons=[
                "the repo stores no matchup metrics; event research matchup rows only juxtapose each side's own team metrics"
            ],
        ),
        _evidence_or_unavailable(
            "projection_distributions",
            "PARTIAL",
            "board P(YES) quantiles (stored levels 0.5 .. 99.5 %) for live markets",
            [R.event_path(e) for e in stats["distribution_events"]],
            limitations=LIM_DISTRIBUTIONS,
            reason_if_none="the current model board has no quantiles for a published market",
        ),
        _evidence_or_unavailable(
            "raw_projections",
            "VERIFIED",
            "per-ticker fair probability (mean + 80 % interval) per run, from the prediction ledger",
            [R.series_path(s["series_id"]) for s in proj_series[:1]]
            + [R.event_path(e) for e in stats["projection_events"][:2]],
            limitations=LIM_PROJECTIONS,
            metrics=[ids.metric_id(SPORT, "model_fair_probability")],
            since=pred_since,
            reason_if_none="no prediction ledger rows for the published fixtures",
        ),
        _cap(
            capability="market_prices",
            status="VERIFIED",
            entity_types=["MARKET"],
            evidence=v1_paths[:2],
            summary=f"{len(inputs.markets)} current Kalshi markets (v1 markets.json, referenced per event)",
        ),
        _evidence_or_unavailable(
            "market_price_history",
            "VERIFIED",
            "per-event Kalshi quote history (bid/ask/last/volume/OI per capture)",
            mh_paths,
            limitations=LIM_MARKET_HISTORY
            + (
                [f"{stats['capped_mh']} event(s) capped to fit the per-event size budget"]
                if stats["capped_mh"]
                else []
            ),
            coverage=f"{len(mh_paths)} events, {stats['mh_tickers']} tickers, {stats['mh_points']} captures",
            since=snap_since,
            entity_types=["MARKET"],
            reason_if_none="no stored captures for the published tickers",
        ),
        _cap(
            capability="advanced_stats",
            status="RESEARCH",
            summary="xG history and league/international strength studies "
            "exist only as frozen research outputs (data/research); not published here",
            limitations=[
                "xG: FiveThirtyEight 2016-17 -> 2022-23 top-5 only (data/research/xg_history_v1.csv.gz), team names "
                "without ids, no live xG",
                "league offsets (multi_league_v1) and intl_hier_v1 are RESEARCH_ONLY; "
                "intl_hier failed 3/8 acceptance criteria",
            ],
        ),
        _cap(
            capability="situational_splits",
            status="PARTIAL",
            entity_types=["TEAM"],
            evidence=first_team,
            splits=["home_away"],
            summary="home / away splits of PPG and GF/GA per game over each pool's primary window",
            limitations=LIM_RESULTS
            + [
                "neutral_site is flagged on 16 of 4,849 ESPN rows; no other split tables are stored"
            ],
        ),
        _cap(
            capability="player_props",
            status="UNAVAILABLE",
            summary="player props are never priced",
            reasons=[
                "player_goals/assists/shots/cards families are dispositioned UNSUPPORTED_FAMILY"
            ],
        ),
        _cap(
            capability="team_props",
            status="VERIFIED",
            entity_types=["MARKET"],
            evidence=v1_paths[:2],
            summary="team_total, first-half, btts, first_to_score markets with model prices",
        ),
        _cap(
            capability="game_markets",
            status="VERIFIED",
            entity_types=["MARKET"],
            evidence=v1_paths[:2],
            summary="match_result_3way, handicap, total_goals, exact_score ... with model prices",
        ),
        _cap(
            capability="play_by_play",
            status="UNAVAILABLE",
            summary="no play-by-play",
            reasons=[
                "ESPN timed scoring plays are used only as settlement evidence and are not archived as events"
            ],
        ),
        _evidence_or_unavailable(
            "weather",
            "PARTIAL",
            "latest Open-Meteo kickoff-hour forecast + venue per published event",
            [R.event_path(e) for e in stats["weather_events"]],
            limitations=LIM_WEATHER,
            reason_if_none="no stored forecast for a published event in this publication",
        ),
        _cap(
            capability="venue_effects",
            status="UNAVAILABLE",
            summary="no venue effects",
            reasons=[
                "venue name/city/country exist only inside weather rows; venue_id is null on fixtures"
            ],
        ),
        _evidence_or_unavailable(
            "calibration",
            "VERIFIED",
            "model_health cells (n, log loss vs market, Brier, ECE, 80 % coverage, CLV) per "
            "model family x market family, attached to each event",
            [R.event_path(e) for e in stats["calibration_events"]],
            limitations=LIM_CALIBRATION + ["international pool cells are marked validated=false"],
            reason_if_none="evaluation/model_health.v1.json has no cell for the published model families",
        ),
        _evidence_or_unavailable(
            "historical_accuracy",
            "VERIFIED",
            f"settled outcomes per ticker for fixtures settled in the last {SETTLED_WINDOW_DAYS} days",
            settled,
            limitations=[f"rolling {SETTLED_WINDOW_DAYS}-day window of settled fixtures"],
            reason_if_none=f"no fixture settled in the last {SETTLED_WINDOW_DAYS} days",
        ),
        _evidence_or_unavailable(
            "clv",
            "PARTIAL",
            "close_v2 and fee-aware CLV per settled ticker",
            settled,
            limitations=LIM_CLV,
            reason_if_none=f"no fixture settled in the last {SETTLED_WINDOW_DAYS} days",
        ),
        _cap(
            capability="wager_history",
            status="UNAVAILABLE",
            summary="no wagers",
            reasons=["the accounting-data ledgers are empty (0 rows)"]
            if not inputs.wagers
            else ["wagers live in the v1 wagers.json, not the explorer"],
        ),
        _evidence_or_unavailable(
            "rankings",
            "PARTIAL",
            f"{len(ranking_docs)} rankings over full competition-pool universes",
            [R.ranking_path(r["ranking_id"]) for r in ranking_docs[:2]],
            limitations=LIM_RESULTS,
            reason_if_none="no metric had two ranked teams",
        ),
        _evidence_or_unavailable(
            "time_series",
            "PARTIAL",
            "per-game GF/GA series, Elo history and per-run model probability",
            [
                R.series_path(s["series_id"])
                for s in (game_series[:1] + nat_series[:1] + proj_series[:1])
            ],
            limitations=[
                f"per-game series capped at the last {GAME_SERIES_CAP} games; Elo at the last {ELO_SERIES_CAP} matches",
                "history on data-archive is 7 days, so run-axis series are a week long",
            ],
            reason_if_none="no series published",
        ),
        _cap(
            capability="comparisons",
            status="PARTIAL",
            entity_types=["TEAM"],
            evidence=v1_paths[:1] + first_team[:1],
            summary="home vs away matchup rows per event and rank/league-average context on every ranked observation",
            limitations=LIM_RESULTS,
        ),
        _cap(
            capability="search",
            status="VERIFIED",
            evidence=[R.app_path(R.SEARCH_NAME)],
            summary="teams, events, metrics and rankings with aliases",
        ),
    ]
    n_settle = sum(len(v) for v in ctx.settled_by_fixture.values())
    n_cells = len(ctx.inputs.model_health)
    measured = {
        "player_game_logs": f"{len(stats['lineup_events'])} events with a stored lineup sheet; "
        f"{len(inputs.appearances)} ESPN athletes with appearance counts",
        "lineups": f"{len(stats['lineup_events'])} of {len(ctx.events)} published events",
        "weather": f"{len(stats['weather_events'])} of {len(ctx.events)} published events",
        "historical_results": f"{len(inputs.results)} ESPN results; {len(inputs.intl_rows)} internationals "
        f"({len(ctx.intl_map)} registry nations mapped exactly)",
        "opponents": f"{len(ctx.profile_teams)} teams with opponent lists and head-to-head records",
        "opponent_adjustment": "; ".join(
            f"{k}: {v['results_used']} results through {v['fitted_through']}"
            for k, v in sorted(ctx.dc_fits.items())
        ),
        "recent_form_windows": f"windows {', '.join(window_labels)}; rest/congestion on "
        f"{len(stats['rest_events'])} events",
        "projection_distributions": f"{len(stats['distribution_events'])} events (current board only)",
        "raw_projections": f"{len(inputs.predictions)} ledger rows for {len(stats['projection_events'])} events; "
        f"{len(proj_series)} run-axis series",
        "market_prices": f"{len(inputs.markets)} v1 markets",
        "situational_splits": f"{sum(1 for t in ctx.profile_teams if ctx.split_obs.get(t))} teams with home/away splits",
        "team_props": f"{len(inputs.markets)} v1 markets",
        "game_markets": f"{len(inputs.markets)} v1 markets",
        "calibration": f"{n_cells} model_health cells; attached to {len(stats['calibration_events'])} events",
        "historical_accuracy": f"{len(stats['settled_events'])} settled events, {n_settle} settlement records",
        "clv": f"{len(stats['settled_events'])} settled events, {n_settle} settlement records",
        "rankings": f"{len(ranking_docs)} rankings",
        "time_series": f"{len(game_series)} per-game, {len(nat_series)} Elo, {len(proj_series)} run-axis series",
        "comparisons": f"{len(ctx.events)} events with matchup rows",
        "search": f"{len(ctx.profile_teams)} teams, {len(ctx.events)} events, {len(ctx.metrics)} metrics",
    }
    since = {
        "historical_results": res_since,
        "lineups": None,
        "calibration": None,
        "historical_accuracy": None,
    }
    settled_since = min((s["settled_at"] for s in inputs.settlements), default=None)
    for name in ("historical_accuracy", "clv"):
        since[name] = settled_since
    for c in caps:
        if (
            c["status"] in ("VERIFIED", "PARTIAL")
            and c["capability"] in measured
            and not c["coverage"]
        ):
            c["coverage"] = measured[c["capability"]] or None
        if c["status"] in ("VERIFIED", "PARTIAL") and since.get(c["capability"]) and not c["since"]:
            c["since"] = since[c["capability"]][:10]
    split_dims = [{"dimension": "home_away", "values": ["HOME", "AWAY"], "status": "PARTIAL"}]
    windows = [w for p in sorted(ctx.pools.values(), key=lambda p: p.key) for w in p.windows]
    uniq = {w["label"]: w for w in windows}
    return R.capability_manifest(
        sport=SPORT,
        run_id=ctx.run_id,
        generated_at=ctx.now,
        capabilities=caps,
        audit_date=AUDIT_DATE,
        split_dimensions=split_dims,
        windows=[uniq[k] for k in sorted(uniq)],
        notes=[
            "statuses follow scratchpad/phase2/audit_soccer.md §4/§10 (2026-10-03)",
            "the model is RESEARCH_ONLY everywhere; the international pool is not validated",
            *ctx.caps_notes,
        ],
    )


def _search(ctx: Ctx, ranking_docs: list[dict[str, Any]]) -> dict[str, Any]:
    entries = []
    for tid in sorted(ctx.profile_teams):
        pid = _pid(tid)
        pool = ctx.pools.get(ctx.team_pool.get(tid, ""))
        meta = ctx.inputs.team_meta.get(tid, {})
        aliases = [*ctx.inputs.team_aliases.get(tid, []), tid]
        if meta.get("country"):
            aliases.append(meta["country"])
        entries.append(
            R.search_entry(
                id=pid,
                kind="TEAM",
                label=_team_name(ctx, tid),
                path=R.team_path(pid),
                sport=SPORT,
                secondary=pool.label if pool else None,
                aliases=sorted(set(aliases)),
                league=ctx.team_pool.get(tid),
                season=pool.season if pool else None,
            )
        )
    for eid in sorted(ctx.events):
        ev = ctx.events[eid]
        home, away = _participants(ev)
        entries.append(
            R.search_entry(
                id=eid,
                kind="EVENT",
                label=f"{_team_name(ctx, home)} vs {_team_name(ctx, away)}",
                path=R.event_path(eid),
                sport=SPORT,
                secondary=f"{ev.get('competition') or ev.get('league')} {ev['start_time_utc'][:10]} {ev['status']}",
                aliases=[ctx.event_fixture[eid]],
                league=ev.get("league"),
                season=ev.get("season"),
            )
        )
    for slug, m in sorted(ctx.metrics.items()):
        entries.append(
            R.search_entry(
                id=m["metric_id"],
                kind="METRIC",
                label=m["name"],
                path=R.app_path(R.METRICS_NAME),
                sport=SPORT,
                secondary=m["category"],
                aliases=[m["short_name"], slug],
            )
        )
    for rk in ranking_docs:
        name = ctx.metrics[rk["metric_id"].split(".", 1)[1]]["name"]
        entries.append(
            R.search_entry(
                id=rk["ranking_id"],
                kind="RANKING",
                label=f"{name} ranking — {rk['universe']['label']}",
                path=R.ranking_path(rk["ranking_id"]),
                sport=SPORT,
                secondary=rk["window"]["label"],
                season=rk["universe"]["season"],
            )
        )
    return R.search_index(sport=SPORT, run_id=ctx.run_id, generated_at=ctx.now, entries=entries)


def build_explorer(
    inputs: ResearchInputs, *, run_id: str | None = None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Pure: loaded inputs -> (explorer documents, publication meta {quality, as_of, windows, warnings})."""
    run_id = run_id or inputs.manifest["run_id"]
    ctx = _build_context(inputs, run_id)
    _register_metrics(ctx)
    ranking_docs = _form_rankings(ctx)
    ranking_docs += _dc_rankings(ctx)
    ranking_docs += _elo(ctx)
    series_docs: list[dict[str, Any]] = []
    event_teams = sorted(
        {
            t
            for ev in ctx.events.values()
            for t in _participants(ev)
            if t and ctx.event_fixture[ev["event_id"]] in ctx.v1_events
        }
    )
    for tid in event_teams:
        series_docs += _series_for_team(ctx, tid)
    event_docs, stats = _event_docs(ctx)
    series_docs += [d for d in event_docs if d["kind"] == "time_series"]
    event_docs = [d for d in event_docs if d["kind"] != "time_series"]
    profiles = _profiles(ctx)
    used = (
        {o["metric_id"] for p in profiles for o in p["metrics"]}
        | {s["metric_id"] for s in series_docs}
        | {r["metric_id"] for r in ranking_docs}
    )
    metrics = [m for m in ctx.metrics.values() if m["metric_id"] in used]
    registry = R.metric_registry(sport=SPORT, run_id=run_id, generated_at=ctx.now, metrics=metrics)
    caps = _capabilities(
        ctx,
        stats,
        [R.team_path(_pid(t)) for t in sorted(event_teams or ctx.profile_teams)],
        ranking_docs,
        series_docs,
    )
    search = _search(ctx, ranking_docs)
    docs = [registry, caps, search, *profiles, *ranking_docs, *series_docs, *event_docs]
    stamps = [p["captured_at"] for pts in inputs.snapshots.values() for p in pts]
    stamps += [timeutil.parse_ts(p["as_of"]) for p in inputs.predictions]
    stamps += [timeutil.parse_ts(s["settled_at"]) for s in inputs.settlements]
    stamps += [timeutil.parse_ts(_day_ts(r["match_date"])) for r in inputs.results]
    as_of = max(stamps) if stamps else None
    quality = R.quality(
        status="PARTIAL",
        source="SOCCER data-archive + main (results, ledgers, captures, registry)",
        generated_at=ctx.now,
        production=True,
        data_as_of=as_of,
        methodology_version=METHODOLOGY_VERSION,
        coverage=f"{len(ctx.events)} events, {len(profiles)} teams, {len(ranking_docs)} rankings, "
        f"{len(series_docs)} series",
        limitations=LIM_RESULTS + LIM_PROJECTIONS[:2],
    )
    windows = caps["windows"]
    meta = {
        "quality": quality,
        "as_of": as_of,
        "windows": windows,
        "warnings": list(inputs.warnings),
        "stats": stats,
    }
    return docs, meta


# ----------------------------------------------------------------------------- export
def _check_no_secrets(docs: list[dict[str, Any]]) -> None:
    for d in docs:
        text = dumps(d)
        for marker in _SECRET_MARKERS:
            if marker in text:
                raise ResearchExportError(
                    f"{d['kind']}: secret-shaped content ({marker!r}) refused"
                )


def refresh_due(app_root: Path, *, now: object, min_interval_seconds: float) -> tuple[bool, str]:
    """``research.refresh_due`` for this sport. SOCCER also publishes settled fixtures as event
    research, so the explorer's event list is a superset of the v1 events: only v1 events the explorer
    does not have yet (new games) force a rebuild; settled extras, and v1 events that left the board,
    wait for the interval refresh."""
    due, reason = R.refresh_due(app_root, now=now, min_interval_seconds=min_interval_seconds)
    if not due or not reason.startswith("v1 events changed"):
        return due, reason
    index = R.read_index(app_root) or {}
    current = {e["event_id"] for e in _v1_items(Path(app_root), "events")}
    published = {e["event_id"] for e in index.get("events", [])}
    new = current - published
    if new:
        return True, f"v1 events changed ({len(new)} new)"
    age = (timeutil.parse_ts(now) - timeutil.parse_ts(index["generated_at"])).total_seconds()
    if age >= min_interval_seconds:
        return True, f"explorer is {int(age)} s old (refresh every {int(min_interval_seconds)} s)"
    return False, (
        f"explorer is {int(age)} s old and has every v1 event "
        f"({len(published - current)} settled/retired extras)"
    )


def export_explorer(
    *,
    app_root: Path,
    data_root: Path,
    now: datetime | str | None = None,
    commit_sha: str | None = None,
    min_interval_seconds: float = 0,
    repo_root: Path = REPO_ROOT,
    log=print,
) -> int:
    """Build and publish ``<app_root>/explorer``. Returns 0, or 1 with the previous tree untouched.
    With ``min_interval_seconds > 0`` the rebuild is skipped (exit 0, tree untouched) unless
    :func:`refresh_due` says it is due."""
    app_root = Path(app_root)
    try:
        when = timeutil.parse_ts(now) if now is not None else None
        if min_interval_seconds > 0:
            manifest_path = app_root / "manifest.json"
            if not manifest_path.exists():
                raise ResearchExportError(
                    f"no v1 manifest at {manifest_path}: run app-export first"
                )
            at = when or timeutil.parse_ts(_read_json(manifest_path)["generated_at"])
            due, reason = refresh_due(app_root, now=at, min_interval_seconds=min_interval_seconds)
            if not due:
                log(f"research-export SKIPPED (not due: {reason}); explorer/ left untouched")
                return 0
            log(f"research-export due: {reason}")
        inputs = load_inputs(
            data_root=Path(data_root), app_root=app_root, now=when, repo_root=repo_root
        )
        docs, meta = build_explorer(inputs)
        _check_no_secrets(docs)
        manifest = inputs.manifest
        index = R.publish_explorer(
            app_root=app_root,
            sport=SPORT,
            run_id=manifest["run_id"],
            generated_at=inputs.now,
            documents=docs,
            quality=meta["quality"],
            as_of=meta["as_of"],
            commit_sha=commit_sha or manifest.get("commit_sha"),
            base_manifest_run_id=manifest["run_id"],
            windows=meta["windows"],
            warnings=meta["warnings"],
        )
    except Exception as exc:  # the failure path is the point: keep the previous tree, exit 1
        log(
            f"research-export FAILED ({type(exc).__name__}: {exc}); previous explorer/ left untouched"
        )
        return 1
    sizes = R.tree_bytes(app_root)
    log(
        f"research-export OK run_id={index['run_id']} counts={json.dumps(index['counts'], sort_keys=True)} "
        f"bytes={json.dumps(sizes, sort_keys=True)} -> {app_root / R.EXPLORER_DIR}"
    )
    return 0


def add_arguments(ap: argparse.ArgumentParser) -> None:
    ap.add_argument(
        "--data-root", required=True, help="archive root (the same --data-root app-export read)"
    )
    ap.add_argument(
        "--out",
        required=True,
        help="the published v1 app root, e.g. <archive>/app/latest (explorer/ goes inside)",
    )
    ap.add_argument(
        "--now", default=None, help="ISO-8601 UTC instant; default = the v1 manifest's generated_at"
    )
    ap.add_argument("--commit-sha", default=None)
    ap.add_argument(
        "--min-interval-minutes",
        type=float,
        default=0,
        help="rebuild only when due (no explorer, new v1 events, or older than this); 0 = always",
    )


def run_from_args(args: argparse.Namespace) -> int:
    return export_explorer(
        app_root=Path(args.out),
        data_root=Path(args.data_root),
        now=args.now or None,
        commit_sha=args.commit_sha or None,
        min_interval_seconds=60.0 * float(getattr(args, "min_interval_minutes", 0) or 0),
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    add_arguments(ap)
    return run_from_args(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
