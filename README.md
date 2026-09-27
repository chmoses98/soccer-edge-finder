# soccer-edge-finder

Probabilistic soccer match world-model connected to an exhaustive Kalshi market-pricing and
research system. The soccer component of a future unified multi-sport Edge Finder.

**Status: foundation build. Every model family is `RESEARCH_ONLY`. Nothing here places bets,
and the operator command outputs `NO BETS` unless a model family has earned authority through
the documented promotion process (it has not).**

```
fixtures/context → lineup/availability uncertainty → team-strength posterior → correlated worlds
→ minute-level match simulation → ONE joint outcome distribution → EVERY discovered Kalshi contract
→ fair probability + interval → executable price + verified fees → robust edge → best expression
→ immutable prospective archive → settlement → calibration → research authority
```

## Quick start

```bash
uv venv && . .venv/bin/activate && uv pip install -e ".[dev]"
pytest -q
soccer run --date 2026-10-10 --window 72                # RUN SOCCER (live public Kalshi discovery)
soccer run --synthetic-kalshi --window 340 --no-freshness-gate   # offline demo surface (clearly labelled)
soccer discover --out data/catalog/latest_catalog.json  # exhaustive Kalshi soccer discovery only
soccer capture --out-dir data/snapshots                 # discovery + change-suppressed quote snapshots
soccer export-schemas                                   # app-contract JSON Schemas -> docs/schemas
```

Only public Kalshi endpoints are used. No credentials are required for anything in this repo.

## Where to read next

| Topic | Doc |
|---|---|
| What was learned from the MLB/NFL/CFB/NBA/router repos | `docs/EXISTING_SYSTEM_AUDIT.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| Data sources actually probed | `docs/DATA_SOURCE_AUDIT.md` |
| Kalshi discovery, taxonomy, coverage invariant | `docs/KALSHI_MARKET_MAP.md`, `docs/KALSHI_CAPTURE.md` |
| Model, uncertainty, simulation | `docs/MODEL_FAMILIES.md`, `docs/UNCERTAINTY_MODEL.md`, `docs/SIMULATION_ENGINE.md` |
| Pricing, fees, robust edge, expression | `docs/MARKET_PRICING.md`, `docs/MARKET_EXPRESSION.md` |
| Evaluation and authority | `docs/CALIBRATION.md`, `docs/RESEARCH_AUTHORITY.md` |
| Operator command | `docs/RUN_SOCCER.md` |
| App contract (versioned JSON) | `docs/APP_CONTRACT.md`, `docs/schemas/` |
| Settlement, storage, limitations, roadmap, handoff | `docs/SETTLEMENT.md`, `docs/STORAGE_STRATEGY.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md` |

## Repository layout

```
src/soccer_edge/
  core/        time, Decimal money, canonical JSON + hashing, error types
  identity/    canonical Competition/Season/Team/Player/Fixture/Tie schemas + alias registry
  providers/   provider protocols, observation provenance, openfootball + historical adapters
  kalshi/      public client (fail-closed pagination), discovery, ownership, taxonomy,
               association, coverage accounting, fees, executable prices, capture schemas
  model/       Dixon-Coles MAP + Laplace posterior, match context, correlated world generator
  sim/         vectorised minute-level match engine, joint outcome arrays
  pricing/     settlement semantics, pricer, robust edge, expression reducer, portfolio, coherence
  archive/     append-only content-hashed prediction ledger
  settlement/  refusal-first settlement engine
  evaluation/  Brier, log loss, reliability, interval calibration, CLV
  authority/   MODEL x MARKET FAMILY x HORIZON authority matrix and promotion rules
  families/    DATA_ONLY / MARKET_ONLY / HYBRID definitions, de-vig, logit blend
  contracts/   versioned app schemas (RecommendationV1, EventV1, ...)
  run/         RUN SOCCER pipeline, freshness gates, simulation cache, rendering
data/          registry (committed), catalog index (committed, compact), everything else archived
docs/          architecture, audits, contracts, handoff
research/      walk-forward evaluation scripts and frozen results
scripts/       workflow helpers (probe sources, catalog summary, workflow lint)
```
