# RUN SOCCER

> **For current prices read `runs/latest.actionable_slate.v1.json`, not `runs/latest.run_output.v1.json`.**
> The run output is the model run's own record (prices as of its discovery sweep). The actionable slate is
> repriced on every fresh Kalshi capture from the cached model board, with per-input freshness
> (docs/ACTIONABLE_SLATE.md). Every run now merges its priced fixtures into the board
> (`--board-out`) and reprices on its own sweep (`--slate-out-dir`). To refresh on demand, run
> **REFRESH SOCCER SLATE** (manual RUN SOCCER now defaults to the fast sweep).

```
soccer run --date 2026-10-10 [--league eng.premier_league ...] [--game eng.arsenal-eng.leeds]
           [--window 72] [--confirmed-lineups-only] [--worlds 1000] [--draws 100]
           [--out-dir data/runs/latest] [--archive-dir <ledger>] [--sim-cache <dir>]
           [--no-freshness-gate] [--fail-on-incomplete] [--synthetic-kalshi]
           [--reference-dir <dir>] [--no-reference] [--espn-dir <data-archive checkout>]
```

Phase 2 flags: `--reference-dir` appends football-data.co.uk reference snapshots (change-suppressed) and
attaches the consensus probability to every record; `--no-reference` skips that fetch (a reference failure is
never fatal either way); `--espn-dir` points at a `data-archive` checkout so ESPN-fed competitions (MLS, Liga MX,
Brasileirão, Argentina, the international pool) are assembled from `results/espn` + `fixtures/espn` when they
have ≥50 pooled results. Rest/congestion context and lineup state are recorded per fixture; neither changes prices.

## What it does, in order

1. **Verify freshness** (`run/freshness.py`): market ≤ 30 min, fixtures ≤ 36 h, results ≤ 8 d,
   model ≤ 3 d, measured at the decision `as_of`. Violations fail closed unless
   `--no-freshness-gate`, in which case they are reported as warnings.
2. **Fixture/context**: openfootball fixtures + results for the current season; historical results
   for the posterior; per-competition Dixon-Coles posterior fitted point-in-time.
3. **Discover the complete Kalshi soccer surface** (all series → soccer/ambiguous → every market in
   `open` and `unopened`, plus events). Incomplete discovery ⇒ warnings and no recommendations.
4. **Associate** contracts to fixtures/competitions (or `unmapped_*`).
5. **Decide what to simulate**: cache key per fixture; reprice from cache when only quotes moved.
6. **Simulate** required fixtures (worlds × draws) and price **every eligible contract** from the
   same joint distribution; coherence audit.
7. **Disposition every other contract** explicitly (`closed, started, no_quote, stale_quote,
   duplicate, ambiguous_ownership, unknown_family, unsupported_family, unmapped_event,
   unmapped_team, no_fixture, no_model, fee_unverified, out_of_window, filtered_by_operator,
   unpriceable`).
8. **Executable EV** from the side ask + verified fee regime; **robust EV** from the world
   distribution; **reduce** redundant expressions; **apply authority**.
9. **Archive** one prediction record per priced contract (both sides' assessments, recommended /
   shadow / exclusion reason).
10. **Prove coverage**: `unaccounted_contracts == 0` or the run raises.
11. Write `run_output.v1.json` (app contract), `RUN_SOCCER.md`, `priced_contracts.json`,
    `coverage.json`.

## Output per recommendation

game, league, kickoff, market description, side, ticker, executable price, fair probability with
80% interval, fee-adjusted edge, P(edge>0), worst-case edge, bet-up-to price, authority,
confidence label, lineup status, market/model/data freshness timestamps, thesis, risks,
correlation group, coverage status.

## NO BETS

If nothing clears the robust-edge bar under an authority that permits recommendations, the
output is `NO BETS` (JSON `no_bets: true`). Today every family is `RESEARCH_ONLY`, so every real
run says `NO BETS` and lists what *would* have qualified under `shadow_recommendations`.

## Example (synthetic Kalshi surface on real 2026-27 fixtures, 2026-09-27)

```
contracts discovered: 252 (discovery complete: True)
contracts evaluated: 204 · excluded mechanically: 0 · unsupported/unknown: 48
unaccounted contracts: 0
NO BETS
Shadow / research-only expressions (13) …
Expressions removed by the reducer (8) …
```
The synthetic surface prices every market at a flat 45/27/28, so the large "edges" in that demo
are artefacts of the fake market, not evidence.

## Is it safe for real money?

**No.** Every cell is `RESEARCH_ONLY`; no prospective settled evidence exists yet; lineups are
unknown at run time; the fee schedule is transcribed, not machine-verified against a fill. Use it to
accumulate prospective shadow records and to study the market.

## Fast (intraday) mode and stage timings (remediation phase 21)

`soccer run --fast` sweeps only the Kalshi series that had markets at the last **exhaustive** discovery
(`data/catalog/latest_index.json`, refreshed daily by `kalshi-discover`) plus any series new since then, and
reconciles the sweep against that catalog (`kalshi/reconcile.py::reconcile_fast_vs_full`, written to
`fast_reconcile.json` in the run directory). If the reconciliation is not complete relative to the daily
catalog the run falls back to an exhaustive sweep in the same process, so **no market is silently lost and
`unaccounted_contracts` stays 0** under both modes; the daily exhaustive reconciliation remains
authoritative. Every run output now carries `freshness.stage_timings` (`discovery_s`, `assemble_fit_s`,
`simulate_price_archive_s`, `total_s`, `mode`), which the handoff and the performance benchmark read.
Full-time market families are priced analytically under `--engine-version world_sim_v2` (no Monte Carlo
noise); the simulation cache persists across workflow runs (`actions/cache`, entries keyed by the content
hash of every input that changes fair probabilities).

`kickoff-dispatch.yml` can run this fast mode at every due horizon (`with_run=true` → `soccer dispatch tick
--with-run`), scoped to a 3-hour window, which is how near-close prediction records (the CLV evidence the
promotion gates require) accumulate without the 13-minute exhaustive sweep.
