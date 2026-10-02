#!/usr/bin/env python3
"""Import a kalshi-bet-router SOCCER settlement payload into data/accounting/settlements.jsonl. COUNTS ONLY.

    python scripts/accounting/import_routed_settlements.py --payload SOCCER-settlements.json \
        --base-dir <accounting-data checkout> --receipts-out receipts.json

Payload: ``{"settlements": [...]}`` rows under router-settlement-economics.v2 (the only version
accepted). A settlement whose ``source_bet_key`` is not on the SOCCER wager ledger is refused as
ORPHAN. An identical repeat is DUPLICATE_NOOP (zero bytes change); a different settlement for an
already-settled wager is CONFLICT; either refusal exits 1. stdout never carries a ticker, payout,
P&L or key.

Stdlib only: the router's runner installs nothing from this repository.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_ROOT, "contract"), os.path.join(_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from edge_finder_contract.routed_ledger import run_import_cli  # noqa: E402

from soccer_edge.accounting import SPEC  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    return run_import_cli(SPEC, "settlements", argv)


if __name__ == "__main__":
    raise SystemExit(main())
