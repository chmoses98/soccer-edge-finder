# Kalshi microstructure (Phase 18, research only)

`soccer microstructure` reads every archived snapshot row and describes the top of book we
actually observed: how wide, how deep, how expensive after fees, how that changes toward kickoff,
and how complete the capture cadence was. It is a **diagnostic**. Nothing in
`kalshi/microstructure.py` is imported by the pricing, selection, recommendation or authority
code paths, and its output never changes which contracts are selected or which model family holds
authority. It exists so that research decisions (e.g. "is a 3-cent mid edge ever real on
exact-score contracts?") are made from measured spreads and fees rather than assumed ones.

## What is measured

Input: `MarketSnapshot` rows (`model_dump(mode="json")`) from `<snapshots-dir>/<YYYY-MM-DD>/*.jsonl`
(the same files `run/settle.py::load_close_quotes` reads). Prices are strings in dollars 0..1;
any price, size, volume or fee field may be `null`.

Per row:

| quantity | definition |
| --- | --- |
| bid present / ask present | `yes_bid > 0` / `yes_ask < 1`. Kalshi reports `0` / `1` when a side has no orders, so those sentinels are treated as *no order*, not as a quote. |
| quote state | `two_sided` (both present), `one_sided` (exactly one), `no_quote` (neither, including all-`null` rows) |
| `spread_yes` | `yes_ask - yes_bid` (two-sided rows only) |
| `mid` | `(yes_bid + yes_ask) / 2`, in YES-probability space |
| executable YES / NO cost | `yes_ask` / `no_ask` — what a taker pays now |
| `gap_yes`, `gap_no` | `yes_ask - mid` and `no_ask - (1 - mid)`: what the mid hides on each side |
| top-of-book sizes | `yes_bid_size`, `yes_ask_size`, `no_bid_size`, `no_ask_size` as captured (contracts) |
| taker fee | `fees.taker_fee(ask, 1 contract, FeeRegime(row.fee_type, row.fee_multiplier))`, i.e. `ceil(0.07 × multiplier × P × (1 − P), $0.000001)`. Rows whose `fee_type` is missing or outside the verified set are counted as `unverified_regime` and contribute no fee statistics (fail closed, like the pricing engine). |
| fee impact | `taker fee / ask` — the fee as a fraction of the price paid, per side |
| family, competition | `taxonomy.classify()` on a minimal `RawMarket` built from the ticker (title-free); fallback `split_competition_and_family()` on the ticker body. Anything unparseable is `unknown` / `?`. |
| horizon label | the stored `horizon` and a recomputed `label_horizon(minutes_to_kickoff)`; the mismatch count exposes rows written before the 2026-09-28 labelling fix |
| horizon bucket | from `minutes_to_kickoff`: `T-24h+` (≥1440), `T-6h..24h` (≥360), `T-1h..6h` (≥60), `T-10m..1h` (≥10), `<10m` (anything smaller, including negative = in-play/after close), `unknown` (`null`) |

### Erased-edge share

For each two-sided row with a verified fee regime, each side (YES at `yes_ask`, NO at `no_ask`) is
one *executable side*. A mid-based edge of `θ` on that side is **erased** when

```
spread_yes / 2 + taker_fee(ask) >= θ
```

`mid_edge_erased_share_3c` and `mid_edge_erased_share_5c` are the shares of executable sides where
this holds for θ = $0.03 and $0.05; `mid_edge_erased_sides_n` is the denominator. Read them as
"if my model shows a 3-cent edge against the mid, this is how often the book alone would eat it
before any model error".

## Summaries in the output

`schema: "microstructure_summary_v1"`. Top level: `generated_at`, `fee_schedule_version`, `rows`,
`tickers`, `date_range`, `input` (files read, unparseable rows skipped, rows dropped by `--since`),
`snapshots_dir`, `since`, `definitions`, then:

- `overall`, `by_family`, `by_competition`, `by_horizon_bucket`, `by_family_horizon`
  (`"<family>|<bucket>"`): each a *group summary* with `rows`, `tickers`, `quote_state`
  (counts + `two_sided_share`), `spread_yes`, `gap_yes`, `gap_no`, `fee_impact_yes`,
  `fee_impact_no`, `fee_status`, `sizes` (four distributions), `mid_edge_erased_share_3c/_5c`,
  `mid_edge_erased_sides_n`, `volume_*` and `open_interest_*` (last row per ticker, so cumulative
  counters are not double counted), `orderbook_rows`.
- top-level shortcuts of the overall group: `quote_state`, `spread_yes`, `fee_impact`, `sizes`,
  `mid_edge_erased_share_3c`, `mid_edge_erased_share_5c`, `mid_edge_erased_sides_n`.
- `toward_kickoff`: ordered list (bucket order above) of spread median/p90, ask sizes, fee impact,
  two-sided share and erased shares — how the book tightens or thins as kickoff approaches.
- `volume_open_interest_by_family`.
- `horizon_labels`: stored vs recomputed histograms and mismatch count.
- `capture_coverage`: distinct capture timestamps, `rows_by_utc_hour`, `captures_by_utc_hour`
  (distinct `captured_at` per UTC hour), `rows_by_day`.
- `capture_cadence` (**capture completeness**): per ticker with ≥3 rows, minutes between
  consecutive rows; reported as distributions of per-ticker medians and per-ticker maxima plus all
  gaps pooled, and `rows_per_ticker`.

Every distribution is `{n, mean, median, p10, p90, min, max}` (linear-interpolated percentiles,
6 dp). Decimal arithmetic is used for every per-row quantity; conversion to float happens only
inside the distribution helper. Dict keys are emitted sorted; `toward_kickoff` is a list to keep
bucket order.

## How to run

```
soccer microstructure --snapshots-dir data/snapshots --out data/research/microstructure.json
soccer microstructure --snapshots-dir data/snapshots --out out.json --since 2026-10-01
```

No network. The command prints a short JSON digest and exits 0 (an empty or missing directory
yields an all-zero summary, not an error).

## How to read it

- `quote_state.two_sided_share` well below 1 in a family means the mid is often undefined there;
  a model edge against `last_price` in such a family is not executable evidence.
- Compare `spread_yes.median` per bucket in `toward_kickoff` with the horizon at which the
  pipeline would act; a spread that only tightens inside `<10m` cannot be harvested by a capture
  cadence that rarely samples that window (see `capture_cadence`).
- `fee_impact_*` rises sharply for low-priced asks (the quadratic fee peaks at P = 0.5 in dollars
  but as a *fraction of price* it grows as P → 0); long-shot exact scores pay proportionally the
  most.
- `mid_edge_erased_share_3c` near 1 for a family says "3 cents against the mid is noise here";
  use it to set the minimum *executable* edge for future research, not the mid edge.
- `capture_cadence.gap_minutes_per_ticker_max` shows the longest blind window per contract.
  Because a row is written only when the quote changes (change suppression), gaps also occur when
  nothing moved; the `captures_by_utc_hour` histogram separates "no capture ran" from "no change".

## Limitations

- **Top of book only.** Unless a row carries `orderbook`, sizes describe the best level only;
  the cost of anything beyond `yes_ask_size` contracts is unknown. `orderbook_rows` counts how
  many rows have depth.
- **Capture cadence limits close-proximity inference.** GitHub cron delivers a minority of
  scheduled slots, and change suppression means an unchanged book leaves no row. Statistics for
  `<10m` and `T-10m..1h` are therefore drawn from few, unevenly sampled rows; they are not an
  estimate of the closing book.
- The empty-book sentinel rule (`0` / `1`) is a convention; a genuine 1-cent bid is
  indistinguishable from nothing only at exactly 0, so it does not hide real quotes.
- Fee statistics apply the transcribed 2026-07 schedule (`fee_schedule_version`); rows with an
  unverified `fee_type` are excluded from fee and erased-edge figures rather than guessed.
- Family/competition come from the ticker grammar; a bare competition body without a title is
  `unknown` family, and unregistered competition codes appear under their raw code.
- Rows from 2026-09-27 carry a known-wrong stored `horizon` label; the summary buckets on
  `minutes_to_kickoff`, which was correct, and reports the mismatch count.

## Authority statement

This module and command are diagnostic. They do not feed `run/pipeline.py`, the recommendation
filters, the selection thresholds or the authority ledger, and their numbers are not inputs to any
trading decision. Changing anything on the basis of what they show requires its own reviewed
change with its own tests.
