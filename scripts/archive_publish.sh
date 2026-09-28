#!/usr/bin/env bash
# Publish files to the append-only `data-archive` orphan branch.
# usage: scripts/archive_publish.sh <src_dir> <dest_subdir> "<commit message>"
# Lessons applied: artifact is uploaded by the caller BEFORE this runs; scoped `git add`; queue-not-cancel
# concurrency is set by the workflow; rebase before push; never `|| true` the push.
set -euo pipefail
SRC="$1"; DEST="$2"; MSG="$3"
BRANCH="${ARCHIVE_BRANCH:-data-archive}"
WORK="$(mktemp -d)"
git config --global user.name "soccer-edge-bot"
git config --global user.email "soccer-edge-bot@users.noreply.github.com"
# A fresh clone does not inherit actions/checkout's auth header; use the workflow token explicitly.
if [ -n "${GITHUB_TOKEN:-}" ] && [ -n "${GITHUB_REPOSITORY:-}" ]; then
  REMOTE_URL="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
else
  REMOTE_URL="$(git config --get remote.origin.url)"
fi
if git ls-remote --exit-code --heads "$REMOTE_URL" "$BRANCH" >/dev/null 2>&1; then
  git clone --quiet --depth 1 --branch "$BRANCH" "$REMOTE_URL" "$WORK"
else
  git clone --quiet --depth 1 "$REMOTE_URL" "$WORK"
  ( cd "$WORK" && git checkout --quiet --orphan "$BRANCH" && git rm -rfq . >/dev/null 2>&1 || true
    printf '# data-archive\n\nAppend-only archive branch for soccer-edge-finder (snapshots, predictions, settlements, runs).\nSee docs/STORAGE_STRATEGY.md on main.\n' > README.md
    git add README.md && git commit -qm "archive: bootstrap" )
fi
mkdir -p "$WORK/$DEST"
# Copy without deleting anything already archived. Workflows rebuild their day files from scratch, so a
# plain copy would REPLACE an archived .jsonl day file (2026-09-28: 830 prediction rows of one run were
# overwritten by the next run). .jsonl files are therefore append-merged: every archived line is kept
# and only lines not already present are appended. Other files (indexes, run outputs) are copied.
SRC_ABS="$(cd "$SRC" && pwd)"
( cd "$SRC_ABS" && find . -type f -print0 ) | while IFS= read -r -d '' rel; do
  rel="${rel#./}"; src_f="$SRC_ABS/$rel"; dst_f="$WORK/$DEST/$rel"
  mkdir -p "$(dirname "$dst_f")"
  if [[ "$rel" == *.jsonl && -s "$dst_f" ]]; then
    if [ -n "$(tail -c1 "$dst_f")" ]; then printf '\n' >> "$dst_f"; fi
    new_lines="$(mktemp)"
    awk 'NR==FNR { seen[$0]=1; next } $0 != "" && !($0 in seen) { print; seen[$0]=1 }' "$dst_f" "$src_f" > "$new_lines"
    cat "$new_lines" >> "$dst_f"; rm -f "$new_lines"
  else
    cp -f "$src_f" "$dst_f"
  fi
done
cd "$WORK"
# size guard: refuse files > 45 MB (GH001 lesson)
if find "$DEST" -type f -size +45M | grep -q .; then echo "::error::file over 45MB in archive payload"; find "$DEST" -type f -size +45M; exit 1; fi
git add -- "$DEST"
if git diff --cached --quiet; then echo "archive: nothing new"; exit 0; fi
git commit -qm "$MSG"
for attempt in 1 2 3 4; do
  if git push --quiet origin "HEAD:$BRANCH"; then echo "archive: pushed to $BRANCH"; exit 0; fi
  echo "push rejected (attempt $attempt); rebasing"
  git fetch --quiet origin "$BRANCH" && git rebase --quiet "origin/$BRANCH" || { echo "::error::rebase failed"; exit 1; }
  sleep $((attempt * 3))
done
echo "::error::archive push failed after retries"; exit 1
