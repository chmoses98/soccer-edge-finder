#!/usr/bin/env python3
"""Export the SOCCER research explorer (docs/APP_EXPORT.md, "Research explorer"). Thin wrapper over
``soccer research-export``; run it right after ``app-export`` against the same archive root:

    python scripts/research_export.py --data-root <archive root> --out <archive root>/app/latest \
        [--now <iso>] [--commit-sha X]

Reads the v1 payload under --out plus the archive's captures, ledgers, results, lineups and weather and
publishes <out>/explorer atomically. On failure the previous explorer tree is untouched and the exit
status is 1; the v1 payload is never modified.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_ROOT, "contract"), os.path.join(_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from soccer_edge.research_export import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
