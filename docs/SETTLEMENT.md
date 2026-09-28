# Settlement

`settlement/engine.py::settle(semantics, official_result, kalshi_result=…)`.

## Principles

* **Semantics come from the contract, not the title.** The same `Semantics` object that priced the
  contract settles it (family, side, line, period, k).
* **Refusal first.** Missing what the contract needs → `REFUSED_*` with a reason:
  `REFUSED_NO_RESULT`, `REFUSED_ABANDONED`, `REFUSED_MISSING_PERIOD_DATA` (e.g. no HT score for a
  first-half contract; no ET/pens data for a to-advance contract), `REFUSED_PLAYER_DATA`,
  `REFUSED_UNSUPPORTED`.
* **Periods.** Regulation contracts settle on 90'+stoppage; `INCLUDING_ET` adds ET goals;
  `INCLUDING_PENS` (advancement) uses the winner after the shoot-out; first-half uses HT arrays.
* **Void.** Draw-no-bet on a draw → `VOID` (Kalshi has no push; if a real DNB contract appears its
  rules text decides, and until then it is `UNSUPPORTED_FAMILY` for pricing).
* **Kalshi cross-check.** Kalshi's `result` (yes/no) is stored verbatim and compared; a disagreement
  is flagged (`agrees_with_kalshi=false`) and never silently overwritten either way.
* **Evidence.** Each `Settlement` carries the fixture id, status, source, the scores used and the
  period; `SettlementV1` adds timestamps and (later) the position link and realised P&L.

## Families and their settlement inputs

| Family | Needs | Rule |
|---|---|---|
| total goals / first-half total | period goals | `h + a > line` |
| team total | period goals | `side goals > line` |
| handicap | period goals | `margin(side) > line` |
| 3-way result / first-half result | period goals | side outcome |
| BTTS | period goals | `h > 0 and a > 0` |
| clean sheet | period goals | opponent scored 0 |
| draw-no-bet | period goals | void on draw |
| to advance (2-way) | winner after ET/pens | `winner == side` |
| first to score | first scorer team | equality |
| player K+ goals | per-player goals | `goals ≥ k` |
| season futures, cards, corners, exact score, combos | — | `REFUSED_UNSUPPORTED` (and not priced) |

## Official results

Results come from `FixtureProvider.results()` (openfootball today: FT and HT). ET/pens, first
scorer and player goals need an event-level source (ESPN summary is the reachable candidate) and
are therefore `REFUSED_*` until wired — which is exactly why those families stay unpriced in
production. Abandoned/postponed fixtures are surfaced through `Fixture.status`.


## Universal settlement (added 2026-09-28, remediation phase 4; audit B4)

Before this change `soccer settle` fetched results for the openfootball leagues only, so 93.5% of archived
prediction records (Nations Leagues, friendlies, qualifiers, Ligue 1, the Americas) could never settle.

**Sources now merged** (`run/settle.py::build_result_index`): openfootball (current + previous season) and the
ESPN results archive on `data-archive` (`results/espn/<league>.jsonl`, every league the sync/backfill jobs
capture: 68 verified ESPN leagues including MLS, Liga MX, Brasileirão, Argentina, Champions/Europa/Conference
League, Nations Leagues, CONCACAF Nations League, World Cup/Euro qualifiers, friendlies, domestic cups).
`settle-evaluate.yml` passes `--espn-dir archive`. `tests/test_settlement_universal.py` asserts every priced
competition has a source.

**Matching** (`settlement/resolve.py::ResultIndex`): exact `fixture_id`, then (competition, home, away,
kickoff date ±1 day) because providers build ids differently (openfootball adds the matchday, ESPN adds
nothing). Two candidates from one source → `PENDING_MAPPING`; two sources disagreeing on the score →
`PENDING_EVIDENCE`; agreeing sources settle with the richest evidence.

**ESPN evidence** (`providers/espn.py::result_evidence`): the scoreboard's timed scoring plays give the
half-time split, regulation vs extra-time goals and the first scorer (own goals credited to the opponent);
`shootoutScore` gives the penalty winner; the status token (`STATUS_FULL_TIME`, `…_AET`, `…_PEN`,
`STATUS_POSTPONED/ABANDONED/CANCELED`) is archived. When the timed plays do not reproduce the reported score,
no split is emitted. Archived rows that lack the evidence are *upgraded* by appending a richer row for the
same event (append-only; last row wins; a different final score never upgrades).

**Contract semantics stay in charge.** Regulation contracts settle on 90' goals: from the derived split, or
from the reported score when the status is full time, the competition format cannot have extra time
(leagues, friendlies) or the source reports 90' scores (openfootball). Otherwise the record waits
(`PENDING_EVIDENCE: extra-time status unknown`). `INCLUDING_ET` uses 90' + ET goals; `INCLUDING_PENS` needs
the shoot-out winner; first-to-score needs a first scorer; half-time families need the split. Abandoned,
postponed, suspended and cancelled matches never settle (void/reschedule is not guessed).

**States** (every record gets exactly one; `unaccounted_settlement_records == 0` is asserted):
`SETTLED`, `PENDING_KICKOFF`, `PENDING_RESULT`, `PENDING_MAPPING`, `PENDING_EVIDENCE`,
`UNSUPPORTED_SETTLEMENT`, `UNSETTLEABLE`. Only `SETTLED` outcomes (yes/no/void) are written to the
settlements ledger; pending states are recomputed every run and reported in
`evaluation/settlement_coverage.v1.json` (counts, by competition, by family, reasons, examples).

**Exact score**: prediction records now carry `semantics.k` (and `player_slot`). For the 840 legacy
exact-score records the score is derived from the record's own generated description
("Exact score H-A (home-away)") only when it matches that exact format and agrees with the ticker's digit
pair; otherwise the record is `PENDING_EVIDENCE`, never settled as 0-0.
