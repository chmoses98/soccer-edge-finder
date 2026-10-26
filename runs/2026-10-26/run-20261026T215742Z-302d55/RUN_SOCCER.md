# RUN SOCCER — 2026-10-26
Run `run-20261026T215742Z-302d55` generated 2026-10-26T21:57:44.580093Z · filters: {'leagues': [], 'games': ['fx:arg.primera:2026:arg.union:arg.estudiantes', 'fx:bra.serie_a:2026:bra.flamengo:bra.atletico_mineiro'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4844** (discovery complete: True)
- contracts evaluated: 14 · excluded mechanically: 1816 · unsupported/unknown: 3014
- **unaccounted contracts: 0**
- by disposition: priced=14, unknown_family=3, unsupported_family=3011, unmapped_event=428, unmapped_team=265, no_fixture=108, filtered_by_operator=1015
- competitions discovered: APFDDH, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CHLLDP, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FRAPLW, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LIGAEXP, LIGAMX, LIGAPORTUGAL, LIGUE1, MLS, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SAPSL, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-26T21:57:42.758599Z; market_observed_at: 2026-10-26T21:55:00.056189Z; fixtures_observed_at: 2026-10-26T17:46:32.766060Z; results_observed_at: 2026-10-26T17:46:25.814948Z; model_fitted_at: 2026-10-26T21:57:40.942251Z; temporal_guard: {'decision_time': '2026-10-26T21:57:42.758599Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-26T17:46:32.766060Z', 'market_snapshots': '2026-10-26T21:57:33.101356Z', 'reference_odds': '2026-10-26T17:46:35.091672Z', 'results': '2026-10-26T21:57:42.359322Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (2)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Flamengo vs Atlético Mineiro · Result: home · NO @ 0.2300 · fair 36.8% [22.0%–51.9%] · edge +12.5% · P(+) 86% · RESEARCH_ONLY · `KXBRASILEIROGAME-26OCT26FLAATL-FLA`
- Flamengo vs Atlético Mineiro · Total goals over 0.5 · NO @ 0.0400 · fair 8.7% [3.6%–14.7%] · edge +4.5% · P(+) 85% · RESEARCH_ONLY · `KXBRASILEIROTOTAL-26OCT26FLAATL-1`

## Expressions removed by the reducer (3)
- `KXBRASILEIROSPREAD-26OCT26FLAATL-FLA2` no: redundant with KXBRASILEIROGAME-26OCT26FLAATL-FLA/no (corr +0.61); best expression kept
- `KXBRASILEIROSPREAD-26OCT26FLAATL-FLA3` no: dominated by KXBRASILEIROGAME-26OCT26FLAATL-FLA/no (corr +0.38)
- `KXBRASILEIROGAME-26OCT26FLAATL-TIE` yes: dominated by KXBRASILEIROGAME-26OCT26FLAATL-FLA/no (corr +0.71)

## Events
- Flamengo vs Atlético Mineiro (Brasileirão Série A) 2026-10-26T23:00:00Z · markets 14/14 evaluated · lineups unknown · xG 1.91-0.73 · 1X2 63%/23%/14%
