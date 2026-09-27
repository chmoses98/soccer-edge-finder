# Storage strategy

Lessons: the MLB repo grew to 3.3 GB by committing captures to `main`; NFL's market-data branch
reached 23 GB; a 99.7 MiB file broke every CFB push. Rules here:

| Data | Where | Retention | Size control |
|---|---|---|---|
| identity registry, config, frozen research tables | `main` | forever | small JSON only |
| compact discovery index | `main` (`data/catalog/latest_index.json`, overwritten) | latest only | ~100 KB |
| full discovery catalog | workflow artifact | 14 days | not in git |
| market snapshots (change-suppressed JSONL) | `data-archive` orphan branch, `snapshots/YYYY-MM-DD/` | forever | one file per capture per day; rows only when quotes change; day sharding keeps files < 5 MB |
| prediction ledger | `data-archive`, `predictions/YYYY-MM-DD/predictions.jsonl` + `index.json` | forever, append-only | compact records (no draws); index rebuildable |
| simulation cache | workflow cache / artifact | per run | per-fixture JSON with quantile summaries |
| settlements, evaluation reports | `data-archive` | forever | small |
| provider downloads | `data/cache/` (gitignored) | ephemeral | — |
| simulation realisations | **never stored** | — | `compact_summary()` only |

Writer workflows share one concurrency group per branch (`data-writer-*`, queue not cancel), scope
`git add` to their own paths, upload an artifact *before* committing, and `git pull --rebase`
before push. A size guard (files > 45 MB fail CI) is on the roadmap for the archive branch.

Repository size target: `main` < 20 MB indefinitely; `data-archive` < 500 MB per season with
monthly compaction of snapshots into parquet if needed.
