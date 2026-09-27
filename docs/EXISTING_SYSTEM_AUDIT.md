# Existing-system audit (MLB, NFL, CFB, NBA, Kalshi router)

Audited 2026-09-27 from read-only clones of `edge-finder-api` (MLB), `nfl-edge-finder`,
`cfb-edge-finder`, `nba-edge-finder` and `kalshi-bet-router`. Full per-repo notes were produced by
parallel audit passes; this document is the reconciled conclusion and states what
`soccer-edge-finder` adopts, adapts, or deliberately avoids. Nothing here was copied wholesale.

## 1. Cross-repo verdicts

| Theme | What the four sports repos learned (the hard way) | Soccer decision |
|---|---|---|
| Discovery | Hardcoded series allowlists (CFB: 8 of 145 series; NFL: 194 contracts orphaned by title-based scoping) silently lost most of the surface. `/events?with_nested_markets` truncates. `[]` on HTTP 429 is indistinguishable from "no markets". | Sweep the *whole* series list every run; per-series `/markets` sweeps in each status; `PageSweep.complete` is structural (terminal page reached, no failures, no cap); an incomplete run is saved for forensics but can never act as a catalog. `discover()` never consults the classifier. |
| Classification | Classify-then-discover hid new families. Substring bugs (`"OT" in "TOTALFG"`). | Structural ticker parse *after* discovery; `UNKNOWN` retained with rationale; inferred families (never observed live) flagged `inferred` and surfaced as a risk. |
| Coverage | CFB `unaccounted_contracts == 0`, NFL `silently_omitted == 0`, NBA `UNRESOLVED == 0` all caught real losses. | `CoverageLedger` partition with one terminal disposition per contract, asserted in the pipeline (`assert_invariant`) and in tests. |
| Fees | MLB and NBA used ceil-to-cent (web-sourced); CFB measured it 2.75x–14x too high on small fees. NFL got the increment wrong twice. Prefix matching of `fee_type` nulled a third of a menu. | Decimal engine; documented $0.000001 ceiling; exact-name allowlist `{quadratic, quadratic_with_maker_fees}`; anything else -> `FeeMechanicsUnverifiedError` (fail closed); schedule version recorded on every record. |
| Executable price | Mid-price pricing (MLB hitter props) and `1 - yes_ask` for NO (disagreed with `no_ask` on 15,444/15,444 CFB contracts). Empty books published as 50%. | Side ask only; NO at `no_ask`; zero-size or $0/$1 books are `NO_QUOTE`, not quotes. |
| Capture | GitHub cron delivered 4.6%–7% of 10–15 minute slots (NBA, NFL, MLB). Committed trigger files re-fired pulls. 100x CLV bug when cents became dollars. | Change-suppressed snapshots with a declared `price_unit`; horizons labelled at capture time, never back-filled; cheap conductor decides work from status files; crons off round minutes (linted). |
| Model vs market | Every repo found the market beats the data-only model in every family (MLB Brier 0.2268 vs 0.1719; NBA 3–7 log-loss points; NFL market encompasses the model). Recalibrating the market hurt. CFB retired an unvalidated pricer after week 1. | Authority defaults to `RESEARCH_ONLY` for every family; promotion thresholds pre-registered; `MARKET_ONLY` kept as the benchmark every family must beat; walk-forward research is chronological only. |
| Storage | MLB repo 3.3 GB (captures committed to main); NFL market-data tree 23 GB; a 99.7 MiB file broke every CFB push. | Main holds registry + compact catalog index + small frozen research tables. Snapshots/predictions go to an orphan archive branch, sharded by day, size-guarded. No raw simulation realisations are ever stored (compact summaries + hashes). |
| Archive | Rebase conflict + `\|\| true` silently dropped NBA snapshots; MLB `git add` list drift discarded weeks of settlement. | Content-hashed append-only ledger with NO_OP/CONFLICT semantics and `verify()`; scoped `git add`; writer workflows publish artifacts *before* committing. |
| Settlement | Total ladder `>= N` vs `> N` defect flipped 564 MLB settlements; silent side defaults on money paths. | Refusal-first pure settlement per family; Kalshi `result` stored as a cross-check only; missing period data -> `REFUSED_*`. |
| Identity | Ticker-date joins broke on postponements (NBA); external-provider identity was key-dependent (CFB). | Fixture ids exclude kickoff time; association matches within ±1 day and reports `unmapped`/`no_fixture` explicitly; identity registry is repo-owned and provider-free. |
| Research honesty | Ladder duplication, both-sides double counting, in-sample scale reported on the tune set, cached scores from an old model. | Aligned samples only; de-laddered comparisons; result hash + data-content hash recorded with every research output; negative results are the expected outcome. |
| App surface | NFL's consumer is ChatGPT via Markdown + Airtable; MLB has a Vercel API; NBA/CFB have Python dataclasses only. No shared schema. | Versioned Pydantic contracts (`RecommendationV1`, `EventV1`, `ModelHealthV1`, `PositionV1`, `SettlementV1`, `RunOutputV1`) exported as JSON Schema and checked in CI. Markdown is a rendering of the JSON, never the source. |

## 2. Per-repo highlights

**NFL** — richest simulation and semantics machinery (question grammar with `semantic_confidence`,
survival-function ladders, refusal-first settlement, decision-time `as_of` gates). Pain: four
parallel shadow stacks, conductors holding runners for 5.5 h, a 23 GB data branch, and constants
that were "operator attested" because the sandbox could not reach Kalshi. Adopted: `(items,
complete)` pagination, confirmed_at vs quote_moved_at, one CLV sign convention, stdlib decision jobs.

**CFB** — the cleanest discover-first pipeline (milestones spine, per-event market sweeps, bulk
prefetch with negatives confirmed, two discovery paths with the difference published), the
`robust_positive_ev` corner-enumeration idea, the removal ledger in expression reduction, and the
most honest postmortem (`MODEL_RETIREMENT_2026.md`). Adopted almost directly: completeness
semantics, disposition vocabulary, fee allowlist, reduction with reasons. Adapted: the uncertainty
"box" becomes posterior worlds (so P(edge>0) and worst case come from the same distribution that
prices the contract).

**NBA** — best archive discipline (content-hashed ledger, orphan branch, `verify()` before push),
support-vs-authority separation, frozen baselines and a written merge gate. Its research found the
market ahead everywhere and said so. Adopted: authority thresholds shape (100/300/1000 settled),
pregame labelling at evaluation time, model-free market baseline first.

**MLB** — the mature production stack and the largest catalogue of live incidents: fee blindness,
100x CLV unit bug, total-ladder semantics defect, scheduler starvation, snapshot duplication, 3.3 GB
repo. Adopted: producer-declared `price_unit`, closing-quote coverage classes, `write_placed_bet`
receipts pattern (for the future position import), preregistered DEV/VAL/FORWARD governance.

**Router** — soccer is explicitly out of scope today (`COMPETITION_OUT_OF_SCOPE`,
`NON_TARGET_SPORT_TOKENS` include `premier league`, `uefa`, `mls`, ...), so soccer fills classify as
`OTHER` (never misrouted to NFL/CFB, but they flip the scheduled run to BLOCKED). Adding `SOCCER`
is two halves: enum + classifier (safe now, fail-closed on bare `football`) and a production write
path (needs this repo's importer/validator contract and a re-scoped token). See
`docs/ROUTER_INTEGRATION.md`.

## 3. What soccer does differently on purpose

1. **Worlds, not point handicaps.** The parameter posterior, lineup draws and model inflation are
   sampled jointly; every contract's interval, P(edge>0) and correlation come from the same draws.
2. **No trust by default.** There is no path from "implemented" to "recommended" without settled
   prospective evidence per (model family × market family × horizon).
3. **Provider-free identity.** Teams/competitions live in this repo with alias scopes (gender,
   country, kind); providers map onto them and fail loudly, never the reverse.
4. **Small main branch.** Nothing bulky is committed to `main`; the archive branch is append-only.
5. **One conductor, cheap decisions.** Discovery/capture is the frequent cheap job; simulation runs
   only when model inputs changed; repricing reuses the cached distribution.
