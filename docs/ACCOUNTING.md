# Routed-wager accounting ledger (SOCCER)

The kalshi-bet-router (as of 2026-10-02) delivers SOCCER wagers through the contract's **shared
ledger** -- `contract/edge_finder_contract/routed_ledger.py`, the generalisation of
NHL-edge-finder's `nhl_edge.accounting.ledger` -- parameterised for this sport by
`src/soccer_edge/accounting/__init__.py`:

    LedgerSpec(sport="SOCCER", id_prefix="soc",
               wager_schema="soccer_accounted_wager.v1", settlement_schema="soccer_wager_settlement.v1")

Wagers mint `socw-<24 hex>` and settlements `socs-<24 hex>` from `sha256(source_bet_key)`.

`src/soccer_edge/router` is **not** this ledger: it remains the PositionV1 translation layer
(`soccer import-wagers` / `import-settlements` / `validate-positions-ledger`, docs/ROUTER_INTEGRATION.md)
and is untouched.

## Where

Orphan branch `accounting-data` (no `.github/`, no code), files `data/accounting/wagers.jsonl` and
`data/accounting/settlements.jsonl`, append-only, one JSON object per line, sorted keys. The router
clones that branch, runs the importers below with `--base-dir <checkout>`, runs the validator, and
commits/pushes under its own merge gate. Nothing in this repository writes to the branch.

## Scripts (stdlib only -- the router's runner installs nothing from this repository)

    python scripts/accounting/import_routed_wagers.py      --payload SOCCER.json             --base-dir <checkout> --receipts-out receipts.json
    python scripts/accounting/import_routed_settlements.py --payload SOCCER-settlements.json --base-dir <checkout> --receipts-out receipts.json
    python scripts/accounting/validate_routed_ledger.py    --base-dir <checkout> [--base-ref origin/accounting-data] --result-out result.json

Each puts `<repo>/contract` and `<repo>/src` on `sys.path` and calls `run_import_cli` /
`run_validate_cli` with the spec. `tests/test_routed_accounting.py` runs them by subprocess with
`pydantic`, `numpy`, `scipy` and `httpx` blocked in `sys.modules`, proving the stdlib-only claim.

## Verdicts and exit codes

| verdict | meaning | bytes written | exit |
| --- | --- | --- | --- |
| NEW | first delivery of this `source_bet_key` | one line appended | 0 |
| DUPLICATE_NOOP | identical re-delivery (the router runs every import twice as an idempotency proof) | none | 0 |
| CONFLICT | same key, different economics; **an existing row is never rewritten** | none | 1 |
| REFUSED | unfilable row: missing/invalid field, model or recommendation provenance, orphan settlement | none | 1 |

Exit 2 means the payload or ledger was unreadable. A wager row says the owner placed a bet; it carries
no model provenance, and a row that tries to (`recommendation_id`, `model_probability`, `edge`, ...) is
refused as a whole. A settlement must reference a wager already on the SOCCER ledger (ORPHAN
otherwise), under `router-settlement-economics.v2`, with either established money (`gross_return` and
`net_profit_loss`) or `refusals`, never both.

## Privacy

Actions logs are public. stdout carries counts and refusal reasons by row position only -- never a
ticker, price, stake, contract count, P&L or `source_bet_key`. Per-row receipts (key, minted id,
verdict) go only to `--receipts-out`; the validator's reasons name a file and line number.

## Consumers

`soccer app-export --accounting-dir <checkout>` reads both files with `routed_ledger.read_jsonl` and
publishes them as contract wagers / settlements (docs/APP_EXPORT.md): `source = KALSHI_ROUTER`,
settlements `EXCHANGE_CONFIRMED` when money is established, temporal links to the model price and
recommendation that predate `placed_at`. Recording is not endorsing: the SOCCER model is RESEARCH_ONLY
and is not involved in any wager.
