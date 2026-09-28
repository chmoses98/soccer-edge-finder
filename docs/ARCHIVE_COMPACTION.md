# Archive compaction and growth

Remediation phase 22 (audit §O). Measured baseline: 30 MB / 65 files after 13.5 h; projection with crons
firing 65–100 MB/day uncompressed, 6–9 MB/day packed ⇒ **2.5–3.5 GB/year of git history**.

## What changed

1. **Stop committing redundant copies** (largest saving, ≈ 70 % of daily growth):
   `runs/<day>/<run>/priced_contracts.json` (5.7 MB/run; every field is on the prediction ledger),
   `coverage_diagnostics.json` (0.9 MB/run; reconstructible from the run output + catalog) and
   `runs/LATEST_RUN_SOCCER.md` are no longer published. They stay in the 14-day Actions artifact of the run.
   `runs/latest.run_output.v1.json` stays (a ~150 KB pointer the kickoff dispatcher reads).
2. **ESPN fixtures dumps are archived only on content change** (audit §O4): the 2-hourly sync compares the
   new dump (minus its timestamp) with the last archived one and drops it when identical.
3. **Closed day files are gzipped** (`soccer archive compact`, `archive-compact.yml` monthly + dispatch):
   `.jsonl` → `.jsonl.gz` (deterministic gzip), manifest-aware. The manifest entry keeps the uncompressed
   byte length and prefix hash (verified by decompressing) plus the gzip hash, so the verifier detects any
   change to the compacted file; the recovery tool, settlement and evaluation readers accept both forms
   (`archive/compact.py::read_jsonl_any`). Expected ratio 6–10× on prediction/snapshot rows.
4. The **simulation cache** persists across runs via `actions/cache` (entries are keyed by the content
   hash of every input that changes fair probabilities: posterior, world and sim config, fixture).

Expected steady state after 1–3: ~10–15 MB/day uncompressed of genuinely new evidence, < 2 MB/day packed.
The manifest's record rows add ~300 B per evidence record and are compacted with their day files.

## Repository-history implications (read before expecting the branch to shrink)

* Git history does not shrink when files are deleted or compressed: everything already committed
  (~35 MB uncompressed / ~3 MB packed at the audit, plus what has landed since) stays in the pack forever
  unless history is rewritten.
* **No history rewrite is performed or planned here.** `data-archive` is the evidence branch; rewriting it
  would invalidate every recovery manifest's origin commit/blob references and every point-in-time
  reproduction. If a rewrite is ever authorised by the owner, the audit's plan (§O6) applies: a new orphan
  branch generation with a manifest mapping old paths → new, the old branch kept read-only as a tag.
* Monthly compaction combines nothing across days on purpose (one file per day keeps the manifest and the
  recovery tool simple); combining closed months into one file is a possible later step and would follow
  the same manifest rules.

## When to leave git

Rule of thumb: when `data-archive`'s packed size approaches **1 GB** (GitHub warns at 1 GB, and clone time
for every workflow run degrades well before that) or when a single day's evidence exceeds ~40 MB
uncompressed (the publisher refuses single files over 45 MB). At the post-change rate that is roughly
**16–24 months** away. The transition is a storage change, not an evidence change: publish the same
manifested day files to an object store (S3/GCS/R2) with the manifest as the index, keep `manifest/` and
`recovery/` in git, and point `soccer archive verify` at the store. Do this before the 1 GB mark, not after.
