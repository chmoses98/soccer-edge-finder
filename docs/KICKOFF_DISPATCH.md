# Kickoff-timed capture dispatcher

> **2026-09-30:** the GitHub cron is now only a backup. An external 5-minute heartbeat is the primary
> clock; wakes record heartbeats, missed horizons carry explicit states, paid calls are claimed first and
> settlement is dispatched when due. See **docs/SCHEDULER.md**, which supersedes the trigger description
> below.

Status: implemented (pre-launch remediation, phase 6; audit §K "capture requirement", §I1). Workflow
`kickoff-dispatch.yml`; logic `src/soccer_edge/dispatch/horizons.py`; commands `soccer dispatch
schedule|plan|tick|diagnostics`.

## Problem

Near-kickoff evidence (KALSHI_CLOSE, TRUE_CLOSE, lineup lead time) needs captures at T-120/60/30/15/5 for
every priced fixture. GitHub cron delivers a fraction of its slots (the audit measured 1 of 4 lineup slots
and no scheduled RUN SOCCER at all), so a single cron tick per horizon loses fixtures silently.

## Mechanism (free, bounded, idempotent)

1. **Schedule** (`dispatch/schedule.json` on `data-archive`): every event of the latest RUN SOCCER output
   (they have Kalshi markets) plus ESPN fixtures of priced competitions, 72 h ahead. Rebuilt by every tick.
2. **Decide job** (stdlib, seconds, no install): runs every 10 minutes on off-round minutes
   (`4,14,…,54`). It reads the schedule and the delivery log from the archive's public raw URLs and computes
   which (fixture, horizon) pairs are *satisfiable now*. Nothing due → the job ends (~20 s of runner time).
3. **Capture job** (only when something is due, or on manual `force`): clones the archive tip, then runs
   `soccer dispatch tick`: logs newly missed horizons, runs one capture batch for every due pair (Kalshi
   fast snapshot with change suppression, reference odds, ESPN lineups for the due leagues), logs each
   delivered horizon with the *achieved* minutes-to-kickoff, and **holds** (sleeps) for the next window when
   it opens within `--max-hold-minutes` (40). One successful job between T-66 and T-30 therefore covers
   T-60, T-30, T-15 and T-5 by itself; the cron only has to land once in that hour.
4. **Durable state**: `dispatch/horizons.jsonl` (append-only, one row per fixture × horizon:
   `delivered` with `achieved_minutes`/`lateness_minutes`/`batch_id`/`actions`, or `missed`) and
   `dispatch/diagnostics.json` (delivery rate per horizon, achieved-minute median/p10/p90, lateness,
   pending fixtures). Both are published through the append-only publisher and covered by the archive
   manifest.

Validity windows (minutes to kickoff): 120 → (60, 130], 60 → (30, 66], 30 → (15, 33], 15 → (5, 17],
5 → (0, 7]. Windows overlap by a small early tolerance and leave no gap: a late tick delivers every horizon whose window it lands in and records how late it was.

Bounds: one concurrency group (`data-writer-archive-kickoff`, queue not cancel), capture job timeout 55
min, hold ≤ 40 min, every tick idempotent (delivered/missed pairs are never re-logged), no cross-workflow
dispatch, no workflow storm (at most one capture job at a time; ticks that find nothing due cost seconds).

## What is not done here

* No RUN SOCCER at the near-close horizons yet: the exhaustive discovery still takes ~13 min per run
  (audit §N). Phase 21 (fast intraday run reconciled against the daily catalog) is the prerequisite; the
  tick has an obvious slot for it once a run costs ~1 min.
* Weather is captured by the 2-hourly ESPN job, not per horizon.

## Measuring

`soccer dispatch diagnostics --archive-dir <clone>` prints, per horizon, delivered/missed counts, the
delivery rate and the achieved-minute distribution. The pre-launch handoff reports these numbers; the
promotion evaluator (phase 23) reads the missing-close rate from the same evidence.

## Update (phase 21): predictions at the horizons

`soccer dispatch tick --with-run` (workflow input `with_run`) runs `soccer run --fast --window 3` at each
due horizon, writing prediction records into the same ledger (index restored from the archive, appended day
files published through the append-only publisher). The action is recorded in the horizon log
(`run_soccer_fast:ok|incomplete|error`). The exhaustive daily `run-soccer` stays as the reconciliation
anchor; the fast run reconciles against the daily catalog and falls back to exhaustive discovery if the
catalog-scoped sweep is incomplete.
