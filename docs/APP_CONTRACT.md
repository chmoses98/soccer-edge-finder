# App contract (versioned JSON for the unified Edge Finder UI)

Schemas: `src/soccer_edge/contracts/v1.py`; JSON Schema exports in `docs/schemas/` (checked in CI:
`soccer export-schemas` must be a no-op). Version `1.0.0`. Within V1 only additive, optional
fields are allowed; breaking changes create `v2.py` and `schema_version: 2.x` side by side.

## Objects

* **`RunOutputV1`** — the unit the app ingests: `run_id, sport, generated_at, run_date, filters,
  no_bets, recommendations[], shadow_recommendations[], events[], coverage, model_health[],
  freshness, warnings[]`.
* **`RecommendationV1`** — `recommendation_id, sport, league, event_id, event_name, start_time,
  market_ticker, market_family, market_description, side, current_price (string decimal),
  available_size, fair_probability, fair_probability_low/high, probability_edge_positive,
  fee_adjusted_edge, worst_case_edge, bet_up_to_price, authority, confidence_label, stake_units
  (null until authorised), model_family, model_version, data_as_of, market_as_of, model_as_of,
  lineup_status, coverage_status, thesis, risks[], correlation_group, fee_schedule_version,
  prediction_record_id`.
* **`EventV1`** — event identity, teams, kickoff, status, lineup status, markets discovered/evaluated.
* **`ModelHealthV1`** — per (model family × market family × horizon): authority, n settled, Brier,
  log loss, market log loss, ECE, interval coverage, CLV, realised EV, notes.
* **`PositionV1`** — imported fills (from the router, later); this repo never creates orders.
* **`SettlementV1`** — outcome with refusal reason, evidence, Kalshi cross-check, P&L link.
* **`CoverageReportV1`** — discovery completeness and the disposition partition with
  `unaccounted_contracts` (must be 0).

## Conventions

* Prices/money are **strings** of decimals (`"0.5200"`); probabilities are floats in [0,1];
  timestamps are ISO-8601 UTC with `Z`; ids are stable strings (`fx:…`, `rec_…`, `pred_…`).
* `sport` is an enum shared across sports (`soccer|mlb|nfl|cfb|nba|other`).
* `authority` ∈ `RESEARCH_ONLY|SHADOW|LIMITED|TRUSTED`; only `LIMITED|TRUSTED` appear in
  `recommendations`; everything else is in `shadow_recommendations` and must be rendered as
  non-actionable.
* `no_bets: true` is a normal, expected state and should render as such.
* `extra="forbid"` on every model: unknown fields fail validation so drift is caught early.

## How the future UI consumes it

Read the latest `run_output.v1.json` per sport (committed to the archive branch / served from a
static bucket), validate against `docs/schemas/RunOutputV1.schema.json`, render `recommendations`
by `correlation_group`, show `coverage.unaccounted_contracts == 0` as a health badge, and read
`model_health[]` for the model-health screen. Positions and settlements arrive as `PositionV1` /
`SettlementV1` streams once the router integration exists. Other sports can adopt the same
objects by mapping their outputs; the only sport-specific content is inside `market_family`
values and free-text fields.
