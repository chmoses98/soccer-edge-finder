# Kalshi router integration plan (SOCCER)

Audit of `chmoses98/kalshi-bet-router` (2026-09-27):

* `Sport` enum (`src/kalshi_router/sports.py`) has no `SOCCER`. Classification is an evidence
  hierarchy in `classify.py` (event competition → live taxonomy sport heading → milestones →
  series tag tokens → exact-match series registry); no prefix matching.
* Soccer is explicitly **out of scope** today: `"soccer"` in `COMPETITION_OUT_OF_SCOPE` and
  `OUT_OF_SCOPE_SPORTS` (`competitions.py`), and league tokens (`premier league, epl, uefa, mls,
  la liga, bundesliga, serie a, ligue 1, world cup, football club`) in `NON_TARGET_SPORT_TOKENS`.
  Soccer fills classify as `OTHER` (never misrouted to NFL/CFB); a bare `Football` tag is the
  ambiguous family `{NFL, CFB}` and fails closed. Side effect: `production.evaluate_order` treats
  `OTHER` like `UNRESOLVED`, so post-cutover soccer orders flip the scheduled run's health to
  `BLOCKED`.
* Delivery is not `repository_dispatch`: the router clones the destination, runs the destination's
  own importer twice (idempotency proof), runs its validator, commits only under
  `committable_prefixes`, pushes `kalshi-router/<SPORT>`, opens a PR, and a pure gate squash-merges.
  Payload: `{"importBatchId": "kalshi-router-v1", "rows": [...]}`. Settlement rows flow via
  `settle-wagers.yml` for profiles with a `settlement_importer`. Bankroll publishing is MLB-only.

## Verdict

Not implemented in this mission because the production write path is not yet safe:

1. **Safe now (separate router PR, when the owner wants it):** add `Sport.SOCCER`; make soccer
   resolve at the taxonomy sport level (like tennis) and via soccer competition names; keep the
   `football` family `{NFL, CFB}` so ambiguous football/soccer metadata stays `UNRESOLVED`; update
   the routable counters in `wager.py` (they KeyError on a new enum member) and `aggregate.py`;
   pin with tests. Without a row builder, soccer becomes `NO_DESTINATION_IMPORTER` (NOT_ROUTABLE),
   which is quieter than today's `BLOCKED`.
2. **Not yet safe:** `PROFILES[Sport.SOCCER]`, `ROW_BUILDERS["SOCCER"]`,
   `LEDGER_VOCABULARIES["SOCCER"]`. These require, on this side: a wager importer and a settlement
   importer with per-row receipts (`source_bet_key`, minted id, `NEW/DUPLICATE_NOOP/CONFLICT/REFUSED`),
   deterministic ids from `source_bet_key`, CONFLICT-never-rewrite, a whole-ledger validator, and
   append-only paths matching `mergeable_patterns`; and on the owner's side a re-scoped
   `DOWNSTREAM_REPO_TOKEN` plus the credential probe listing this repo. Do not set `requires_season`
   (season month is a global CFB constant there).

## Contracts this repo will expose for the router

* `PositionV1` (import target) and `SettlementV1` (export) in `docs/APP_CONTRACT.md`.
* Importer CLI (`soccer import-wagers <payload.json>`) and validator — **not built yet**; they are
  the first item once the owner decides soccer fills should route here.
* Privacy: positions are written only to the private archive branch/bucket, never to `main`;
  bankroll numbers are never written to this public repository (the router's redacted-but-fresh
  semantics apply).
