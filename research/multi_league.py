"""Walk-forward evaluation of the hierarchical multi-league strength model (multi_league_v1).

Protocol (chronological, strictly point-in-time; negative results reported as-is):
* Domestic data: club-football-match-data Matches.csv (football-data.co.uk redistribution),
  leagues E0,E1,SP1,SP2,D1,D2,I1,I2,F1,F2 (core10) and optionally P1,N1,B1,T1,SC0,G1 (ext16).
  Team identity is resolved through the alias registry with the league's country as scope; teams
  outside the registry get a country-scoped provisional id so promotion/relegation keeps identity.
* Cross-league data: openfootball cl/el/conf .txt files (2014-15 .. 2025-26) parsed from GitHub
  raw, names mapped with AliasRegistry.resolve_team(name, gender=MEN); unmapped names reported.
* Every prediction for a match on date D uses a posterior fitted on matches with date < D
  (refit cadence in days; between refits the last posterior is used, which is only staler).
* (i) Domestic: same aligned sample as walk_forward_v1 (E0,SP1,D1,I1,F1, scored 2019-20..2025-26,
  odds present, teams seen >= 5 in their league) - multi-league vs recomputed single-league DC
  vs de-vigged Bet365 pre-match 1X2 vs walk-forward hybrid blends.
* (ii) UEFA: matches whose two teams both have domestic history in the model, scored 90-minute
  1X2 out of sample against a base-rate baseline, an Elo-difference multinomial logistic fitted
  walk-forward, and a naive single-league DC that ignores league strength.

Usage: `python research/multi_league.py run --variant core|ext|elo|pooled|dc` (one process each,
they are independent) then `python research/multi_league.py assemble`.
"""

from __future__ import annotations

import argparse
import bisect
import contextlib
import csv
import hashlib
import json
import re
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from soccer_edge.core.errors import AmbiguousAliasError, UnknownAliasError
from soccer_edge.core.serialization import content_hash, read_json, write_json
from soccer_edge.evaluation.metrics import (
    bootstrap_mean_ci,
    brier,
    expected_calibration_error,
    log_loss,
    multiclass_brier,
    multiclass_log_loss,
)
from soccer_edge.families.base import blend_logit, devig_proportional, fit_blend_weight
from soccer_edge.identity.models import Gender
from soccer_edge.identity.registry import AliasRegistry, normalize_alias
from soccer_edge.model.multi_league import (
    LeagueMatchRow,
    MultiLeagueConfig,
    MultiLeagueFitter,
    MultiLeaguePosterior,
    fit_elo_mapping,
    integrated_outcome_probs,
)
from soccer_edge.model.strength import (
    DixonColesFitter,
    MatchRow,
    ParameterPosterior,
    StrengthConfig,
)
from soccer_edge.providers.club_football_data import season_id_for

REPO = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = "multi_league_v1"
CSV_PATH = REPO / "data" / "cache" / "Matches.csv"
UEFA_CACHE = REPO / "data" / "cache" / "openfootball"
PARTS_DIR = REPO / "data" / "research" / "_multi_league_parts"
OUT_JSON = REPO / "data" / "research" / "multi_league_v1.json"
PRED_CSV = REPO / "data" / "research" / "multi_league_v1_predictions.csv"

CORE10 = ("E0", "E1", "SP1", "SP2", "D1", "D2", "I1", "I2", "F1", "F2")
EXT16 = CORE10 + ("P1", "N1", "B1", "T1", "SC0", "G1")
TOP5 = ("E0", "SP1", "D1", "I1", "F1")
LEAGUE_COUNTRY = {
    "E0": "ENG", "E1": "ENG", "SP1": "ESP", "SP2": "ESP", "D1": "GER", "D2": "GER",
    "I1": "ITA", "I2": "ITA", "F1": "FRA", "F2": "FRA", "P1": "POR", "N1": "NED",
    "B1": "BEL", "T1": "TUR", "SC0": "SCO", "G1": "GRE",
}  # fmt: skip
UEFA_FILES = {
    "cl": [f"{y}-{str(y + 1)[2:]}" for y in range(2014, 2026)],
    "el": [f"{y}-{str(y + 1)[2:]}" for y in range(2020, 2025)],
    "conf": [f"{y}-{str(y + 1)[2:]}" for y in range(2021, 2025)],
}
UEFA_URL = (
    "https://raw.githubusercontent.com/openfootball/champions-league/master/{season}/{comp}.txt"
)
# openfootball spellings of clubs that already exist in seed.json under other aliases. Explicit,
# not fuzzy: seed.json is frozen for this mission, so the three are mapped here and reported.
EXPLICIT_UEFA_ALIASES = {
    "Bor. Mönchengladbach": "ger.gladbach",
    "1899 Hoffenheim": "ger.hoffenheim",
    "Lazio Roma": "ita.lazio",
}
MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    )
}
FIRST_FIT_DATA = date(2017, 7, 1)  # burn-in season 2017-18
SCORE_START = date(2018, 7, 1)  # first predictions (2018-19); aligned domestic sample from 2019-20
MIN_PRIOR_FOR_HYBRID = 500
POSTERIOR_SAMPLES = 100  # as in the frozen walk_forward_v1 run


# ----------------------------------------------------------------------------------------------
# data
# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class DomRow:
    date: date
    div: str
    season: str
    home: str
    away: str
    hg: int
    ag: int
    p_mkt: tuple[float, float, float] | None
    p_mkt_o25: float | None
    odds_home: float | None
    home_elo: float | None
    away_elo: float | None


@dataclass(frozen=True)
class UefaMatch:
    date: date
    comp: str
    season: str
    stage: str
    home_name: str
    away_name: str
    home: str | None
    away: str | None
    hg: int
    ag: int
    neutral: bool
    aet: bool


class TeamIds:
    """Registry-first ids with country-scoped provisional fallbacks (identity survives
    promotion/relegation because the provisional id is keyed on country + normalised name)."""

    def __init__(self, reg: AliasRegistry) -> None:
        self.reg = reg
        self.cache: dict[tuple[str, str], str] = {}
        self.provisional: set[str] = set()

    def get(self, name: str, country: str) -> str:
        key = (country, name)
        if key in self.cache:
            return self.cache[key]
        try:
            tid = self.reg.resolve_team(name, country=country, gender=Gender.MEN).team_id
        except UnknownAliasError:
            slug = re.sub(r"[^a-z0-9]+", "_", normalize_alias(name)).strip("_")
            tid = f"prov.fd.{country.lower()}.{slug}"
            self.provisional.add(tid)
        self.cache[key] = tid
        return tid


def load_domestic(
    ids: TeamIds, leagues: tuple[str, ...], start: date
) -> tuple[list[DomRow], list[tuple[float, float, int, int]], str]:
    """Returns (rows for the modelled leagues from `start`, pre-window Elo rows for the Elo
    mapping fit, csv sha256)."""
    h = hashlib.sha256()
    rows: list[DomRow] = []
    elo_fit: list[tuple[float, float, int, int]] = []
    with CSV_PATH.open("rb") as fb:
        for chunk in iter(lambda: fb.read(1 << 20), b""):
            h.update(chunk)
    with CSV_PATH.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["FTHome"] == "" or r["FTAway"] == "":
                continue
            d = date.fromisoformat(r["MatchDate"])
            hg, ag = int(float(r["FTHome"])), int(float(r["FTAway"]))
            he = float(r["HomeElo"]) if r["HomeElo"] else None
            ae = float(r["AwayElo"]) if r["AwayElo"] else None
            if d < start:
                if he is not None and ae is not None and r["Division"] in EXT16:
                    elo_fit.append((he, ae, hg, ag))
                continue
            div = r["Division"]
            if div not in leagues:
                continue
            cc = LEAGUE_COUNTRY[div]
            p_mkt = None
            p_o25 = None
            oh = None
            try:
                o = [float(r["OddHome"]), float(r["OddDraw"]), float(r["OddAway"])]
                if all(v > 1 for v in o):
                    pm = devig_proportional(np.array([o]))[0]
                    p_mkt = (float(pm[0]), float(pm[1]), float(pm[2]))
                    oh = o[0]
            except ValueError:
                pass
            try:
                ov, un = float(r["Over25"]), float(r["Under25"])
                if ov > 1 and un > 1:
                    p_o25 = float(devig_proportional(np.array([[ov, un]]))[0][0])
            except ValueError:
                pass
            rows.append(
                DomRow(
                    d,
                    div,
                    season_id_for(div, r["MatchDate"]),
                    ids.get(r["HomeTeam"], cc),
                    ids.get(r["AwayTeam"], cc),
                    hg,
                    ag,
                    p_mkt,
                    p_o25,
                    oh,
                    he,
                    ae,
                )
            )
    rows.sort(key=lambda x: x.date)
    return rows, elo_fit, "sha256:" + h.hexdigest()


def fetch_uefa_files() -> dict[tuple[str, str], str]:
    """Download (once) and return {(comp, season): text}. Missing files are reported, not fatal."""
    import httpx

    UEFA_CACHE.mkdir(parents=True, exist_ok=True)
    out: dict[tuple[str, str], str] = {}
    for comp, seasons in UEFA_FILES.items():
        for s in seasons:
            p = UEFA_CACHE / f"{s}_{comp}.txt"
            if not p.exists():
                url = UEFA_URL.format(season=s, comp=comp)
                try:
                    resp = httpx.get(url, timeout=60, follow_redirects=True)
                except Exception as e:
                    print(f"fetch failed {url}: {e}")
                    continue
                if resp.status_code != 200:
                    print(f"missing {url} ({resp.status_code})")
                    continue
                p.write_text(resp.text, encoding="utf-8")
            out[(comp, s)] = p.read_text(encoding="utf-8")
    return out


_DATE_RE = re.compile(
    r"^\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?\s*$"
)
_MATCH_RE = re.compile(r"^\s+(?:\d{1,2}[:.]\d{2}\s+)?(.+?)\s+v\s+(.+?)\s{2,}(\S.*)$")
_SCORE_RE = re.compile(r"^(\d+)-(\d+)")
_PAREN_RE = re.compile(r"\(([^)]*)\)")
_CC_RE = re.compile(r"^(.*?)\s*\(([A-Z]{3})\)$")


def parse_openfootball(text: str, comp: str, season: str) -> tuple[list[dict], list[str]]:
    """Parse an openfootball league .txt. Returns (matches, warnings). 90-minute scores only:
    for a.e.t. lines the first bracketed pair is the 90-minute result."""
    y0 = int(season[:4])
    stage = ""
    cur: date | None = None
    out: list[dict] = []
    warn: list[str] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith(("▪", "»", "=")):
            if not line.startswith("="):
                stage = line.lstrip("▪» ").strip()
            continue
        m = _DATE_RE.match(line)
        if m:
            mon, day, year = MONTHS[m.group(1)], int(m.group(2)), m.group(3)
            if year:
                cur = date(int(year), mon, day)
            else:
                cands = []
                for y in (y0, y0 + 1):
                    with contextlib.suppress(ValueError):
                        cands.append(date(y, mon, day))
                if cur is None:
                    cur = date(y0 if mon >= 7 else y0 + 1, mon, day)
                else:
                    cur = min(cands, key=lambda c: abs((c - cur).days))
            continue
        m = _MATCH_RE.match(line)
        if not m:
            if " v " in line:
                warn.append(f"unparsed: {line.strip()[:80]}")
            continue
        hn, an, rest = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        if "[cancelled]" in rest or "[awarded]" in rest or "[postponed]" in rest:
            continue
        if cur is None:
            warn.append(f"match before any date: {line.strip()[:80]}")
            continue
        aet = "a.e.t." in rest
        if aet:
            par = _PAREN_RE.search(rest)
            sc = _SCORE_RE.match(par.group(1).split(",")[0].strip()) if par else None
            if sc is None:
                warn.append(f"aet without 90-min score: {line.strip()[:80]}")
                continue
        else:
            sc = _SCORE_RE.match(rest)
            if sc is None:
                continue  # fixture without a result yet
        neutral = stage.split(",")[-1].strip().lower() == "final" or (
            season == "2019-20" and cur >= date(2020, 8, 1)
        )  # one-off finals; 2019-20 final-eight tournaments were played at neutral venues
        out.append(
            {
                "date": cur,
                "comp": comp,
                "season": season,
                "stage": stage,
                "home_name": hn,
                "away_name": an,
                "hg": int(sc.group(1)),
                "ag": int(sc.group(2)),
                "neutral": neutral,
                "aet": aet,
            }
        )
    return out, warn


def map_uefa_names(reg: AliasRegistry, matches: list[dict]) -> tuple[list[UefaMatch], dict]:
    cache: dict[str, str | None] = {}
    unmapped: dict[str, int] = defaultdict(int)
    via_country: set[str] = set()
    via_explicit: set[str] = set()

    def resolve(full: str) -> str | None:
        if full in cache:
            return cache[full]
        m = _CC_RE.match(full)
        base, cc = (m.group(1).strip(), m.group(2)) if m else (full, None)
        tid: str | None = None
        if base in EXPLICIT_UEFA_ALIASES:
            tid = EXPLICIT_UEFA_ALIASES[base]
            via_explicit.add(full)
        else:
            try:
                tid = reg.resolve_team(base, gender=Gender.MEN).team_id
            except AmbiguousAliasError:
                try:
                    tid = reg.resolve_team(base, country=cc, gender=Gender.MEN).team_id
                    via_country.add(full)
                except (AmbiguousAliasError, UnknownAliasError):
                    tid = None
            except UnknownAliasError:
                tid = None
        if tid is None:
            unmapped[full] += 1
        cache[full] = tid
        return tid

    out = [
        UefaMatch(
            m["date"],
            m["comp"],
            m["season"],
            m["stage"],
            m["home_name"],
            m["away_name"],
            resolve(m["home_name"]),
            resolve(m["away_name"]),
            m["hg"],
            m["ag"],
            m["neutral"],
            m["aet"],
        )
        for m in matches
    ]
    report = {
        "distinct_names": len(cache),
        "mapped": sum(1 for v in cache.values() if v),
        "unmapped_names": dict(sorted(unmapped.items(), key=lambda kv: -kv[1])),
        "resolved_via_country_scope": sorted(via_country),
        "resolved_via_explicit_table": sorted(via_explicit),
        "explicit_table": EXPLICIT_UEFA_ALIASES,
    }
    return out, report


# ----------------------------------------------------------------------------------------------
# prediction helpers
# ----------------------------------------------------------------------------------------------
def _dc_sample_rates(post: ParameterPosterior, n: int, rng, home: str, away: str):
    idx = [
        post.idx_attack(home),
        post.idx_defence(home),
        post.idx_attack(away),
        post.idx_defence(away),
        post.idx_home,
        post.idx_rho,
    ]
    mu_ = post.mean[idx]
    cov = post.cov[np.ix_(idx, idx)]
    w, v = np.linalg.eigh(0.5 * (cov + cov.T))
    L = v * np.sqrt(np.clip(w, 1e-12, None))
    z = mu_ + rng.standard_normal((n, len(idx))) @ L.T
    lam = np.exp(z[:, 0] - z[:, 3] + z[:, 4])
    mu = np.exp(z[:, 2] - z[:, 1])
    return lam, mu, np.clip(z[:, 5], -0.3, 0.3)


def _y(hg: int, ag: int) -> int:
    return 0 if hg > ag else (1 if hg == ag else 2)


@dataclass
class VariantSpec:
    name: str
    family: str
    leagues: tuple[str, ...]
    refit_days: int
    config: MultiLeagueConfig
    use_elo: bool = False


def variant_specs(elo_gamma: float) -> dict[str, VariantSpec]:
    return {
        "core": VariantSpec("core", "data_only.multi_league_v1", CORE10, 7, MultiLeagueConfig()),
        "ext": VariantSpec(
            "ext",
            "data_only.multi_league_v1_ext16",
            EXT16,
            14,
            MultiLeagueConfig(version="multi_league_v1_ext16"),
        ),
        "elo": VariantSpec(
            "elo",
            "data_only.multi_league_v1_elo_prior",
            CORE10,
            7,
            MultiLeagueConfig(
                elo_gamma=elo_gamma, elo_league_prior=True, version="multi_league_v1_elo_prior"
            ),
            use_elo=True,
        ),
        "pooled": VariantSpec(
            "pooled",
            "ablation.pooled_no_league_offset",
            EXT16,
            14,
            MultiLeagueConfig(prior_sd_league=0.001, version="ablation_pooled_no_offset"),
        ),
    }


def run_multi_variant(
    spec: VariantSpec,
    dom_all: list[DomRow],
    uefa: list[UefaMatch],
    *,
    snapshot_dates: list[date],
    verbose: bool = True,
) -> dict:
    t0 = time.time()
    rng = np.random.default_rng(0)
    dom = [r for r in dom_all if r.div in spec.leagues]
    fit_rows: list[LeagueMatchRow] = [
        LeagueMatchRow(r.date, r.home, r.away, r.hg, r.ag, r.div) for r in dom
    ]
    fit_dates = [r.date for r in fit_rows]
    dom_by_date: dict[date, list[DomRow]] = defaultdict(list)
    for r in dom:
        dom_by_date[r.date].append(r)
    uefa_by_date: dict[date, list[UefaMatch]] = defaultdict(list)
    for u in uefa:
        if u.home and u.away:
            uefa_by_date[u.date].append(u)
    all_dates = sorted(set(dom_by_date) | {d for d in uefa_by_date if d >= SCORE_START})
    seen: dict[str, int] = defaultdict(int)
    latest_elo: dict[str, float] = {}
    uefa_fit_rows: list[LeagueMatchRow] = []
    post: MultiLeaguePosterior | None = None
    last_fit: date | None = None
    dom_preds: list[dict] = []
    uefa_preds: list[dict] = []
    snapshots: dict[str, dict] = {}
    n_fits = 0
    fit_time = 0.0
    snap_left = sorted(snapshot_dates)
    for d in all_dates:
        need_snapshot = bool(snap_left) and d >= snap_left[0]
        if d >= SCORE_START and (
            last_fit is None or (d - last_fit).days >= spec.refit_days or need_snapshot
        ):
            k = bisect.bisect_left(fit_dates, d)
            rows = fit_rows[:k] + uefa_fit_rows
            if k >= 100:
                tf = time.time()
                post = MultiLeagueFitter(spec.config).fit(
                    rows, as_of=d, elo=latest_elo if spec.use_elo else None
                )
                fit_time += time.time() - tf
                n_fits += 1
                last_fit = d
                if need_snapshot:
                    snapshots[snap_left.pop(0).isoformat()] = _snapshot(post, latest_elo)
        if post is not None and d >= SCORE_START:
            for r in dom_by_date.get(d, []):
                if (
                    r.div in TOP5
                    and r.p_mkt is not None
                    and r.home in post.teams
                    and r.away in post.teams
                    and seen[r.home] >= 5
                    and seen[r.away] >= 5
                ):
                    lam, mu, rho = post.sample_rates(POSTERIOR_SAMPLES, rng, r.home, r.away)
                    p, o25 = integrated_outcome_probs(lam, mu, rho)
                    dom_preds.append(
                        {
                            "key": f"{r.div}|{r.date.isoformat()}|{r.home}|{r.away}",
                            "div": r.div,
                            "season": r.season,
                            "date": r.date.isoformat(),
                            "y": _y(r.hg, r.ag),
                            "total": r.hg + r.ag,
                            "p": [round(float(x), 6) for x in p],
                            "p_o25": round(o25, 6),
                            "p_mkt": list(r.p_mkt),
                            "p_mkt_o25": r.p_mkt_o25,
                            "odds_home": r.odds_home,
                            "home": r.home,
                            "away": r.away,
                        }
                    )
            for u in uefa_by_date.get(d, []):
                if (
                    u.home in post.teams
                    and u.away in post.teams
                    and seen[u.home] >= 5
                    and seen[u.away] >= 5
                    and post.league_of.get(u.home, "_other") != "_other"
                    and post.league_of.get(u.away, "_other") != "_other"
                ):
                    lam, mu, rho = post.sample_rates(
                        POSTERIOR_SAMPLES, rng, u.home, u.away, neutral=u.neutral
                    )
                    p, o25 = integrated_outcome_probs(lam, mu, rho)
                    uefa_preds.append(
                        {
                            "key": f"{u.comp}|{u.date.isoformat()}|{u.home}|{u.away}",
                            "comp": u.comp,
                            "season": u.season,
                            "date": u.date.isoformat(),
                            "y": _y(u.hg, u.ag),
                            "total": u.hg + u.ag,
                            "p": [round(float(x), 6) for x in p],
                            "p_o25": round(o25, 6),
                            "home": u.home,
                            "away": u.away,
                            "home_league": post.league_of[u.home],
                            "away_league": post.league_of[u.away],
                            "neutral": u.neutral,
                            "home_elo": latest_elo.get(u.home),
                            "away_elo": latest_elo.get(u.away),
                        }
                    )
        # roll state forward with today's results
        for r in dom_by_date.get(d, []):
            seen[r.home] += 1
            seen[r.away] += 1
            if r.home_elo is not None:
                latest_elo[r.home] = r.home_elo
            if r.away_elo is not None:
                latest_elo[r.away] = r.away_elo
        for u in uefa_by_date.get(d, []):
            if seen[u.home] > 0 and seen[u.away] > 0:
                uefa_fit_rows.append(
                    LeagueMatchRow(u.date, u.home, u.away, u.hg, u.ag, None, u.neutral)
                )
    if post is not None and snap_left:
        snapshots[post.fitted_through.isoformat()] = _snapshot(post, latest_elo)
    if verbose:
        print(
            f"[{spec.name}] fits={n_fits} fit_time={fit_time:.0f}s total={time.time() - t0:.0f}s "
            f"dom_preds={len(dom_preds)} uefa_preds={len(uefa_preds)} uefa_fit_rows={len(uefa_fit_rows)}"
        )
    return {
        "variant": spec.name,
        "family": spec.family,
        "leagues": list(spec.leagues),
        "refit_days": spec.refit_days,
        "config": asdict(spec.config),
        "n_fits": n_fits,
        "fit_time_s": round(fit_time, 1),
        "elapsed_s": round(time.time() - t0, 1),
        "final_fit": _snapshot(post, latest_elo) if post is not None else None,
        "snapshots": snapshots,
        "dom_preds": dom_preds,
        "uefa_preds": uefa_preds,
    }


def _snapshot(post: MultiLeaguePosterior, latest_elo: dict[str, float]) -> dict:
    offs = post.league_offsets()
    elo_by_league: dict[str, list[float]] = defaultdict(list)
    for t, lg in post.league_of.items():
        if t in latest_elo:
            elo_by_league[lg].append(latest_elo[t])
    ref = "E0" if "E0" in post.leagues else post.leagues[0]
    for lg, o in offs.items():
        o["mean_elo_current_teams"] = (
            round(float(np.mean(elo_by_league[lg])), 1) if elo_by_league[lg] else None
        )
        o["n_teams"] = sum(1 for v in post.league_of.values() if v == lg)
        diff, sd = post.offset_difference(lg, ref)
        o[f"diff_vs_{ref}"] = round(diff, 4)
        o[f"diff_vs_{ref}_sd"] = round(sd, 4)
        o["mean"] = round(o["mean"], 4)
        o["sd"] = round(o["sd"], 4)
        o["cross_play_weight"] = round(o["cross_play_weight"], 2)
    return {
        "as_of": post.fitted_through.isoformat(),
        "n_matches": post.n_matches,
        "n_cross_league": post.n_cross_league,
        "home_advantage": round(float(post.mean[post.idx_home]), 4),
        "rho": round(float(post.mean[post.idx_rho]), 4),
        "offsets": offs,
        "top_teams": {
            lg: [(t, round(v, 3)) for t, v in post.league_table(lg)[:3]] for lg in post.leagues
        },
    }


def run_dc_variant(dom_all: list[DomRow], uefa: list[UefaMatch], *, verbose: bool = True) -> dict:
    """Single-league dc_laplace_v1 recomputed with walk_forward_v1's rules (weekly refit, per
    league, all rows since the burn-in season) for the top-5 leagues; 14-day refits for the other
    leagues, used only by the naive cross-league baseline (league strength ignored)."""
    t0 = time.time()
    rng = np.random.default_rng(0)
    cfg = StrengthConfig()
    by_div: dict[str, list[DomRow]] = defaultdict(list)
    for r in dom_all:
        by_div[r.div].append(r)
    state: dict[str, dict] = {}
    for div, rows in by_div.items():
        state[div] = {
            "mrows": [MatchRow(r.date, r.home, r.away, r.hg, r.ag) for r in rows],
            "dates": [r.date for r in rows],
            "post": None,
            "last_fit": None,
            "seen": defaultdict(int),
            "refit": 7 if div in TOP5 else 14,
        }
    dom_by_date: dict[date, list[DomRow]] = defaultdict(list)
    for r in dom_all:
        dom_by_date[r.date].append(r)
    uefa_by_date: dict[date, list[UefaMatch]] = defaultdict(list)
    for u in uefa:
        if u.home and u.away:
            uefa_by_date[u.date].append(u)
    team_div: dict[str, str] = {}
    all_dates = sorted(set(dom_by_date) | {d for d in uefa_by_date if d >= SCORE_START})
    dom_preds: list[dict] = []
    uefa_preds: list[dict] = []
    n_fits = 0
    for d in all_dates:
        divs_today = {r.div for r in dom_by_date.get(d, [])}
        for div in divs_today:
            st = state[div]
            if d < SCORE_START:
                continue
            if st["last_fit"] is None or (d - st["last_fit"]).days >= st["refit"]:
                k = bisect.bisect_left(st["dates"], d)
                if k >= 100:
                    st["post"] = DixonColesFitter(cfg).fit(st["mrows"][:k], as_of=d)
                    st["last_fit"] = d
                    n_fits += 1
        if d >= SCORE_START:
            for r in dom_by_date.get(d, []):
                st = state[r.div]
                post = st["post"]
                if (
                    r.div in TOP5
                    and post is not None
                    and r.p_mkt is not None
                    and st["seen"][r.home] >= 5
                    and st["seen"][r.away] >= 5
                    and r.home in post.teams
                    and r.away in post.teams
                ):
                    lam, mu, rho = _dc_sample_rates(post, POSTERIOR_SAMPLES, rng, r.home, r.away)
                    p, o25 = integrated_outcome_probs(lam, mu, rho)
                    dom_preds.append(
                        {
                            "key": f"{r.div}|{r.date.isoformat()}|{r.home}|{r.away}",
                            "div": r.div,
                            "season": r.season,
                            "date": r.date.isoformat(),
                            "y": _y(r.hg, r.ag),
                            "total": r.hg + r.ag,
                            "p": [round(float(x), 6) for x in p],
                            "p_o25": round(o25, 6),
                            "p_mkt": list(r.p_mkt),
                            "p_mkt_o25": r.p_mkt_o25,
                            "odds_home": r.odds_home,
                            "home": r.home,
                            "away": r.away,
                        }
                    )
            for u in uefa_by_date.get(d, []):
                dh, da = team_div.get(u.home), team_div.get(u.away)
                if dh is None or da is None:
                    continue
                ph, pa = state[dh]["post"], state[da]["post"]
                if (
                    ph is None
                    or pa is None
                    or u.home not in ph.teams
                    or u.away not in pa.teams
                    or state[dh]["seen"][u.home] < 5
                    or state[da]["seen"][u.away] < 5
                ):
                    continue
                # naive: relative strengths from two separate league fits, league gap ignored
                hadv = 0.0 if u.neutral else 0.5 * (ph.mean[ph.idx_home] + pa.mean[pa.idx_home])
                lam = np.exp(
                    ph.mean[ph.idx_attack(u.home)] - pa.mean[pa.idx_defence(u.away)] + hadv
                )
                mu = np.exp(pa.mean[pa.idx_attack(u.away)] - ph.mean[ph.idx_defence(u.home)])
                rho = 0.5 * (ph.mean[ph.idx_rho] + pa.mean[pa.idx_rho])
                p, o25 = integrated_outcome_probs(np.array([lam]), np.array([mu]), np.array([rho]))
                uefa_preds.append(
                    {
                        "key": f"{u.comp}|{u.date.isoformat()}|{u.home}|{u.away}",
                        "season": u.season,
                        "y": _y(u.hg, u.ag),
                        "p": [round(float(x), 6) for x in p],
                        "home_league": dh,
                        "away_league": da,
                    }
                )
        for r in dom_by_date.get(d, []):
            st = state[r.div]
            st["seen"][r.home] += 1
            st["seen"][r.away] += 1
            team_div[r.home] = r.div
            team_div[r.away] = r.div
    if verbose:
        print(
            f"[dc] fits={n_fits} total={time.time() - t0:.0f}s dom_preds={len(dom_preds)} uefa_preds={len(uefa_preds)}"
        )
    return {
        "variant": "dc",
        "family": "data_only.dc_laplace_v1",
        "leagues": list(by_div),
        "refit_days": 7,
        "config": asdict(cfg),
        "n_fits": n_fits,
        "elapsed_s": round(time.time() - t0, 1),
        "dom_preds": dom_preds,
        "uefa_preds": uefa_preds,
    }


# ----------------------------------------------------------------------------------------------
# UEFA baselines
# ----------------------------------------------------------------------------------------------
def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def fit_multinomial(X: np.ndarray, y: np.ndarray, l2: float = 1e-3) -> np.ndarray:
    """3-class logistic with class 2 (away) as reference. X includes an intercept column."""
    k = X.shape[1]

    def f(theta):
        W = np.column_stack([theta[:k], theta[k:], np.zeros(k)])
        Z = X @ W
        P = _softmax(Z)
        nll = -np.sum(np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1))) + 0.5 * l2 * theta @ theta
        Y = np.zeros_like(P)
        Y[np.arange(len(y)), y] = 1
        G = X.T @ (P - Y)
        return nll, np.concatenate([G[:, 0], G[:, 1]]) + l2 * theta

    res = minimize(f, np.zeros(2 * k), jac=True, method="L-BFGS-B")
    th = res.x
    return np.column_stack([th[:k], th[k:], np.zeros(k)])


def predict_multinomial(W: np.ndarray, X: np.ndarray) -> np.ndarray:
    return _softmax(X @ W)


def uefa_baselines(
    dom_all: list[DomRow], uefa_all: list[UefaMatch], scored_keys: set[str]
) -> dict[str, dict[str, list[float]]]:
    """Base rate (earlier UEFA seasons) and an Elo-difference multinomial logistic fitted on
    matches strictly before each UEFA season (domestic matches of the previous two seasons with
    pre-match Elo + earlier UEFA matches with latest-domestic Elo)."""
    # latest domestic Elo per team, point in time
    dom_sorted = sorted(dom_all, key=lambda r: r.date)
    seasons = sorted({u.season for u in uefa_all})
    out_base: dict[str, list[float]] = {}
    out_elo: dict[str, list[float]] = {}
    uefa_sorted = sorted(uefa_all, key=lambda u: u.date)
    # build per-UEFA-match Elo features chronologically
    latest: dict[str, float] = {}
    di = 0
    feats: dict[str, tuple[float, float]] = {}
    for u in uefa_sorted:
        while di < len(dom_sorted) and dom_sorted[di].date < u.date:
            r = dom_sorted[di]
            if r.home_elo is not None:
                latest[r.home] = r.home_elo
            if r.away_elo is not None:
                latest[r.away] = r.away_elo
            di += 1
        if u.home in latest and u.away in latest:
            feats[u.key] = (latest[u.home] - latest[u.away], 0.0 if u.neutral else 1.0)
    for s in seasons:
        s_start = date(int(s[:4]), 7, 1)
        earlier = [u for u in uefa_all if u.date < s_start]
        counts = np.ones(3)
        for u in earlier:
            counts[_y(u.hg, u.ag)] += 1
        base = counts / counts.sum()
        X_rows, y_rows = [], []
        for r in dom_all:
            if (
                s_start - timedelta(days=730) <= r.date < s_start
                and r.home_elo is not None
                and r.away_elo is not None
            ):
                X_rows.append([1.0, (r.home_elo - r.away_elo) / 100.0, 1.0])
                y_rows.append(_y(r.hg, r.ag))
        for u in earlier:
            if u.key in feats:
                X_rows.append([1.0, feats[u.key][0] / 100.0, feats[u.key][1]])
                y_rows.append(_y(u.hg, u.ag))
        W = fit_multinomial(np.array(X_rows), np.array(y_rows)) if len(y_rows) > 200 else None
        for u in uefa_all:
            if u.season != s or u.key not in scored_keys:
                continue
            out_base[u.key] = [float(x) for x in base]
            if W is not None and u.key in feats:
                p = predict_multinomial(
                    W, np.array([[1.0, feats[u.key][0] / 100.0, feats[u.key][1]]])
                )[0]
                out_elo[u.key] = [float(x) for x in p]
    return {"base_rate": out_base, "elo_logistic": out_elo}


# ----------------------------------------------------------------------------------------------
# assembly / metrics
# ----------------------------------------------------------------------------------------------
def _m3(P: np.ndarray, y: np.ndarray) -> dict:
    return {
        "log_loss": round(multiclass_log_loss(P, y), 5),
        "brier": round(multiclass_brier(P, y), 5),
        "ece_home": round(expected_calibration_error(P[:, 0], (y == 0).astype(int)), 4),
        "n": len(y),
    }


def _paired(Pa: np.ndarray, Pb: np.ndarray, y: np.ndarray) -> dict:
    la = -np.log(np.clip(Pa[np.arange(len(y)), y], 1e-9, 1))
    lb = -np.log(np.clip(Pb[np.arange(len(y)), y], 1e-9, 1))
    diff = la - lb
    ci = bootstrap_mean_ci(diff, n_boot=1000)
    return {
        "mean_diff": round(float(diff.mean()), 5),
        "ci95": [round(ci[0], 5), round(ci[1], 5)],
        "n": len(y),
    }


def _season_start(s: str) -> int:
    return int(s[:4])


def assemble(parts_dir: Path, out_path: Path, pred_csv: Path, meta: dict) -> dict:
    parts = {p.stem: read_json(p) for p in sorted(parts_dir.glob("*.json")) if p.stem != "meta"}
    if "dc" not in parts or "core" not in parts:
        raise SystemExit("need at least the dc and core parts")
    # ---------------- domestic aligned sample ----------------
    dc = {p["key"]: p for p in parts["dc"]["dom_preds"]}
    ml_variants = {k: {p["key"]: p for p in v["dom_preds"]} for k, v in parts.items() if k != "dc"}
    common = set(dc)
    for preds in ml_variants.values():
        common &= set(preds)
    keys = sorted(common, key=lambda k: (dc[k]["date"], k))
    seasons = sorted({dc[k]["season"] for k in keys}, key=_season_start)
    y_all = np.array([dc[k]["y"] for k in keys])
    seas = np.array([dc[k]["season"] for k in keys])
    P_mkt = np.array([dc[k]["p_mkt"] for k in keys])
    fam_raw = {"data_only.dc_laplace_v1": np.array([dc[k]["p"] for k in keys])}
    for k, preds in ml_variants.items():
        fam_raw[parts[k]["family"]] = np.array([preds[kk]["p"] for kk in keys])
    # hybrid weights per season fitted on strictly earlier seasons
    hybrids: dict[str, np.ndarray] = {}
    weights: dict[str, dict[str, float | None]] = {}
    for fam, P in fam_raw.items():
        H = np.full_like(P, np.nan)
        wb: dict[str, float | None] = {}
        for s in seasons:
            prior = np.array([_season_start(x) < _season_start(s) for x in seas])
            cur = seas == s
            if prior.sum() < MIN_PRIOR_FOR_HYBRID:
                wb[s] = None
                continue
            w = fit_blend_weight(P[prior], P_mkt[prior], y_all[prior])
            wb[s] = w
            H[cur] = blend_logit(P[cur], P_mkt[cur], w)
        hybrids[fam] = H
        weights[fam] = wb
    aligned = ~np.isnan(hybrids["data_only.dc_laplace_v1"][:, 0])
    y = y_all[aligned]
    fam = {k: P[aligned] for k, P in fam_raw.items()}
    fam["market_only.bet365_prematch_v1"] = P_mkt[aligned]
    for k, H in hybrids.items():
        fam[f"hybrid[{k}+market]"] = H[aligned]
    divs = np.array([dc[k]["div"] for k in keys])[aligned]
    seas_a = seas[aligned]
    frozen = read_json(REPO / "data" / "research" / "walk_forward_v1.json")
    domestic = {
        "n_aligned": int(aligned.sum()),
        "seasons": sorted(set(seas_a), key=_season_start),
        "overall": {k: _m3(P, y) for k, P in fam.items()},
        "frozen_walk_forward_v1_reference": {
            k: frozen["overall"][k]
            for k in ("data_only.dc_laplace_v1", "market_only.bet365_prematch_v1")
        },
        "hybrid_weight_by_season": weights,
        "by_league": {
            d: {k: _m3(P[divs == d], y[divs == d]) for k, P in fam.items()}
            for d in sorted(set(divs))
        },
        "by_season": {
            s: {k: _m3(P[seas_a == s], y[seas_a == s]) for k, P in fam.items()}
            for s in sorted(set(seas_a), key=_season_start)
        },
        "paired_logloss_diff_ci95": {},
        "over25": {},
    }
    mk = "market_only.bet365_prematch_v1"
    dck = "data_only.dc_laplace_v1"
    for k in fam:
        if k == mk:
            continue
        domestic["paired_logloss_diff_ci95"][f"{k} - market"] = _paired(fam[k], fam[mk], y)
        if k != dck and not k.startswith("hybrid"):
            domestic["paired_logloss_diff_ci95"][f"{k} - dc_laplace_v1"] = _paired(
                fam[k], fam[dck], y
            )
    io = [i for i, k in enumerate(keys) if aligned[i] and dc[k]["p_mkt_o25"] is not None]
    if io:
        yo = np.array([dc[keys[i]]["total"] > 2.5 for i in io]).astype(int)
        pm_ = np.array([dc[keys[i]]["p_mkt_o25"] for i in io])
        domestic["over25"] = {
            "n": len(io),
            "market_only": {
                "log_loss": round(log_loss(pm_, yo), 5),
                "brier": round(brier(pm_, yo), 5),
            },
            "base_rate": round(float(yo.mean()), 4),
        }
        for k, preds in [("dc", dc), *[(kk, vv) for kk, vv in ml_variants.items()]]:
            pd_ = np.array([preds[keys[i]]["p_o25"] for i in io])
            domestic["over25"][parts[k]["family"]] = {
                "log_loss": round(log_loss(pd_, yo), 5),
                "brier": round(brier(pd_, yo), 5),
                "mean_pred": round(float(pd_.mean()), 4),
            }
    # per-match predictions for downstream research (context features)
    pred_csv.parent.mkdir(parents=True, exist_ok=True)
    with pred_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        cols = ["key", "div", "season", "date", "home", "away", "y", "total", "odds_home"]
        cols += ["p_mkt_h", "p_mkt_d", "p_mkt_a", "p_mkt_o25"]
        for k in ["dc", *ml_variants]:
            cols += [f"{k}_h", f"{k}_d", f"{k}_a", f"{k}_o25"]
        w.writerow(cols)
        for i, k in enumerate(keys):
            if not aligned[i]:
                continue
            r = dc[k]
            row = [
                k,
                r["div"],
                r["season"],
                r["date"],
                r["home"],
                r["away"],
                r["y"],
                r["total"],
                r["odds_home"],
            ]
            row += [*r["p_mkt"], r["p_mkt_o25"]]
            row += [*r["p"], r["p_o25"]]
            for kk in ml_variants:
                q = ml_variants[kk][k]
                row += [*q["p"], q["p_o25"]]
            w.writerow(row)
    # ---------------- UEFA out of sample ----------------
    uefa_variants = {k: {p["key"]: p for p in v["uefa_preds"]} for k, v in parts.items()}
    base = meta["uefa_baselines"]
    uefa_out: dict = {"samples": {}}
    for sample_name, members in (
        ("core_teams", ["core", "elo", "ext", "pooled", "dc"]),
        ("ext16_teams", ["ext", "pooled", "dc"]),
    ):
        members = [m for m in members if m in uefa_variants]
        ks = set.intersection(*[set(uefa_variants[m]) for m in members]) & set(base["elo_logistic"])
        ks = sorted(ks)
        if not ks:
            continue
        yy = np.array([uefa_variants[members[0]][k]["y"] for k in ks])
        fams = {
            "baseline.uefa_base_rate": np.array([base["base_rate"][k] for k in ks]),
            "baseline.elo_diff_logistic": np.array([base["elo_logistic"][k] for k in ks]),
        }
        for m in members:
            fams[parts[m]["family"] if m != "dc" else "baseline.naive_single_league_dc"] = np.array(
                [uefa_variants[m][k]["p"] for k in ks]
            )
        ref = uefa_variants[members[0]]
        comps = np.array([k.split("|")[0] for k in ks])
        seasons_u = np.array([ref[k]["season"] for k in ks])
        cross = np.array([ref[k]["home_league"] != ref[k]["away_league"] for k in ks])
        neutral = np.array([bool(ref[k].get("neutral", False)) for k in ks])
        entry = {
            "n": len(ks),
            "n_cross_league": int(cross.sum()),
            "n_neutral": int(neutral.sum()),
            "outcome_rates": [round(float((yy == c).mean()), 4) for c in (0, 1, 2)],
            "overall": {k: _m3(P, yy) for k, P in fams.items()},
            "cross_league_only": {k: _m3(P[cross], yy[cross]) for k, P in fams.items()},
            "by_competition": {
                c: {k: _m3(P[comps == c], yy[comps == c]) for k, P in fams.items()}
                for c in sorted(set(comps))
            },
            "by_season": {
                s: {k: _m3(P[seasons_u == s], yy[seasons_u == s]) for k, P in fams.items()}
                for s in sorted(set(seasons_u))
            },
            "paired_logloss_diff_ci95": {},
        }
        for k, Pk in fams.items():
            if k.startswith("baseline"):
                continue
            for b in ("baseline.elo_diff_logistic", "baseline.naive_single_league_dc"):
                if b in fams:
                    entry["paired_logloss_diff_ci95"][f"{k} - {b}"] = _paired(Pk, fams[b], yy)
        uefa_out["samples"][sample_name] = entry
    # ---------------- offsets ----------------
    offsets = {
        k: {"final_fit": v.get("final_fit"), "snapshots": v.get("snapshots", {})}
        for k, v in parts.items()
        if k != "dc"
    }
    # offsets vs mean Elo (final fit, core and ext variants)
    elo_cmp = {}
    for k in ("core", "ext", "elo"):
        if k not in parts or not parts[k].get("final_fit"):
            continue
        offs = parts[k]["final_fit"]["offsets"]
        xs = [
            (o["mean_elo_current_teams"], o["mean"], lg)
            for lg, o in offs.items()
            if o["mean_elo_current_teams"]
        ]
        if len(xs) >= 3:
            e = np.array([x[0] for x in xs])
            L = np.array([x[1] for x in xs])
            slope = float(np.polyfit(e, L, 1)[0])
            elo_cmp[k] = {
                "n_leagues": len(xs),
                "corr_offset_vs_mean_elo": round(float(np.corrcoef(e, L)[0, 1]), 4),
                "slope_offset_per_elo_point": round(slope, 6),
                "elo_mapping_gamma_from_pre_window_fit": meta["elo_mapping"][
                    "poisson_gamma_log_rate_per_elo_point"
                ],
                "note": "offset applies to attack and defence, so a league-mean total-strength gap "
                "of 2*dL corresponds to an Elo gap of 2*dL/(2*gamma)=dL/gamma points",
                "implied_elo_gap_vs_E0": {
                    lg: round(
                        o["diff_vs_E0"]
                        / meta["elo_mapping"]["poisson_gamma_log_rate_per_elo_point"],
                        0,
                    )
                    for lg, o in offs.items()
                    if "diff_vs_E0" in o
                },
            }
    out = {
        "protocol": PROTOCOL_VERSION,
        "status": "RESEARCH_ONLY",
        "generated_from": meta,
        "variants": {
            k: {
                kk: vv
                for kk, vv in v.items()
                if kk not in ("dom_preds", "uefa_preds", "snapshots", "final_fit")
            }
            for k, v in parts.items()
        },
        "domestic_aligned": domestic,
        "uefa_out_of_sample": uefa_out,
        "league_offsets": offsets,
        "offsets_vs_club_elo": elo_cmp,
        "elapsed_s_by_variant": {k: v["elapsed_s"] for k, v in parts.items()},
    }
    out["result_hash"] = content_hash({k: v for k, v in out.items() if k != "elapsed_s_by_variant"})
    write_json(out_path, out)
    return out


# ----------------------------------------------------------------------------------------------
def _uefa_key(u: UefaMatch) -> str:
    return f"{u.comp}|{u.date.isoformat()}|{u.home}|{u.away}"


UefaMatch.key = property(_uefa_key)  # type: ignore[attr-defined]


def load_registry(directory: Path = REPO / "data" / "registry") -> AliasRegistry:
    """AliasRegistry.from_directory, restricted to files that follow the seed.json schema
    (a `teams` list of team records). Other JSON files that may live in the directory (e.g.
    provider lookup tables produced by other work) are skipped and reported."""
    from soccer_edge.identity.models import Competition, Player, Team

    reg = AliasRegistry()
    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        teams = payload.get("teams", [])
        if not isinstance(teams, list) or not all(
            isinstance(t, dict) and "team_id" in t for t in teams
        ):
            print(f"registry: skipping {path.name} (not a team registry file)")
            continue
        for c in payload.get("competitions", []):
            reg.add_competition(Competition(**c))
        for t in teams:
            reg.add_team(Team(**t))
        for p in payload.get("players", []):
            reg.add_player(Player(**p))
    return reg


def prepare(verbose: bool = True):
    reg = load_registry()
    amb = reg.ambiguous_team_aliases()
    assert not amb, f"ambiguous aliases in registry: {amb}"
    ids = TeamIds(reg)
    dom, elo_fit, csv_hash = load_domestic(ids, EXT16, FIRST_FIT_DATA)
    files = fetch_uefa_files()
    raw: list[dict] = []
    warnings: dict[str, list[str]] = {}
    file_hashes = {}
    for (comp, s), text in sorted(files.items()):
        ms, w = parse_openfootball(text, comp, s)
        raw.extend(ms)
        if w:
            warnings[f"{s}/{comp}"] = w
        file_hashes[f"{s}/{comp}.txt"] = hashlib.sha256(text.encode()).hexdigest()[:16]
    uefa, name_report = map_uefa_names(reg, raw)
    ef = np.array(elo_fit)
    elo_map = fit_elo_mapping(ef[:, 0], ef[:, 1], ef[:, 2], ef[:, 3])
    meta = {
        "csv_content_hash": csv_hash,
        "n_domestic_rows": len(dom),
        "n_provisional_ids": len(ids.provisional),
        "uefa_files": sorted(file_hashes),
        "uefa_file_hashes": file_hashes,
        "n_uefa_matches_parsed": len(uefa),
        "n_uefa_matches_both_mapped": sum(1 for u in uefa if u.home and u.away),
        "uefa_parse_warnings": warnings,
        "uefa_name_mapping": name_report,
        "elo_mapping": elo_map,
        "elo_mapping_note": "fitted on all EXT16-league matches with pre-match ClubElo dated before "
        + FIRST_FIT_DATA.isoformat()
        + " (outside every evaluation window)",
    }
    if verbose:
        print(
            f"domestic rows={len(dom)} provisional ids={len(ids.provisional)} uefa parsed={len(uefa)} "
            f"both mapped={meta['n_uefa_matches_both_mapped']} unmapped names={len(name_report['unmapped_names'])}"
        )
        print("elo mapping:", json.dumps(elo_map))
    return dom, uefa, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "assemble", "prepare"])
    ap.add_argument("--variant", default="core")
    ap.add_argument("--parts", default=str(PARTS_DIR))
    ap.add_argument("--out", default=str(OUT_JSON))
    a = ap.parse_args()
    parts = Path(a.parts)
    parts.mkdir(parents=True, exist_ok=True)
    if a.cmd == "prepare":
        dom, uefa, meta = prepare()
        write_json(parts / "meta.json", meta)
        return 0
    if a.cmd == "run":
        dom, uefa, meta = prepare(verbose=False)
        snaps = [date(y, 6, 1) for y in range(2019, 2027)]
        if a.variant == "dc":
            res = run_dc_variant(dom, uefa)
        else:
            spec = variant_specs(meta["elo_mapping"]["poisson_gamma_log_rate_per_elo_point"])[
                a.variant
            ]
            res = run_multi_variant(spec, dom, uefa, snapshot_dates=snaps)
        write_json(parts / f"{a.variant}.json", res)
        return 0
    dom, uefa, meta = prepare()
    scored = set()
    for p in parts.glob("*.json"):
        if p.stem == "meta":
            continue
        scored |= {x["key"] for x in read_json(p).get("uefa_preds", [])}
    meta["uefa_baselines"] = uefa_baselines(dom, uefa, scored)
    res = assemble(parts, Path(a.out), PRED_CSV, meta)
    print(json.dumps(res["domestic_aligned"]["overall"], indent=1))
    print(
        json.dumps(
            {k: v["overall"] for k, v in res["uefa_out_of_sample"]["samples"].items()}, indent=1
        )
    )
    print("result_hash", res["result_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
