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

## Family taxonomy (from the live catalog, 2026-09-27)

Split rule: the longest known family token is stripped from the ticker body; whatever remains is
the competition code, registered or not. A bare competition body with winner wording is an
outright-winner contract. Specials (transfers, manager exits, Ballon d'Or) are whole-series bodies.

| token(s) | family | scope | observed live | priced in v1 |
|---|---|---|---|---|
| `GAME` (legs `<TEAM>`, `TIE`) | match_result_3way | match | ✅ (726) | ✅ |
| `TOTAL` | total_goals | match | ✅ (462) | ✅ |
| `SPREAD` ("wins by more than N.5") | handicap | match | ✅ (308) | ✅ |
| `TEAMTOTAL` | team_total | match | ✅ (126) | ✅ |
| `BTTS` | btts | match | ✅ (76) | ✅ |
| `SCORE` (leg `<A><g><B><g>`) | exact_score | match | ✅ (630) | ✅ |
| `1H`, `1HTOTAL`, `1HSPREAD`, `1HBTTS` | first-half result / total / handicap / BTTS | match | ✅ | ✅ |
| `FTTS` (incl. extra time per rules) | first_to_score | match | ✅ | ✅ (regulation-only fixtures) |
| `GOAL`, `ANYGOAL`, `BRACE` | player_goals | player | ✅ | scaffold (no lineup provider) |
| `RELEGATION`, `TOP/TOPX/TOP8`, `LAST/BOTTOM`, `QUAL/GROUPWIN`, `ROUND`, `PROMO`, `HOST`, `TEAMPOINTS`, `POINTMARGIN`, `H2HFINISH`, `CUP`, bare body | competition futures | competition | ✅ | ❌ (`UNSUPPORTED_FAMILY`) |
| `LEADER`, `SEASONSTAT`, `AWARD`, `RANK`, `BALLONDOR*` | player season / awards | competition | ✅ | ❌ |
| `JOINCLUB`, `MANAGERSOUT`, `SOCCERRETIRE`, `SOCCERLEAVE`, `FIFALEAVE`, `SOCCERTROPHIES` | soccer_special / trophies | competition | ✅ | ❌ |
| `WINNER`, `CS`, `ASSIST`, `SHOTS`, `SOT`, `CARD` | (by analogy) | — | not seen | — |
| anything else | `UNKNOWN` | — | — | ❌ (`UNKNOWN_FAMILY`, rationale kept) |

Verified settlement wording (from `rules_primary`): match families settle "after 90 minutes plus
stoppage time (does not include extra time or penalties)"; `FTTS` counts "regulation, stoppage
and any extra time periods"; exact score is regulation. **Event codes and titles are HOME then
AWAY** (`SPASAN` = "Sao Paulo vs Santos").

Competition codes seen live (2026-09-27): UEFANL, CONCACAFNL, LIGAMX, MLS, BRASILEIRO, USL, EPL,
LALIGA, BUNDESLIGA, LIGUE1, SERIEA, NWSL, UCLW, LIGAEXP, COPADELREY, plus futures-only codes (WC,
UCL, UEL, UECL, UEFAEURO, COPAAMERICA, CONCACAFGC, MLSCUP, PREMIERLEAGUE, FACUP, EFLCUP, DFBPOKAL,
KNVBCUP, COPADOBRASIL, CONMEBOLLIB, ...) and lower leagues (APFDDH, ARGNACB, BRASILEIROB/C, CANPL,
CHNL1, CHNSL, CHLLDP, ECULP, EKSTRAKLASA, PERLIGA1, TACAPORT, THAIL1, URYPD, VENFUTVE, ...).
`COMPETITION_CODES` maps each to a canonical id or `None` (known soccer, not modelled).

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
