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

## Update 2026-09-28 (Phase 2): the downstream importer exists; routing is still OFF

Router `main` re-audited 2026-09-28: unchanged at `2322bd7` (single squashed commit; nothing
in `destinations.py`, `production.py`, `destination.py`, `receipts.py` or the delivery bash
moved since the 2026-09-27 audit). Everything the router's `DestinationProfile` docstrings
demand of a destination is now built on THIS side. **No live routing is enabled by this
change**: there is no `PROFILES[Sport.SOCCER]`, no `ROW_BUILDERS["SOCCER"]`, no `Sport.SOCCER`,
and this repository still never places, routes or settles a real order. The importer runs
only when the router (or a person) invokes it against a payload file.

### What is built here (`src/soccer_edge/router/`)

| Piece | CLI | Contract it satisfies |
|---|---|---|
| Wager importer (`importer.import_wagers`) | `soccer import-wagers <payload.json> --ledger-root <dir> --receipts-out <file> [--season <ignored>]` | payload `{"importBatchId": "kalshi-router-v1", "rows": [...]}` in the NFL/CFB snake_case dialect; the vocabulary is the explicit frozenset `SOCCER_WAGER_FIELDS` (`source_bet_key, import_batch_id, entry_method, game_date, market_ticker, side YES/NO, executed_at, contracts, actual_price` **or** `execution_price` (exactly one), `stake, fees_paid, fees_are_estimated, venue`, optional NFL evidence `fee_state, execution_action`). Any other field, and any field whose name claims model provenance (`model_*`, `fair_*`, `edge_*`, `probability*`, `recommendation*`, `prediction_*`, `thesis`, `authority`, `confidence*`), refuses that row. Money is parsed via `Decimal(str(x))` and stays Decimal; the ledger stores strings. |
| Settlement importer (`importer.import_settlements`) | `soccer import-settlements <payload.json> --ledger-root <dir> --receipts-out <file> [--season <ignored>]` | payload `{"settlements": [...]}` with the router's `_settlement_row` shape (`source_bet_key, market_ticker, side, settlement_status, settled_at, result WON/LOST/null, gross_return, net_profit_loss, refusals[], venue, economics_version?`). An orphan (no filed position for the key) is REFUSED per row; a row whose `market_ticker`/`side` disagree with the filed position is REFUSED; `result: null` (void/abandoned) is accepted as outcome `void` with `realised_pnl: null`. |
| Validator (`validator.validate_ledger`) | `soccer validate-positions-ledger --ledger-root <dir> [--result-out <file>]` | whole-ledger: JSONL parse, `PositionV1`/`SettlementV1` pydantic validation, unique ids, `position_id == mint(source_bet_key)`, settlements reference filed positions, wagers sit in their `game_date` year file, no file under the root other than `wagers/<YYYY>.jsonl` and `settlements/<YYYY>.jsonl`. Exit 1 on any violation; prints counts by violation kind. |
| Shim | `python scripts/kalshi_router_import.py <subcommand> ...` | puts `src/` on `sys.path` so the CLI runs with the router's `cd {work}` and a separate `{code}` checkout, exactly like the NFL/CFB profiles' script paths. |

Identity: `position_id = "pos_" + sha256(source_bet_key)[:24]`, `settlement_id = "stl_" + ...`
-- a function of the router's key alone, never of a clock or a row index, so a re-delivery
lands on the same record and the validator can re-derive every id.

Receipts (`--receipts-out`): `{"importBatchId", "written", "alreadyPresent", "conflicts",
"refused", "rows": [{source_bet_key, wager_id | settlement_id, status, success,
conflicting_fields: [names], reason}]}` -- a shape `kalshi_router.receipts.normalise` reads as
is (`rows` list, `status` verdict, `wager_id`/`settlement_id` identity, `conflicting_fields`
as strings). Verdicts: `NEW`, `DUPLICATE_NOOP` (identical re-delivery; no byte of the ledger
changes -- the file is not even opened for writing), `CONFLICT` (a filed record disagrees on an
economic field: `game_date, market_ticker, side, executed_at, contracts, price, stake,
fees_paid, fees_are_estimated, venue`; the filed record is never rewritten and the receipt
names the fields, never the values), `REFUSED` (reason is a field/shape name such as
`unknown_field:x`, `model_provenance_field:x`, `missing_field:x`, `invalid_value:side`,
`import_batch_id:disagrees_with_envelope`, `orphan:source_bet_key`). A refused or conflicting
row never blocks the others; exit status is 1 if any row was REFUSED or CONFLICT, 2 if the
payload itself was unreadable (empty receipts written), else 0. A second identical import
therefore produces a byte-identical tree (`git write-tree` unchanged), which is the router's
idempotency proof. Appends go through a same-directory temp file and `os.replace`; nothing is
sorted or re-serialised; the importer leaves no residue (nothing to `.gitignore`).

Ledger record (one JSON line, sorted keys):
`{"schema": "soccer_routed_wager.v1", "source_bet_key", "position": <PositionV1>, "imported": <the normalised row>}`
and `{"schema": "soccer_routed_settlement.v1", "source_bet_key", "settlement": <SettlementV1>, "imported": <row>}`.
`PositionV1.source = "kalshi-router"`, `sport = "soccer"`, `recommendation_id = null` always
(recording is not endorsing), `status = "open"`. **`event_id` is the Kalshi event ticker**
derived offline from the market ticker (`KXEPLGAME-26OCT10ARSLEE-ARS` -> `KXEPLGAME-26OCT10ARSLEE`);
resolving it to an `fx:` fixture id needs the fixture data on `main` at run time and is left
to the consumer, which can join on `market_ticker`. `SettlementV1.outcome` is the MARKET
result implied by the wager's side and `WON`/`LOST` (`yes`/`no`), `void` for `result: null`;
`agrees_with_kalshi` stays `null` because this repo did not independently settle the market;
`refusal_reason` carries the router's refusal codes joined by commas; `realised_pnl` is the
router's `net_profit_loss`. Settlements shard by the POSITION's `game_date` year so a fixture's
wager and settlement share a file.

Privacy: stdout/stderr carry counts and field names only (`tests/test_router_importer.py`
captures a full import and asserts no ticker, key, price, stake, id or date appears). Values
exist only in the ledger file and the receipts file, both of which the router keeps off logs.

### The `PROFILES[Sport.SOCCER]` a future router PR would add (owner's decision, not made here)

```python
Sport.SOCCER: DestinationProfile(
    sport=Sport.SOCCER,
    repo="chmoses98/soccer-edge-finder",
    ledger_branch="data-archive",          # the private archive branch; NEVER main
    code_branch="main",                    # importer source lives on main: two checkouts
    wager_importer=(
        "python", "{code}/scripts/kalshi_router_import.py", "import-wagers", "{payload}",
        "--ledger-root", "{work}/archive/positions", "--receipts-out", "{receipts}",
    ),
    settlement_importer=(
        "python", "{code}/scripts/kalshi_router_import.py", "import-settlements", "{payload}",
        "--ledger-root", "{work}/archive/positions", "--receipts-out", "{receipts}",
    ),
    ledger_validator=(
        "python", "{code}/scripts/kalshi_router_import.py", "validate-positions-ledger",
        "--ledger-root", "{work}/archive/positions", "--result-out", "{receipts}",
    ),
    committable_prefixes=("archive/positions/",),
    mergeable_paths=frozenset(
        {f"archive/positions/wagers/{y}.jsonl" for y in range(2026, 2036)}
        | {f"archive/positions/settlements/{y}.jsonl" for y in range(2026, 2036)}
    ),
    # or, equivalently, as patterns (the validator enforces exactly these shapes):
    mergeable_patterns=(
        r"archive/positions/wagers/20\d{2}\.jsonl",
        r"archive/positions/settlements/20\d{2}\.jsonl",
    ),
    record_layout="jsonl",
    ledger_branch_runs_ci=False,           # data-archive is an orphan with no .github/
    row_identity_field="source_bet_key",
    requires_season=False,                 # ledger is per calendar year; --season is ignored
    settlement_economics="router-settlement-economics.v2",  # economics_version accepted and compared
    auto_merge=False,                      # observation period: a person reads the first deliveries
)
```

`{season}` is not in any template; the CLI accepts `--season` and ignores it so a router that
passes it anyway is not refused. The ledger root `archive/positions/` was chosen so the
committable prefix is a single directory that nothing else on `data-archive` (`snapshots/`,
`predictions/`, `runs/`, `reference/`) shares; if the owner prefers `positions/` at the branch
root, the change is one argv token and the prefix. Append-only is the whole permission: the
router's gate reads added lines of the mergeable paths, and any modified or deleted line is a
rewrite it refuses.

### What remains on the owner's side (nothing here does any of it)

1. **Router PR, classifier half** (safe on its own): `Sport.SOCCER`, taxonomy-level
   resolution, keep the `football` family `{NFL, CFB}` ambiguous, counters in `wager.py` /
   `aggregate.py`, `series_probe` corroborating tokens. Soccer then becomes
   `NO_DESTINATION_IMPORTER` instead of today's `BLOCKED`.
2. **Router PR, destination half**: `to_soccer_import_row` (copy the NFL builder; emit
   `actual_price`), `ROW_BUILDERS["SOCCER"]`, `LEDGER_VOCABULARIES["SOCCER"]` (must equal
   `SOCCER_WAGER_FIELDS` minus the optional evidence fields), the profile above, the repo in
   `downstream-credential-probe.yml` and `test_workflow_safety.py`, and an end-to-end fixture
   like `test_cfb_delivery_end_to_end.py` driving this importer.
3. **Runner dependencies**: the router's workflows `pip install` only the router. This
   importer needs `pydantic` (and `numpy` through the CLI module); the delivery step must
   `pip install {code}` (or an equivalent) before the argv runs, or the profile cannot be
   activated. Not solvable from this repository.
4. **Token scoping**: re-scope `DOWNSTREAM_REPO_TOKEN` to include `chmoses98/soccer-edge-finder`
   (Contents + Pull requests write) and run the credential probe.
5. **Branch**: create `archive/positions/` on `data-archive` (or let the first delivery
   create it); confirm `data-archive` protection allows the router's `kalshi-router/SOCCER`
   PR. The ledger never lives on `main`.
6. **Observation**: keep `auto_merge=False` and read the first real deliveries and the
   validator verdicts; only then flip it.

Open questions for the owner: (a) Kalshi's live taxonomy heading and competition names for
soccer are still unverified in the router; (b) a v1-vs-v2 `economics_version` difference on
re-delivery is treated as `CONFLICT` here (NFL answers it with an append-only amendment) --
acceptable while no v1 settlement has ever been filed, revisit if the router ever sends v1
first; (c) whether `event_id` should be resolved to an `fx:` fixture id at import time once
the ledger and the fixture registry are readable from one place.

## Update (remediation phase 25): compatibility with the remediated contracts

`tests/test_router_e2e.py` runs a synthetic end-to-end path: a RUN SOCCER output under app contract
1.2.0 (additive fields `model_posterior_edge_share`, `selection_policy`, `edge_v2_*`, `no_bets` true), a
router wager payload built from its shadow recommendations, `soccer import-wagers`,
`soccer import-settlements` and `soccer validate-positions-ledger`. Two properties are pinned: the new
fields do not break the importer, and a wager row that carries `prediction_record_id` (or any other
model-provenance field) is refused as a whole, because the router must never claim model provenance; the
join to prediction records happens in evaluation by ticker, side and time. No live routing exists, no
routing was activated, and the settlement records written by `soccer settle` are independent of the
router's settlement rows.

## Update 2026-10-02: the router delivers through the contract's shared ledger

The kalshi-bet-router now files SOCCER wagers and settlements through the SHARED destination ledger
of the vendored contract (`contract/edge_finder_contract/routed_ledger.py`), on the orphan
`accounting-data` branch (`data/accounting/wagers.jsonl`, `settlements.jsonl`), via the stdlib-only
wrappers `scripts/accounting/import_routed_wagers.py`, `import_routed_settlements.py` and
`validate_routed_ledger.py` with `LedgerSpec(sport="SOCCER", id_prefix="soc", ...)` -- see
docs/ACCOUNTING.md. `src/soccer_edge/router` and the `soccer import-wagers` / `import-settlements` /
`validate-positions-ledger` commands are untouched: they remain this repository's PositionV1
translation layer and are not the ledger the router writes to. The app export (docs/APP_EXPORT.md)
reads the shared ledger, not `archive/positions`.
