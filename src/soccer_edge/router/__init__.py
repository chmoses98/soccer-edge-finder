"""Downstream importer for `chmoses98/kalshi-bet-router` (Phase 22: router PREPARATION).

The router never edits a destination ledger. It clones this repository, runs THIS importer
twice (the second run must change nothing), runs THIS validator, commits only what the
importer wrote under the committable prefix, and opens a pull request against the ledger
branch. Everything the router needs from this side lives in this package:

* :func:`import_wagers` -- one receipt per payload row, deterministic identity minted from
  `source_bet_key` alone, append-only JSONL, CONFLICT-never-rewrite.
* :func:`import_settlements` -- the same for the router's per-order settlement rows.
* :func:`validate_ledger` -- whole-ledger check the router runs instead of CI on a branch
  that has no `.github/`.

Nothing here makes a network call, and nothing here is wired into a router profile: no live
routing is enabled by this package existing. Stdout is counts and field NAMES only.
"""

from soccer_edge.router.identity import (
    POSITION_ID_PREFIX,
    SETTLEMENT_ID_PREFIX,
    event_ticker_for,
    mint_position_id,
    mint_settlement_id,
)
from soccer_edge.router.importer import (
    ROUTER_IMPORT_BATCH_ID,
    SOCCER_SETTLEMENT_FIELDS,
    SOCCER_WAGER_FIELDS,
    ImportOutcome,
    import_settlements,
    import_wagers,
)
from soccer_edge.router.ledger import LedgerPaths
from soccer_edge.router.validator import ValidationResult, validate_ledger

__all__ = [
    "POSITION_ID_PREFIX",
    "ROUTER_IMPORT_BATCH_ID",
    "SETTLEMENT_ID_PREFIX",
    "SOCCER_SETTLEMENT_FIELDS",
    "SOCCER_WAGER_FIELDS",
    "ImportOutcome",
    "LedgerPaths",
    "ValidationResult",
    "event_ticker_for",
    "import_settlements",
    "import_wagers",
    "mint_position_id",
    "mint_settlement_id",
    "validate_ledger",
]
