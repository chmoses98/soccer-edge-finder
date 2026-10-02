#!/usr/bin/env python3
"""Import a kalshi-bet-router SOCCER wager payload into data/accounting/wagers.jsonl. COUNTS ONLY.

    python scripts/accounting/import_routed_wagers.py --payload SOCCER.json \
        --base-dir <accounting-data checkout> --receipts-out receipts.json

Payload: the router's envelope ``{"importBatchId": ..., "rows": [...]}``. Identity (``wager_id``) is
minted here from ``source_bet_key``; an identical re-delivery is DUPLICATE_NOOP and changes zero bytes;
a re-delivery with different economics is CONFLICT and exits 1 so the router's merge gate fails. A row
carrying model/recommendation provenance is REFUSED as a whole: recording is not endorsing.

Actions logs are public: stdout carries counts and refusal REASONS by row position, never a ticker,
price, stake, contract count or key. Per-row receipts go only to the --receipts-out file.

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
    return run_import_cli(SPEC, "wagers", argv)


if __name__ == "__main__":
    raise SystemExit(main())
