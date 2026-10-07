# App export (SOCCER -> unified Edge Finder app payload)

`soccer app-export` (`src/soccer_edge/app_export.py`, thin wrapper `scripts/app_export.py`) turns what
the production pipeline already publishes to the `data-archive` branch into the vendored contract's
documents (`contract/edge_finder_contract/`, byte-identical across sport repositories; `sync.check()`
is pinned in `tests/test_app_contract_v1.py`). It is an adapter only: no model, gate, authority,
staking or promotion logic lives here, and every probability, price, edge and action is copied from
the slate / run output that produced it.

Three objects stay distinct: a **model price** (one per Kalshi ticker, P(YES)), a **recommendation**
(a slate row whose action is `ACTIONABLE` or `RESEARCH_CANDIDATE`, for that row's side) and a
**wager** (a row the kalshi-bet-router filed on the accounting ledger). An edge is never a wager.

## Where the app reads it

`contract/edge_finder_contract/registry.json` -> SOCCER: repo `chmoses98/soccer-edge-finder`, branch
`data-archive`, root `app/latest`. `scripts/archive_publish.sh` runs the export inside `apply_payload`
right after the merged slate is re-rendered, from the MERGED archive tree, so every publisher
(run-soccer, kalshi-capture, espn-lineups, settle-evaluate, ...) carries a fresh `app/latest`. The
hook never aborts a publish: on failure the exporter writes `health.json` only and the script logs a
warning. `app/*` is declared mutable in `archive/manifest.py` (it is a derived view, never a ledger
record), so `archive manifest` / `archive verify` and the CI archive-verify job ignore it.

## Sources (archive-root relative) and what each becomes

| Source | Parsed with | Produces |
| --- | --- | --- |
| `runs/latest.actionable_slate.v1.json` (required) | `ActionableSlateV1` | markets, model prices, recommendations, run, health (Kalshi stamps) |
| `runs/latest.run_output.v1.json` | `RunOutputV1` | events (37 on 2026-10-02), theses, run `source_ids.run_id`, fixture freshness |
| `runs/latest.model_board.v1.json` | dict | preferred P(YES) / interval per ticker, `period`, `line`, `n_worlds`, `param_sd` |
| `config/authority.json` (on main) | dict | `bet_authority` (default `RESEARCH_ONLY`) |
| `STATUS.json`, `snapshots/STATUS.json` | dict | extra health components `espn_fixtures`, `kalshi_sweep` |
| `dispatch/heartbeats/<day>.jsonl` (newest line) | dict | `commit_sha`, `next_scheduled_run` (= completed_at + next_window_minutes), `dispatch` component |
| `fixtures/espn/<day>/*.json` (newest 7 days) | dict | `espn_event_id` into event `source_ids` |
| `<accounting-dir>/data/accounting/{wagers,settlements}.jsonl` | `routed_ledger.read_jsonl` | wagers, settlements (docs/ACCOUNTING.md) |

`--accounting-dir` is optional; without it wagers/settlements are empty and a warning is recorded
(the archive publishers do not check out `accounting-data` today -- see Known gaps).

## Identity

* **event**: source `fixture_id`, source_id the repo's `fx:<competition>:<season>:<home>:<away>` id;
  `source_ids = {fixture_id, espn_event_id?}`. Teams: source `team_id` (slug such as `eng.arsenal`),
  display names from `EventV1.home/away` (a slate-only fixture falls back to its `event_name`).
  `league` = competition slug, `competition` = display name, `season` from the fixture id,
  `start_time_confidence = SCHEDULED`, status mapped scheduled/live/finished -> SCHEDULED/LIVE/FINAL.
* **market**: `mkt_kalshi_<TICKER>`; the slate's two rows per ticker (yes/no) collapse into one market
  with yes/no bid/ask, `captured_at = kalshi_observed_at`, `market_family` from the slate,
  `yes_description` = the slate's `market_description` (the pricing module's deterministic
  description). `side` is parsed back from that description: `Result: home` -> HOME/AWAY/DRAW,
  `home wins by more than 1.5` -> HOME/AWAY + `line`, `Total goals over 2.5` / `home team total over
  0.5` -> OVER (+ `participant_id` for the team), btts / exact score / player props -> null.
  `kalshi_series_ticker` is the event ticker's series prefix. `market_status` is always OPEN (the slate
  only lists open contracts; `extensions.actions` carries NO_QUOTE etc. per side).
* **model price**: one per ticker, `fair_probability` = P(YES) -- the board's `p` when present, else the
  yes row's `model_probability`, else `1 - model_probability` of the no row; bounds likewise;
  `market_probability` = the yes ask; `edge` = the yes row's `fee_adjusted_ev`; `inputs_as_of` = the
  fixture's model freshness stamp (the run's decision time); `support_status` = the slate's model
  validity (`VALID`/`INVALIDATED`/`MISSING`); `data_quality_status` DEGRADED when either side's action
  is MODEL_INVALIDATED / MODEL_STALE, else OK; `freshness_status` from the row's model freshness state
  (STALE when MODEL_STALE). A NO_QUOTE / STALE_PRICE action is a MARKET condition and is reported on
  the market (`extensions.actions`, null prices), not as model staleness.
* **recommendation**: slate rows with action ACTIONABLE / RESEARCH_CANDIDATE; selection = side
  uppercased; status RECOMMENDED only for ACTIONABLE with `bet_permitted`, else RESEARCH_CANDIDATE;
  `authority` from the row; `research_only = not bet_permitted`; `current_price` = `kalshi_price`
  (the executable ask for that side), `fair_probability` = `model_probability` (for the side),
  `edge` = `fee_adjusted_ev`, `bet_up_to_price`, `expires_at` = `action_valid_until`,
  `data_freshness` from the row's Kalshi freshness, `lineup_status` from the fixture;
  native id `<slate_id>|<ticker>|<side>` (in `source_ids`). `RunOutputV1.recommendations` with
  authority LIMITED/TRUSTED would be added as RECOMMENDED (none exist: every family is RESEARCH_ONLY).
* **thesis**: one per event, from `RecommendationV1.thesis` / `risks` / `confidence_label` that RUN
  SOCCER already writes (summary text, opposing factors, evidence per recommendation). Nothing is
  authored here; an event without a run recommendation has no thesis.
* **wager / settlement**: ledger rows -> `source = KALSHI_ROUTER`, `source_bet_key`, ledger ids in
  `source_ids`; a ticker no longer on the slate gets a `market_stub`; settlements are
  `EXCHANGE_CONFIRMED` when gross/net are established, else `REFUSED` with the ledger's refusals;
  links to model price / recommendation are applied by `linkage.apply_links` (temporal only).
* **run**: `native_run_id = slate_id`, `source_ids = {slate_id, run_id, kalshi_discovery_run_id}`,
  `commit_sha` from the newest heartbeat else `--commit-sha`; its `run_id` is the run id of every
  document.

## Freshness thresholds and health

* market data: fresh <= 20 min, stale > 60 min (the slate's own policy: current <= 20, aging <= 30;
  Kalshi is swept roughly every 15 min).
* model: fresh <= 12 h, stale > 36 h (the slate's policy for the model board).
* `bet_authority = RESEARCH_ONLY` (config/authority.json default; `no_bets` is true on every slate), so a
  fully fresh export reports `overall_status = RESEARCH_ONLY`, never HEALTHY.
* Failure path: any exception leaves the previous `app/latest` byte-identical and writes `health.json`
  with `export_failed = true`, `payload_run_id` of the standing payload and the last-known-good stamps
  (DEGRADED while a good payload stands, UNAVAILABLE when none does); exit 1.

## Determinism

Ids are deterministic (contract `ids`); with the same inputs and `--now` two runs are byte-identical
(pinned on the fixtures in tests and checked by hand on the 2026-10-02 archive).

## Real-data proof (2026-10-02 data-archive)

slate `slate-20261002T172404Z-39df8c`, run `run-20261002T142020Z-e11a59`: 37 events (all with
`espn_event_id`), 1311 markets, 1311 model prices, 1 recommendation (RESEARCH_CANDIDATE, NO on
`KXBRASILEIROBTTS-26OCT03ATLRBB-BTTS`), 2 theses, 0 wagers, health RESEARCH_ONLY,
`verify_published == []`, `python -m edge_finder_contract validate <out>` OK.

## Known gaps

* `accounting-data` is not checked out by the archive publishers, so the published `wagers.json` /
  `settlements.json` are empty until a workflow passes `--accounting-dir` (the ledger is empty today).
* The newest dispatch heartbeat is the commit source; a publish with no heartbeat falls back to
  `--commit-sha` (`GITHUB_SHA`), which is the main-branch commit of the publishing workflow.
* Slate-only fixtures (added by a slate refresh after the last RUN SOCCER) get team names from the
  slate's `event_name`, not the identity registry.
* Model-quality notes observed, not fixed (hard rule 1): evaluation/model_health shows ECE 0.17 on the
  btts family at n=10 (SHADOW gates unmet); not an export concern.

## Contract feedback

* `build.market_stub` defaults `market_status = SETTLED`; a ledger ticker that merely left the 48 h
  slate window is not necessarily settled. Stubs here keep that default for want of a CLOSED-vs-SETTLED
  signal.
* `linkage.apply_links` returns a copy; an easy mistake is to ignore the return value (the adapter
  rebinds the list).

## Soccer script engine in the explorer (2026-10-07)

Every v1 event's `explorer/events/<evt>.json` carries `extensions.soccer_script_engine`
(`soccer_script_engine.v1`): glance, script cards, survivability at the slate price, the script x market
matrix, matchup, context, lineup re-scripting, data confidence, data gaps, freshness, authority, provenance. It is
built from `runs/latest.model_board.v1.json` and `runs/latest.actionable_slate.v1.json` of the same merged tree,
held under 75 KB (deep evidence trimmed in a fixed, recorded order). `markets.json` items carry a compact
`extensions.script_robustness` per side and `events.json` items `extensions.scripts`. No contract change:
`event_research.extensions` is the shared contract's sport-specific slot. Spec: `docs/GAME_SCRIPTS.md`.

## Research explorer (`app/latest/explorer`, contract 1.1.0)

`soccer research-export` (`src/soccer_edge/research_export.py`, wrapper `scripts/research_export.py`)
publishes the research graph beside the v1 payload, right after `app-export`, from the same archive root:

    python -m soccer_edge.cli research-export --data-root <archive> --out <archive>/app/latest [--now ISO] [--commit-sha X]

It reads the v1 publication it extends (`manifest.json` -> `run_id` and, unless `--now` is given,
`generated_at`; `events/markets/model_prices/recommendations.json`), so every `evt_` / `prt_` / `mkt_` id is
the v1 id (teams: `build.participant(TEAM, source "team_id", the slug)` exactly as `app_export._team`;
past games and settled fixtures: `build.event(source "fixture_id", ...)`). It writes nothing outside
`explorer/`, never touches the v1 files, and publishes atomically (`research.publish_explorer`): on any
failure the previous tree stays byte-identical and the command exits 1. `scripts/archive_publish.sh` runs it
as its own command after the v1 export (every publisher: run-soccer, kalshi-capture, kickoff-dispatch via
`kickoff_publish.sh`, espn-lineups, settle-evaluate, backfills); a failure logs a `research_export` warning
and a line in the step summary and never blocks the v1 payload or the push. Point-in-time: every timestamped
input is cut at the publication instant (`now`).

### Sources and what each becomes

| Source (archive / main) | Becomes |
| --- | --- |
| `snapshots/<day>/cap-*.jsonl[.gz]` | `market_history/<evt_>.json`: every v1 ticker of the event (or every settled ticker), bid/ask/last/volume/OI per capture, `source = kalshi:<batch_id>` |
| `predictions/<day>/predictions.jsonl[.gz]` | per-event `extensions.projection_history` (as_of, fair mean, 80 % low/high, Kalshi ask at the run, ledger run id) per ticker; run-axis `time_series` of `model_fair_probability` for the 3-way result tickers; rest/congestion context |
| `settlements/<day>/predictions.jsonl[.gz]` (settled in the last 7 days) | settled-event documents (`status FINAL`) with per-ticker outcome, fair mean/interval, entry/close, close class and CLV, plus arithmetic Brier / log loss of model vs entry mid vs close mid |
| `evaluation/model_health.v1.json` | `extensions.calibration` per event (model family x market family, horizon `any`; `validated: false` on `*.intl_pool`) and one calibration context note |
| `results/espn/<league>.jsonl` (dedup by `espn_event_id`, last row wins; repeated fixture ids get `:occN`) | team game logs (last 40 per profile), opponents + head-to-head, form metrics per window, rankings, per-game GF/GA series (last 40), home/away splits, and the RESEARCH dc_laplace_v2 refit |
| `data/international/results_v1.csv.gz` (main) + exact `intl:` -> `nat.` map from registry names/aliases | `elo_rating` (pre-match Elo of the latest archived match), Elo series (last 100 matches), international head-to-head |
| `lineups/<day>/*`, `lineups/history/*` | `context.lineups`: newest sheet with players per event + per-athlete appearance counts over every stored sheet |
| `weather/<day>.jsonl[.gz]` | `context.weather` (newest forecast revision) and `context.venue` |
| `runs/latest.model_board.v1.json` | `distributions` (stored quantile levels 0.5/10.5/25.5/49.5/50.5/74.5/89.5/99.5 % of P(YES), mean, sd, n_worlds) and the board summary note |

### Metrics (`metrics.json`)

`points_per_game`, `goals_for_per_game`, `goals_against_per_game`, `goal_difference_per_game`,
`clean_sheet_rate`, `btts_rate`, `over_2_5_rate` (PARTIAL; per competition pool: club leagues SEASON + L5,
national teams L10 + L5; ranked over every team of the pool that meets the window filter), `elo_rating`
(PARTIAL; ranked over the 122 exactly-mapped registry nations), `dc_attack` / `dc_defence` (RESEARCH: the
repo's own `fit_competition` + `StrengthConfigV2` refit on `results/espn` per pool, 730-day lookback, ranked
over teams with >= 8 effective matches; never the production posterior, which prices with dc_laplace_v1),
`model_fair_probability` (VERIFIED ledger data, entity MARKET, run axis; the model itself is RESEARCH_ONLY).
Projections from the international pool are published with `quality_status RESEARCH` (not validated).

### Capabilities (audit `audit_soccer.md`, 2026-10-03)

| Capability | Status | Why |
| --- | --- | --- |
| market_price_history, market_prices, raw_projections, team_props, game_markets, calibration, historical_accuracy, event_research, search | VERIFIED | production ledgers / captures on a cadence, tested, history present |
| team_profiles, team_metrics, team_game_logs, historical_results, opponents, recent_form_windows, situational_splits, rankings, comparisons, time_series | PARTIAL | ESPN results are goals only, 2024-07 onward; club top-5 history is not committed |
| opponent_adjustment | PARTIAL | ratings are not persisted; a labelled RESEARCH refit is shown |
| lineups, player_game_logs | PARTIAL | sheets only: no minutes, no stats; ~50 % pre-kickoff XI |
| projection_distributions | PARTIAL | current board only |
| weather | PARTIAL | joined by espn_event_id; geocode health DEGRADED |
| clv | PARTIAL | sharp reference almost never present |
| advanced_stats | RESEARCH | xG 2016-2023 top-5 only, league offsets, intl_hier: frozen research outputs, not published |
| player_profiles, player_metrics, usage, player_props, injuries, schedule_strength, matchup_metrics, play_by_play, venue_effects, wager_history | UNAVAILABLE | see each item's `reasons` |

A PARTIAL/VERIFIED capability whose evidence is absent from a given publication (no lineup, forecast,
board quantile, calibration cell or settlement for the published events) is published UNAVAILABLE with
that reason instead of being claimed.

### Sizes (2026-10-03 archive, 43 v1 + 49 settled events, `research.tree_bytes`)

| explorer/ | files | bytes | largest file |
| --- | --- | --- | --- |
| teams | 202 | 7,829,663 | 49 KB (budget 150 KB) |
| events | 92 | 8,086,371 | 144 KB (budget 150 KB; projection history shrinks to fit, 9 events trimmed) |
| market_history | 78 | 14,544,338 | 377 KB (budget 400 KB; opening + latest k captures per ticker on 21 events) |
| series | 341 | 4,010,128 | 35 KB |
| rankings | 65 | 785,691 | 29 KB |
| index.json / search_index.json / metrics.json / capabilities.json | 4 | 210,785 (compact, contract 1.1.1) / 166,872 / 24,841 / 21,719 | index budget 300 KB |

Total ~35.7 MB. A real-archive export takes ~20 s CPU (load ~4 s; most of the rest is contract schema
validation), so `archive_publish.sh` passes `--min-interval-minutes 60`: the rebuild runs only when
`refresh_due` says so (no explorer yet, a v1 event the explorer lacks, or a tree older than 60 min).
Settled events are published too, so extra explorer events never force a rebuild; otherwise the capture
batches leave `explorer/` untouched (contract 1.1.1 `publish.publish` no longer prunes it). Largest GAME
packet on the 2026-10-03 archive: 15,519 chars of text (61 markets, nothing truncated; budget 60,000).

### Deliberately not published

Player profiles (no canonical player ids; `data/registry` has `players: 0`), player metrics / usage /
props, injuries, schedule strength, matchup metrics, venue effects, play-by-play, wagers (ledger empty),
xG history and league / international hierarchical research ratings (RESEARCH, no ids for the published
teams), the stored `horizon` / `minutes_to_kickoff` snapshot fields (unreliable: time to kickoff is
`event.start_time_utc - captured_at`), sharp reference odds (112 rows), and any refit presented as the
production posterior.
