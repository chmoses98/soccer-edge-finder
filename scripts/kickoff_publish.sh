#!/usr/bin/env bash
# Publish a kickoff-dispatch work dir to data-archive (append-only). Used after EVERY capture batch by a
# chained tick (so an interrupted link loses nothing) and once more by the workflow's final step.
# usage: scripts/kickoff_publish.sh <work_dir> "<commit message>"
set -euo pipefail
WORK="$1"; MSG="$2"
rm -f "$WORK/snapshots/latest_catalog.json"
rm -rf "$WORK/results" "$WORK/fixtures/espn" "$WORK/simcache" 2>/dev/null || true   # espn-sync side outputs: the lineups job owns those
# fast-run outputs: ledger day files + index, run outputs (no priced_contracts / diagnostics copies)
if [ -d "$WORK/ledger" ]; then
  mkdir -p "$WORK/predictions"
  for f in $(find "$WORK/ledger" -name 'predictions.jsonl'); do d=$(basename "$(dirname "$f")"); mkdir -p "$WORK/predictions/$d"; cat "$f" >> "$WORK/predictions/$d/predictions.jsonl"; done
  cp -f "$WORK/ledger/index.json" "$WORK/predictions/index.json" 2>/dev/null || true
  rm -rf "$WORK/ledger"
fi
if [ -d "$WORK/runs" ]; then
  # model-refresh runs live under runs/<day>/<run_id>/ (archive verify resolves run_ids there); older fast
  # runs used runs/<batch_id>/. Neither publishes the ledger duplicate or the reconstructible diagnostics.
  find "$WORK/runs" -mindepth 2 -maxdepth 3 \( -name priced_contracts.json -o -name coverage_diagnostics.json \) -delete
  rm -rf "$WORK/runs/_pending"
fi
[ -d "$WORK/dispatch" ] || exit 0
"$(dirname "$0")/archive_publish.sh" "$WORK" . "$MSG"
