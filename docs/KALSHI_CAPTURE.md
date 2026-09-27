# Kalshi capture

`soccer capture` = one discovery (`discover()`, all statuses requested) + one `SnapshotBatch`.

## What a snapshot holds (`kalshi/capture.py::MarketSnapshot`)

ticker, event/series tickers, `captured_at`, status, yes/no bid/ask (dollars, 4 dp), sizes
(`*_fp`), last price, volume, open interest, close/expected expiration, series `fee_type` and
`fee_multiplier`, hash of `rules_primary` (full text lives in the catalog), declared
`price_unit="dollars"` (consumers refuse undeclared units — the 100× CLV lesson), horizon label,
minutes to kickoff, optional order book (depth 10).

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
