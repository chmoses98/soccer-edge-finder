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

## Live catalog (runner-side discovery, taxonomy v2)

Discovery `disc-20260927T230633Z-3639e9` finished 2026-09-27T23:19:42.305981Z — complete: **True** · series in Kalshi: 14398 · soccer series swept: 1389 · ambiguous unswept: 134 · events: 17691 · **contracts discovered: 6534** · unknown-family: 95 · requests: 3152 (retries 0)

Contracts by family:

| family | contracts |
|---|---|
| competition_winner | 1045 |
| match_result_3way | 1041 |
| exact_score | 675 |
| total_goals | 647 |
| handicap | 430 |
| competition_team_points | 384 |
| competition_top_n | 306 |
| player_season_leader | 247 |
| soccer_special | 211 |
| player_award | 167 |
| tournament_advancement | 160 |
| competition_qualification | 138 |
| competition_last_place | 132 |
| team_total | 127 |
| btts | 108 |
| competition_relegation | 96 |
| first_half_result | 96 |
| first_half_total | 96 |
| unknown | 95 |
| first_half_handicap | 64 |
| first_to_score | 63 |
| season_player_total | 50 |
| first_half_btts | 32 |
| competition_points_margin | 30 |
| competition_trophies | 30 |
| competition_host | 26 |
| competition_promotion | 24 |
| competition_head_to_head | 14 |

Contracts by competition code:

| code | contracts |
|---|---|
| UEFANL | 1694 |
| ? | 512 |
| CONCACAFNL | 398 |
| EPL | 361 |
| UCL | 354 |
| LALIGA | 237 |
| LIGAMX | 218 |
| SERIEA | 210 |
| LIGUE1 | 199 |
| BUNDESLIGA | 195 |
| MLS | 187 |
| WC | 172 |
| INTLFRIENDLY | 163 |
| BRASILEIRO | 139 |
| USL | 98 |
| EFLL1 | 86 |
| ISRNL | 80 |
| BRASILEIROB | 79 |
| UEFAEURO | 60 |
| FIFAW | 48 |
| APFDDH | 40 |
| DIMAYOR | 40 |
| COPADELREY | 38 |
| EFL | 37 |
| ENGNL | 36 |
| UECL | 36 |
| UEL | 36 |
| URYPD | 33 |
| WCW | 32 |
| ARGPREMDIV | 30 |
| LIGAMX1H | 30 |
| NWSL | 30 |
| BRASILEIROC | 27 |
| UCLW | 27 |
| COPAAMERICA | 25 |
| EFLCHAMPIONSHIP | 24 |
| FA | 24 |
| LIGAEXP | 24 |
| CONCACAFGC | 23 |
| DFBPOKAL | 21 |
| KNVB | 21 |
| PERLIGA1 | 21 |
| PREMIERLEAGUE | 20 |
| TACAPORT | 20 |
| BELGIANPL | 18 |
| EKSTRAKLASA | 18 |
| EREDIVISIE | 18 |
| LIGAPORTUGAL | 18 |
| SUPERLIG | 18 |
| CHLLDP | 16 |
| CHNSL | 16 |
| CONMEBOLLIB | 16 |
| COPADOBRASIL | 16 |
| ECULP | 16 |
| THAIL1 | 16 |
| UCLLEAGUE | 16 |
| UEFANLGROUP | 16 |
| MLS1H | 15 |
| MLSEAST | 15 |
| MLSWEST | 15 |
| ARGNACB | 14 |
| LALIGA2 | 14 |
| SVK2L | 14 |
| VENFUTVE | 14 |
| LIGAMX2H | 12 |
| MLS2H | 6 |
| CANPL | 3 |
| CHNL1 | 3 |
| SVKCUP | 3 |
| USLCUP | 3 |

Unknown ticker bodies (top 40) — the next taxonomy work items:

| body | n | example ticker | example title |
|---|---|---|---|
| CONMEBOLSUD | 8 | `KXCONMEBOLSUD-26-ATL` | Will Atlético Mineiro win the 2026 CONMEBOL Sudamericana? |
| COPADELREYADVANCE | 10 | `KXCOPADELREYADVANCE-26OCT03BAZATL-ATL` | Atletico Calatayud To Advance |
| DENSUPERLIGA | 12 | `KXDENSUPERLIGA-27-AGF` | Will Aarhus win the Danish Superliga? |
| EPLH2H | 6 | `KXEPLH2H-27ARSTOT-ARS` | Will Arsenal win both 2026-27 EPL matches against Tottenham? |
| HKANEKNIGHT | 1 | `KXHKANEKNIGHT-26-YES` | Will Harry Kane be Knighted in 2026? |
| JOINLEAGUE | 8 | `KXJOINLEAGUE-26OCT02DALABA-BUND` | Where will David Alaba go next? |
| JOINRONALDO | 11 | `KXJOINRONALDO-27-BOT` | Where will Cristiano Ronaldo go next? |
| KLEAGUE | 12 | `KXKLEAGUE-26-ANY` | Will FC Anyang win the Korea K League 1? |
| LAMINEYAMAL | 1 | `KXLAMINEYAMAL-27-LYAM` | Will Lamine Yamal leave Barcelona before 2027? |
| LIGAMX2H | 6 | `KXLIGAMX2H-26SEP27LEOJUA-JUA` | Juarez wins 2nd Half |
| MANAGEROUTDATE | 4 | `KXMANAGEROUTDATE-28TUCHEL-27JAN01` | Will Thomas Tuchel be out before Jan 1, 2027? |
| MLS2H | 3 | `KXMLS2H-26SEP27CLBMIA-CLB` | Columbus wins 2nd Half |
| POCHETTINOOUT | 1 | `KXPOCHETTINOOUT-30-Y` | Will Mauricio Pochettino leave as manager of the US Men's National Team before the start date of the 2030 Men's FIFA World Cup main tourname |
| SOCCERTREBLE | 2 | `KXSOCCERTREBLE-27ARS-DOM` | Will Arsenal win the domestic treble in the 2026-27 season? |
| SUPERBALLONDOR | 1 | `KXSUPERBALLONDOR-30-YES` | Will a Super Ballon d'Or be awarded before 2030? |
| SVKCUPADVANCE | 2 | `KXSVKCUPADVANCE-26SEP29BRAZEP-BRA` | Inter Bratislava To Advance |
| USLCUPADVANCE | 2 | `KXUSLCUPADVANCE-26OCT04HARLFC-HAR` | Hartford Athletic To Advance |
| WCCAREERGOALS | 3 | `KXWCCAREERGOALS-KMBAPPE-30` | Will Kylian Mbappe score at least 30 goals in the World Cup in his career? |
| WCTEAMS | 1 | `KXWCTEAMS-2030-YES` | Will there be 64 teams in the 2030 World Cup Tournament? |
| WINSTREAKMANU | 1 | `KXWINSTREAKMANU-27-5` | Will Manchester United men's soccer win at least 5 games in a row this year? |

Events sanity: events_matching_a_market_event=1050, events_not_in_swept_series=0, events_total=17691, market_event_tickers=1050, market_event_tickers_without_event_row=0

Market status histogram: active=6534


`data/catalog/latest_index.json` is refreshed daily; `unknown_body_histogram` there is the queue of taxonomy work.
