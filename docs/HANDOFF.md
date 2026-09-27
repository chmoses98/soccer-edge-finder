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
| RUN SOCCER pipeline + CLI (`soccer run`) incl. sim cache, freshness gates, NO BETS, coverage proof | **working** end to end on real fixtures with the synthetic Kalshi surface; live-surface run pending the merged discovery fix | `tests/test_run_pipeline.py` |
| App contract V1 (7 schemas, exported JSON Schema, CI-synced) | **working** | `tests/test_app_contract.py` |
| Player/lineup layer | **scaffold** (tested with synthetic players; no provider) | `test_absent_star_lowers_attack_and_removes_goals` |
| Player-prop, futures, exact-score, cards/corners pricing | **not implemented** (dispositioned and counted) | coverage report |
| Router integration, positions import | **not implemented** (plan in `docs/ROUTER_INTEGRATION.md`) | — |

## B. What runs automatically (once PR #2 is merged)

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

1. The daily discovery is ~13 minutes; the fast capture relies on the committed index listing
   `series_with_markets`, which the first post-merge discovery run will populate (until then capture
   falls back to exhaustive and takes as long as discovery).
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

1. Merge PR #2 once CI is green (it contains the discovery ownership fix and the workflows).
2. Nothing to add as secrets: all sources are public. Optional later: `FOOTBALL_DATA_ORG_TOKEN`.
3. If you want the archive branch created immediately, dispatch `kalshi-capture` once after merge;
   otherwise the first scheduled capture creates it.
4. Do **not** edit `config/authority.json` until `settle-evaluate` shows ≥300 settled in a cell
   with positive skill (the workflow will write `authority_proposals.json` when that happens).
