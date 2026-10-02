# Scheduler: fixture-aware bounded chain (no external heartbeat)

Status: implemented 2026-09-30 (replaces the 5-minute external heartbeat design of #24, which is not
required and not enabled). Code: `scripts/kickoff_decide.py` (wake / complete / chain), `src/soccer_edge/
dispatch/` (`wake.py` decisions, `gitstore.py` heartbeats, claims, durable spend caps, chain lease,
`reliability.py`, `horizons.py`), `soccer dispatch tick --chain`, `reference/odds_api_capture.py` spend-time
guards, workflow `kickoff-dispatch.yml`. Tests: `tests/test_fixture_chain.py`, `tests/test_scheduler.py`.

## 1. Why GitHub's schedule failed (audit, 2026-09-28 → 09-30)

Every run GitHub created succeeded. Most scheduled runs were never created:

| window | expected | what happened | root cause |
|---|---|---|---|
| kickoff-dispatch cron `*/10` | ~144/day | 8 scheduled runs in ~36 h (≈ 4 %) | schedule slots never created |
| 09-29 16:00 slate, T-120 / 60 / 30 | wakes 13:50–15:45 | none | same |
| 09-29 16:00 slate, T-15 / T-5 | delivered | 15:54 run delivered both; Pinnacle priced neither match | dispatcher fine; provider had no price |
| 09-29 18:45 slate (8 fixtures) | wakes 16:35–18:45 | no run 15:54 → 20:41 | schedule absent; the 15:54 run also measured its hold from job start and would not wait 36 min |
| settle-evaluate 04:49 | daily | 11:16, 10:55, 10:46 | ~6 h late every day |
| backup cron after #24 | hourly slots | 1 run between 15:19 and 22:30 on 09-30 | same |

GitHub documents that scheduled runs can be delayed or dropped. **Scheduled-run creation cannot be the
timing authority.** Anything that must happen at a given minute has to come from something already
running, or from an event.

## 2. What GitHub Actions actually offers (constraints used)

* A job on a GitHub-hosted runner may run up to **6 h** and may simply sleep. A workflow run may last up to
  35 days, but each job is capped at 6 h.
* `workflow_dispatch` / `repository_dispatch` sent with the workflow's own `GITHUB_TOKEN` **do** create
  runs (the documented exception to "GITHUB_TOKEN events don't trigger workflows"). They are events, not
  schedules, so they are not subject to schedule dropping.
* `workflow_run` (another workflow completed) is also an event trigger.
* There is **no** native "run this workflow at 19:30 tomorrow": no delayed or future dispatch.
* Concurrency groups hold at most one running and one pending job per group; a newer pending job
  replaces an older pending one. `cancel-in-progress: false` never cancels a running job.
* This repository is public, so runner minutes are free. A sleeping job costs nothing and makes no API
  calls.

So the only GitHub-native way to be *awake at the right minute* is to be already running: a bounded job
that sleeps until the window, and hands over to exactly one successor before its 6 h limit while real
fixture windows remain.

## 3. Architectures considered

| | reliability | GitHub runs/day (season) | runs on empty days | owner setup | external credential | can miss a whole slate | complexity |
|---|---|---|---|---|---|---|---|
| **A. GitHub cron only** (before #24) | ≈ 4 % of slots | ~5 created of 144 | yes | none | none | **yes** (09-29 18:45) | low |
| **B. permanent 5-min external heartbeat** (#24 design, baseline only, *not enabled*) | high | ~288 decide + links | yes, 288/day | token + cron-job.org | yes (Actions RW token) | only if the provider fails | medium |
| **C. one morning controller** | depends on one cron slot landing on time | few | yes | none | none | yes, when that slot is dropped or late | low |
| **D. restart from other workflows' completion (`workflow_run`)** | event-driven, but those workflows are cron-driven | ~5–20 decide | yes (cheap) | none | none | yes, if none completes before the slate | low |
| **E. fixture-aware bounded chain** (chosen) + D + hourly cron as restarts | high while the chain lives; restart latency = next D/cron event | ≈ 5 links + ~5–20 decide | no links; only cheap decides | **none** | **none** | only if a link *and* every restart fail across the whole pre-slate period | medium |

External alternatives are only needed if E proves unreliable (§11).

## 4. The chosen design

```
decide (stdlib, ~15 s, on every trigger)
  reads data-archive (sparse): schedule, horizon log, heartbeats, settle runs
  settlement due?            -> dispatch settle-evaluate (90 min dedupe)
  known future window and no link alive?  -> start a LINK
  nothing known ahead        -> NO_WORK_DUE (normal success, nothing else runs)

LINK = capture job, <= 5 h 30 (job limit 6 h)
  holds the chain lease (dispatch/chain_lease.json; one link at a time)
  loop: plan -> capture what is due -> sleep until the NEXT HORIZON'S NOMINAL TIME
        (T-60 at exactly 60 min, T-15 at exactly 15 min); refresh archive + schedule every 30 min;
        publish after every batch (an interrupted link loses nothing)
  ends at its time limit, or immediately when no future window remains

chain step (after the link)
  exactly one successor (workflow_dispatch source=chain) when the link reached its limit with windows
  ahead and ran >= 20 min, or failed after >= 20 min (recovery). A short, cancelled or early-ended link
  never chains.

restarts of a stopped or broken chain (all run the same decide):
  workflow_run: run-soccer, kalshi-discover, kalshi-capture, espn-lineups, settle-evaluate completed
  hourly GitHub schedule (7 * * * *), backup only
  manual Run workflow
```

The chain exists only while the schedule (latest Kalshi listing, 72 h ahead) holds a future window. When
the last window passes it stops by itself. A new Kalshi listing (RUN SOCCER) that completes with fixtures
restarts it through `workflow_run`, typically days before those fixtures kick off.

## 5. Capture horizons

| horizon | Kalshi snapshot + lineups | Pinnacle (paid) |
|---|---|---|
| T-120 | yes (free) | no |
| **T-60** | yes | **yes (entry)** |
| T-30 | yes (free) | no |
| **T-15** | yes | **yes (close; TRUE_CLOSE ≤ 15 min)** |
| T-5 | yes (free) | only if the T-15 close was not captured (fallback, same purpose, still one call) |

Pinnacle was already restricted to entry and close by #21, so dropping T-120/T-30/T-5 from paid capture
saves **0 credits**: they were never paid. The change here is precision. A link wakes at each horizon's
nominal time, so the paid close lands at T-15. Before, a T-15 capture at the window opening (T-17) fell
outside the ≤ 15 min close window and slid to T-5. The three free Kalshi horizons stay: they cost no
credits, add no scheduling (the link is awake anyway) and feed the Kalshi close and microstructure
evidence.

## 6. Expected activity

| day | GitHub starts | paid Odds API calls | credits |
|---|---|---|---|
| no fixture known within 72 h | 0 links; ~5–20 decide-only runs (~15 s) from other workflows + delivered backup slots | 0 | 0 |
| light matchday (e.g. 3 kickoff clusters with a sport key) | ~5 links (chain continuous while windows remain) + decides | ≤ 6 (entry + close per cluster) | ≤ 18 |
| heavy club weekend day (~20 clusters) | ~5 links + decides | ≤ ~40 | ≤ ~120 (daily cap 150) |

Fixtures in competitions without a Pinnacle key (friendlies, CONCACAF Nations League) cost 0: they are
recorded once as `NO_SPORT_KEY`.

## 7. Runaway protection at the paid-call boundary (independent of the scheduler)

A paid `/odds` call happens only if **all** of these hold, checked in `capture()` / the claim store
right before the call:

1. the live `x-requests-remaining` read in the same tick is known, and remaining − cost ≥ **8,000**;
2. local ledger: today + cost ≤ **150** (entries ≤ 150 − **45**), 30 days + cost ≤ **2,000**;
3. running in Actions ⇒ a claim store is present (`NO_CLAIM_STORE` otherwise);
4. the Kalshi listing behind the schedule is ≤ 36 h old, and known (`STALE_SCHEDULE` /
   `SCHEDULE_AGE_UNKNOWN`);
5. per fixture, on a fresh clock at the moment of spend: not kicked off; provider event exists with
   commence time > now and within 30 min of the schedule's kickoff (`KICKOFF_MISMATCH`); purpose window
   valid (entry (30, 66], close (0, 15]);
6. **claim**: `the_odds_api|<purpose>|<fixture>` not yet claimed on data-archive (first writer wins);
7. **durable call cap**: in the same claim commit, the call records already on data-archive for today and
   the last 30 days, plus this call's expected cost, must fit 150 / 2,000. The check and the record are one
   atomic push, so a stale or empty local ledger, a restarted dispatcher, or any number of parallel runs
   cannot spend past the caps;
8. any failure to record the claim means no spend.

## 8. Maximum damage (credits)

| scenario | bound |
|---|---|
| normal operation | 3 credits × (entry + close) per kickoff cluster with a key; ≤ 150/day |
| duplicate triggers / GitHub retry storm | 0 extra: every (fixture, purpose) is claimed once, ever |
| infinite accidental trigger loop | **≤ 150 credits per UTC day and ≤ 2,000 per 30 days** (durable call records), never below 8,000 remaining; in practice ≤ the normal spend, since claims dedupe every due fixture |
| stale fixture list | 0 for fixtures that don't match a live provider event within 30 min; otherwise the listing-age limit (36 h) stops all paid calls |
| dispatcher restarting repeatedly | 0 extra (claims + durable caps); chain restarts can't loop fast (a < 20 min link never chains) |
| publishing broken (local ledger stale every run) | the durable records still cap at 150/day and 2,000/30 d |

Today's quota (11,5xx remaining, 8,000 floor) leaves soccer at most ~3,500 credits before the next reset,
whatever the scheduler does.

## 9. Settlement

The decide step (at every link start, every `workflow_run` completion and every backup slot) dispatches
settle-evaluate when a fixture finished (kickoff + 3 h 15 min) since the last run, or pending results are
due a 3 h retry (90 min dedupe; `dispatch/settle_runs.jsonl`). A chain wakes decide at least every ~5.5 h,
and other workflows' completions add more wakes. Settlement is idempotent. The daily 04:49 cron stays
as backup.

## 10. States, heartbeats, reliability (unchanged from #24)

Horizon states `DELIVERED / MISSED_BEFORE_WAKE / MISSED_EXECUTION_FAILURE / NOT_APPLICABLE` (PENDING is
computed); `close_v2.reference_attempt` (`PINNACLE_VALID_CLOSE`, `PINNACLE_QUOTED_NOTHING`, …,
`MISSED_DISPATCHER_CLOSE`); `dispatch/heartbeats/<day>.jsonl` (every wake and every link completion);
`dispatch/reliability.json` (24 h / 7 d: P(horizon delivered | fixture existed), close success, heartbeats
by source). Operator views: `soccer dispatch upcoming | reliability | close-report`. "Expected heartbeats"
in `config/dispatch.json` now describes the backup cron only; the external-heartbeat expectation is
disabled.

## 11. If this turns out not to be reliable enough

Judge by `dispatch/reliability.json` → `close_success_rate` over a club weekend. If links break and
restarts arrive too late, the smallest external addition is a **matchday-only wake**, not a 24/7
heartbeat: one external POST ~2 h before each day's first kickoff (1–3 requests/day, only on days with
fixtures). It would call the same dispatch endpoint with a fine-grained token limited to this repository
(*Actions: Read and write*), which cannot read code or secrets. Paid API exposure stays bounded by §7–§8,
whatever it sends. It needs owner approval and is **not** enabled.

## 11b. Live slate cadence (2026-10-02, docs/ACTIONABLE_SLATE.md)

Every batch now ends with a reprice of the cached model board on the batch's own Kalshi sweep. The model
runs selectively (`--model-refresh selective`): at T-60 for the due fixture(s), at T-15 only when an input
changed or T-60 was missed, at any horizon when a cached fixture is invalidated or missing. Between
horizons a link that has a fixture within 12 h runs a free Kalshi capture + reprice every 15 min
(`--slate-refresh-minutes 15`). None of this adds a paid call: the Odds API action keeps its own purpose
windows, claims and durable caps. The simulation cache persists across links (`actions/cache`, `simcache/`).

## 12. Owner action

**None.** No token, no external scheduler. Manual backstop: Actions → kickoff-dispatch → *Run workflow*.
