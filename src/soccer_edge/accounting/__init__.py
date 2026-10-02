"""SOCCER routed-wager accounting: this repository's destination ledger for the kalshi-bet-router.

The router (as of 2026-10-02) delivers SOCCER wagers through the contract's SHARED ledger
(``contract/edge_finder_contract/routed_ledger.py``), parameterised here for this sport. The three
scripts under ``scripts/accounting/`` are thin wrappers over that module and this spec.

Stdlib-only on purpose: the router's runner executes those scripts WITHOUT installing this
repository, so this module imports nothing beyond the vendored contract package (which is itself
stdlib-only). It must never import pydantic/numpy-backed ``soccer_edge`` modules.

``src/soccer_edge/router`` is unrelated: it remains the PositionV1 translation layer
(docs/ROUTER_INTEGRATION.md); it is not the ledger the router writes to.
"""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
_CONTRACT_DIR = os.path.join(_REPO_ROOT, "contract")

try:
    from edge_finder_contract.routed_ledger import LedgerSpec
except (
    ImportError
):  # pragma: no cover - only when neither pytest nor the scripts put it on the path
    if _CONTRACT_DIR not in sys.path:
        sys.path.insert(0, _CONTRACT_DIR)
    from edge_finder_contract.routed_ledger import LedgerSpec

#: Wagers mint ``socw-<24hex>``, settlements ``socs-<24hex>`` (sha256 of ``source_bet_key``).
SPEC = LedgerSpec(
    sport="SOCCER",
    id_prefix="soc",
    wager_schema="soccer_accounted_wager.v1",
    settlement_schema="soccer_wager_settlement.v1",
)

#: Repository that owns this ledger (the router's ``destination_repo``).
REPO_FULL_NAME = "chmoses98/soccer-edge-finder"
#: Orphan branch the ledger lives on (``data/accounting/*.jsonl`` under its root).
LEDGER_BRANCH = "accounting-data"

__all__ = ["LEDGER_BRANCH", "REPO_FULL_NAME", "SPEC", "LedgerSpec"]
