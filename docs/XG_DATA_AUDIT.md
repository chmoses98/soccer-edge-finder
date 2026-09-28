# xG data audit (Phase 10)

Question: is there a **free, licensed-for-this-use, machine-readable** expected-goals source good enough to
build and *evaluate* an xG-based strength family? Probes were executed from the GitHub runner on 2026-09-28
(`scripts/probe_espn_xg.py`, results in `data/samples/espn_xg_probe.json`; the dev container cannot reach any
of these hosts). Status codes below are what the runner actually received.

| Source | Probe | Result | Usable? |
|---|---|---|---|
| football-data.co.uk `mmz4281/2627/E0.csv` | GET | 200; header contains **`HxG,AxG`** (new for 2026-27) | **yes** — same licence/terms we already rely on for results and odds; current season only |
| football-data.co.uk `2526/E0`, `2425/E0`, `2324/E0`, `2526/{SP1,D1,I1,F1}` | GET | 200; **no xG columns** | no history → cannot back-test |
| football-data.co.uk `2627/{SP1,D1,I1,F1,E1,N1,P1}` | GET (second probe) | see `data/samples/espn_xg_probe.json` → `xg.football_data_couk_*_2627.has_xg_cols` | per-league, current season only |
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
