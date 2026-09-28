"""Every workflow argv must parse: a flag the pipeline reads but the parser lacks is a production outage."""

from __future__ import annotations

import pytest

from soccer_edge.cli import build_parser

WORKFLOW_ARGV = [
    # run-soccer.yml
    "run --window 48 --out-dir w/out --archive-dir w/ledger --sim-cache w/simcache --reference-dir w/reference --espn-dir espn_archive",
    "run --window 48 --out-dir w/out --no-reference --no-freshness-gate --league eng.premier_league --date 2026-10-01",
    # kalshi-capture.yml / kalshi-discover.yml
    "capture --fast --status open --out-dir w/snapshots",
    "capture-reference --out-dir w/reference",
    "discover --out artifacts/catalog.json",
    "reconcile-discovery --fast a.json --full b.json --out r.json",
    # settle-evaluate.yml
    "settle --archive-dir a/predictions --snapshots-dir a/snapshots --settlements-dir a/settlements --reference-dir a/reference --out-dir w/evaluation",
    "microstructure --snapshots-dir a/snapshots --out w/m.json",
    "replay-policies --archive-dir a/predictions --settlements-dir a/settlements --out w/p.json",
    # espn-lineups.yml / espn-backfill.yml
    "espn-sync --out-dir w/espn",
    "espn-backfill --leagues usa.1,mex.1 --start 2024-07-01 --out-dir w/espn",
    # router
    "import-wagers payload.json --ledger-root w/ledger --receipts-out w/r.json",
    "import-settlements payload.json --ledger-root w/ledger --receipts-out w/r.json",
    "validate-positions-ledger --ledger-root w/ledger",
    "export-schemas --out w/schemas",
]


@pytest.mark.parametrize("argv", WORKFLOW_ARGV)
def test_workflow_argv_parses(argv):
    parser = build_parser()
    ns = parser.parse_args(argv.split())
    assert callable(ns.func)
