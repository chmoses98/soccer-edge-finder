#!/usr/bin/env python3
"""Entry point for `chmoses98/kalshi-bet-router`: the `soccer` CLI, runnable from any cwd.

The router runs a destination's importer with the LEDGER checkout as the working directory and
this repository's code in a separate checkout (`{code}`), so `python -m soccer_edge.cli` would
not resolve. This shim puts `<repo>/src` on `sys.path` and dispatches unchanged:

    python {code}/scripts/kalshi_router_import.py import-wagers {payload} \\
        --ledger-root {work}/archive/positions --receipts-out {receipts}
    python {code}/scripts/kalshi_router_import.py import-settlements {payload} \\
        --ledger-root {work}/archive/positions --receipts-out {receipts}
    python {code}/scripts/kalshi_router_import.py validate-positions-ledger \\
        --ledger-root {work}/archive/positions --result-out {receipts}

It adds no behaviour of its own. This repository's runtime dependencies (pydantic; numpy via the
CLI module) must be importable in the router's runner -- see docs/ROUTER_INTEGRATION.md.
No live routing is enabled by this file existing.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from soccer_edge.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
