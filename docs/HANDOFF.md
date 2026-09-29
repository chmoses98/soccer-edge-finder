# Pre-launch remediation build (2026-09-28) - handoff

Source of truth for the work: `docs/PRELAUNCH_AUDIT.md` (audit branch `claude/wonderful-gauss-pao6jg`,
merged as PR #10). Development branch for every PR below: `claude/fervent-dirac-ezmkzb`.

## A. CURRENT VERDICT

**No family is ready for real-money use.** Every family stays `RESEARCH_ONLY` (`config/authority.json`
unchanged: `{"default": "RESEARCH_ONLY", "entries": {}}`). The promotion evaluator reports every cell
`NOT_ELIGIBLE`, first on the reference gate (no free, terms-compliant live sharp reference exists;
`live_sharp_reference_available()` returns False) and then on sample size (no settled selected sides with a
close observation). Nothing in this build changes that; the build makes the evidence pipeline capable of
producing the proof the gates require, it does not produce the proof.

## B. MAIN / PRS
* `main` at **6993fbddde53b36e13747892ea964c2b8a2bde79** (PR #19 merge, 2026-09-29T01:2xZ). CI (`ci.yml`:
  tests on 3.11/3.12 + `archive-verify`) green on every merge; the data-archive publisher's pre-commit
  verify green on every publish.
* Audit merge: #10. Remediation PRs (all merged, all green): #11 PR A (recovery + manifest), #12 PR B
  (universal settlement + temporal guard), #13 PR C (kickoff dispatcher + reference quality + close v2),
  #14 PR D (edge_v2 + retail fees + move_v1), #15 PR E (dc_laplace_v2 + world_sim_v2 + harness),
  #16 PR H/I (lineups, oracle, xG path, fast runs, compaction, promotion evaluator, LIMITED config,
  router compat), #17 PR G (international), #18 PR F (worlds_v2, k re-estimate, structural term,
  coverage report, xg_strength_v1 eval, production fixes), #19 PR J (dc_v2 results, engine default,
  oracle join/result, docs). Open PRs: none.

## C. EVIDENCE RECOVERY
* Recovery `rec-20260928T181536Z-ef52e9a6` (applied 2026-09-28T18:15:36Z, dry run first): 854 lines appended
  (830 prediction records of run `run-20260928T124253Z-4f9bfb`, 5 lineup rows, 19 weather rows), 0 conflicts,
  timestamps / run ids / model versions preserved from the overwritten blobs, nothing recomputed.
* Manifest bootstrapped over 51 files / 2,335 records; `soccer archive verify` OK; CI `archive-verify` job and
  the publisher's pre-commit verify are green on every run since.

## D. SETTLEMENT
* Universal settlement (`soccer settle`, PR #12) runs in `settle-evaluate.yml`; production pass 2026-09-28T20:01Z
  over 2,265 archived prediction records: SETTLED 336, PENDING_EVIDENCE 30 (period data missing: half-time
  split / first scorer for 1H and first-to-score contracts), PENDING_KICKOFF 1,899, PENDING_MAPPING 0,
  PENDING_RESULT 0, UNSUPPORTED 0, UNSETTLEABLE 0, **unaccounted_settlement_records 0**.
  Settled share of due records: 91.8 % (336 / 366); the 30 pending are not guessed.
* Every priced competition has a settlement path (top-5 via football-data + openfootball; Americas and
  international pools via the ESPN archive with goal-event evidence).

## E. TEMPORAL INTEGRITY
* `core/temporal.py::TemporalGuard` + `strict_point_in_time` fitter flag; the pipeline refuses any input
  observed after the decision time (fail closed); property tests in `tests/test_temporal_guard.py`.
* Production runs since PR B: 0 future-data violations (guard reports in run output `temporal_guard`).

## F. CAPTURE / CLOSE
* Reference quality classes (`reference/quality.py`): the only free, keyless, terms-compliant sources are
  football-data.co.uk (pre-match retail, daily) and the Kalshi book itself; **no free live sharp source
  exists**, so `live_sharp_reference_available()` is False and the sharp gate cannot pass.
* Close v2 (`reference/close.py`): TRUE_CLOSE <= 15 min, NEAR_CLOSE <= 120 min, KALSHI_CLOSE <= 30 min with a
  valid two-sided book; side-aware; completeness reported in `settlement_coverage.v1.json`.
* Production close completeness on the 366 due records (settled 2026-09-28T20:01Z): Kalshi close NONE 122 /
  STALE 244 / KALSHI_CLOSE 0; reference close NONE 366. Reason: the kickoff dispatcher (PR #13) had **never
  run** before this verification - its cron produced 0 scheduled runs and no schedule file had been
  published; a manual `force=true` run (19:59Z) built the schedule (37 fixtures) and captured, and the cron
  began firing on its own at 23:31Z (about 5 h after the workflow reached main). Dispatcher log at
  2026-09-28T23:55Z: 14 horizons delivered / 42 missed (the misses predate the first scheduled tick),
  lateness median 0.5-5 min, actions `kalshi_capture:ok`, `lineups:ok`, `reference:empty` (no free
  pre-match reference rows exist for international pools). From here on, close evidence accumulates
  only for fixtures the dispatcher can see (run output + ESPN fixtures).

## G. EDGE V2
* `pricing/edge_v2.py`: EV = p* - break-even(entry ask + documented cent-ceiling fee), EV_lower = EV - 1.645 sigma,
  sigma^2 = devig^2 + stale^2 + w^2 sigma_struct^2; research rule EV >= 0.02 and EV_lower >= 0.01 (NOT betting
  authority). `P(edge > 0)` retired from selection, kept as `model_posterior_edge_share`.
* Retail fee model: cent-rounding tests; `RETAIL_FEE_VERIFICATION = VERIFIED_FROM_DOCUMENTATION_NOT_FILL_RECONCILED`.
* `move_v1` open-to-close study: NEGATIVE (1X2 beta -0.006 [-0.013, +0.002], directional accuracy 0.476;
  O/U beta -0.015 with CI below 0; n = 11,387) - preserved in docs/RESEARCH_MOVE.md.
* sigma_struct per family (walk-forward vs Bet365): ~0.33 logit / 0.065 pts (1X2), ~0.27 / 0.065 (O/U 2.5).

## H. DC_LAPLACE_V2
* Pre-registered grid (9 variants) on 2019-24, chosen d0030_s060; ONE-TIME holdout 2024-26 (n = 3,463):
  1X2 log loss 0.99203 vs v1 1.00179 (paired -0.0098 [-0.0141, -0.0056]); away level ratio 0.994 (v1 0.898,
  the audit's B2 defect removed); home ECE 0.018 (v1 0.033); gap to market 0.020 (v1 0.030).
* Acceptance: 5 of 9 criteria pass; **FAIL** on per-league level error (up to 4.6 %), O/U 2.5 significance,
  >10 pt disagreement bias (-0.056: when v2 disagrees with the market, the market is right) and the
  intercept LR share (0.56). Hybrid weight on the market is 1.0 in every season for both posteriors.
* Consequence: production model default stays `dc_laplace_v1`; v2 is runnable by flag, documented in
  docs/RESEARCH_DC_V2.md, and is the base of xg_strength_v1. The chosen point is a grid corner; a wider grid
  is a new pre-registration.

## I. WORLD_SIM_V2
* `sim/engine_v2.py` + `pricing/analytic_pricer.py`: exact per-world Dixon-Coles score matrices, analytic
  full-time pricing (no Monte Carlo noise), rho honoured, binomial HT thinning (first-half share 0.441),
  regression examples 2.30/0.80 and 1.52/1.13 pinned; audit xfails flipped to passing tests.
* Engine reconciliation on 1,500 real matches: world_sim_v1 (production) prices the draw 1.1 pt low and BTTS
  1.3 pt high against the exact matrix, systematically (audit regression points: draw 0.174 vs 0.191 at
  2.30/0.80); world_sim_v2 reconciles within Monte Carlo error (mean-abs 0.35 pt) and exactly for
  analytically priced full-time families. world_sim_v2 meets its acceptance. **Production engine default switched to world_sim_v2 in PR #19** (`soccer run` and the
  dispatcher's fast run); the model default stays dc_laplace_v1; reversible by `--engine-version
  minute_engine_v1`; records carry `engine_version` / `model_family` (`data_only.world_sim_v2`), so the
  first exhaustive run after the merge starts a new model-family cell in every report.

## J. UNCERTAINTY
* worlds_v2 (`model/worlds.py`): parameter uncertainty = Laplace x k, hand-set inflation removed, analytic
  per-world probabilities under world_sim_v2, structural term separate (edge_v2 only).
* k re-estimated on dc_laplace_v2: k_hat 0.8366 (95 % CI 0.7657-0.8971), 6/7 seasons below 1 -> R2 supported;
  totals PIT variance z -7.85 (F4 requires within +-3) -> **estimated, NOT adopted**; worlds_v2 runs at k = 1.0.
* Coverage report (`soccer uncertainty report`, settle-evaluate.yml): grouped 80 % coverage per cell; on the
  first 336 settled records the promotion evaluator's read is 0.911 (outside [0.70, 0.90], too wide) for the
  international pool cell that has data.

## K. INTERNATIONAL
* Dataset: CC0 international results (sha256 df35268f...), 48,249 of 49,547 matches, 231 teams, point-in-time Elo,
  neutral flag; licence verified; ESPN neutral-site inference for live fixtures.
* `intl_hier_v1` one-time holdout 2022-2026 (n = 4,563): log loss 0.8671 vs pool 0.9716 vs Elo 0.8739 (paired CIs
  below zero; beats both, also on competitive / neutral / cross-confederation subsets). FAILS 3 of 8
  pre-registered criteria (friendlies vs Elo, per-match heavy-favourite pricing at Elo gap >= 400, neutral-site
  goals +0.16 under-predicted for the listed-first team). Not promoted; `intl_shadows_enabled = False`.

## L. LINEUPS
* Capture reliability (`soccer lineups report`, prospective captures only; backfilled rows excluded): 58
  fixtures tracked, 26 past kickoff, 4 with an XI >= 20 min before kickoff (15 %; lead times 25-58 min, all
  from the dispatcher's T-60/T-30 captures on 2026-09-28/29), 15 first seen post-kickoff (pre-dispatcher).
  Before the dispatcher the share was 0 %. The audit's >= 90 % target is a prospective target from here.
* Post-hoc XI backfill: 3,717 XIs (top-5, 2024-08..2026-09) via `lineup-backfill.yml`, 2,648 joined to results.
* Oracle upper bound (pre-registered, `data/research/lineup_oracle_v1.json`): perfect-XI 1X2 gain -0.0009
  [-0.0048, +0.0035] on 1,061 matches; O/U 2.5 -0.0046 [-0.0081, -0.0008]; 4/5 leagues chose no adjustment.
  **STOP** under the audit rule (< 0.002): no prospective lineup model. Method calibration recorded (null league
  -0.003, synthetic 0.35 star +0.004): the study detects large effects only; more seasons would raise power.

## M. XG
* Historical path found: the Internet Archive copy of FiveThirtyEight `spi_matches.csv` (CC-BY 4.0),
  hash-pinned, 12,676 top-5 matches 2016-17..2022-23 with xG (`data/research/xg_history_v1.csv.gz`).
* `xg_strength_v1` (joint goals + omega x xG pseudo-likelihood through the v2 fitter) has a pre-registered
  walk-forward evaluation (`research/xg_strength_eval.py`; omega on 2017-18..2020-21, one-time holdout
  2021-22..2022-23; PASS iff paired 1X2 gain CI > 0 and mean >= 0.003). **Result: PASS** - holdout (n = 3,638) paired 1X2 gain
  +0.0061 [0.0041, 0.0082], O/U 2.5 +0.0046 [0.0026, 0.0066], omega = 0.75 (top of the grid; a wider grid
  would be a new pre-registration). Positive but not usable live: the historical xG source is retired and
  the prospective football-data HxG/AxG feed is unverified for comparability. Stays RESEARCH_ONLY.
* Prospective football-data HxG/AxG accumulation from 2026-27 continues; scraped sources excluded.

## N. PERFORMANCE
* `soccer run --fast` (catalog-scoped sweep reconciled against the daily exhaustive catalog, exhaustive
  fallback, `unaccounted_contracts` stays 0), stage timings in `freshness.stage_timings`, persistent sim cache
  in run-soccer.yml, analytic full-time pricing under world_sim_v2, dispatcher `--with-run` for near-close
  predictions. Exhaustive production run `run-20260929T010803Z-b1ba1c`:
  discovery 785 s (3,116 requests, 14,442 series, 6,395 contracts), assemble + fit 11 s, simulate + price +
  archive 18 s, total 814 s; the sweep is the cost, pricing is not. Fast run `run-20260929T012637Z-1a0ba3`: catalog-scoped sweep 210 s (5,993 markets), reconciliation
  against the daily catalog judged `evidence_level: insufficient` (the fast STATUS carried no series
  counters and the comparison catalog was the 2026-09-27 index), so the run fell back to an exhaustive
  sweep (785 s) and finished with 6,401 contracts, 0 unaccounted, 1,021 s total. The safety rule worked;
  the time saving did not materialise. Follow-up: publish series counters in the fast STATUS and let
  `kalshi-discover` refresh the daily index before the first fast run of the day.

## O. ARCHIVE
* Manifest + verify (C); `soccer archive compact` gzips closed day files in place, verified through the
  compacted twin, no history rewrite (docs/ARCHIVE_COMPACTION.md); `archive-compact.yml` (manual, `--apply`).
* Workflow copies of `priced_contracts.json` / `coverage_diagnostics.json` no longer published (14-day artifacts).

## P. PROMOTION EVALUATOR
* `authority/promotion_v2.py`, `soccer promote evaluate` (settle-evaluate.yml): verdicts only NOT_ELIGIBLE /
  ELIGIBLE_FOR_OWNER_REVIEW, never AUTO_PROMOTE, never writes `config/authority.json`.
* LIMITED mode: `config/limited_mode.json` `enabled: false`, validated by `authority/limited_mode.py`.
* Router compatibility: synthetic e2e under contract 1.2.0; provenance-field refusal pinned; no live routing.
* Production report 2026-09-29T01:09Z: 22 cells, **0 ELIGIBLE_FOR_OWNER_REVIEW, 22 NOT_ELIGIBLE**; the closest
  cell fails 12 gates, first `reference:no_live_sharp_source`, then every CLV gate (no settled selected sides
  with a close observation yet), `kalshi:no_close_observations`, `liquidity:no_depth_data`.

## Q. PRODUCTION RUN (13 proof points)
Dispatched and read back from `data-archive` after all PRs merged (runs on `main` at db55f03..6993fbd):

| # | proof | evidence |
|---|---|---|
| 1 | exhaustive discovery succeeds | `run-20260929T010803Z-b1ba1c`: `discovery_complete: true`, 14,442 series, 6,395 contracts, 3,116 requests, 785 s |
| 2 | fast reconciliation succeeds | run 36506522880 (`fast=true`): fast sweep 210 s / 5,993 markets, reconciliation refused to accept it (`complete_relative_to_full: false`, evidence insufficient), exhaustive fallback 785 s, 6,401 contracts, **0 unaccounted**, 1,585 records appended for the day. Reconciliation succeeded at its job (no market silently lost); the fast path saved no time this run (see N) |
| 3 | archive manifest verifies | publisher pre-commit verify OK on every publish (54 files / 2,725 records at the 20:01Z settle pass; more since); CI `archive-verify` green on every merge |
| 4 | RUN SOCCER completes | run 36505311944 success (the earlier 36475281249 failed closed on the 41 ms decision-time gap, fixed in PR #18) |
| 5 | 0 unaccounted contracts | `coverage.unaccounted_contracts = 0` (788 priced, 993 out of window, 3,132 unsupported family, 965 unmapped event, 246 unmapped team, 176 no fixture, 43 started, 42 ambiguous ownership, 10 unpriceable, all accounted) |
| 6 | no future-data violation | `temporal_guard.ok = true`, 0 violations, decision time 01:08:03.78Z after the last observation (01:08:02.74Z) |
| 7 | settlement job runs | settle-evaluate 01:09Z: 3,053 records, 838 settled, 32 pending evidence, 2,183 pending kickoff, 0 unaccounted; publishes settlement coverage, promotion, uncertainty coverage, lineup, horizon reports |
| 8 | reference capture runs | `reference/STATUS.json` batch `ref-20260929T010802Z` (41 upcoming rows, all lower-division/unmapped this evening, 0 written; the top-5 rows arrive with the weekend fixtures); dispatcher batches log `reference:empty` for international pools |
| 9 | close dispatcher runs | kickoff-dispatch: manual run 36476004949 (built the schedule, 4 batches) and scheduled run 36498488852 (cron, 23:31Z); `dispatch/horizons.jsonl` 56 rows, 14 delivered |
| 10 | no authority changed | `config/authority.json` = `{"default": "RESEARCH_ONLY", "entries": {}}`, unchanged since #1; `config/limited_mode.json` `enabled: false`; promotion report 0 eligible |
| 11 | NO BETS remains expected | every run output `no_bets: true`, `recommendations: []`; 9 shadow recommendations on the latest exhaustive run |
| 12 | shadow recommendations archive correctly | the 9 shadows are prediction records in `predictions/2026-09-29/predictions.jsonl` (788 records, content-hash ids, index updated, manifest extended) |
| 13 | repeated same-day runs append | `predictions/2026-09-28` holds 2,148 records from runs c14b83 / 4f9bfb / fdefb8 (append-only publisher; recovery of the once-overwritten 830 rows in C) |

## R. BLOCKERS
1. **No free, terms-compliant live sharp reference exists** (docs/REFERENCE_SOURCES.md). The promotion gates
   require one; without it no cell can ever pass. This is an owner/sourcing decision, not code.
2. **No close evidence yet**: the dispatcher started capturing on 2026-09-28T19:59Z (manual) / 23:31Z (cron);
   the first settled records with a KALSHI_CLOSE arrive at the next settle pass after those kickoffs + 3 h.
   The audit's CLV protocol needs >= 200 selected sides from >= 80 fixtures with >= 70 % TRUE_CLOSE; at the
   current shadow-selection rate (9 per exhaustive run) that is months of prospective data.
3. **Model quality vs the market**: the hybrid weight on the market is 1.0 in every season for both
   dc_laplace_v1 and v2; where the model disagrees with the market by > 10 pt the market is right
   (bias -0.056). The data-only posteriors carry no edge against a market on the historical sample.
4. **Uncertainty**: totals PIT variance z -7.85 (the totals distribution is misdispersed in a way no scalar
   fixes); k_v2 estimated 0.84 but not adopted.
5. **Kickoff dispatcher coverage**: 25 % of horizons delivered in its first two hours (cron delay); needs a
   week of prospective data before its reliability can be stated.
6. **International model**: better than pool and Elo but fails 3/8 acceptance criteria; shadows gated.
7. **GitHub cron latency**: new scheduled workflows started firing ~5 h after reaching main; the dense
   dispatcher cron drops slots under load (idempotent catch-up mitigates, cannot recover T-5 windows).

## S. NEXT ACTION
Let the remediated pipeline run untouched for at least one full matchday cycle (top-5 weekend + midweek):
exhaustive runs 4x daily, kickoff dispatcher at every horizon, daily settle-evaluate. Then read
`evaluation/settlement_coverage.v1.json` (close completeness), `horizon_diagnostics.v1.json` (delivery
rate per horizon), `uncertainty_coverage.v1.json` (now keyed by worlds_version, with the new
`data_only.world_sim_v2` family) and `promotion_report.v1.json`. No model work is justified before that
evidence exists; the only pre-registered research left is a wider dc_laplace_v2 grid (new registration)
and the prospective xg_strength_v1 plan (needs the 2026-27 HxG feed verified).

## T. OWNER ACTIONS
1. Decide whether to source a sharp reference (paid or licensed feed). Without it the promotion gates cannot
   pass by design; the code will keep reporting NOT_ELIGIBLE. Nothing in this repository can substitute.
2. Confirm the production engine switch to `world_sim_v2` (PR #19; reversible by flag) or revert it.
3. Decide whether the dc_laplace_v2 acceptance should be re-registered with per-league level tolerances
   set from season sampling error (the current 2 % per league is tighter than one season's noise); this is
   a protocol change, not a re-run.
4. Review docs/INTERNATIONAL_MODEL.md and approve or decline a v1.1 design (neutral listed-first term).
5. Keep `config/authority.json` and `config/limited_mode.json` as they are until the evaluator reports an
   ELIGIBLE_FOR_OWNER_REVIEW cell; nothing here has changed them.


---

# HANDOFF — soccer-edge-finder

Two build phases are documented here: **Phase 2 intelligence build (2026-09-28)** first, then the Mission-1
foundation handoff (2026-09-27) unchanged below it. Nothing is described as validated unless a test or a frozen
research artefact backs it.

---

# Phase 2 — intelligence build (2026-09-28)

Rules honoured: architecture not rebuilt; no model tuned to beat the historical market; no authority promoted
(everything RESEARCH_ONLY); no bets; no purchased services; no new secrets; market coverage not reduced
(`unaccounted_contracts == 0` on every run); historical predictions untouched (new fields are additive).

## A. Production verification (before changes)

Audited on `main` at `15a8f7c` before any Phase 2 change: latest dispatched `kalshi-discover`, `kalshi-capture`,
`run-soccer`, `settle-evaluate` all green; `runs/latest.run_output.v1.json` schema-valid (run
`run-20260927T234251Z-484160`: 6,499 discovered, 117 priced, 0 unaccounted, NO BETS, 16 shadow); 117 ledger records
verify; authority all RESEARCH_ONLY; archive 5.7 MB; no workflow storms. **One production bug found and fixed**:
`label_horizon` returned `T-10m` for every archived snapshot (raw `minutes_to_kickoff` was correct); regression test
added; analyses must recompute the label for pre-2026-09-28 rows (the microstructure summary does).

## B. Coverage forensics and identity expansion

`docs/COVERAGE_FORENSICS.md` + `data/diagnostics/latest_coverage_diagnostics.json` (machine-readable, per
disposition × time-to-kickoff × competition × family × region, ranked unknown teams, unregistered competitions).
Baseline: `unmapped_team` 258 / 805 / 111 contracts (next 72 h / 14 d / later). After explicit registry work
(+~250 teams: 23 UEFA nations, Liga MX, MLS, Brasileirão, Argentina, CONCACAF nations, NWSL, WSL, SPL, Süper Lig,
Saudi, Eredivisie, Primeira; 5 alias fixes; no fuzzy matching): **0 / 28 / 6**. The loss moved to `no_fixture`
(honest: known team, no fixture/model yet), which the ESPN archive path addresses (section D). Newly registered
competitions: `fifa.friendly`, `concacaf.nations_league`. Tokens with uncertain meaning stay unmapped by design.

## C. Reference market + CLV infrastructure

football-data.co.uk `fixtures.csv` → point-in-time `ReferenceMarketSnapshot` (bet365/pinnacle/average +
documented `consensus`), proportional de-vig with overround stored, fingerprint change-suppression, never
overwritten (`data-archive/reference/`). Records carry `reference.*`; settlements carry `close_class`
(TRUE_CLOSE ≤30 m / NEAR_CLOSE ≤6 h / PRE_CLOSE / NONE), side-aware probability / price / fee-aware CLV for both
sides, reference close and reference CLV. App contract **v1.1** (optional fields only; v1 consumers unaffected).
At the 2-hourly capture cadence most Kalshi closes will be NEAR_CLOSE — reported as such, never as closing lines.

## D. ESPN adapter, lineups, weather, rest

Endpoints verified from the runner (two probes, `data/samples/espn_xg_probe.json`): per-day scoreboards (the
date-range form returns 400), summaries with rosters/formations, team lists for 23 leagues, 60+ valid slugs.
Explicit identity map `data/mappings/espn_map.json` v3: 486 teams by exact alias resolution, unresolved ids listed.
`espn-lineups.yml` (every 2 h): fixtures window, FT results archive (`results/espn/<league>.jsonl`, append-only),
point-in-time lineup snapshots (`confirmed` only when captured before kickoff; post-kickoff sheets are history,
never confirmation), Open-Meteo forecast at kickoff hour (context only), identity-map proposals.
`espn-backfill.yml` (dispatch) backfills results from 2024-07-01 for `usa.1, mex.1, bra.1, arg.1` and the
international pool; `run-soccer` reads the archive (`--espn-dir`) and fits `usa.mls`, `mex.liga_mx`, `bra.serie_a`,
`arg.primera`, `uefa.nations_league`, `fifa.friendly`, `concacaf.nations_league` once ≥50 pooled results exist.
Lineup uncertainty layer (`model/lineups.py`): P(start)/P(bench)/P(unavailable), minutes priors, refuses future
history; **not wired into pricing** — ESPN publishes no XI 31–94 h ahead (probe) and the publication lead time is
unmeasured; the tracker records it prospectively. Rest days / 14-28-day congestion are on every record (context).

## E. xG

`docs/XG_DATA_AUDIT.md`: football-data.co.uk 2026-27 files carry `HxG/AxG` for all eight leagues probed;
FBref/Sofascore/WhoScored/Opta/FootyStats/API-Football are 403 or paid; Understat is HTML-only (not adopted);
StatsBomb open data and the 538 archive are historical-only. Ingestion built (`results_with_xg`), family
`data_only.xg_strength_v1` scaffolded and marked **NOT_EVALUATED** — no historical xG for the benchmark window,
so no like-for-like walk-forward comparison is possible. Negative result recorded; production unchanged.

## F. Kalshi microstructure and discovery efficiency

`soccer microstructure` (published by `settle-evaluate`): spread, sizes, mid-vs-executable gap, taker-fee impact,
share of 3c/5c mid-edges erased by spread+fee, evolution toward kickoff, volume/OI per family, capture cadence
gaps and hour-of-day coverage. `soccer reconcile-discovery` proves each fast capture complete relative to the last
full discovery (violations fail loudly; wired into `kalshi-capture`). Faster capture is never less complete.

## G. Policy versioning (MODEL vs SELECTION vs STAKING)

`src/soccer_edge/policy/`: `selection_v1` frozen = Mission-1 thresholds (hash recorded); research variants declared
up front; `soccer replay-policies` replays any policy over the immutable archive (flat 1-contract accounting,
CLV by side) — no record rewritten, staking DISABLED. `docs/POLICY_VERSIONING.md`.

## H. Router preparation

`import-wagers`, `import-settlements`, `validate-positions-ledger` with per-row receipts
(NEW/DUPLICATE_NOOP/CONFLICT/REFUSED), deterministic ids from `source_bet_key`, CONFLICT-never-rewrite, byte-identical
re-import, privacy-safe stdout (tested), shim script for the router's argv template. Router main re-audited
(unchanged at `2322bd7`). `docs/ROUTER_INTEGRATION.md` lists the exact profile the owner would add. **No live
routing.**

## I. Research results (walk-forward, frozen benchmark preserved)

All studies re-implement `walk_forward_v1` exactly (aligned n = 12,248; data LL 1.00099, market 0.97321
reproduced) and leave the v1 benchmark frozen. Result files carry content hashes; `config/frozen_baselines.json`
records protocol, dependencies and the pre-stated decision rule for each.

* **Home bias (`docs/RESEARCH_HOME_BIAS.md`)** — root cause is structural: the frozen fitter has no scoring
  intercept and pins mean attack/defence to zero, so away goal intensity is under-predicted by ~11% in every
  league (μ 1.127 vs 1.270 realised) while home advantage γ absorbs the missing level (0.295 fitted vs 0.216
  market-implied vs 0.190 realised). Effect: +2.9 pt P(home), −1.9 pt P(away), −3.0 pt P(over 2.5), worst for
  strong away sides. H1 supported (as symptom), H2/H5/H6 partial, H3/H7 rejected, H4 supported, H8 (intercept)
  supported. Candidates ranked by paired LL vs v1: intercept + slower decay −0.0087 [−0.0104, −0.0069] — bias
  removed but **still +0.019 behind the market**, hybrid weight 1.00 every season. Recommendation: a new
  versioned family `dc_laplace_v2`, evaluated as `walk_forward_v2`; **not** an edit of v1.
* **Disagreement (`docs/RESEARCH_DISAGREEMENT.md`)** — 116 pre-declared cells; none passes the rule (n ≥ 200,
  CI < 0, ≥ 4/7 seasons); the market is reliably better in 112. Penalty grows monotonically with the model's
  deviation from the market. No selection rule can be derived from disagreement size or sign.
* **Market families (`docs/RESEARCH_MARKET_FAMILIES.md`)** — paired LL difference vs market: 1X2 +0.028,
  O/U 2.5 +0.014, Asian handicap +0.024, BTTS worse than the base rate (+0.0045). Market wins every family,
  league and season; naive "model > implied + 3 pt" at Bet365 loses (home −6.0% ROI on 5,075 bets).
* **Uncertainty recalibration (`docs/UNCERTAINTY_RECALIBRATION.md`)** — outcomes first, market second. The
  grouped goal-residual estimator gives a posterior-sd multiplier k̂ = 0.81 (cluster-bootstrap CI 0.73–0.89;
  6/7 seasons on the same side of 1), so the v1 intervals are modestly too wide; the a-priori guess of 0.5–0.7
  is **rejected** by the outcomes. World-layer inflation (`sigma_model_log_rate`, `sigma_environment`) is not
  the cause of the totals over-dispersion (PIT z −7.1 → −5.2 without it) and stays. Rule-based decision:
  `global_outcome_k`, recommended `posterior_sd_scale = 0.8` for a **versioned `worlds_v2`** — not applied to
  v1; the residual "market inside 85.6%" gap is bias (home-advantage workstream), not width.
* **P(edge>0) (`docs/PEDGE_CALIBRATION.md`)** — historical proxy against de-vigged Bet365 with the 7% fee:
  higher P(edge>0) buckets do **not** realise higher returns (every bucket above 0.6 loses 2–4 cents; hit rate
  falls 36% → 19% as the statistic rises). The field is a model-internal agreement share, not a probability
  about the world; recommendation: introduce `share_worlds_positive_ev` (plus a reference-aware
  `p_positive_ev_vs_reference`) in a versioned `edge_v2`, keep the v1 field for archive continuity and mark it
  deprecated-in-name. Binning infrastructure (`research/pedge_eval.py`) is ready for the prospective ledger.
* **Multi-league hierarchical strength (`docs/MULTI_LEAGUE_MODEL.md`)** — per-league latent offsets with
  promotion/relegation and UEFA rows as cross-league evidence. Domestic aligned sample (n = 12,338): log loss
  0.9988 vs v1 1.0010 (paired −0.0022 [−0.0036, −0.0006]; Elo-prior variant −0.0028), still +0.026 behind the
  market with hybrid weight 1.00 every season; the no-offset ablation is worse than v1, so the gain is the
  offsets. UEFA out-of-sample (599 / 1,224 matches never fitted): −0.015 / −0.059 log loss vs pricing UEFA ties
  as equal-strength leagues, but **indistinguishable from a one-feature ClubElo logistic** (CIs straddle 0).
  Offsets correlate 0.93–0.95 with league mean Elo. Status: RESEARCH_ONLY candidate for UEFA *research*
  pricing; not a v1 replacement.
* **Rest / congestion / context features (`docs/RESEARCH_CONTEXT_FEATURES.md`)** — walk-forward residual test on
  top of the market, v1 and the multi-league posterior: rest days carry **no** residual information; trailing
  7/14/28-day congestion carries a detectable but negligible ≈ −0.001 log loss against every reference (the
  market does not fully price it either); calendar flags add nothing. Features stay context-only on records.

Net: the retrospective evidence still says the model is not informative relative to a sharp bookmaker; Phase 2
made it *honest about why* and built the prospective instruments (reference, CLV, close classes, replay) that
can test whether Kalshi's thinner books behave differently. No threshold, family or authority changed.

## J. What changed in production behaviour

Nothing that affects which contracts are recommended: same model family, same `selection_v1` thresholds, same
RESEARCH_ONLY authority. Additive: reference/CLV/context fields on records, more identities resolved (more
contracts reach `no_fixture` instead of `unmapped_team`), ESPN-fed competitions become priceable only after the
backfill has produced ≥50 results per pool.

## K. Verification after merge

Production on `main` after PRs #5–#7 (all dispatched and scheduled runs checked 2026-09-28):

| workflow | run | result |
|---|---|---|
| `run-soccer` (main, dispatch) | `run-20260928T033036Z-c14b83` | green; 6,338 discovered, 0 unaccounted, 0 evaluated (international break: no fixtures in the 48 h window), NO BETS, no freshness violations |
| `kalshi-capture` (main + branch) | runs 3 and 4 | green; fast-vs-full reconcile step passes; reference step present from run 4 (first live capture: 41/41 fixtures.csv rows skipped — no top-flight rows during the break; notes now name divisions) |
| `kalshi-discover`, `settle-evaluate` (scheduled 11:16 / 11:42 UTC) | | green |
| `espn-lineups` (dispatch + 2-hourly schedule) | | green after the empty-cache fix; 27 lineup snapshots (0 published pre-kickoff, 4 post), 19 weather rows, 15 results appended; 53 unmapped ids all Copa del Rey first-round clubs |
| `espn-backfill` (dispatch) | 36373486343 | green; results archived: MLS 1,171, Liga MX 691, Brasileirão 657, Argentina 1,139, Nations League 222, friendlies 333, CONCACAF NL 125; qualifiers 0 (slugs lacked a competition id — fixed, re-dispatched) |
| `diagnostics` (branch) | runs 1–2 | green; before/after tables in `docs/COVERAGE_FORENSICS.md` |
| `run-soccer` (main, dispatch after the backfill) | `run-20260928T124253Z-4f9bfb` | green; 6,272 discovered, **830 priced** (from 0 in the morning run), 0 unaccounted, NO BETS, 43 RESEARCH_ONLY shadows — all internationals; 8 fixtures (506 contracts) went `unpriceable` on a coherence rule that flagged skewed exact-score means (rule relaxed to a 1-point tolerance in PR #9); the shadows show the international pool is **not** calibrated (see limitation 26) |
| `espn-backfill` (qualifiers, second dispatch) | 36422848568 | green |

Two production defects were introduced by Phase 2 and fixed the same day, both caught by dispatching after merge:
an empty archive-restored cache file crashed `espn-sync`/`run-soccer` (PR #7), and the `run` parser lacked the
new flags (`tests/test_cli_parse.py` now parses every workflow argv). The next `run-soccer` on `main` after the
backfill will be the first with ESPN-fed competitions in the model set.

## L. Genuine blockers / risks

1. Still zero settled prospective evidence; nothing can be promoted. The international-pool shadows produced
   by the first ESPN-fed run are noise from an unvalidated model (distinct family id, limitation 26), not signal.
2. International/Americas pricing depends on the ESPN results backfill and on pooled international strengths
   fitted from friendlies + Nations League + qualifiers with a single home-advantage term (friendlies at neutral
   venues are flagged `neutral_site` but the fitter currently treats all rows alike — a documented simplification).
3. Lineups: publication lead time unknown; injuries absent.
4. Archive growth is unbounded (five new append-only writers); no compaction job.
5. GitHub cron jitter still leaves horizon gaps; TRUE_CLOSE captures will be rare.

## M. Next highest-value work

`docs/ROADMAP.md` (status-annotated). In order: confirm the backfill fits the Americas/international pools →
two weeks of lineup snapshots → CLV by close class after ~300 settled → only then any selection-policy change,
via a new policy version and the replay tool.

## N. Owner actions

1. None required to keep running. Optional: dispatch `espn-backfill.yml` again with an earlier `start` if the
   international pool is thin.
2. Do not edit `config/authority.json`; do not activate a router profile until you have read
   `docs/ROUTER_INTEGRATION.md` §Update 2026-09-28.

## O. Files / PRs

PRs: #5 (horizon fix, diagnostics, reference layer, probes), #6 (ESPN, lineups, policy replay, router importer,
microstructure, coverage expansion, xG, weather, rest), #7 (empty-cache and parser fixes), #8 (research results, qualifier mapping, reference-step fix). CLI subcommands: `run,
discover, capture, capture-reference, espn-sync, espn-backfill, replay-policies, settle, export-schemas,
import-wagers, import-settlements, validate-positions-ledger, microstructure, reconcile-discovery`. Workflows:
ci, kalshi-discover, kalshi-capture, run-soccer, settle-evaluate, diagnostics, espn-lineups, espn-backfill,
probe-espn-xg, probe-sources.

---

# HANDOFF — soccer-edge-finder foundation build (2026-09-27)

This file says exactly what is real, what is scaffolding, what is research-only, and what remains.
Nothing below is described as validated unless a test or a frozen research artifact backs it.

## A. What is actually functional

| Component | State | Evidence |
|---|---|---|
| Repository, CI (ruff + pytest on 3.11/3.12 + schema sync + workflow lint) | **working** | green CI on PR #1 and branch pushes |
| Canonical identities + alias registry (238 teams, 34 competitions; men/women/reserve scopes) | **working** | `tests/test_identity.py` |
| openfootball fixtures/results provider (EPL, Championship, La Liga, Bundesliga, Serie A, Ligue 1 2026-27) | **working, live** | assembled 1,752 fixtures + current results in `soccer run` |
| Historical results + Bet365 odds + Elo provider (238k matches) | **working, live** | walk-forward research ran on it |
| football-data.co.uk closing odds / upcoming reference odds adapters | implemented, unit-tested, **not yet exercised from a runner** | `tests/test_providers.py` |
| Kalshi public client, discover-everything, ownership, taxonomy, association, coverage ledger | **working**; live discovery from GitHub runner: see section C | `tests/test_kalshi_discovery.py`, workflow run |
| Fee engine (Decimal, documented mechanics, fail-closed) + executable price | **working** | `tests/test_fees_and_executable.py` |
| Dixon-Coles posterior, world generator, minute-level simulator | **working** (fits real 2026-27 data for 5 leagues in <1 s each) | `tests/test_simulation.py` |
| Contract pricer, coherence audit, robust edge, expression reducer, portfolio stats | **working** | `tests/test_pricing.py` |
| Prediction ledger (append-only, hashed), settlement engine, evaluation metrics, authority policy | **working** | `tests/test_archive_settlement_eval.py`, `tests/test_settle_loop.py` |
| RUN SOCCER pipeline + CLI (`soccer run`) incl. sim cache, freshness gates, NO BETS, coverage proof | **working in production**: run `run-20260927T234251Z-484160` on `main` priced 117 of 6,499 live contracts, 0 unaccounted, NO BETS, 16 shadow expressions, 117 records archived to `data-archive` | `tests/test_run_pipeline.py`, archive branch `runs/` |
| App contract V1 (7 schemas, exported JSON Schema, CI-synced) | **working** | `tests/test_app_contract.py` |
| Player/lineup layer | **scaffold** (tested with synthetic players; no provider) | `test_absent_star_lowers_attack_and_removes_goals` |
| Player-prop, futures, exact-score, cards/corners pricing | **not implemented** (dispositioned and counted) | coverage report |
| Router integration, positions import | **not implemented** (plan in `docs/ROUTER_INTEGRATION.md`) | — |

## B. What runs automatically (PRs #1–#3 merged; verified by dispatch on `main` 2026-09-27)

| Workflow | Schedule | Writes |
|---|---|---|
| `ci.yml` | push / PR | nothing |
| `kalshi-discover.yml` | daily 05:17 UTC + dispatch | `data/catalog/latest_index.json` on `main` (compact); full catalog as artifact |
| `kalshi-capture.yml` | :23/:53 08–22 UTC Fri–Mon; every 2 h Tue–Thu (+ dispatch) | `snapshots/` on `data-archive` |
| `run-soccer.yml` | 07:11, 11:11, 15:11, 18:11 UTC (+ dispatch); stdlib decision job skips when no fixtures | `runs/`, `predictions/` on `data-archive` |
| `settle-evaluate.yml` | daily 04:49 UTC (+ dispatch) | `settlements/`, `evaluation/` on `data-archive` |
| `probe-sources.yml` | weekly | artifact only |

Manual: promoting any authority cell (`config/authority.json`, reviewed PR); adding new families to
the taxonomy; re-running research; adding providers.

## C. Kalshi coverage — first runner-side discovery

Discovery `disc-20260927T230633Z-3639e9` finished 2026-09-27T23:19:42.305981Z — complete: **True** · series in Kalshi: 14398 · soccer series swept: 1389 · ambiguous unswept: 134 · events: 17691 · **contracts discovered: 6534** · unknown-family: 95 · requests: 3152 (retries 0)

Contracts by family:

| family | contracts |
|---|---|
| competition_winner | 1045 |
| match_result_3way | 1041 |
| exact_score | 675 |
| total_goals | 647 |
| handicap | 430 |
| competition_team_points | 384 |
| competition_top_n | 306 |
| player_season_leader | 247 |
| soccer_special | 211 |
| player_award | 167 |
| tournament_advancement | 160 |
| competition_qualification | 138 |
| competition_last_place | 132 |
| team_total | 127 |
| btts | 108 |
| competition_relegation | 96 |
| first_half_result | 96 |
| first_half_total | 96 |
| unknown | 95 |
| first_half_handicap | 64 |
| first_to_score | 63 |
| season_player_total | 50 |
| first_half_btts | 32 |
| competition_points_margin | 30 |
| competition_trophies | 30 |
| competition_host | 26 |
| competition_promotion | 24 |
| competition_head_to_head | 14 |

Contracts by competition code:

| code | contracts |
|---|---|
| UEFANL | 1694 |
| ? | 512 |
| CONCACAFNL | 398 |
| EPL | 361 |
| UCL | 354 |
| LALIGA | 237 |
| LIGAMX | 218 |
| SERIEA | 210 |
| LIGUE1 | 199 |
| BUNDESLIGA | 195 |
| MLS | 187 |
| WC | 172 |
| INTLFRIENDLY | 163 |
| BRASILEIRO | 139 |
| USL | 98 |
| EFLL1 | 86 |
| ISRNL | 80 |
| BRASILEIROB | 79 |
| UEFAEURO | 60 |
| FIFAW | 48 |
| APFDDH | 40 |
| DIMAYOR | 40 |
| COPADELREY | 38 |
| EFL | 37 |
| ENGNL | 36 |
| UECL | 36 |
| UEL | 36 |
| URYPD | 33 |
| WCW | 32 |
| ARGPREMDIV | 30 |
| LIGAMX1H | 30 |
| NWSL | 30 |
| BRASILEIROC | 27 |
| UCLW | 27 |
| COPAAMERICA | 25 |
| EFLCHAMPIONSHIP | 24 |
| FA | 24 |
| LIGAEXP | 24 |
| CONCACAFGC | 23 |
| DFBPOKAL | 21 |
| KNVB | 21 |
| PERLIGA1 | 21 |
| PREMIERLEAGUE | 20 |
| TACAPORT | 20 |
| BELGIANPL | 18 |
| EKSTRAKLASA | 18 |
| EREDIVISIE | 18 |
| LIGAPORTUGAL | 18 |
| SUPERLIG | 18 |
| CHLLDP | 16 |
| CHNSL | 16 |
| CONMEBOLLIB | 16 |
| COPADOBRASIL | 16 |
| ECULP | 16 |
| THAIL1 | 16 |
| UCLLEAGUE | 16 |
| UEFANLGROUP | 16 |
| MLS1H | 15 |
| MLSEAST | 15 |
| MLSWEST | 15 |
| ARGNACB | 14 |
| LALIGA2 | 14 |
| SVK2L | 14 |
| VENFUTVE | 14 |
| LIGAMX2H | 12 |
| MLS2H | 6 |
| CANPL | 3 |
| CHNL1 | 3 |
| SVKCUP | 3 |
| USLCUP | 3 |

Unknown ticker bodies (top 40) — the next taxonomy work items:

| body | n | example ticker | example title |
|---|---|---|---|
| CONMEBOLSUD | 8 | `KXCONMEBOLSUD-26-ATL` | Will Atlético Mineiro win the 2026 CONMEBOL Sudamericana? |
| COPADELREYADVANCE | 10 | `KXCOPADELREYADVANCE-26OCT03BAZATL-ATL` | Atletico Calatayud To Advance |
| DENSUPERLIGA | 12 | `KXDENSUPERLIGA-27-AGF` | Will Aarhus win the Danish Superliga? |
| EPLH2H | 6 | `KXEPLH2H-27ARSTOT-ARS` | Will Arsenal win both 2026-27 EPL matches against Tottenham? |
| HKANEKNIGHT | 1 | `KXHKANEKNIGHT-26-YES` | Will Harry Kane be Knighted in 2026? |
| JOINLEAGUE | 8 | `KXJOINLEAGUE-26OCT02DALABA-BUND` | Where will David Alaba go next? |
| JOINRONALDO | 11 | `KXJOINRONALDO-27-BOT` | Where will Cristiano Ronaldo go next? |
| KLEAGUE | 12 | `KXKLEAGUE-26-ANY` | Will FC Anyang win the Korea K League 1? |
| LAMINEYAMAL | 1 | `KXLAMINEYAMAL-27-LYAM` | Will Lamine Yamal leave Barcelona before 2027? |
| LIGAMX2H | 6 | `KXLIGAMX2H-26SEP27LEOJUA-JUA` | Juarez wins 2nd Half |
| MANAGEROUTDATE | 4 | `KXMANAGEROUTDATE-28TUCHEL-27JAN01` | Will Thomas Tuchel be out before Jan 1, 2027? |
| MLS2H | 3 | `KXMLS2H-26SEP27CLBMIA-CLB` | Columbus wins 2nd Half |
| POCHETTINOOUT | 1 | `KXPOCHETTINOOUT-30-Y` | Will Mauricio Pochettino leave as manager of the US Men's National Team before the start date of the 2030 Men's FIFA World Cup main tourname |
| SOCCERTREBLE | 2 | `KXSOCCERTREBLE-27ARS-DOM` | Will Arsenal win the domestic treble in the 2026-27 season? |
| SUPERBALLONDOR | 1 | `KXSUPERBALLONDOR-30-YES` | Will a Super Ballon d'Or be awarded before 2030? |
| SVKCUPADVANCE | 2 | `KXSVKCUPADVANCE-26SEP29BRAZEP-BRA` | Inter Bratislava To Advance |
| USLCUPADVANCE | 2 | `KXUSLCUPADVANCE-26OCT04HARLFC-HAR` | Hartford Athletic To Advance |
| WCCAREERGOALS | 3 | `KXWCCAREERGOALS-KMBAPPE-30` | Will Kylian Mbappe score at least 30 goals in the World Cup in his career? |
| WCTEAMS | 1 | `KXWCTEAMS-2030-YES` | Will there be 64 teams in the 2030 World Cup Tournament? |
| WINSTREAKMANU | 1 | `KXWINSTREAKMANU-27-5` | Will Manchester United men's soccer win at least 5 games in a row this year? |

Events sanity: events_matching_a_market_event=1050, events_not_in_swept_series=0, events_total=17691, market_event_tickers=1050, market_event_tickers_without_event_row=0

Market status histogram: active=6534


Taxonomy v2 was rebuilt from this evidence (the first run had 4,186 unknown of 6,694; v2 leaves
95 of 6,534 unknown, and the v2.1 tokens for second-half, first-half exact score and cup "to
advance" legs are in the code but not yet reflected in a committed index). Priced today: 3-way,
totals, spreads, team totals, BTTS, exact score, first-half result/total/spread/BTTS/exact score,
second-half result, first-to-score (non-knockout), to-advance. Counted but not priced: every
season/competition future, player-season, awards and specials. Coverage invariant
`unaccounted_contracts == 0` holds in every run (asserted, tested).

Discovery limitations: the daily exhaustive run costs ~3,100 requests (~13 min at 4 rps); intraday
capture uses the documented fast mode. `/events` per series returns historical events too (17,691
for 1,050 live market events), which is why events are fetched only for series that carry markets.
Milestones (`soccer_tournament_multi_leg`, 17,860 rows) are probed advisory-only.


## D. Data

Providers: openfootball (fixtures/results), club-football-match-data (history/odds/Elo),
football-data.co.uk (closing + upcoming odds; adapter ready), Kalshi public API.
Reachable-but-unwired: ESPN scoreboards (UEFA fixtures, lineups), Open-Meteo.
Not usable: FBref, FotMob, SofaScore (bot-blocked), football-data.org and The Odds API (keys),
ClubElo (502 during probe). Freshness gates: market 30 min, fixtures 36 h, results 8 d, model 3 d.
Limitations: no lineups/injuries; no UEFA fixtures; kickoff zones assumed; no xG inputs yet.

## E. Model

Families implemented: `data_only.dc_laplace_v1` (benchmark), `data_only.world_sim_v1`
(production pricing), `market_only.bet365_prematch_v1`, `hybrid.logit_blend_v1`, two baselines.
Inputs today: goals for/against per match with exponential time decay (half-life ≈107 days),
home advantage, Dixon-Coles ρ, per-team shrinkage priors (wider for teams with <8 effective
matches). Parameter uncertainty: Laplace posterior (inverse observed information). Correlated
worlds: joint draws of posterior, lineups (when provided), shared environment and model inflation,
red-card hazards, game-state multipliers. Match simulation: minute-level Poisson thinning with
state and red-card effects, HT capture, ET/pens for knockouts, aggregate ties.
Still simplistic: configured (not fitted) state/red/ET parameters; one home-advantage term;
no xG, no lineups in production, no cross-fixture correlation, intervals over-dispersed.

## F. Performance

Fit 20–60 ms per competition; 1,000 worlds × 100 draws ≈ 1.0 s per fixture; a 17-fixture slate
priced end to end in ~10 s at 500 × 100; repricing from cache is milliseconds. A weekend slate fits
in a 2-minute Actions job. Draw counts: 1,000 × 100 default (100k realisations per fixture).

## G. Research evidence (retrospective; does not count toward promotion)

12,248 aligned matches, 5 leagues, 2019-20 → 2025-26. Log loss: market 0.9732, hybrid 0.9732
(w=1.0 every season), DATA_ONLY 1.0010, baselines 1.075. Paired DATA − market +0.028
(95% CI 0.024–0.031). O/U 2.5: market 0.671 vs DATA 0.685. Where they disagree by >10 pts the
market wins (0.565 vs 0.624) and the model over-rates home sides. 80% intervals on P(home) are too
wide (mean width 0.29). Naive betting at Bet365 prices: −12% to −14% ROI. Every family remains
`RESEARCH_ONLY` because there is no prospective evidence and the retrospective evidence is negative.
CLV: not available yet (needs prospective captures). Full numbers: `docs/RESEARCH_RESULTS.md`.

## H. RUN SOCCER

`soccer run --date YYYY-MM-DD [--league …] [--game …] [--window H] [--confirmed-lineups-only]`
or the `run-soccer` workflow. Example output in `docs/RUN_SOCCER.md`. **Not safe for real-money
recommendations**: it will output `NO BETS` by construction until a cell is promoted.

## I. App readiness

`RunOutputV1`, `RecommendationV1`, `EventV1`, `ModelHealthV1`, `PositionV1`, `SettlementV1`,
`CoverageReportV1` — Pydantic + JSON Schema in `docs/schemas/`, CI-synced, strings for money,
UTC `Z` timestamps, `extra=forbid`. Consumption pattern in `docs/APP_CONTRACT.md`.

## J. Automation and storage

Recompute triggers: new results / lineup state / config / new contract on a fixture → re-simulate
that fixture (cache key). Quote-only changes → reprice from cache. `main` holds registry, config,
compact catalog index, small frozen research JSON. Everything bulky goes to the `data-archive`
orphan branch via `scripts/archive_publish.sh` (size guard, scoped add, rebase-retry). Raw
realisations are never stored.

## K. Genuine blockers / risks

1. Prospective evidence is zero today: the first archived predictions (117 contracts, 39 fixtures on
   2026-10-09..11) settle after the international break. Nothing can be promoted before hundreds of
   settled contracts per cell exist.
2. No lineup/injury source → every recommendation risk list says "lineups unknown".
3. UEFA fixtures unmapped until an ESPN adapter exists.
4. Fee mechanics are transcribed + probe-verified, not fill-reconciled in this repo.
5. Uncertainty layer over-dispersed; `P(edge>0)` conservative until calibrated.
6. GitHub cron unreliability will leave horizon gaps (reported, not hidden).

## L. Next highest-value work

See `docs/ROADMAP.md` (ordered): confirm live families → calibrate intervals → reference-odds
capture and Kalshi-vs-reference research → closing-line research → xG family → ESPN adapter →
multi-league model → prospective accrual → positions import/router.

## M. Owner actions (kept minimal)

1. Nothing is required for the system to keep running: all sources are public, no secrets are
   needed, and the schedules are live. Optional later: `FOOTBALL_DATA_ORG_TOKEN`.
2. Do **not** edit `config/authority.json` until `settle-evaluate` shows ≥300 settled in a cell
   with positive skill (`evaluation/authority_proposals.json` on `data-archive` will say so).
3. Decide when soccer fills should route here; that unlocks the importer work and the safe half of
   the router change (`docs/ROUTER_INTEGRATION.md`).
