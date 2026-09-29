# Pinnacle reference via The Odds API (shared account with MLB)

Status: implemented 2026-09-29, **inactive until the owner adds the secret** (one action, below). Code:
`providers/the_odds_api.py` (client), `reference/odds_budget.py` (guard + ledger),
`reference/odds_api_capture.py` (batched capture), `config/odds_api_budget.json` (limits),
`soccer dispatch tick` (runs it), `soccer odds-api status|probe`, workflows `kickoff-dispatch.yml` and
`odds-api-probe.yml`. Tests: `tests/test_odds_api_reference.py`.

## Role: reference market only

Pinnacle is an **external reference**. It is used to benchmark model probabilities, flag possible Kalshi
mispricing, measure independent closing-line value (close_v2 `TRUE_CLOSE`), and tell model disagreement
apart from exchange-specific edge. It never replaces Kalshi, which stays the complete market-discovery
surface, the execution venue, and the source of executable prices, fees and liquidity. The capture only
requests quotes for fixtures that Kalshi already lists (`run_output` fixtures in the dispatch schedule).
It does nothing for a fixture that has no Kalshi market.

## 1. Audit of the existing account (chmoses98/edge-finder-api, read at `a690f9b`, 2026-09-29)

| item | finding |
|---|---|
| secret name | `ODDS_API_KEY` (GitHub Actions secret; also a Vercel env var for `api/odds.js`, `api/slate.js`) |
| plan size | **20,000 credits per cycle**. `x-requests-used + x-requests-remaining = 20,000` on every recorded response |
| latest reading | 2026-09-29T01:03Z (`ALPHA0002_20260929T010307Z`): used **8,398**, remaining **11,602** |
| measured burn | 2026-09-02 → 09-29: used 2,120 → 8,398 = **6,278 credits in ~26 days ≈ 240/day**, account-wide (all MLB consumers). Late-season decline: 09-27 = 129, 09-28 = 42 |
| cycle reset | **not observed**. used = 2,000 at the 2026-09-02 audit, so a reset happened before that. The exact date is unknown. The soccer guard doesn't need it because it reads live `remaining` |
| cost rule (measured on this key) | live `/odds` = markets × region-equivalents, where a `bookmakers` list of ≤10 books counts as 1. Pinnacle h2h = 1 (activation audit); 4 books h2h+totals = 2 (ALPHA-0002); 4 books h2h+spreads+totals = 3 (MRV ledger). `/historical` = 10× |
| sports/markets requested | only `baseball_mlb`. No soccer sport key anywhere in the repo, so soccer can't duplicate any existing request |

Consumers and cadence:

| consumer | cadence | request | cost / call | quota headers kept? | caching |
|---|---|---|---|---|---|
| `api/odds.js` via `fetch-slate.yml` | 3×/day (16, 20, 22 UTC) + any public hit | `/odds` 5 books h2h,spreads,totals + per-game `/events/{id}/odds` (4 F5/TT markets) | 3 + 4 × games | `remaining` returned in the JSON (`creditsRemaining`), not ledgered | none |
| `api/slate.js` via `fetch-slate.yml`, `lineup-recheck.yml` | per slate build | `/odds` regions=us h2h,spreads,totals + h2h_h1 | 4 | `remaining` read, not ledgered | none |
| `clv_update.py` (`clv-update.yml`) | daily 06:00 UTC | `/scores?daysFrom=2` | small | printed to the log only | none |
| `research-mlb-alpha-0002-capture.yml` | every 10 min 15–04 UTC (GitHub delivers ~3–8/day) | `/odds` pinnacle,dk,fd,betmgm h2h,totals | 2 | **yes**, `oddsCredits` last/used/remaining per run | row change-suppression only |
| `research-mrv-prospective-capture.yml` | hourly chain, 10-min cycles (active 09-23/24) | `/odds` 4 books h2h,spreads,totals | 3 | **yes**, full append-only ledger; own guard: 450/day, 5,000 reserve | none |
| `research-sharp-market-probe.yml`, `pull_pinnacle_history.py` | manual only | `/historical` | 10× | yes, hard stop on `remaining` | file cache |

## 2. Does the existing plan support soccer reference capture?

| requirement | verdict | evidence |
|---|---|---|
| soccer competitions | **expected yes, to be confirmed by the free probe** | The Odds API doesn't restrict sports by plan. Every mapped key is checked against the free `/sports` list at run time, and an inactive or unlisted key is skipped (`SPORT_NOT_ACTIVE`) without spending anything |
| `bookmakers=pinnacle` | **yes** | proven on this key by the MLB collectors |
| h2h / 1X2 | **yes (provider standard)** | soccer `h2h` has three outcomes (home, away, `Draw`). The parser requires all three or counts the market as `incomplete_markets` |
| totals | **main line only** | one Pinnacle line per event (usually 2.5). Kalshi's other total lines (1.5, 3.5, …) get no reference. Alternate lines need the per-event endpoint and are deliberately **not** used |
| spreads (Asian handicap) | **main line only** | same limit. Each side keeps its own handicap as `line` (`home -0.5` / `away 0.5`) |

I couldn't verify this live in this session. The key isn't in this repository, and the-odds-api.com is
blocked by this session's network egress. The first `odds-api-probe` run (free) and the first captures
(ledgered) settle it. Per-competition Pinnacle coverage of totals and spreads shows up as
`incomplete_markets` in `odds_api/STATUS.json`.

## 3. Capture strategy and its credit cost

**Chosen: kickoff-timed, entry + close, batched per competition.** On each dispatcher tick, every
Kalshi-listed fixture that is

* in the **entry** window (30, 66] min before kickoff (the T-60 horizon: pre-lineup benchmark), or
* in the **close** window (0, 15] min (T-15 when it lands ≤ 15 min, else T-5; always a `TRUE_CLOSE`)

and that has no successful capture for that purpose yet is grouped by sport key. Each key costs **one** paid
`/odds` call (`bookmakers=pinnacle`, `markets=h2h,totals,spreads`, `eventIds=` every joined fixture), so
**3 credits** whatever the number of fixtures. Free `/sports` and `/events` calls come first. A key with no
joinable event never reaches a paid call. Nothing eligible means no HTTP at all.

Unit = one *cluster* (sport key × tick). Fixtures of one league that kick off together share both calls.

| scenario | calls | credits / week | ≈ credits / 30 days | share of 20k |
|---|---|---|---|---|
| **entry + close, 3 markets (chosen)**, ~60 clusters/wk in season | 2 / cluster | **360** | **~1,550** | 7.7 % |
| close only, 3 markets | 1 / cluster | 180 | ~780 | 3.9 % |
| entry + close, h2h only | 2 / cluster | 120 | ~520 | 2.6 % |
| worst case: no batching (~95 fixtures/wk, each its own kickoff) | 2 / fixture | 570 | ~2,440 → capped at 2,000 | 10 % |
| rejected: all five horizons (T-120…T-5) | 5 / cluster | 900 | ~3,860 | 19 % |
| rejected: per-game `/events/{id}/odds` | per fixture | ≥ 570 | ≥ 2,440 | no batching |

~60 clusters/week is an in-season estimate: top-5 leagues ~35 (EPL ~6 kickoff slots, La Liga ~9, Bundesliga
~5, Serie A ~8, Ligue 1 ~7), MLS/Liga MX/Brasileiro/NWSL ~20, UEFA club weeks +~10. It isn't a measurement.
The dispatch schedule on 2026-09-29 is an international window (37 fixtures, 21 clusters in 72 h, mostly
Nations League, which has a key). The real number is in the ledger after the first week (`soccer odds-api
status`). A busy Saturday (~20 clusters) costs ~120 credits, under the daily ceiling.

MLB + soccer at the in-season MLB rate: 240 + ~51 ≈ 290 credits/day ≈ 8,800 per 30 days, under 20,000.

## 4. Guard: soccer yields to MLB (`config/odds_api_budget.json`)

| limit | value | why |
|---|---|---|
| account reserve floor | **8,000 remaining** | checked against `x-requests-remaining` read **in the same tick** (the free `/sports` call returns it, and it already includes MLB's spend). Soccer stops 3,000 above the MRV collector's own 5,000 reserve, so soccer can never be what trips an MLB guard. Today that leaves soccer ≤ ~3,600 credits before a reset |
| daily ceiling (UTC) | 150 | covers a peak Saturday. Entry captures may only use 150 − 45; the last **45 are reserved for closes** (the CLV anchor) |
| rolling 30-day ceiling | 2,000 | about 1.3× the expected spend; binds only when batching fails |
| no quota evidence | block | a `/sports` response without `x-requests-remaining` means no paid call that tick |
| unknown free-endpoint cost | guarded | if a ledger row ever shows `/events` charging credits, later `/events` calls go through the same guard |

The ledger is `odds_api/budget/<UTC date>.jsonl` on `data-archive` (append-only, restored at every tick,
covered by the archive manifest). It has one row per request (free or paid) with `requests_last/used/remaining`,
HTTP status, redacted endpoint, `credits_charged` (from `x-requests-last`, or the design cost if the header
is missing or the paid call got no response), and the fixtures served. It also records blocked decisions
(`request_made: false`, reason) and `NOT_CONFIGURED` ticks. `odds_api/STATUS.json` is the latest tick
summary. Raw provider payloads are kept gzipped under `odds_api/raw/<date>/`.

Key hygiene: the key is read only from `ODDS_API_KEY`. Every URL or error that leaves the client is
redacted (`apiKey=***`), and a test asserts the key appears in no written file. The workflows pass the
secret only to the capture step. `settle-evaluate` gets just a boolean (`SOCCER_ODDS_API_CONFIGURED`).

## 5. Where the data goes

Snapshots are ordinary `ReferenceMarketSnapshot` rows (`source=the_odds_api`, `bookmaker=pinnacle`,
`source_quality=SHARP_REFERENCE`, power de-vig, `quoted_at` = Pinnacle's `last_update`) in
`reference/<date>/oddsapi-<batch>.jsonl`. They aren't change-suppressed, because an unchanged price at
T-5 is itself the close observation. The settlement's `close_v2` already reads that directory and prefers
the sharpest quality, so Pinnacle rows become the reference close with no settlement change.
`live_sharp_reference_available()` returns True where the key (or the workflow flag) is present. The
promotion gates still require the TRUE_CLOSE share and CLV evidence that these captures must accumulate.

Not done yet (deliberately): the intraday `run --fast` still takes its decision-time reference from
football-data. Joining archived Pinnacle rows to predictions for research is an offline join on
`fixture_id`.

## 6. The one owner action

Add the **same** key to this repository as an Actions secret:

> github.com/chmoses98/soccer-edge-finder → Settings → Secrets and variables → Actions → **New repository
> secret** → Name `ODDS_API_KEY`, Value = the key already used by `chmoses98/edge-finder-api`.

GitHub never shows an existing secret's value, so paste it from The Odds API account page or wherever it's
stored. Don't create a new account and don't buy more quota. Optionally, run **odds-api-probe** once
(Actions tab; free endpoints only) to confirm the soccer keys and see the current quota. After that, the
kickoff dispatcher starts capturing at the next due horizon.

If the plan proves unable to support this (for example, remaining quota near the floor before each reset),
the guard blocks soccer, logs `BLOCKED_BUDGET_GUARD` with the reason, and MLB is unaffected. Read that
result from `soccer odds-api status` and record it here rather than raising any limit.
