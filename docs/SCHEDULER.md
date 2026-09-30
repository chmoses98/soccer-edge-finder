# Scheduler: reliable evidence delivery (external heartbeat + GitHub backup)

Status: implemented 2026-09-30. Code: `scripts/kickoff_decide.py` (the wake), `src/soccer_edge/dispatch/`
(`wake.py` decisions, `gitstore.py` heartbeats + claims, `reliability.py` metrics, `horizons.py` states),
`src/soccer_edge/reference/close_attempts.py`, workflows `kickoff-dispatch.yml` and `settle-evaluate.yml`,
config `config/dispatch.json`. Tests: `tests/test_scheduler.py`.

## 1. Why: GitHub's schedule was the only clock, and it mostly did not fire

Production run history, 2026-09-28 → 2026-09-30 (every run GitHub created succeeded; none failed, was
cancelled, was concurrency-suppressed or ran a stale revision):

| window | expected | what happened | root cause |
|---|---|---|---|
| kickoff-dispatch cron `*/10` (off-round) | ~144 runs/day | **8 scheduled runs in ~36 h** (≈ 4 % of slots) | GitHub schedule simply absent: the runs were never created |
| 09-29 16:00 slate, T-120 / T-60 / T-30 | wakes between 13:50 and 15:45 | only 09:06 and 15:54 existed | schedule absent |
| 09-29 16:00 slate, T-15 / T-5 | delivered | the 15:54 run delivered both, paid one Pinnacle call, Pinnacle priced neither match | dispatcher worked; provider had no price (PINNACLE_QUOTED_NOTHING) |
| 09-29 18:45 slate (8 fixtures), every horizon | wakes 16:35 → 18:45 | no run between 15:54 and 20:41 | schedule absent; plus the 15:54 run declined to hold for the 16:35 T-120 window: its hold deadline was measured from job start (40 min) and the window opened ~36 min after the batch ended |
| settle-evaluate `49 4 * * *` | 04:49 daily | ran 11:16, 10:55, 10:46 | GitHub schedule delayed ~6 h every day (not dropped) |

Other crons show the same pattern (run-soccer 5 of ~8, espn-lineups 8 of ~24, kalshi-capture 9 of many).
GitHub documents that scheduled runs can be delayed or dropped under load. Moving cron minutes off
:00 was already done and did not help. The fix is a second, independent clock.

## 2. Architecture after the fix

```
external heartbeat (every 5 min)  ─┐
GitHub schedule backup (7,17,…,57) ─┼─► kickoff-dispatch · decide  (stdlib, ~15 s, no install)
manual / repository_dispatch       ─┘        │ reads data-archive (fresh tip, sparse, ~KBs)
                                             │ records a heartbeat row (every wake, every trigger)
                                             │ settlement due?  → POST dispatch settle-evaluate.yml
                                             │ horizon due / missed to log / schedule stale?
                                             ▼
                                   kickoff-dispatch · capture  (concurrency: data-writer-archive-kickoff,
                                             │                  cancel-in-progress: false)
                                             │ tick: re-plans, Kalshi snapshot + reference + lineups,
                                             │ claims paid calls on data-archive before spending,
                                             │ publishes (append-only), records a completion row
                                             ▼
                                   data-archive: dispatch/horizons.jsonl, heartbeats/, reliability.json,
                                                 odds_api/budget/, reference/, claims/, settle_runs.jsonl
```

* **One canonical dispatcher.** All four triggers run the same `decide` step; `decide_wake()` does not
  even take the trigger source as an input. The source only labels the heartbeat row.
* **Nothing due is a normal success.** The decide job exits 0, the capture job is skipped, no Odds API
  call, no simulation, no failure notification.
* **No event-specific logic in the heartbeat.** It sends one label (`external-heartbeat`). Fixtures,
  markets, Odds API parameters, bankroll and betting are all decided (or not) inside the repository.

## 3. Horizon states (no silent gaps)

Every (fixture, horizon) ends in exactly one state in `dispatch/horizons.jsonl` (`state` field):

| state | meaning |
|---|---|
| `DELIVERED` | a capture batch ran inside the window and the Kalshi snapshot succeeded |
| `MISSED_BEFORE_WAKE` | no dispatcher wake landed inside the window (the scheduler never fired) |
| `MISSED_EXECUTION_FAILURE` | at least one wake landed inside the window but the horizon was not delivered |
| `NOT_APPLICABLE` | the fixture entered the schedule after the window had closed |
| `PENDING` | window not closed yet (computed; see `soccer dispatch upcoming`) |

Windows use actual minutes to kickoff: 120 → (60, 130], 60 → (30, 66], 30 → (15, 33], 15 → (5, 17],
5 → (0, 7]. A late wake still delivers every horizon whose window it lands in (one batch). A horizon is
never delivered after kickoff. A failed capture is not logged as delivered: the next wake retries while
the window is open. Rows written before 2026-09-30 carry no state and read as DELIVERED / MISSED_BEFORE_WAKE
(the audit above shows those misses were scheduler absence).

## 4. Idempotency: no duplicate paid call

1. **Durable ledger check** (sequential wakes): a fixture with a successful `entry` or `close` capture in
   `odds_api/budget/` is never re-paid (`NO_ACTION`, zero HTTP).
2. **Claims before spending** (races, publish failures): right before a paid `/odds` call the capture writes
   one claim file per identity `the_odds_api|<purpose>|<fixture_id>` to `claims/odds_api/..` on data-archive
   and pushes. Two dispatchers racing for the same identity build on the same tip, and only one push can
   land. The loser refetches, sees the claim, and drops the fixture (`NO_ACTION_ALREADY_CLAIMED`). A claim
   that cannot be recorded means no spend (fail closed). Claims are made after the quota guard passes, so a
   refused call claims nothing.
3. **Concurrency**: only the `capture` job is in the writer group, with `cancel-in-progress: false`, so a
   newer wake never cancels an in-flight capture. A wake that sees a capture job already in progress does
   not queue another (`CAPTURE_IN_PROGRESS`, a normal success), because the running one re-plans every loop.
4. Heartbeat rows and claims are written by a fetch → apply → commit → push loop that restarts from the new
   tip on rejection. The append-only publisher never writes those paths, so the two cannot conflict.

Batching is unchanged: one paid call per competition per tick, covering every entry and close fixture of
that competition (`tests/test_scheduler.py::test_valid_close_and_cluster_is_one_call`).

## 5. Settlement without one fragile cron

The wake dispatches `settle-evaluate.yml` (workflow_dispatch with `source=dispatcher`) when:

* a fixture in the horizon log kicked off 3 h 15 min or more ago (settlement's own grace is 3 h) and after
  the last successful settlement run started, or
* the last run left fixtures pending (result not yet available) and is at least 3 h old (retry), for
  fixtures up to 72 h old;
* and no settlement was dispatched or ran in the last 90 minutes (dedupe).

Every settlement run appends `dispatch/settle_runs.jsonl` (`settle_run_v1`: started/completed, source,
newly settled, pending fixtures). Settlement itself is idempotent: settled records are skipped, pending
ones are re-evaluated and stay `PENDING_RESULT` / `PENDING_EVIDENCE` until results exist. It never guesses.
The daily 04:49 cron stays as backup.

## 6. Reference close: dispatcher vs provider

`close_v2.reference_attempt` on every new settlement record (and `soccer dispatch close-report`) states
why there is or isn't an external close:

`PINNACLE_VALID_CLOSE`, `PINNACLE_QUOTED_NOTHING`, `CLOSE_REQUEST_FAILED`, `CLOSE_BLOCKED_BUDGET`,
`NO_REFERENCE_EVENT`, `SPORT_NOT_ACTIVE`, `NO_SPORT_KEY`, `DISPATCHER_CLOSE_NO_ATTEMPT`,
`MISSED_DISPATCHER_CLOSE`, `PENDING`.

On the archive of 2026-09-30: Finland–Belarus and Moldova–Faroe Islands are `PINNACLE_QUOTED_NOTHING`
(close attempted, no Pinnacle price). All eight 18:45 fixtures (Spain–Croatia, Czech Republic–England, …)
are `MISSED_DISPATCHER_CLOSE` (never attempted).

## 7. Heartbeats and reliability

`dispatch/heartbeats/<UTC date>.jsonl`: one `wake` row per wake (trigger_source, requested_at, started_at,
completed_at, commit, fixtures examined, horizons due / newly missed, capture requested, settlement
dispatched, no-action reason, status) and one `capture` row per capture job (horizons delivered, missed
states, paid calls, credits, status OK/FAILED). The three cases are now distinct:
**NO WORK DUE** (`wake` row, `no_action_reason = NO_WORK_DUE`), **NEVER RAN** (no row; the expected-vs-
actual heartbeat gap), **RAN AND FAILED** (`status = FAILED`, or a failed Actions run with no row).

`dispatch/reliability.json` (rewritten by every wake; also `soccer dispatch reliability`, and
`evaluation/dispatch_reliability.v1.json` from settle-evaluate), for the last 24 h and 7 days: expected and
actual heartbeats by source, external-trigger and GitHub-backup success, eligible / delivered / missed
horizons by state, capture success rate = P(required horizon delivered | fixture existed), close success
rate (fixture got T-15 or T-5), capture runs, paid calls, credits.

## 8. Quota

Unchanged: 8,000 remaining floor, 150/day, 45 of it kept for closes, 2,000 per rolling 30 days, all
through the same `odds_api/budget/` ledger and guard. The decide job never calls The Odds API. A capture
tick with nothing due makes no provider call. Frequent heartbeats therefore cost 0 credits.

## 9. Owner setup (one time, free)

The external clock needs one credential that can start this repository's workflows and nothing else.

**A. Create the token (GitHub)**
1. github.com → your avatar → **Settings** → **Developer settings** → **Personal access tokens** →
   **Fine-grained tokens** → **Generate new token**.
2. Name `soccer-dispatcher-heartbeat`; Expiration: the longest you are comfortable with (note the date).
3. **Resource owner** `chmoses98`; **Repository access** → *Only select repositories* →
   `chmoses98/soccer-edge-finder`.
4. **Repository permissions** → **Actions: Read and write**. Leave everything else at *No access*
   (*Metadata: Read-only* is added automatically). This token can start and read workflow runs in this one
   repository. It cannot read or push code, read secrets or touch other repositories.
5. Generate, and copy the token once (it is shown only once). Do not paste it anywhere else.

**B. Create the heartbeat (cron-job.org, free)**
1. Sign up at cron-job.org → **Create cronjob**.
2. **Title** `soccer dispatcher heartbeat`.
3. **URL** `https://api.github.com/repos/chmoses98/soccer-edge-finder/actions/workflows/kickoff-dispatch.yml/dispatches`
4. **Execution schedule**: every **5 minutes**, **24/7**. Kickoffs span every time zone, and a wake with
   nothing due costs nothing.
5. **Advanced** → **Request method** `POST`; **Headers**:
   * `Authorization` = `Bearer ` followed by the token from A
   * `Accept` = `application/vnd.github+json`
   * `X-GitHub-Api-Version` = `2022-11-28`
   * `Content-Type` = `application/json`
   **Request body**: `{"ref":"main","inputs":{"source":"external-heartbeat"}}`
6. **Notifications**: on failure, preferably only after several consecutive failures. A 401/403/404 means
   the token expired, was revoked or lacks *Actions: Read and write*.
7. Save. The credential is only in a request header, never in a URL or query string.

Any other free HTTP scheduler that can send a POST with headers works the same way; nothing in the
repository depends on cron-job.org.

**C. Verify**
* cron-job.org → the job's **History** shows HTTP **204** every 5 minutes.
* GitHub → **Actions** → *kickoff-dispatch*: runs titled `kickoff-dispatch · external-heartbeat` every
  ~5 minutes, `decide` green, `capture` skipped unless something is due.
* data-archive `dispatch/heartbeats/<today>.jsonl` gains rows with `"trigger_source":"external-heartbeat"`.
  `dispatch/reliability.json` → `last_24h.external_trigger_success` climbs toward 1.0.

## 10. Operator commands (diagnostics only)

* `soccer dispatch upcoming --archive-dir <data-archive clone> --hours 6`: UPCOMING REQUIRED CAPTURES,
  window open/close times, and which of them will make a paid reference capture.
* `soccer dispatch reliability --archive-dir …`: the rolling metrics above.
* `soccer dispatch close-report --archive-dir … [--fixture …]`: reference-close attempt states.
* Manual wake: Actions → kickoff-dispatch → *Run workflow* (`force` to run the capture tick regardless).
  This isn't needed in normal operation.
