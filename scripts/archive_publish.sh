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
SRC_ABS="$(cd "$SRC" && pwd)"
HAVE_PKG=0; python -c "import soccer_edge" >/dev/null 2>&1 && HAVE_PKG=1
# Copy without deleting anything already archived. Workflows rebuild their day files from scratch, so a
# plain copy would REPLACE an archived .jsonl day file (2026-09-28: 830 prediction rows of one run were
# overwritten by the next run). .jsonl files are therefore append-merged: every archived line is kept
# and only lines not already present are appended. The live-slate pointers are merged, never blindly
# replaced (several workflows write them): the model board is a union by fixture (newer entry wins) and the
# actionable slate keeps whichever copy has the newer Kalshi observation (docs/ACTIONABLE_SLATE.md). The
# predictions index is a union (records are append-only; a payload's index can predate another writer's).
# Other files (indexes, run outputs) are copied.
apply_payload() {
  ( cd "$SRC_ABS" && find . -type f -print0 ) | while IFS= read -r -d '' rel; do
    rel="${rel#./}"; src_f="$SRC_ABS/$rel"; dst_f="$WORK/$DEST/$rel"
    mkdir -p "$(dirname "$dst_f")"
    if [[ "$rel" == *.jsonl && -s "$dst_f" ]]; then
      if [ -n "$(tail -c1 "$dst_f")" ]; then printf '\n' >> "$dst_f"; fi
      new_lines="$(mktemp)"
      awk 'NR==FNR { seen[$0]=1; next } $0 != "" && !($0 in seen) { print; seen[$0]=1 }' "$dst_f" "$src_f" > "$new_lines"
      cat "$new_lines" >> "$dst_f"; rm -f "$new_lines"
    elif [[ "$HAVE_PKG" == 1 && -s "$dst_f" && ( "$rel" == predictions/index.json || "$rel" == */predictions/index.json ) ]]; then
      # union: another writer may have archived records since this payload's index was restored
      python -m soccer_edge.cli slate merge-latest --kind index --src "$src_f" --dst "$dst_f"
    elif [[ "$HAVE_PKG" == 1 && -s "$dst_f" && "$rel" == */latest.model_board.v1.json ]]; then
      python -m soccer_edge.cli slate merge-latest --kind board --src "$src_f" --dst "$dst_f"
    elif [[ "$HAVE_PKG" == 1 && -s "$dst_f" && "$rel" == */latest.actionable_slate.v1.json ]]; then
      python -m soccer_edge.cli slate merge-latest --kind slate --src "$src_f" --dst "$dst_f"
    elif [[ "$HAVE_PKG" == 1 && -s "$dst_f" && "$rel" == */LATEST_ACTIONABLE_SLATE.md ]]; then
      :  # rewritten below from whichever slate JSON was kept
    else
      cp -f "$src_f" "$dst_f"
    fi
  done
  if [[ "$HAVE_PKG" == 1 && -f "$SRC_ABS/runs/latest.actionable_slate.v1.json" ]]; then
    python - "$WORK/$DEST/runs" <<'PY'
import sys
from pathlib import Path
from soccer_edge.contracts.slate_v1 import ActionableSlateV1
from soccer_edge.core.serialization import read_json
from soccer_edge.slate.render import render_slate_markdown
d = Path(sys.argv[1])
s = ActionableSlateV1.model_validate(read_json(d / "latest.actionable_slate.v1.json"))
(d / "LATEST_ACTIONABLE_SLATE.md").write_text(render_slate_markdown(s), encoding="utf-8")
PY
  fi
  # App export (docs/APP_EXPORT.md): the unified Edge Finder UI reads app/latest from this branch
  # (contract/edge_finder_contract/registry.json). Built from the MERGED tree so every publisher
  # carries it. It must never abort the publish: on failure the exporter writes health.json only
  # (export_failed=true), keeps the last-known-good payload and exits 1, which is logged here.
  if [[ "$HAVE_PKG" == 1 ]]; then
    python -m soccer_edge.cli app-export --data-root "$WORK/$DEST" --out "$WORK/$DEST/app/latest" \
      --commit-sha "${GITHUB_SHA:-}" --workflow-run-id "${GITHUB_RUN_ID:-}" \
      || echo "::warning::app export failed; app/latest/health.json carries the failure (payload unchanged)"
  fi
  # Research explorer (docs/APP_EXPORT.md "Research explorer"): app/latest/explorer, built from the same
  # merged tree right after the v1 export, as its own command so a research failure can never block the v1
  # payload or this publish. It reuses the v1 manifest's run_id and generated_at. On failure the previous
  # explorer tree is kept byte-identical (atomic publish), the job logs a research_export warning and the
  # step summary records it; the push of app/latest carries the explorer when it succeeded. Gated by
  # research.refresh_due (60 min): capture batches that bring no new v1 event skip the rebuild and leave
  # the ~36 MB tree untouched (publish.publish never prunes explorer/).
  if [[ "$HAVE_PKG" == 1 && -f "$WORK/$DEST/app/latest/manifest.json" ]]; then
    RX_LOG="$(mktemp)"
    if python -m soccer_edge.cli research-export --data-root "$WORK/$DEST" --out "$WORK/$DEST/app/latest" \
        --commit-sha "${GITHUB_SHA:-}" --min-interval-minutes 60 >"$RX_LOG" 2>&1; then
      RX_STATUS=ok
    else
      RX_STATUS=FAILED
      echo "::warning title=research_export::research export failed; app/latest/explorer keeps the previous tree"
    fi
    cat "$RX_LOG"
    if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
      { echo "### research_export: $RX_STATUS"; echo '```'; tail -n 3 "$RX_LOG"; echo '```'; } >>"$GITHUB_STEP_SUMMARY" || true
    fi
    rm -f "$RX_LOG"
  fi
  # Integrity: extend the manifest over the merged tree and verify it. A manifest that does not verify means
  # the archive lost or changed evidence; the publish is aborted rather than committing on top of corruption.
  # Before the manifest is bootstrapped (archive-recover.yml with init_manifest) both steps are no-ops.
  if [[ "$HAVE_PKG" == 1 ]]; then
    ( cd "$WORK" && python -m soccer_edge.cli archive manifest --archive-dir "$WORK" --if-present ) || { echo "::error::archive manifest refused (corruption)"; return 1; }
    ( cd "$WORK" && python -m soccer_edge.cli archive verify --archive-dir "$WORK" --allow-missing-manifest ) || { echo "::error::archive verify failed"; return 1; }
  else
    echo "archive: soccer_edge not importable; manifest/verify skipped"
  fi
  # size guard: refuse files > 45 MB (GH001 lesson)
  if ( cd "$WORK" && find "$DEST" -type f -size +45M | grep -q . ); then echo "::error::file over 45MB in archive payload"; ( cd "$WORK" && find "$DEST" -type f -size +45M ); return 1; fi
  ( cd "$WORK" && git add -- "$DEST" )
}
apply_payload || exit 1
cd "$WORK"
if git diff --cached --quiet; then echo "archive: nothing new"; exit 0; fi
git commit -qm "$MSG"
for attempt in 1 2 3 4; do
  if git push --quiet origin "HEAD:$BRANCH"; then echo "archive: pushed to $BRANCH"; exit 0; fi
  echo "push rejected (attempt $attempt); rebasing"
  git fetch --quiet origin "$BRANCH" || { echo "::error::fetch failed"; exit 1; }
  if ! git rebase --quiet "origin/$BRANCH"; then
    # both sides changed a mutable pointer (e.g. the latest slate): re-apply this payload onto the new tip
    # with the same merge rules instead of failing the publish
    echo "rebase conflict; re-applying the payload onto origin/$BRANCH"
    git rebase --abort || true
    git reset --quiet --hard "origin/$BRANCH"
    apply_payload || exit 1
    if git diff --cached --quiet; then echo "archive: nothing new after re-apply"; exit 0; fi
    git commit -qm "$MSG"
  fi
  sleep $((attempt * 3))
done
echo "::error::archive push failed after retries"; exit 1
