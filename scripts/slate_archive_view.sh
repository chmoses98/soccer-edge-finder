#!/usr/bin/env bash
# Minimal read-only view of data-archive for a reprice (docs/ACTIONABLE_SLATE.md): the model board and the
# latest slate, the dispatch schedule, recent ESPN fixtures, lineups and Pinnacle rows, the lineup-sync
# status. A blobless sparse clone downloads only those files (a few MB) instead of the whole archive.
# usage: scripts/slate_archive_view.sh <dest_dir>
set -euo pipefail
DEST="$1"
BRANCH="${ARCHIVE_BRANCH:-data-archive}"
if [ -n "${GITHUB_TOKEN:-}" ] && [ -n "${GITHUB_REPOSITORY:-}" ]; then
  REMOTE_URL="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
else
  REMOTE_URL="$(git config --get remote.origin.url)"
fi
rm -rf "$DEST"
PATTERNS=("/runs/latest.*" "/dispatch/schedule.json" "/STATUS.json")
for back in 0 1 2; do
  d="$(date -u -d "-${back} day" +%Y-%m-%d)"
  PATTERNS+=("/fixtures/espn/$d/" "/lineups/$d/" "/reference/$d/")
done
if git clone --quiet --depth 1 --filter=blob:none --sparse --branch "$BRANCH" "$REMOTE_URL" "$DEST" 2>/dev/null \
   && git -C "$DEST" sparse-checkout set --no-cone "${PATTERNS[@]}"; then
  echo "slate view: sparse $(du -sh "$DEST" | cut -f1)"
else
  rm -rf "$DEST"
  git clone --quiet --depth 1 --branch "$BRANCH" "$REMOTE_URL" "$DEST" || mkdir -p "$DEST"
  echo "slate view: full clone fallback"
fi
