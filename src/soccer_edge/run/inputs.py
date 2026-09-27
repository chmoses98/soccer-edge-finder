"""Assemble RunInputs from providers + a Kalshi discovery (live or synthetic)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from soccer_edge.authority.policy import AuthorityMatrix
from soccer_edge.core.time import utc_now
from soccer_edge.identity.models import Fixture
from soccer_edge.identity.registry import AliasRegistry
from soccer_edge.kalshi.discovery import DiscoveryRun
from soccer_edge.providers.club_football_data import ClubFootballDataProvider
from soccer_edge.providers.http import CachedFetcher
from soccer_edge.providers.interfaces import MatchResult
from soccer_edge.providers.openfootball import COMPETITION_FILES, OpenFootballProvider
from soccer_edge.run.modeling import CompetitionModel, fit_competition
from soccer_edge.run.pipeline import RunInputs

DEFAULT_COMPETITIONS = (
    "eng.premier_league",
    "esp.la_liga",
    "ger.bundesliga",
    "ita.serie_a",
    "fra.ligue_1",
)
DIVISION_FOR = {
    "eng.premier_league": "E0",
    "eng.championship": "E1",
    "esp.la_liga": "SP1",
    "ger.bundesliga": "D1",
    "ita.serie_a": "I1",
    "fra.ligue_1": "F1",
}


def current_season_id(comp: str, today: date) -> str:
    start = today.year if today.month >= 7 else today.year - 1
    return f"{start}-{str(start + 1)[2:]}"


@dataclass
class AssembledData:
    fixtures: list[Fixture]
    fixtures_observed_at: datetime
    results: dict[str, list[MatchResult]]
    results_observed_at: datetime
    models: dict[str, CompetitionModel]
    notes: list[str]


def assemble(
    registry: AliasRegistry,
    *,
    competitions: tuple[str, ...] = DEFAULT_COMPETITIONS,
    today: date | None = None,
    fetcher: CachedFetcher | None = None,
    historical_content: bytes | None = None,
    seasons_back: int = 2,
) -> AssembledData:
    today = today or utc_now().date()
    fetcher = fetcher or CachedFetcher()
    of = OpenFootballProvider(registry, fetcher)
    hist = ClubFootballDataProvider(registry, fetcher)
    fixtures: list[Fixture] = []
    results: dict[str, list[MatchResult]] = {}
    notes: list[str] = []
    fx_obs: datetime | None = None
    res_obs: datetime | None = None

    # historical results (multi-season) from the GitHub redistribution of football-data.co.uk
    divisions = [DIVISION_FOR[c] for c in competitions if c in DIVISION_FOR]
    start = (today - timedelta(days=365 * seasons_back + 60)).isoformat()
    try:
        h = hist.load(divisions=divisions, start_date=start, content=historical_content)
        res_obs = h.provenance.observed_at
        for hm in h.payload:
            results.setdefault(hm.result.competition_id, []).append(hm.result)
        notes.append(
            f"historical: {len(h.payload)} matches from {hist.provider_id}; flags={[f.value for f in h.flags]}"
        )
    except Exception as exc:
        notes.append(f"historical provider failed: {exc}")

    season = None
    for comp in competitions:
        if comp not in COMPETITION_FILES:
            notes.append(f"{comp}: no openfootball file")
            continue
        season = current_season_id(comp, today)
        try:
            fx = of.fixtures(comp, season)
        except Exception as exc:
            notes.append(f"{comp} {season}: openfootball fixtures unavailable ({str(exc)[:80]})")
            continue
        fixtures.extend(fx.payload)
        fx_obs = max(fx_obs, fx.provenance.observed_at) if fx_obs else fx.provenance.observed_at
        # merge current-season results from openfootball (fresher than the CSV redistribution)
        try:
            rs = of.results(comp, season)
            known = {(r.match_date, r.home_team_id, r.away_team_id) for r in results.get(comp, [])}
            added = 0
            for r in rs.payload:
                if (r.match_date, r.home_team_id, r.away_team_id) not in known:
                    results.setdefault(comp, []).append(r)
                    added += 1
            notes.append(
                f"{comp} {season}: {len(fx.payload)} fixtures, {len(rs.payload)} results ({added} new vs historical)"
            )
        except Exception as exc:
            notes.append(f"{comp} {season}: openfootball results unavailable ({str(exc)[:80]})")

    models: dict[str, CompetitionModel] = {}
    for comp in competitions:
        rs = results.get(comp, [])
        if len(rs) < 50:
            notes.append(f"{comp}: insufficient results to fit ({len(rs)})")
            continue
        comp_fx = [f for f in fixtures if f.competition_id == comp]
        models[comp] = fit_competition(comp, rs, as_of=today, fixtures=comp_fx)
        if models[comp].teams_missing:
            notes.append(f"{comp}: teams without history {models[comp].teams_missing}")
    return AssembledData(
        fixtures, fx_obs or utc_now(), results, res_obs or utc_now(), models, notes
    )


def build_inputs(
    registry: AliasRegistry,
    data: AssembledData,
    discovery: DiscoveryRun,
    *,
    as_of: datetime,
    authority_path: Path | None = None,
) -> RunInputs:
    return RunInputs(
        registry=registry,
        fixtures=data.fixtures,
        fixtures_observed_at=data.fixtures_observed_at,
        models=data.models,
        results_observed_at=data.results_observed_at,
        discovery=discovery,
        market_observed_at=discovery.finished_at or as_of,
        authority=AuthorityMatrix.load(authority_path) if authority_path else AuthorityMatrix(),
        as_of=as_of,
    )
