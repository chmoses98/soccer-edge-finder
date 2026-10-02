#!/usr/bin/env python3
"""Export the SOCCER app payload (docs/APP_EXPORT.md). Thin wrapper over ``soccer app-export``.

    python scripts/app_export.py --data-root <archive root> --out <archive root>/app/latest \
        [--accounting-dir <accounting-data checkout>] [--now <iso>] [--commit-sha X] [--workflow-run-id Y]

Reads the data-archive's merged live slate, latest run output, model board and status pointers (plus
the routed-wager ledger when --accounting-dir is given) and publishes the contract documents
atomically. On any failure only health.json is written (export_failed) and the exit status is 1.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_ROOT, "contract"), os.path.join(_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from soccer_edge.app_export import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
