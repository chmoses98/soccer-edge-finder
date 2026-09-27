# data/

| path | committed? | contents |
|---|---|---|
| `registry/` | yes | canonical identity seed (competitions, teams, aliases) |
| `catalog/latest_index.json` | yes (compact, overwritten) | summary of the latest complete Kalshi discovery |
| `catalog/latest_catalog.json` | **no** (workflow artifact) | full raw discovery payload |
| `snapshots/` | no on `main`; archived on the `data-archive` branch | change-suppressed market snapshots (JSONL by UTC day) |
| `predictions/` | archive branch | append-only prediction ledger |
| `settlements/`, `evaluation/` | archive branch | settlement evidence and evaluation reports |
| `research/` | yes, small frozen result tables only | walk-forward research outputs |
| `cache/` | never | provider download cache |

See `docs/STORAGE_STRATEGY.md`.
