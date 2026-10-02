# Archive integrity: manifest, verifier, recovery

Status: implemented (pre-launch remediation, PR A). Addresses audit defects B1 (overwritten day files) and
B13 (the ledger could not detect deletion). Nothing here changes a model, a threshold or authority.

## Why

`data-archive` is the only prospective evidence the promotion process can ever use. Until audit fix S1 the
publisher replaced `.jsonl` day files, and `PredictionLedger.verify()` only re-hashed the rows that survived,
so 830 prediction rows of run `run-20260928T124253Z-4f9bfb` vanished from the tip without any signal.

## Manifest

`soccer archive manifest --archive-dir <tree>` records, under `manifest/`:

* `manifest/files.json` — one entry per archived file: `record_type`, `byte_length`, `sha256_prefix` (sha256 of
  the first `byte_length` bytes), `line_count`, `day`, `closed`, `immutable`, `recovery_id`.
* `manifest/records/<day>.jsonl` — one append-only row per evidence record (predictions, settlements, lineups,
  weather): `record_id`, `record_type`, `run_id`, `captured_at`, `content_hash` (sha256 of the raw line bytes,
  24 hex), `archive_path`, `schema_version`.

Why a byte prefix: every archived file is append-only or immutable, so "nothing was deleted or rewritten" is
exactly "the manifested prefix still hashes the same". Appends past the prefix are the normal publish; the
next `archive manifest` extends the entry. A day older than `CLOSE_GRACE_DAYS` (2) is *closed*: its length
must equal the manifested length. Run outputs, fixture dumps and recovery manifests are immutable from the
first publish.

`archive manifest` verifies the existing manifest first and **refuses** to extend it when the archive does not
verify — a corrupt archive can never be re-manifested as healthy. `--init` bootstraps a manifest from the
current state (one-time; done by `archive-recover.yml` after the recovery so that the recovered rows are
inside the manifested prefix).

Mutable pointer files (`index.json`, `last_*.json`, `STATUS.json`, `runs/latest.*`, `evaluation/*`, caches)
are not manifested; they are rebuildable and are checked for consistency instead.
The live-slate pointers (`runs/latest.model_board.v1.json`, `runs/latest.actionable_slate.v1.json`,
`runs/LATEST_ACTIONABLE_SLATE.md`) are mutable too and are merged at publish time (docs/ACTIONABLE_SLATE.md
§9); the reprice log `dispatch/slate_log/<day>.jsonl` is append-only and manifested like the other logs.

## Verifier

`soccer archive verify --archive-dir <tree>` exits **1** on any problem, **2** when no manifest exists
(`--allow-missing-manifest` runs the intrinsic checks only, reports them as `UNVERIFIED` and exits 0, so publishing keeps working until the manifest is bootstrapped; from then on verification is strict). It detects:

| kind | meaning |
|---|---|
| `missing_file` | a manifested file is gone |
| `file_shrunk` | a manifested file is shorter than its manifested length (a deletion) |
| `file_prefix_rewritten` | bytes inside the manifested prefix changed (an edit or reorder) |
| `closed_file_appended` | a closed day file or an immutable file grew outside a recorded recovery |
| `record_missing` | a manifested evidence record's line is no longer in its file |
| `record_rewritten` | a prediction/settlement row no longer re-hashes to its own `record_id` |
| `duplicate_id_conflict` | the same `record_id` appears with two different payloads |
| `index_dangling` | `predictions/index.json` lists an id with no row (this is what B1 looks like) |
| `index_missing_record` | a row exists that the index does not list |
| `run_reference_broken` | a prediction's `run_id` has no archived `runs/*/<run_id>/run_output.v1.json` |
| `prediction_reference_broken` | a settlement's `prediction_record_id` has no prediction row |
| `unparsable_line` | a line that is not JSON |

Duplicate identical lines are a warning (a publish bug, not evidence loss).

Where it runs: inside `scripts/archive_publish.sh` before every archive commit (publish aborts on failure),
and as the `archive-verify` job of `ci.yml` against the archive tip on every push.

## Recovery

`soccer archive recover --repo <clone> --branch data-archive [--archive-dir <tree>] [--apply]` reads every
historical blob of every `.jsonl` path (oldest commit first), unions lines by exact bytes, and reports the
lines absent from the tip together with the commit and blob that first carried them. Before writing anything
it checks identities over history ∪ tip: prediction rows must re-hash to their `record_id`; the same identity
(prediction `record_id`; lineup `(espn_event_id, captured_at, content_hash)`; weather
`(espn_event_id, captured_at, forecast_time_utc)`) must never map to two payloads. Any conflict or
unverifiable row **refuses the whole recovery** and nothing is written.

`--apply` appends the recoverable lines in first-seen order (original bytes: timestamps, run ids, model
versions and probabilities untouched), repairs missing `index.json` entries, writes
`recovery/<recovery_id>.json` (origin commit/blob, line counts, run ids, sha256 of each recovered group) and,
when a manifest exists, extends it with the recovery id on the affected entries. Re-running finds nothing.

Dry run against the archive at `c7e4374` (16 commits): 29 paths scanned, **854 recoverable lines, 0
conflicts, 0 unverifiable** — 830 prediction rows (run `4f9bfb`, from `7383daa`), 5 lineup rows
(`fifa.friendly`, from `644b72f`), 19 weather rows (from `644b72f`). Run `archive-recover.yml` with
`apply=true, init_manifest=true` once to apply and bootstrap the manifest; the workflow uploads the dry-run
report and the verification report as artifacts.

## Growth note

Record-level manifest rows cost ~300 bytes per evidence record (≈0.7 MB for the 2,335 records archived so
far). Phase 22 (archive compaction) gzips closed `manifest/records/<day>.jsonl` files together with the closed
day files they describe; the verifier reads both forms.
