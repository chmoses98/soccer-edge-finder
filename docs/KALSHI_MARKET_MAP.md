# Kalshi soccer market map

## Discovery architecture (discover → own → classify → account)

1. `GET /series?limit=1000&include_product_metadata=true` — the **entire** series list (~14k rows,
   one page). Nothing is filtered by category or tag at this step.
2. Ownership (`kalshi/ownership.py`): `SOCCER` (soccer tag, soccer ticker grammar, or soccer
   competition wording in a Sports series), `NOT_SOCCER` (American-football prefixes/wording,
   everything else), `AMBIGUOUS` (bare `Football` tag; soccer tag on an American-football ticker).
   Ambiguous series **with** soccer wording are swept; ambiguous series without it are recorded,
   counted (`series_ambiguous_unswept`) and listed — never silently dropped. This matters: 349 NFL
   series carry only the tag `Football`.
3. For every swept series: `GET /markets?series_ticker=…&status=open|unopened&limit=1000` and
   `GET /events?series_ticker=…&limit=200`, each a full cursor walk. `with_nested_markets` is never
   used (it truncates).
4. `GET /milestones?type=soccer_tournament_multi_leg&limit=200` is probed advisory-only.
5. Classification (`kalshi/taxonomy.py`) runs on the finished market set; `UNKNOWN` is retained.
6. Completeness: run.complete ⇔ series sweep complete ∧ every market/event sweep complete ∧ no
   parse failures. An incomplete run is saved and flagged; RUN SOCCER never recommends from it.

## Ticker grammar (verified on live tickers)

```
KX<COMPCODE><FAMILYTOKEN>-<YYMONDD><AWAYCODE><HOMECODE>-<LEG>
KXMLSTOTAL-26AUG22SJMIN-9              total goals, floor_strike 8.5   ("over 8.5")
KXUCLSPREAD-26SEP10MUNSBH-MUN4         MUN wins by more than 3.5
KXUCLTEAMTOTAL-26SEP09SPOGAL-GAL4      GAL scores over 3.5
KXEPLGOAL-26AUG22ARSCOV-ARSMZUBIM36-1  player (ARS, M. Zubimendi, #36) 1+ goals
```
Team codes are Kalshi's own 2–4 letter abbreviations and are **not** identity; association uses the
event title and the registry. `floor_strike` from the API is the authoritative line.

## Family taxonomy (from observations + grammar)

| token | family | scope | observed live before this build | priced in v1 |
|---|---|---|---|---|
| `TOTAL` | total_goals | match | ✅ | ✅ |
| `SPREAD` | handicap ("wins by more than N.5") | match | ✅ | ✅ |
| `TEAMTOTAL` | team_total | match | ✅ | ✅ |
| `GOAL` | player_goals (K+) | player | ✅ | scaffold only (no lineup provider) |
| `GAME` | match_result_3way (home/away/`TIE` legs) | match | inferred, needs title corroboration | ✅ (flagged `inferred` until observed) |
| `BTTS` | btts | match | inferred | ✅ (flagged) |
| `1HTOTAL`/`H1TOTAL`, `1HGAME`/`H1` | first-half total / result | match | inferred | ✅ (flagged) |
| `WINNER` | to advance (ET+pens) | match | inferred | ✅ (flagged) |
| `SCORE`, `CS` | exact score, clean sheet | match | inferred | clean sheet ✅; exact score ❌ |
| `ASSIST`, `SHOTS`, `SOT`, `CARD` | player families | player | inferred | ❌ |
| `CHAMP(ION)`, `TOP2/4/6`, `RELEGATION`, `GOLDENBOOT` | competition futures | competition | inferred | ❌ (`UNSUPPORTED_FAMILY`) |
| anything else | `UNKNOWN` | — | — | ❌ (`UNKNOWN_FAMILY`, rationale kept) |

Competition codes seen live (37 series, 2026-07..09, via a sibling repo's broad market sweep):
MLS, NWSL, USL, LEAGUESCUP, LIGAMX, LIGAEXP, EPL, EFLCHAMPIONSHIP, LALIGA, COPADELREY,
BUNDESLIGA2, SERIEB, TFF1LIG, BELGIANPL, ALLSVENSKAN, SAUDIPL, UCL, UCLW, UEL, UEFANL,
CONCACAFNL, CONMEBOLLIB, COPADOBRASIL, BRASILEIRO. `COMPETITION_CODES` maps each to a canonical
competition id or `None` (known soccer, not yet modelled).

## Coverage accounting

Every discovered contract ends in exactly one `Disposition`:
`priced, closed, started, no_quote, stale_quote, duplicate, ambiguous_ownership, unknown_family,
unsupported_family, unmapped_event, unmapped_team, no_fixture, no_model, fee_unverified,
inferred_family_unconfirmed, out_of_window, filtered_by_operator, unpriceable`.
`unaccounted_contracts = discovered − Σ dispositions` must be 0 (`CoverageLedger.assert_invariant`,
tested in `tests/test_kalshi_discovery.py` and `tests/test_run_pipeline.py`).

## Settlement fields captured

`status` (active/closed/finalized), `result`, `settlement_value(_dollars)`, `settlement_ts`,
`expiration_time`, `expected_expiration_time`, `close_time`, `rules_primary/secondary`,
`can_close_early`, series `fee_type`/`fee_multiplier`, `settlement_sources`.

## Live catalog (first runner-side discovery)

See the section appended below by the first complete `kalshi-discover` run and
`data/catalog/latest_index.json` for the current state.
