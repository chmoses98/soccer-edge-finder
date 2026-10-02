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
