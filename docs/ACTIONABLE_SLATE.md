# Actionable slate: continuously fresh prices without continuous simulation

Status: implemented 2026-10-02. Code: `src/soccer_edge/slate/` (board, reprice, invalidation, refresh,
observations, market_view, freshness, render), `src/soccer_edge/contracts/slate_v1.py`, `soccer slate
reprice | refresh | merge-latest`, `soccer run --board-out/--slate-out-dir`, `soccer dispatch tick
--model-refresh/--slate-refresh-minutes`. Workflows: `kickoff-dispatch.yml`, `kalshi-capture.yml`,
`run-soccer.yml`, `refresh-soccer-slate.yml` (**REFRESH SOCCER SLATE**). Tests: `tests/test_actionable_slate.py`.

## 1. Root cause (why a fresh capture could sit next to a stale slate)

`runs/latest.run_output.v1.json` was the only priced view of the market, and only RUN SOCCER wrote it.
RUN SOCCER is a 13.5-minute job (≈790 s of exhaustive Kalshi discovery, ≈10 s of model fitting, ≈10 s of
simulation and pricing; live stage timings) on a 4-a-day GitHub cron that GitHub mostly drops. The
fixture-aware kickoff chain captured Kalshi at T-120/60/30/15/5 reliably, but a capture only wrote raw
snapshots: nothing joined those fresh quotes to the model's probabilities. Its `--with-run` option could
re-run the model, but it defaulted to off and would have re-run the whole job at every horizon. So prices
were fresh in `snapshots/` and stale in the only file ChatGPT read.

## 2. Architecture: model computation vs market repricing

```
MODEL COMPUTATION (rare)                         MARKET REPRICING (every fresh Kalshi sweep)
soccer run (full, fast, or a scoped refresh)     soccer slate reprice / tick batch / slate refresh
  fit -> worlds -> simulate (cache reuse)          model board (cached distributions)
  -> price every contract                          x latest Kalshi sweep (asks, sizes, fee regimes)
  -> immutable prediction ledger  (evidence)       x stored Pinnacle rows (no API call)
  -> MODEL BOARD runs/latest.model_board.v1.json   x lineups / fixture context (invalidation)
                                                   -> fee-adjusted EV, q0.20 robust edge, bet-up-to,
                                                      reference-anchored EV, selection, best expression
                                                   -> runs/latest.actionable_slate.v1.json (latest state)
```

* **Model board** (`slate/board.py`): one entry per fixture with the model/engine/world versions, the
  parameter hash, the simulation content key, the pricing-input fingerprint and, per Kalshi contract, the
  fair probability, its 80 % interval and 100 quantiles of the per-world probability distribution. The
  quantiles reproduce the run's own worst-case edge and bet-up-to on the same quote (test
  `test_board_quantiles_reproduce_the_robust_edge`). Contracts without a quote at model time are priced
  from the same draws for the board only (never archived), so a quote that appears later is repriceable.
  Writers merge by fixture (newer entry wins); started fixtures and entries older than 7 days drop.
* **Reprice** (`slate/reprice.py`) reads only local files and one in-memory sweep. It cannot fit, simulate,
  call The Odds API or write the ledger (tests replace every one of those with a failure and reprice anyway).

## 3. The contract ChatGPT reads

`runs/latest.actionable_slate.v1.json` on `data-archive`
(raw: `https://raw.githubusercontent.com/chmoses98/soccer-edge-finder/data-archive/runs/latest.actionable_slate.v1.json`),
JSON Schema `docs/schemas/ActionableSlateV1.schema.json`, human summary `runs/LATEST_ACTIONABLE_SLATE.md`.

Top level: `contract: "actionable_slate.v1"`, `slate_id`, `generated_at`, `lookahead_hours` (48),
`consumer_rule`, `freshness_policy`, `kalshi` (observed_at, status, current_until, stale_after),
`actionable_until`, `model_board_generated_at`, `authority_summary`, `no_bets`, `compute` (mode, trigger,
simulations_run, fixtures_resimulated, fixtures_reused_from_cache, odds_api_calls, odds_api_credits,
reprice / model-refresh / capture runtimes), `counts`, `fixtures[]`, `contracts[]`, `removed_started[]`.

`fixtures[]`: kickoff, minutes to kickoff, `model` (validity VALID | INVALIDATED | MISSING, reasons,
versions, sim key, source run, freshness), `lineup` (status, last change, freshness), `context`,
`reference` (Pinnacle quality, entry/close role, bookmaker quote time, freshness), `contracts_priced`,
`contracts_without_model`, `best_expressions`.

`contracts[]` (one row per contract side, candidates first): fixture_id, event_name, competition, kickoff,
market_family, market_description, ticker, side, model_probability (+ low/high, family, version,
generated_at), kalshi_price (the executable ask, never a midpoint), yes/no bid/ask, kalshi_observed_at,
available_size, breakeven_price, fee_per_contract, reference_probability / quality / observed_at /
freshness, fee_adjusted_ev, worst_case_edge, model_posterior_edge_share, reference_anchored_ev (+ lower),
bet_up_to_price, lineup_status / observed_at, context_observed_at, authority, research_status,
bet_permitted, action, action_reasons, action_valid_until, best_expression, `freshness` {model, kalshi,
reference, lineup, context}.

### Actions (per contract side, at publish)

| action | meaning |
|---|---|
| ACTIONABLE | authority LIMITED/TRUSTED and every gate passed. **Never today.** |
| RESEARCH_CANDIDATE | passes the production selection (selection_v2) on a CURRENT price; RESEARCH_ONLY, analysis only |
| NO_EDGE | current price, valid model, no edge under the selection policy |
| EXCLUDED_BY_GATE | e.g. international pool not validated (audit §E6) |
| STALE_PRICE | Kalshi price not CURRENT: **NO ACTION** |
| MODEL_INVALIDATED / MODEL_STALE | a pricing input changed / the cached model is too old: NO ACTION |
| FEE_UNVERIFIED / NO_QUOTE | no verified fee regime / no executable ask |

## 4. Freshness contract

Separate timestamps and states for MODEL, KALSHI, REFERENCE, LINEUP, CONTEXT; no single `as_of`.

| input | CURRENT | AGING | STALE after | source of the timestamp |
|---|---|---|---|---|
| Kalshi | ≤ 20 min | ≤ 30 min (the approved live market gate) | 30 min | start of the sweep (oldest quote) |
| Reference (Pinnacle) | ≤ 15 min (edge_v2 limit) | ≤ 75 min | 75 min | capture time of the stored row |
| Lineup | ≤ 30 min | ≤ 2 h | 2 h | last ESPN lineup sync covering the league |
| Context (fixtures) | ≤ 12 h | ≤ 36 h | 36 h | latest ESPN fixture list / the run's fixtures |
| Model | ≤ 12 h | ≤ 36 h | 36 h | the run that produced the cached probability; INVALIDATED overrides |

An action needs Kalshi CURRENT, model VALID and not STALE, and a verified fee regime. The states are
computed at publish time **and** given as absolute instants (`current_until`, `stale_after`,
`action_valid_until`, top-level `actionable_until`). Consumer rule (also in the file): recompute at read
time; after `action_valid_until` every price is STALE_PRICE / NO ACTION, whatever the file says.

## 5. Automatic cadence

| event | what runs | simulations | paid Odds API |
|---|---|---|---|
| any fresh Kalshi capture (kalshi-capture cron, chain batch) | reprice the whole board on that sweep | 0 | 0 |
| chain, between horizons, a fixture within 12 h | free fast Kalshi capture + reprice every 15 min | 0 | 0 |
| a scheduled fixture enters the 48 h lookahead without ever having been modelled (beyond the last RUN SOCCER window) | the next periodic refresh adds one fixture-scoped model run on the same sweep; attempted once per link | 1 per new fixture with Kalshi markets | 0 |
| T-120, T-30 | capture + reprice; model only if the fixture is invalidated / missing | 0 normally | 0 |
| **T-60** | capture → Pinnacle **entry** (existing guarded call) → lineups → **fast model refresh scoped to the due fixture(s)** on the same sweep (no second discovery; sim cache reused when inputs are unchanged) → board → reprice | ≤ 1 per due fixture (0 on a cache hit) | the existing entry call |
| **T-15** | capture → Pinnacle **close** (existing) → lineups → model **only if** an input changed (XI published, kickoff, venue, version) or no refresh since T-60 → reprice | 0 unless an input changed | the existing close call |
| T-5 | capture + reprice; model only on an input change | 0 normally | 0 (the existing fallback close only if T-15 failed) |
| lineup / input change | invalidation marks the fixture MODEL_INVALIDATED (NO ACTION) at the next reprice; the next horizon batch reruns the model | 1 for that fixture | 0 |
| RUN SOCCER (cron or manual) | full or fast run → merges every priced fixture into the board → reprice | as before (cache) | 0 |
| REFRESH SOCCER SLATE (manual) | capture → lineups (≤ 3 h) → fast model on that sweep (cache reuse) → reprice | only fixtures whose inputs changed | 0 |

Selective refresh lives in `slate/refresh.py`; `--model-refresh every` (workflow input `with_run`)
restores a model run at every horizon, `off` disables it. Pinnacle cadence is unchanged: the paid calls
are still decided by the odds-API action's own purpose windows, claims and durable caps, independently of
the model refresh plan; the 8,000 floor, 150/day and 2,000/30-day caps are untouched.

### Rolling global slate

There is no daily slate. Every reprice includes the board fixtures with `now < kickoff ≤ now + 48 h`;
a fixture that kicked off leaves (`removed_started`), a later one enters as soon as it is inside the
lookahead, whichever league or time zone. Fixtures listed on Kalshi (dispatch schedule, `run_output`
source) but not yet modelled appear with `model.validity = MISSING` and no prices.

## 6. Invalidation (`slate/invalidation.py`)

Cached probabilities are valid while their pricing inputs are unchanged: model / engine / world versions
equal the configured production versions; kickoff within 5 min of the cached one; neutral-site flag and
stage unchanged; fixture not postponed/cancelled; lineup key unchanged ('none' until an XI is published,
then the sheet's content hash). A published XI also enters the simulation content key, so the model run
after a lineup change does not reuse the cached simulation. A Kalshi price move never invalidates.
Competition/stage are part of the canonical fixture id, so a re-assignment arrives as a new fixture
(MISSING). No injury/availability provider is wired: availability enters only through XI publication.

## 7. Efficiency (measured)

| path | runtime | what dominates |
|---|---|---|
| full RUN SOCCER (exhaustive, live 2026-09-29 … 10-01) | 804–815 s | Kalshi discovery 785–795 s; fit 8–11 s; simulate + price + archive 8–18 s |
| fast model refresh in a chain batch | ≈ 10–20 s on top of the batch's own capture (from the live fit and simulation stage timings; no second discovery) | refit 8–11 s; simulation of the due fixture ≈ 1 s (0 on a cache hit) |
| reprice only | **0.56–0.89 s live for 37 fixtures / 2,866 contract sides** (2026-10-02); 0.5 s for 1,032 sides (benchmark) | bet-up-to search per side |
| free Kalshi fast sweep feeding a reprice | ≈ 150 s (live batches) | Kalshi API pagination |

A reprice is more than 1,000× cheaper than a full RUN SOCCER (811 s vs < 1 s) and does no simulation. 100 price snapshots with
unchanged inputs = 100 reprices, 0 simulations, 0 credits. Each slate's `compute` block and the append-only
log `dispatch/slate_log/<day>.jsonl` (one row per reprice: trigger, mode, simulations, Odds API calls and
credits, runtimes, number of price changes vs the previous slate with a sample) make this auditable.

One honest exception: a model run that reuses a cached simulation for a fixture that has a shadow
candidate re-simulates that fixture once, deterministically, to rebuild joint draws for the expression
reducer (pre-existing pipeline behaviour). It is counted in `simulations_run`, never hidden. Reprices never
do this; their best expression is the largest robust edge per fixture × family.

### Live proof (2026-10-02, production data-archive)

1. RUN SOCCER (manual, this branch; the fast sweep fell back to exhaustive discovery, 1,044 s) built the
   first board: 37 fixtures across UEFA NL, CONCACAF NL, friendlies, Argentina, Brazil, kickoffs from
   16:00Z today to 13:00Z on 10-04; 37 simulations; slate `slate-20261002T142040Z-9cfcd1`
   (`model_refresh_and_reprice`, Kalshi observed 14:06:58Z, 0 Odds API calls).
2. kalshi-capture (this branch) at 14:22Z: free fast sweep, then reprice only. Slate
   `slate-20261002T142443Z-46d87b`: `reprice_only`, simulations 0, Odds API calls 0, credits 0, 0.56 s,
   217 contract-side prices changed versus the previous slate. Example: Cyprus vs Armenia (16:00Z),
   `KXUEFANLFTTS-26OCT02CYPARM-CYP` YES (first team to score: home): Kalshi ask 0.77 → 0.74, model
   probability 0.6035 unchanged (same board, generated 14:20:20Z), break-even 0.782 → 0.753, fee-adjusted
   EV −0.179 → −0.150, worst case −0.304 → −0.275, action NO_EDGE, valid until 14:42:03Z. The capture
   commit touched no `odds_api/` path.

## 8. Research evidence stays clean

* The prediction ledger is written only by model runs (`soccer run`, the T-60/T-15 refresh, REFRESH
  SOCCER SLATE): each record is the model probability known at that time with its market snapshot. A
  reprice never writes it (test `test_reprice_never_writes_the_immutable_ledger`).
* Pinnacle entry/close rows are unchanged evidence under `reference/`; reprices only read them.
* The slate and board are mutable latest-state pointers (`runs/latest.*`, unmanifested); the reprice log is
  append-only and manifested (`dispatch/slate_log/*.jsonl`).
* Model-refresh runs are archived as `runs/<day>/<run_id>/` so `archive verify` resolves every prediction's
  run (the old `--with-run` layout `runs/<batch_id>/` would have failed verification).

## 9. Publishing safety

Several workflows write the latest pointers. `scripts/archive_publish.sh` merges instead of overwriting:
the board is a union by fixture (newer entry wins), the slate keeps the copy with the newer Kalshi
observation (an older capture can never replace a newer price), and `predictions/index.json` is a union
(so a payload whose index predates another writer's records cannot break `archive verify`). If a push
races and the rebase conflicts, the payload is re-applied onto the new tip with the same rules instead of
failing.

## 10. Owner action

None. Optional: Actions → **REFRESH SOCCER SLATE** → Run workflow, when a current slate is wanted right now
(the chain keeps it current automatically while a fixture is within 12 h).
