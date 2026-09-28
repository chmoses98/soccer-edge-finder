# Kalshi capture

`soccer capture` = one discovery (`discover()`, all statuses requested) + one `SnapshotBatch`.

## What a snapshot holds (`kalshi/capture.py::MarketSnapshot`)

ticker, event/series tickers, `captured_at`, status, yes/no bid/ask (dollars, 4 dp), sizes
(`*_fp`), last price, volume, open interest, close/expected expiration, series `fee_type` and
`fee_multiplier`, hash of `rules_primary` (full text lives in the catalog), declared
`price_unit="dollars"` (consumers refuse undeclared units — the 100× CLV lesson), horizon label,
minutes to kickoff, optional order book (depth 10).

## Fast capture vs exhaustive discovery

The daily `kalshi-discover` job is exhaustive (every soccer/ambiguous-with-wording series, `open` +
`unopened`, ~4,500 requests, ~19 min at 4 rps). Intraday `kalshi-capture` runs `--fast --status open`:
it re-reads the full series list (so **new series are always swept**) but enumerates markets only for
series that carried markets in the last committed full discovery. Owned series skipped this way are
recorded with `swept=false` and counted as `series_skipped_fast_mode` in the batch status. The
relaxation is therefore explicit: a series that was empty at the last full discovery and gained
markets before the next one is picked up by the next daily run, not by the intraday capture.

## Change suppression

`quote_fingerprint()` hashes status + the four prices + sizes. A capture writes only snapshots
whose fingerprint differs from the previous capture (`last_fingerprints.json`), plus a per-capture
`STATUS.json` (batch id, discovery completeness, counts). Unchanged quotes are therefore *implied*
by the absence of a newer row; evaluation reads the last row strictly before kickoff.

## Horizons

`T-24h, T-12h, T-6h, T-2h, T-90m, T-60m, T-30m, lineup, T-15m, T-10m, close`. A capture is labelled
with the nearest horizon it satisfies *at capture time* (`label_horizon(minutes_to_kickoff)`);
labels are never back-filled. Because GitHub cron delivers a fraction of scheduled slots (measured
5–7% for 10–15 minute crons across sibling repos), the capture workflow is designed to be
**idempotent and cheap** so that missed slots simply produce a coarser horizon set for that
fixture rather than a corrupted one. Evaluation reports horizon coverage per fixture.

## Market refresh vs model refresh

The pipeline's simulation cache key (`run/simcache.py::sim_key`) is
`hash(posterior params, world config, sim config, match context, seed)`; the per-fixture cache also
stores the contract set. On a capture where only prices moved, RUN SOCCER reprices from cached
per-contract world-probability summaries (mean, quantiles, 20-bin histogram) without simulating.
New results, a lineup-state change, a config change or a new contract on the fixture invalidates
the cache and re-simulates that fixture only.

## Storage

Snapshots are JSONL per UTC day under `data/snapshots/YYYY-MM-DD/<batch>.jsonl`, intended for the
`data-archive` orphan branch (see `docs/STORAGE_STRATEGY.md`). `latest_catalog.json` (full raw
discovery) is a workflow artifact; only `data/catalog/latest_index.json` is committed to `main`.

## Completeness on every capture

`STATUS.json.discovery_complete` is the health signal. An incomplete discovery still writes the
snapshots it did obtain (they are real observations) but the batch is flagged and RUN SOCCER will
not recommend from it.

## Fast capture completeness proof (Phase 23)

Fast mode is a relaxation, so it carries a proof obligation: every market present in the last
full discovery must be either present in the fast run or explained. `kalshi/reconcile.py::
reconcile_fast_vs_full(fast, full)` performs that reconciliation from the JSON documents the CLI
already writes and reports **counts only**:

```
soccer reconcile-discovery --fast <fast out-dir>/latest_catalog.json \
                           --full data/catalog/latest_index.json      \
                           --out  data/research/reconcile.json        # exit 1 if not complete
```

Inputs and the evidence level they support:

| side | document | evidence |
| --- | --- | --- |
| fast | the capture's `latest_catalog.json` (`DiscoveryRun.to_json()`, has `series[].swept` and `markets`) | market |
| fast | the capture's `STATUS.json` (counters only) | insufficient — fails closed |
| full | `latest_catalog.json` from the daily discovery (workflow artifact) | market |
| full | committed `data/catalog/latest_index.json` (`series`, `series_with_markets`, `market_count`, no market tickers) | series |

Report (`schema: "discovery_reconcile_v1"`): `evidence_level` (`market` / `series` /
`insufficient`), `fast` and `full` descriptors (run id, timestamp, statuses requested, series
counts, `markets_available`), `series` (swept in each, skipped by fast, **skipped by fast but
carrying markets in full**, new in fast, vanished from Kalshi's list), `markets`
(`full_total`, `fast_total`, `in_both`, `in_full_not_fast`, `in_fast_not_full`, and
`full_not_fast_breakdown`), `violations` and `complete_relative_to_full`.

`full_not_fast_breakdown` classifies each full-run market the fast run did not see, in this order:

1. `in_skipped_series` — its series was fast-skipped. Expected to be **0**: a skipped series is
   by construction one that had no markets at the last full discovery. Any count here is the
   `fast_mode_missed` violation.
2. `closed_between_runs` — the full-run row already had a closed/settled status, or its
   `close_time` / expiration is at or before the fast run's timestamp. Lifecycle, not a violation.
3. `status_not_requested` — its status is outside what the fast run asked for (intraday captures
   run `--status open`, so `initialized`/unopened markets are expected to be absent). Not a
   violation.
4. `unexplained` — an open market in a series the fast run swept, absent without reason. This is
   the `unexplained_missing_markets` violation (with `unexplained_by_series` to localise it).

`complete_relative_to_full` is true only when there are no violations: no `fast_mode_missed`, no
`unexplained_missing_markets`, no series that had markets in full and was neither swept nor
fast-skipped, both runs flagged their own discovery complete, and the evidence level is at least
`series`. With series evidence only (committed index on the full side) the proof covers the
skip decision but cannot see individual markets; the report says so via `evidence_level` and
`null` market intersections. Markets new since the full discovery (`in_fast_not_full`) are
informational: fast mode always sweeps new series and re-enumerates swept ones.
