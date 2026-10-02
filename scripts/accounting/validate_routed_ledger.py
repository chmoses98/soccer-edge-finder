#!/usr/bin/env python3
"""Validate the SOCCER routed-wager ledger: the destination's own verdict on its own data. COUNTS AND REASONS ONLY.

    python scripts/accounting/validate_routed_ledger.py --base-dir <accounting-data checkout> \
        [--base-ref origin/accounting-data] [--result-out result.json]

Checks: every line decodes; wager and settlement schemas (incl. no model/recommendation provenance
field); source_bet_key unique per file; every settlement has its wager; with --base-ref (a git ref
resolvable in --base-dir) both files are APPEND-ONLY relative to that ref.

accounting-data carries no .github/, so a pull request into it gets no CI; kalshi-bet-router runs
this after its import and the exit status is the verdict (0 pass, 1 fail, 2 unreadable). Failures
name a file and LINE NUMBER and a reason, never a ticker, stake, price, P&L or key.

Stdlib only: the router's runner installs nothing from this repository.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_ROOT, "contract"), os.path.join(_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from edge_finder_contract.routed_ledger import run_validate_cli  # noqa: E402

from soccer_edge.accounting import SPEC  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    return run_validate_cli(SPEC, argv)


if __name__ == "__main__":
    raise SystemExit(main())
