"""RUN SOCCER pipeline: discovery -> association -> (re)simulation -> pricing -> edge -> expression
-> authority -> archive -> coverage proof -> versioned output. No bets is a first-class result."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np

from soccer_edge.archive.ledger import PredictionLedger
from soccer_edge.authority.policy import Authority, AuthorityKey, AuthorityMatrix
from soccer_edge.contracts.v1 import CoverageReportV1, EventV1, RecommendationV1, RunOutputV1
from soccer_edge.core.serialization import content_hash
from soccer_edge.core.time import ensure_utc, iso_utc, minutes_until, utc_now
from soccer_edge.identity.models import Fixture, FixtureStatus
from soccer_edge.identity.registry import AliasRegistry
from soccer_edge.kalshi.association import Association, associate, index_fixtures
from soccer_edge.kalshi.capture import label_horizon
from soccer_edge.kalshi.coverage import CoverageLedger, Disposition
from soccer_edge.kalshi.discovery import DiscoveryRun
from soccer_edge.kalshi.executable import top_of_book
from soccer_edge.kalshi.fees import FEE_SCHEDULE_VERSION, FeeRegime
from soccer_edge.kalshi.schemas import Ownership, RawMarket
from soccer_edge.kalshi.taxonomy import ContractSpec, MarketFamily, Scope
from soccer_edge.model.context import LineupState, MatchContext
from soccer_edge.model.worlds import WorldConfig, WorldGenerator
from soccer_edge.pricing.coherence import audit as coherence_audit
from soccer_edge.pricing.edge import EdgeAssessment, EdgeConfig, assess
from soccer_edge.pricing.expression import Candidate, payoff_vector, reduce_expressions
from soccer_edge.pricing.pricer import PricedProbability, price
from soccer_edge.pricing.semantics import Semantics, UnsupportedSemantics, resolve_semantics
from soccer_edge.run.freshness import FreshnessPolicy, FreshnessReport
from soccer_edge.run.modeling import CompetitionModel
from soccer_edge.run.simcache import (
    CachedFixtureSim,
    SimCache,
    compact,
    expand_world_probs,
    sim_key,
)
from soccer_edge.sim.engine import SimConfig, simulate

MODEL_FAMILY_ID = "data_only.world_sim_v1"


@dataclass(frozen=True)
class RunConfig:
    run_date: date
    window_hours: int = 48
    leagues: tuple[str, ...] = ()
    games: tuple[str, ...] = ()
    confirmed_lineups_only: bool = False
    n_worlds: int = 1000
    draws_per_world: int = 100
    seed: int = 20260927
    interval_level: float = 0.80
    edge: EdgeConfig = field(default_factory=EdgeConfig)
    world: WorldConfig = field(default_factory=WorldConfig)
    freshness: FreshnessPolicy = field(default_factory=FreshnessPolicy)
    enforce_freshness: bool = True


@dataclass
class RunInputs:
    registry: AliasRegistry
    fixtures: list[Fixture]
    fixtures_observed_at: datetime
    models: dict[str, CompetitionModel]  # competition_id -> fitted posterior
    results_observed_at: datetime
    discovery: DiscoveryRun
    market_observed_at: datetime
    authority: AuthorityMatrix
    as_of: datetime
    lineup_contexts: dict[str, MatchContext] = field(
        default_factory=dict
    )  # optional richer contexts


@dataclass
class ContractWork:
    market: RawMarket
    spec: ContractSpec
    assoc: Association | None = None
    fixture: Fixture | None = None
    sem: Semantics | None = None
    priced: PricedProbability | None = None
    yes: EdgeAssessment | None = None
    no: EdgeAssessment | None = None
    regime: FeeRegime | None = None
    indicator: np.ndarray | None = None


@dataclass
class RunArtifacts:
    output: RunOutputV1
    markdown: str
    coverage: CoverageLedger
    per_contract: list[dict[str, Any]]
    fixtures_simulated: list[str]
    fixtures_repriced: list[str]
    prediction_record_ids: list[str]


def _kickoff(f: Fixture) -> datetime:
    return f.kickoff_utc or datetime.fromisoformat(f.kickoff_date + "T12:00:00+00:00")


def run(
    inputs: RunInputs,
    cfg: RunConfig,
    *,
    ledger: PredictionLedger | None = None,
    sim_cache: SimCache | None = None,
) -> RunArtifacts:
    as_of = ensure_utc(inputs.as_of)
    run_id = f"run-{as_of:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"
    warnings: list[str] = []
    disc = inputs.discovery
    cov = CoverageLedger()
    cov.discover(list(disc.markets))

    fresh = FreshnessReport(
        as_of,
        inputs.market_observed_at,
        inputs.fixtures_observed_at,
        inputs.results_observed_at,
        min((m.fitted_at for m in inputs.models.values()), default=None),
        cfg.freshness,
    )
    if cfg.enforce_freshness:
        fresh.require()
    else:
        warnings.extend(f"freshness: {v}" for v in fresh.violations())
    if not disc.complete:
        warnings.append("DISCOVERY INCOMPLETE: catalog cannot be trusted; nothing is recommended")

    series_by_ticker = {t: r for t, r in disc.series_records.items()}
    fx_index = index_fixtures(inputs.fixtures)
    window_end = as_of + timedelta(hours=cfg.window_hours)
    works: dict[str, ContractWork] = {}

    # ---- mechanical dispositions ------------------------------------------------------------
    for tk, m in disc.markets.items():
        spec = disc.specs[tk]
        w = ContractWork(m, spec)
        works[tk] = w
        srec = series_by_ticker.get(m.series_ticker or "")
        if srec is not None and srec.ownership is Ownership.AMBIGUOUS:
            cov.set(tk, Disposition.AMBIGUOUS_OWNERSHIP, srec.ownership_reason)
            continue
        if m.status.lower() in ("closed", "finalized", "settled", "determined"):
            cov.set(tk, Disposition.CLOSED, f"status={m.status}")
            continue
        if spec.family is MarketFamily.UNKNOWN:
            cov.set(tk, Disposition.UNKNOWN_FAMILY, spec.rationale)
            continue
        if spec.scope is Scope.COMPETITION:
            cov.set(
                tk,
                Disposition.UNSUPPORTED_FAMILY,
                f"{spec.family.value}: competition futures not modelled in v1",
            )
            continue
        if not spec.is_priceable_family:
            cov.set(tk, Disposition.UNSUPPORTED_FAMILY, f"{spec.family.value}: no pricer")
            continue
        if spec.competition_id and cfg.leagues and spec.competition_id not in cfg.leagues:
            cov.set(
                tk, Disposition.FILTERED_BY_OPERATOR, f"--league excludes {spec.competition_id}"
            )
            continue
        assoc = associate(spec, disc.events.get(m.event_ticker), inputs.registry, fx_index)
        w.assoc = assoc
        if assoc.status != "mapped":
            disp = {
                "unmapped_event": Disposition.UNMAPPED_EVENT,
                "unmapped_team": Disposition.UNMAPPED_TEAM,
                "ambiguous_team": Disposition.UNMAPPED_TEAM,
                "no_fixture": Disposition.NO_FIXTURE,
                "competition_only": Disposition.UNSUPPORTED_FAMILY,
                "not_match_scope": Disposition.UNSUPPORTED_FAMILY,
            }[assoc.status]
            cov.set(tk, disp, assoc.detail)
            continue
        fx = next(
            f
            for f in fx_index[(assoc.home_team_id, assoc.away_team_id)]
            if f.fixture_id == assoc.fixture_id
        )
        w.fixture = fx
        ko = _kickoff(fx)
        if cfg.games and not any(
            g in fx.fixture_id or g in f"{fx.home_team_id}-{fx.away_team_id}" for g in cfg.games
        ):
            cov.set(tk, Disposition.FILTERED_BY_OPERATOR, "--game filter")
            continue
        if ko <= as_of or fx.status in (FixtureStatus.LIVE, FixtureStatus.FINISHED):
            cov.set(tk, Disposition.STARTED, f"kickoff {iso_utc(ko)} <= as_of")
            continue
        if fx.status in (
            FixtureStatus.POSTPONED,
            FixtureStatus.CANCELLED,
            FixtureStatus.ABANDONED,
            FixtureStatus.RESCHEDULED,
        ):
            cov.set(tk, Disposition.NO_FIXTURE, f"fixture status {fx.status.value}")
            continue
        if ko > window_end:
            cov.set(tk, Disposition.OUT_OF_WINDOW, f"kickoff {iso_utc(ko)} beyond window")
            continue
        if fx.competition_id not in inputs.models:
            cov.set(tk, Disposition.NO_MODEL, f"no fitted model for {fx.competition_id}")
            continue
        if spec.family is MarketFamily.PLAYER_GOALS:
            ctx0 = inputs.lineup_contexts.get(fx.fixture_id)
            if ctx0 is None or not (ctx0.home_players or ctx0.away_players):
                cov.set(
                    tk,
                    Disposition.UNSUPPORTED_FAMILY,
                    "player_goals: player/lineup layer is RESEARCH_ONLY and no lineup provider is wired",
                )
                continue
        if srec is None or srec.series.fee_type is None:
            cov.set(tk, Disposition.FEE_UNVERIFIED, "series fee_type missing")
            continue
        regime = FeeRegime(srec.series.fee_type, srec.series.fee_multiplier or Decimal(1))
        try:
            regime.verify()
        except Exception as exc:
            cov.set(tk, Disposition.FEE_UNVERIFIED, str(exc)[:120])
            continue
        w.regime = regime
        ctx_l = inputs.lineup_contexts.get(fx.fixture_id)
        if cfg.confirmed_lineups_only and (
            ctx_l is None or ctx_l.lineup_state is not LineupState.CONFIRMED
        ):
            cov.set(tk, Disposition.FILTERED_BY_OPERATOR, "--confirmed-lineups-only")
            continue
        yq, nq = top_of_book(m, "yes"), top_of_book(m, "no")
        if not yq.is_quote and not nq.is_quote:
            cov.set(tk, Disposition.NO_QUOTE, "no executable quote on either side")
            continue

    # ---- simulation / repricing per fixture -----------------------------------------------------
    pending = [w for tk, w in works.items() if tk not in cov.dispositions]
    by_fx: dict[str, list[ContractWork]] = {}
    for w in pending:
        by_fx.setdefault(w.fixture.fixture_id, []).append(w)  # type: ignore[union-attr]
    simulated: list[str] = []
    repriced: list[str] = []
    fixture_summaries: dict[str, dict[str, Any]] = {}
    fixture_ctx: dict[str, MatchContext] = {}
    sim_cfg = SimConfig(draws_per_world=cfg.draws_per_world)

    for fid, ws in by_fx.items():
        fx = ws[0].fixture
        assert fx is not None
        cm = inputs.models[fx.competition_id]
        base_ctx = inputs.lineup_contexts.get(fid) or MatchContext(
            fid,
            fx.competition_id,
            fx.home_team_id,
            fx.away_team_id,
            fx.kickoff_utc,
            neutral_site=fx.neutral_site,
            requires_winner=bool(fx.penalties_possible),
        )
        fixture_ctx[fid] = base_ctx
        missing = [t for t in (fx.home_team_id, fx.away_team_id) if t not in cm.posterior.teams]
        if missing:
            for w in ws:
                cov.set(
                    w.market.ticker,
                    Disposition.NO_MODEL,
                    f"team(s) {missing} not in fitted posterior",
                )
            continue
        # resolve semantics first (so the cache key covers the exact contract set)
        for w in ws:
            side_home = None
            if w.assoc and w.assoc.side_team_id:
                side_home = w.assoc.side_team_id == fx.home_team_id
            elif w.spec.side_team_code and w.spec.side_team_code != "DRAW":
                # fall back: soccer event codes are HOME then AWAY (verified live)
                tc = w.spec.team_codes or ""
                code = w.spec.side_team_code
                if tc.startswith(code) and not tc.endswith(code):
                    side_home = True
                elif tc.endswith(code) and not tc.startswith(code):
                    side_home = False
            try:
                if w.spec.family is MarketFamily.FIRST_TO_SCORE and base_ctx.requires_winner:
                    raise UnsupportedSemantics(
                        f"{w.market.ticker}: first-to-score including extra time is not simulated for knockout legs"
                    )
                w.sem = resolve_semantics(w.spec, side_is_home=side_home)
            except UnsupportedSemantics as exc:
                cov.set(w.market.ticker, Disposition.UNPRICEABLE, str(exc)[:160])
        ws = [w for w in ws if w.sem is not None]
        if not ws:
            continue
        ctx_json = {
            "fixture": fid,
            "home": fx.home_team_id,
            "away": fx.away_team_id,
            "neutral": base_ctx.neutral_site,
            "requires_winner": base_ctx.requires_winner,
            "lineup_state": base_ctx.lineup_state.value,
            "players": [p.player_id for p in (*base_ctx.home_players, *base_ctx.away_players)],
        }
        key = sim_key(
            posterior_hash=cm.posterior.param_hash(),
            world_cfg=cfg.world.__dict__,
            sim_cfg=sim_cfg.__dict__,
            context=ctx_json,
            seed=cfg.seed,
        )
        tickers = [w.market.ticker for w in ws]
        cached = sim_cache.load(fid) if sim_cache else None
        if cached and cached.sim_key == key and cached.has(tickers):
            repriced.append(fid)
            fixture_summaries[fid] = cached.summary
            for w in ws:
                c = cached.contracts[w.market.ticker]
                w.priced = PricedProbability(
                    w.market.ticker,
                    c["fair_probability_mean"],
                    c["fair_probability_median"],
                    c["fair_probability_low"],
                    c["fair_probability_high"],
                    c["interval_level"],
                    c["parameter_sd"],
                    c["mc_standard_error"],
                    c["n_worlds"],
                    c["n_draws"],
                    c["effective_draws"],
                    expand_world_probs(c),
                    c["description"],
                )
            continue
        rng = np.random.default_rng(cfg.seed ^ (int(content_hash(fid).split(":")[1][:8], 16)))
        worlds = WorldGenerator(cm.posterior, cfg.world).generate(base_ctx, cfg.n_worlds, rng)
        out = simulate(worlds, base_ctx, sim_cfg, seed=int(rng.integers(0, 2**31 - 1)))
        simulated.append(fid)
        summ = out.compact_summary()
        summ["worlds"] = worlds.summary()
        fixture_summaries[fid] = summ
        priced_pairs: list[tuple[Semantics, PricedProbability]] = []
        for w in ws:
            try:
                w.indicator = w.sem.settle(out)  # type: ignore[union-attr]
                w.priced = price(w.sem, out, interval_level=cfg.interval_level)  # type: ignore[arg-type]
                priced_pairs.append((w.sem, w.priced))  # type: ignore[arg-type]
            except UnsupportedSemantics as exc:
                cov.set(w.market.ticker, Disposition.UNPRICEABLE, str(exc)[:160])
        problems = coherence_audit(priced_pairs)
        if problems:
            for w in ws:
                if w.priced is not None and w.market.ticker not in cov.dispositions:
                    cov.set(
                        w.market.ticker,
                        Disposition.UNPRICEABLE,
                        f"coherence audit failed: {problems[0][:120]}",
                    )
            warnings.append(f"coherence failure on {fid}: {problems[0]}")
            continue
        if sim_cache:
            sim_cache.save(
                CachedFixtureSim(
                    key,
                    fid,
                    out.outcome_hash(),
                    summ,
                    {w.market.ticker: compact(w.priced) for w in ws if w.priced is not None},
                )
            )

    # ---- edge, expression, authority --------------------------------------------------------------
    candidates: list[Candidate] = []
    per_contract: list[dict[str, Any]] = []
    for tk, w in works.items():
        if w.priced is None or tk in cov.dispositions:
            continue
        assert w.regime is not None and w.fixture is not None
        yq, nq = top_of_book(w.market, "yes"), top_of_book(w.market, "no")
        if yq.is_quote:
            w.yes = assess(w.priced, yq, w.regime, cfg.edge)
        if nq.is_quote:
            w.no = assess(w.priced, nq, w.regime, cfg.edge)
        cov.set(tk, Disposition.PRICED, "priced and evaluated")
        for a in (w.yes, w.no):
            if a is None:
                continue
            ind = w.indicator
            if (
                ind is None
            ):  # repriced from cache: approximate payoff from world probs (no draw-level corr)
                ind = (
                    np.random.default_rng(0).random(len(w.priced.world_probs))
                    < w.priced.world_probs
                )
            payoff = payoff_vector(ind, a.side, float(a.price), float(a.fee_per_contract))
            if a.robust_positive_ev:
                candidates.append(
                    Candidate(
                        w.fixture.fixture_id,
                        a,
                        payoff,
                        liquidity=float((yq if a.side == "yes" else nq).size or 0),
                        thesis=_thesis(
                            w, fixture_summaries.get(w.fixture.fixture_id, {}), inputs.registry
                        ),
                    )
                )
        per_contract.append(
            _contract_record(
                w, run_id, as_of, inputs, fixture_summaries.get(w.fixture.fixture_id, {})
            )
        )

    reduced = reduce_expressions(candidates)
    recs: list[RecommendationV1] = []
    shadow: list[RecommendationV1] = []
    removed_keys = {f"{c.assessment.ticker}|{c.assessment.side}": r for c, r in reduced.removed}
    for c in reduced.kept:
        w = works[c.assessment.ticker]
        fx = w.fixture
        assert fx is not None and w.priced is not None and w.regime is not None
        ko = _kickoff(fx)
        horizon = label_horizon(minutes_until(ko, as_of)).value
        akey = AuthorityKey(MODEL_FAMILY_ID, w.spec.family.value, horizon)
        state = inputs.authority.get(akey)
        ctx = fixture_ctx.get(fx.fixture_id)
        rec = RecommendationV1(
            recommendation_id=f"rec_{content_hash({'run': run_id, 't': c.assessment.ticker, 's': c.assessment.side}).split(':')[1][:20]}",
            sport="soccer",
            league=fx.competition_id,
            event_id=fx.fixture_id,
            event_name=_event_name(fx, inputs.registry),
            start_time=ko,
            market_ticker=c.assessment.ticker,
            market_family=w.spec.family.value,
            market_description=w.priced.description or w.market.title,
            side=c.assessment.side,  # type: ignore[arg-type]
            current_price=c.assessment.price,
            available_size=Decimal(str(c.liquidity)) if c.liquidity else None,
            fair_probability=c.assessment.fair,
            fair_probability_low=c.assessment.fair_low,
            fair_probability_high=c.assessment.fair_high,
            probability_edge_positive=c.assessment.p_edge_positive,
            fee_adjusted_edge=c.assessment.fee_adjusted_edge,
            worst_case_edge=c.assessment.worst_case_edge,
            bet_up_to_price=c.assessment.bet_up_to_price,
            authority=state.value,  # type: ignore[arg-type]
            confidence_label=_confidence_label(state, c.assessment),
            model_family=MODEL_FAMILY_ID,
            model_version=inputs.models[fx.competition_id].posterior.version,
            data_as_of=inputs.results_observed_at,
            market_as_of=inputs.market_observed_at,
            model_as_of=inputs.models[fx.competition_id].fitted_at,
            lineup_status=(ctx.lineup_state.value if ctx else "unknown"),  # type: ignore[arg-type]
            coverage_status="complete" if disc.complete else "incomplete",
            thesis=c.thesis,
            risks=_risks(w, state, ctx, disc.complete),
            correlation_group=f"{fx.fixture_id}#g{reduced.groups.get(f'{c.assessment.ticker}|{c.assessment.side}', 0)}",
            fee_schedule_version=FEE_SCHEDULE_VERSION,
        )
        if state in (Authority.LIMITED, Authority.TRUSTED) and disc.complete:
            recs.append(rec)
        else:
            shadow.append(rec)

    # ---- archive ----------------------------------------------------------------------------------
    record_ids: list[str] = []
    if ledger is not None:
        rec_by_ticker_side = {(r.market_ticker, r.side): r for r in (*recs, *shadow)}
        for rec_d in per_contract:
            for side in ("yes", "no"):
                r = rec_by_ticker_side.get((rec_d["ticker"], side))
                rec_d.setdefault("recommendation", {})[side] = {
                    "recommended": bool(r is not None and r.authority in ("LIMITED", "TRUSTED")),
                    "shadow": bool(r is not None and r.authority not in ("LIMITED", "TRUSTED")),
                    "authority": r.authority if r else None,
                    "exclusion_reason": (
                        removed_keys.get(f"{rec_d['ticker']}|{side}")
                        or (rec_d["edge"].get(side) or {}).get("reasons")
                        or None
                    )
                    if r is None
                    else None,
                }
            rid, _ = ledger.append(rec_d, when=as_of)
            record_ids.append(rid)

    cov.assert_invariant()
    summary = cov.summary()
    events = _events(by_fx, fixture_ctx, inputs.registry, cov, works)
    coverage = CoverageReportV1(
        discovery_run_id=disc.run_id,
        discovery_complete=disc.complete,
        contracts_discovered=summary["contracts_discovered"],
        contracts_evaluated=summary["contracts_evaluated"],
        contracts_excluded_mechanically=summary["contracts_excluded_mechanically"],
        contracts_unsupported=summary["contracts_unsupported"],
        unaccounted_contracts=summary["unaccounted_contracts"],
        by_disposition=summary["by_disposition"],
        contracts_by_family=disc.counters()["contracts_by_family"],
        competitions_discovered=sorted(
            {s.competition_code for s in disc.specs.values() if s.competition_code}
        ),
    )
    output = RunOutputV1(
        run_id=run_id,
        sport="soccer",
        generated_at=utc_now(),
        run_date=cfg.run_date.isoformat(),
        filters={
            "leagues": list(cfg.leagues),
            "games": list(cfg.games),
            "window_hours": cfg.window_hours,
            "confirmed_lineups_only": cfg.confirmed_lineups_only,
        },
        no_bets=len(recs) == 0,
        recommendations=recs,
        shadow_recommendations=shadow,
        events=events,
        coverage=coverage,
        freshness=fresh.to_json(),
        warnings=warnings,
    )
    from soccer_edge.run.render import render_markdown

    md = render_markdown(output, reduced, fixture_summaries)
    return RunArtifacts(output, md, cov, per_contract, simulated, repriced, record_ids)


def _event_name(fx: Fixture, reg: AliasRegistry) -> str:
    h = reg.teams.get(fx.home_team_id)
    a = reg.teams.get(fx.away_team_id)
    return f"{h.name if h else fx.home_team_id} vs {a.name if a else fx.away_team_id}"


def _thesis(w: ContractWork, summ: dict[str, Any], reg: AliasRegistry) -> str:
    fx = w.fixture
    assert fx is not None
    h = reg.teams[fx.home_team_id].name
    a = reg.teams[fx.away_team_id].name
    if not summ:
        return f"{h} vs {a}: priced from cached simulation"
    return (
        f"{h} vs {a}: model xG {summ.get('mean_home_goals', 0):.2f}-{summ.get('mean_away_goals', 0):.2f}; "
        f"1X2 {summ.get('p_home', 0):.0%}/{summ.get('p_draw', 0):.0%}/{summ.get('p_away', 0):.0%}; "
        f"P(O2.5) {summ.get('p_over_2_5', 0):.0%}; BTTS {summ.get('p_btts', 0):.0%}; "
        f"contract '{w.priced.description if w.priced else w.market.title}' fair {w.priced.fair_mean:.1%} vs market"
        if w.priced
        else ""
    )


def _risks(
    w: ContractWork, state: Authority, ctx: MatchContext | None, complete: bool
) -> list[str]:
    r = []
    if state in (Authority.RESEARCH_ONLY, Authority.SHADOW):
        r.append(f"model authority {state.value}: not validated for real money")
    if ctx is None or ctx.lineup_state is LineupState.UNKNOWN:
        r.append("lineups unknown: availability shocks not priced")
    if w.spec.inferred:
        r.append(
            "market family inferred from ticker grammar; confirm Kalshi rules text before acting"
        )
    if w.priced and w.priced.param_sd > 0.06:
        r.append(f"wide parameter uncertainty (sd {w.priced.param_sd:.2f})")
    if not complete:
        r.append("discovery incomplete")
    r.append("Bet365/closing benchmark not compared at run time (research only)")
    return r


def _confidence_label(state: Authority, a: EdgeAssessment) -> str:
    base = {
        Authority.RESEARCH_ONLY: "research",
        Authority.SHADOW: "shadow",
        Authority.LIMITED: "limited",
        Authority.TRUSTED: "trusted",
    }[state]
    return f"{base}; P(edge>0)={a.p_edge_positive:.0%}"


def _contract_record(
    w: ContractWork, run_id: str, as_of: datetime, inputs: RunInputs, summ: dict[str, Any]
) -> dict[str, Any]:
    fx = w.fixture
    assert fx is not None and w.priced is not None
    cm = inputs.models[fx.competition_id]
    return {
        "schema": "prediction_record_v1",
        "run_id": run_id,
        "as_of": iso_utc(as_of),
        "ticker": w.market.ticker,
        "event_ticker": w.market.event_ticker,
        "fixture_id": fx.fixture_id,
        "competition_id": fx.competition_id,
        "kickoff_utc": iso_utc(_kickoff(fx)),
        "family": w.spec.family.value,
        "semantics": {
            "side": w.sem.side if w.sem else None,
            "line": str(w.sem.line) if w.sem and w.sem.line is not None else None,
            "period": w.sem.period.value if w.sem else None,
            "description": w.priced.description,
        },
        "model_family": MODEL_FAMILY_ID,
        "model_version": cm.posterior.version,
        "parameter_hash": cm.posterior.param_hash(),
        "world_hash": summ.get("world_hash"),
        "engine_version": summ.get("engine_version"),
        "sim_seed": summ.get("seed"),
        "data_as_of": iso_utc(inputs.results_observed_at),
        "model_as_of": iso_utc(cm.fitted_at),
        "market_as_of": iso_utc(inputs.market_observed_at),
        "discovery_run_id": inputs.discovery.run_id,
        "lineup_state": (
            inputs.lineup_contexts.get(fx.fixture_id).lineup_state.value
            if fx.fixture_id in inputs.lineup_contexts
            else "unknown"
        ),
        "probability": w.priced.to_json(),
        "market": {
            "yes_bid": str(w.market.yes_bid),
            "yes_ask": str(w.market.yes_ask),
            "no_bid": str(w.market.no_bid),
            "no_ask": str(w.market.no_ask),
            "yes_ask_size": str(w.market.yes_ask_size),
            "no_ask_size": str(w.market.no_ask_size),
            "status": w.market.status,
            "price_unit": "dollars",
        },
        "fee_regime": {
            "fee_type": w.regime.fee_type if w.regime else None,
            "fee_multiplier": str(w.regime.fee_multiplier) if w.regime else None,
            "schedule_version": FEE_SCHEDULE_VERSION,
        },
        "edge": {"yes": w.yes.to_json() if w.yes else None, "no": w.no.to_json() if w.no else None},
    }


def _events(by_fx, fixture_ctx, reg, cov, works) -> list[EventV1]:
    out = []
    for fid, ws in by_fx.items():
        fx = ws[0].fixture
        ctx = fixture_ctx.get(fid)
        evaluated = sum(
            1 for w in ws if cov.dispositions.get(w.market.ticker, (None,))[0] is Disposition.PRICED
        )
        out.append(
            EventV1(
                event_id=fid,
                sport="soccer",
                league=reg.competitions[fx.competition_id].name
                if fx.competition_id in reg.competitions
                else fx.competition_id,
                league_id=fx.competition_id,
                event_name=_event_name(fx, reg),
                start_time=_kickoff(fx),
                home=reg.teams[fx.home_team_id].name,
                away=reg.teams[fx.away_team_id].name,
                home_id=fx.home_team_id,
                away_id=fx.away_team_id,
                neutral_site=fx.neutral_site,
                status=fx.status.value,
                lineup_status=(ctx.lineup_state.value if ctx else "unknown"),
                stage=fx.stage,
                markets_discovered=len(ws),
                markets_evaluated=evaluated,
            )
        )
    return out


def write_outputs(art: RunArtifacts, out_dir: Path) -> dict[str, Path]:
    from soccer_edge.core.serialization import write_json

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": out_dir / "run_output.v1.json",
        "md": out_dir / "RUN_SOCCER.md",
        "contracts": out_dir / "priced_contracts.json",
        "coverage": out_dir / "coverage.json",
    }
    write_json(paths["json"], art.output.model_dump(mode="json"))
    paths["md"].write_text(art.markdown, encoding="utf-8")
    write_json(paths["contracts"], art.per_contract)
    write_json(paths["coverage"], art.coverage.summary())
    return paths
