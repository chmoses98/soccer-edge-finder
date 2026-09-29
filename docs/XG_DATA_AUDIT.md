# xG data audit (Phase 10)

Question: is there a **free, licensed-for-this-use, machine-readable** expected-goals source good enough to
build and *evaluate* an xG-based strength family? Probes were executed from the GitHub runner on 2026-09-28
(`scripts/probe_espn_xg.py`, results in `data/samples/espn_xg_probe.json`; the dev container cannot reach any
of these hosts). Status codes below are what the runner actually received.

| Source | Probe | Result | Usable? |
|---|---|---|---|
| football-data.co.uk `mmz4281/2627/E0.csv` | GET | 200; header contains **`HxG,AxG`** (new for 2026-27) | **yes** — same licence/terms we already rely on for results and odds; current season only |
| football-data.co.uk `2526/E0`, `2425/E0`, `2324/E0`, `2526/{SP1,D1,I1,F1}` | GET | 200; **no xG columns** | no history → cannot back-test |
| football-data.co.uk `2627/{SP1,D1,I1,F1,E1,N1,P1}` | GET (second probe) | 200; **all eight 2026-27 files carry `HxG,AxG`** | **yes** — every benchmark league, current season only |
| Understat league/match pages | GET HTML | 200, "xG" in title, embedded JSON present | **not adopted**: HTML scraping of a site whose terms do not grant it; no API; brittle |
| FBref (Sports Reference / Opta xG) | GET | **403** | no |
| StatsBomb open data (`competitions.json`) | GET | 200 | historical, selected competitions only (no current top-5 seasons); event-level; research-only licence — fine for *method* research, useless for live strength |
| FiveThirtyEight SPI archive | GET | 200 (CSV) | archive frozen in 2023; has `xg1/xg2` for 2016–2023 — usable only for historical method checks |
| FotMob match details API | GET | 404 (endpoint changed) | no |
| Sofascore, WhoScored, Opta Analyst, FootyStats, API-Football | GET | 403 / paywalled / key required | no ("do not purchase services") |
| ESPN summary | GET | 200 — `shotMapAvailable` flag exists in header; no xG field observed | no xG |

## Verdict

* A **prospective** xG feed exists for free: football-data.co.uk now publishes match xG (`HxG/AxG`) in the
  2026-27 files. It is ingested from this phase on (`MatchResult.home_xg/away_xg` via the existing provider)
  and will accumulate one season at a time.
* There is **no free historical xG** for the leagues and seasons the walk-forward benchmark uses (2018-19 →
  2025-26, E0/SP1/D1/I1/F1). Therefore an `xg_strength_v1` family **cannot be evaluated walk-forward against the
  frozen benchmark today**. Building one and "trying it" on 6–8 matchweeks would be exactly the kind of
  unevaluable model the mission forbids promoting.
* What was built instead (`data_only.xg_strength_v1` scaffold): the Dixon-Coles fitter already accepts any
  non-negative per-match intensity target; the family is defined as "fit on `xG` where present, goals
  otherwise, with a per-league xG→goals scale", registered RESEARCH_ONLY with an explicit **NOT_EVALUATED**
  evidence flag. It will become evaluable when either (a) football-data.co.uk publishes ≥ 2 full seasons with
  xG, or (b) a licensed historical source appears. See `docs/RESEARCH_RESULTS.md` for the frozen benchmark.
* Negative result recorded: no action changes production; the goals-based benchmark remains the only priced
  family.

## Data quality notes for the prospective feed

* xG is a **third-party model output**, not an observation. Its provider and version are not disclosed in the
  CSV; treat it as a covariate with unknown drift (record `xg_source="football_data_couk"` with each row).
* Expect missing values early in the season and for postponed/re-arranged matches; the provider leaves the
  field empty rather than 0.

## Update (remediation phase 20): historical xG path

`research/xg_history.py` (workflow `research-xg.yml`) tries, in order and without violating any
source's terms, the reproducible downloads the audit identified: FiveThirtyEight `spi_matches.csv`
(CC-BY 4.0, project retired) at its original endpoint, at the Internet Archive, and in the
`fivethirtyeight/data` GitHub repository; each response is hash-pinned and accepted only if its header
carries `xg1/xg2`. If found, `data/research/xg_history_v1.csv.gz` (top-5 leagues, goals + xG + non-shot
xG) is built and `xg_strength_v1` becomes evaluable (walk-forward omega grid on 2017-18..2020-21, frozen
holdout 2021-22..2022-23, against `dc_laplace_v2`'s goal-only likelihood). If no source is reachable the
result file says `xg_strength_v1_status: NOT_EVALUATED` and nothing is invented; the prospective
football-data.co.uk `HxG/AxG` accumulation from 2026-27 remains the only path. Understat, FBref/Opta and
scraped sources stay excluded. The result of the workflow run is recorded in docs/RESEARCH_RESULTS.md.

### Result of the retrieval (2026-09-28, `research-xg.yml` run 1)

The original FiveThirtyEight endpoint answers with a 310 kB page without xG columns; the Internet
Archive's 2023 snapshot of `spi_matches.csv` (9.7 MB, `xg1/xg2/nsxg1/nsxg2` present, CC-BY 4.0) was
retrieved from a runner, hash-pinned, and normalised into `data/research/xg_history_v1.csv.gz`:
12,676 top-5 matches, seasons 2016-17 to 2022-23, with per-division mean xG per match within 0.1 of
mean goals (E0 2.88 vs 2.77, SP1 2.69 vs 2.60, D1 3.00 vs 3.05, I1 2.86 vs 2.83, F1 2.67 vs 2.69),
so the divisions are comparable at the level needed for a strength model.

### `xg_strength_v1` evaluation (pre-registered in `research/xg_strength_eval.py`)

Family: `dc_laplace_v2` fitted on the joint likelihood Poisson goals + omega x quasi-Poisson xG
pseudo-likelihood (the v2 fitter takes the xG side as a second, fractional-target row per match with
weight omega and no Dixon-Coles low-score correction; `MatchRow.dc_correction`). Burn-in 2016-17,
selection 2017-18..2020-21 (omega in {0.25, 0.5, 0.75} by 1X2 log loss, weekly refits per division,
posterior-mean plug-in), ONE-TIME holdout 2021-22..2022-23. Decision: PASS if the paired 1X2 log-loss
gain over the goal-only fit has a 95 % CI above zero and a mean of at least 0.003. The workflow input
`evaluate=true` runs it on a runner and commits `data/research/xg_strength_v1.json`; the result is
recorded in docs/RESEARCH_RESULTS.md. Prospective football-data HxG/AxG accumulation continues either
way; the `0.7 xG / 0.3 goals` blend in `model/xg_family.py` remains unvalidated and unused.

### `xg_strength_v1` result (2026-09-29, `research-xg.yml` run 2, `data/research/xg_strength_v1.json`)

| | goal-only (omega = 0) | xg_strength_v1 (omega = 0.75) |
|---|---|---|
| selection 2017-18..2020-21, n = 7,156: 1X2 log loss | 0.99044 | 0.98430 (0.25: 0.98730, 0.5: 0.98529) |
| holdout 2021-22..2022-23, n = 3,638: 1X2 log loss | 0.99826 | 0.99215 |
| holdout O/U 2.5 log loss | 0.68710 | 0.68250 |
| paired 1X2 gain on the holdout | | **+0.0061 [0.0041, 0.0082]** |
| paired O/U 2.5 gain | | +0.0046 [0.0026, 0.0066] |
| per division (1X2 gain) | | E0 +0.0083, SP1 +0.0087, D1 +0.0056 (CIs exclude 0); I1 +0.0045, F1 +0.0033 (CIs touch 0) |

**PASS under the pre-registered rule** (CI above zero and mean >= 0.003): fitting team strengths on goals
plus xG improves out-of-sample 1X2 and totals log loss by about 0.005-0.006, consistently across
divisions. Caveats recorded with the result: the chosen omega sits at the top of the grid {0.25, 0.5,
0.75}, so the optimum may lie higher (a wider grid is a new pre-registration, not a re-run of this
holdout); the xG source ends in 2022-23 and is retired, so the family cannot be run live on this data;
the live path is the prospective football-data `HxG/AxG` feed (2026-27 onward) whose provider is
undisclosed and whose comparability to the FiveThirtyEight xG has not been checked. `xg_strength_v1`
therefore stays RESEARCH_ONLY with a positive historical result and no production wiring; the prospective
evaluation plan (in-season walk-forward from matchday 8, decision after >= 1,700 settled matches) is the
next step.
