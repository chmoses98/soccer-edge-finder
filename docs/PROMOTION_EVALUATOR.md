# Promotion evaluator v2 and LIMITED mode configuration (remediation phases 23-24)

Audit references: `docs/PRELAUNCH_AUDIT.md` §M (LIMITED mode design) and §Q (promotion gates).

## Verdicts

`soccer promote evaluate --archive-dir <archive> --out evaluation/promotion_report.v1.json` evaluates
every cell `model_family x market_family x competition_group x horizon_bucket` that has prospective
evidence and writes one machine-readable row per cell with exactly one of two verdicts:

| verdict | meaning |
|---|---|
| `NOT_ELIGIBLE` | at least one gate fails; every failed gate is named with the observed value and threshold |
| `ELIGIBLE_FOR_OWNER_REVIEW` | every gate passes on the evidence to date; a human decides what, if anything, follows |

There is no `AUTO_PROMOTE`. The evaluator never edits `config/authority.json`, never changes a family's
authority and never enables anything; `tests/test_promotion_and_limited.py` pins that the verdict set is
closed and that the CLI writes only the report. Promotion remains an owner decision made outside the
code, documented in `config/authority.json` by hand.

## Gates (frozen in `PromotionGates`, all must hold)

| group | gate |
|---|---|
| integrity | `unaccounted_contracts == 0` in every contributing run; archive manifest verifies; missing reference close <= 20 %; settlement rate >= 98 % of kickoffs older than 3 h |
| CLV | >= 200 selected sides from >= 80 fixtures; >= 70 % `TRUE_CLOSE` among close observations; fixture-cluster bootstrap 95 % lower bound of `EV_close` > 0; mean `EV_close` >= +1.0 pt; same sign in both chronological halves |
| Kalshi CLV | fee-aware Kalshi price CLV mean >= 0 (vs `KALSHI_CLOSE` two-sided valid mid) |
| prediction quality | log loss <= Kalshi valid-mid log loss + 0.005 and <= reference log loss + 0.010; ECE <= 0.04 |
| uncertainty | realised 80 % interval coverage within [0.70, 0.90] |
| liquidity | >= 80 % of selected sides had depth >= 3x intended size; median spread <= 3 cents; reference present for 100 % of selected sides |
| reference | a `SHARP_REFERENCE` source is available (`reference/quality.py::live_sharp_reference_available`); today it returns **False** (docs/REFERENCE_SOURCES.md), so **no cell can pass** until a compliant sharp live source exists |
| realised | ROI 95 % lower bound > -10 % (guardrail only, never the objective) |

`EV_close` for a settled side is `p_side(reference close) - break-even(entry ask + fee)` where the
reference close is `close_v2.reference` written by settlement (`TRUE_CLOSE` or `NEAR_CLOSE` only) and the
Kalshi close is `close_v2.kalshi` (`KALSHI_CLOSE` only, valid two-sided book).

## Current production read

`settle-evaluate.yml` runs the evaluator after every settlement pass and publishes the report to the
archive (`evaluation/promotion_report.v1.json`). At the time of writing every cell is `NOT_ELIGIBLE`,
first on the reference gate (no sharp live source), then on sample size (no settled selected sides with a
close observation yet). This is the expected state and not a defect.

## LIMITED mode (phase 24): configured, validated, DISABLED

`config/limited_mode.json` is the audit's §M design encoded as data so that a future owner decision has a
concrete, reviewed object to point at. `authority/limited_mode.py::LimitedModeConfig.load()` validates the
schema and `assert_disabled()` (called by the pipeline's authority path and pinned by
`tests/test_frozen_config.py` / `tests/test_promotion_and_limited.py`) fails the run if it ever reads
`enabled: true` while any family is `RESEARCH_ONLY`. Nothing reads the file into a staking or routing
authority; the flag is a documented intent, not a switch.

Design encoded: top-5 competitions only; only cells with `ELIGIBLE_FOR_OWNER_REVIEW` + written owner
sign-off + a hand-edited `authority.json` entry; excluded market families (exact score, player goals,
first-to-score, half markets, 2-way winner); T-90 to T-5 only; a `SHARP_REFERENCE` at most 15 min old with
model/reference disagreement <= 0.10; price in [0.15, 0.85], spread <= 4 cents, two-sided book; depth >= 3x
the order; edge_v2 `EV >= 0.02` and `EV_lower >= 0.01`, `sigma_edge <= 0.02`, documented cent-ceiling fee
model; one position per fixture, 0.5 % of a dedicated bankroll per position, 3 % per matchday, 10 % open
exposure, flat stakes; demotion on the rolling-100-bet closing-line lower bound falling below zero or a
15 % drawdown, plus the integrity kill switches (freshness, temporal guard, incomplete discovery, missing
reference, unaccounted contracts, manifest failure); every order links its prediction, reference and close
records.
