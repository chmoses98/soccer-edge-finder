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
