# Architecture

```
                 ┌──────────────── providers (observations with provenance) ────────────────┐
 fixtures/results│ openfootball · football-data.co.uk · club-football-match-data · (ESPN, Open-Meteo: probed, adapters pending) │
                 └──────────────┬───────────────────────────────────────────────────────────┘
                                ▼
  identity registry ──► Fixture / Team / Competition ids (provider-free, alias scopes)
                                ▼
  model/strength   ──► Dixon-Coles MAP + Laplace posterior  (per competition, point-in-time)
  model/context    ──► MatchContext (neutral, knockout, aggregate, lineup state, players)
  model/worlds     ──► WorldSet: joint draws of params · lineups · environment · red-card hazard · state effects · model inflation
                                ▼
  sim/engine       ──► JointOutcome (N = worlds × draws): FT/HT scores, reds, first goal, ET/pens, player goals
                                ▼
  kalshi/discovery ──► DiscoveryRun (ALL series → soccer/ambiguous → all markets/events, completeness proven)
  kalshi/taxonomy  ──► ContractSpec (family, side, line, period, player; UNKNOWN retained)
  kalshi/association► Association (fixture / competition / unmapped)
  pricing/semantics──► Semantics.settle(JointOutcome) → YES indicator per draw
  pricing/pricer   ──► fair mean, median, 80% interval (per-world probabilities), MC error
  kalshi/fees + executable ──► breakeven from side ask + verified fee regime
  pricing/edge     ──► point edge, fee-adjusted edge, P(edge>0), worst case, bet-up-to, robust flag
  pricing/expression► correlation groups from shared draws; dominance; removal ledger
  authority        ──► MODEL × MARKET FAMILY × HORIZON → RESEARCH_ONLY | SHADOW | LIMITED | TRUSTED
  kalshi/coverage  ──► one terminal disposition per discovered contract; unaccounted == 0 asserted
  archive/ledger   ──► append-only content-hashed prediction records
  contracts/v1     ──► RunOutputV1 (RecommendationV1[], EventV1[], CoverageReportV1, freshness)
  run/render       ──► RUN_SOCCER.md for humans (derived from the JSON, never the source)
                                ▼ later
  settlement/engine──► refusal-first settlement with evidence; Kalshi result as cross-check
  evaluation       ──► Brier, log loss, ECE, interval coverage, CLV, realised EV → ModelHealthV1
```

## Design rules that everything else follows

1. **Discovery is exhaustive and independent of classification.** The classifier never filters
   discovery; it labels it. New Kalshi families appear as `UNKNOWN` with a rationale.
2. **Completeness is structural.** A sweep is complete iff the terminal page was reached with no
   failed page and no cap; a run is complete iff every sweep is. Incomplete runs are saved, flagged,
   and can never produce a recommendation.
3. **One joint distribution prices everything.** Every contract on a fixture is settled against the
   same `JointOutcome`; coherence is by construction and audited anyway.
4. **Three uncertainties, kept apart.** Aleatoric = within-world draws; parameter = across worlds
   (posterior, lineups, environment); model = specification inflation and family mixing.
5. **Market refresh ≠ model refresh.** The simulation cache key covers the posterior hash, world
   config, sim config, context and contract set. Quote moves reprice from cached per-contract
   world-probability summaries; anything else re-simulates.
6. **Fail closed.** Unknown fee regime, unmapped team, unresolved side, missing period data,
   stale market, incomplete discovery: each is an explicit disposition or refusal, never a guess.
7. **No authority by existence.** Default `RESEARCH_ONLY` everywhere; promotion requires settled
   prospective evidence per cell and a human-applied config change.
8. **Immutable history.** Prediction records are content-hashed and append-only; corrections are
   new records that reference the old one.
9. **Small `main`.** Raw payloads and snapshots live in artifacts / the archive branch; only the
   registry, a compact catalog index, config and small frozen research tables are committed.
10. **Machine-readable first.** The app consumes versioned JSON; Markdown is a rendering.

## Package map

See `README.md` for the package layout. Key entry points:

| Concern | Module | Entry |
|---|---|---|
| RUN SOCCER | `soccer_edge.run.pipeline` | `run(inputs, cfg)` |
| Input assembly | `soccer_edge.run.inputs` | `assemble()`, `build_inputs()` |
| Discovery | `soccer_edge.kalshi.discovery` | `discover(client)` |
| Taxonomy | `soccer_edge.kalshi.taxonomy` | `classify(market)` |
| Pricing | `soccer_edge.pricing.pricer` | `price(semantics, outcome)` |
| Edge | `soccer_edge.pricing.edge` | `assess(priced, quote, regime)` |
| Simulation | `soccer_edge.sim.engine` | `simulate(worlds, ctx, cfg, seed)` |
| Worlds | `soccer_edge.model.worlds` | `WorldGenerator.generate()` |
| Strength | `soccer_edge.model.strength` | `DixonColesFitter.fit()` |
| Ledger | `soccer_edge.archive.ledger` | `PredictionLedger.append()` |
| Settlement | `soccer_edge.settlement.engine` | `settle(semantics, result)` |
| Authority | `soccer_edge.authority.policy` | `AuthorityMatrix`, `recommend_state()` |
| App contract | `soccer_edge.contracts.v1` | `RunOutputV1`, `export_json_schemas()` |
