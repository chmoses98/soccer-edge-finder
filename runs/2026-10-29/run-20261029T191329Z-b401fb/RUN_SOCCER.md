# RUN SOCCER — 2026-10-29
Run `run-20261029T191329Z-b401fb` generated 2026-10-29T19:13:46.661422Z · filters: {'leagues': [], 'games': ['fx:bra.serie_a:2026:bra.coritiba:bra.vitoria', 'fx:usa.mls:2026:usa.sporting_kc:usa.fc_dallas', 'fx:usa.mls:2026:usa.st_louis_city:usa.san_diego'], 'window_hours': 49, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5627** (discovery complete: True)
- contracts evaluated: 120 · excluded mechanically: 2529 · unsupported/unknown: 2978
- **unaccounted contracts: 0**
- by disposition: priced=120, unknown_family=3, unsupported_family=2975, unmapped_event=1048, unmapped_team=164, no_fixture=120, filtered_by_operator=1197
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAPSL, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-29T19:13:29.482650Z; market_observed_at: 2026-10-29T19:10:36.240587Z; fixtures_observed_at: 2026-10-29T17:27:59.773710Z; results_observed_at: 2026-10-29T17:27:53.076548Z; model_fitted_at: 2026-10-29T19:13:28.312598Z; temporal_guard: {'decision_time': '2026-10-29T19:13:29.482650Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-29T17:27:59.773710Z', 'market_snapshots': '2026-10-29T19:13:25.188940Z', 'reference_odds': '2026-10-29T17:28:00.282933Z', 'results': '2026-10-29T19:13:29.282990Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (4)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- St. Louis City SC vs San Diego FC · Result: away · NO @ 0.7300 · fair 85.4% [75.8%–93.5%] · edge +11.0% · P(+) 92% · RESEARCH_ONLY · `KXMLSGAME-26OCT31STLSD-SD`
- St. Louis City SC vs San Diego FC · away team total over 1.5 · NO @ 0.5700 · fair 69.5% [56.9%–81.9%] · edge +10.8% · P(+) 87% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT31STLSD-SD2`
- St. Louis City SC vs San Diego FC · away team total over 0.5 · NO @ 0.2300 · fair 34.0% [23.0%–46.3%] · edge +9.8% · P(+) 87% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT31STLSD-SD1`
- St. Louis City SC vs San Diego FC · away wins by more than 1.5 · NO @ 0.9000 · fair 94.4% [89.7%–98.0%] · edge +3.8% · P(+) 86% · RESEARCH_ONLY · `KXMLSSPREAD-26OCT31STLSD-SD2`

## Expressions removed by the reducer (3)
- `KXMLSGAME-26OCT31STLSD-STL` yes: redundant with KXMLSGAME-26OCT31STLSD-SD/no (corr +0.60); best expression kept
- `KXMLSSPREAD-26OCT31STLSD-STL2` yes: redundant with KXMLSGAME-26OCT31STLSD-SD/no (corr +0.40); best expression kept
- `KXMLSSPREAD-26OCT31STLSD-STL3` yes: redundant with KXMLSGAME-26OCT31STLSD-SD/no (corr +0.27); best expression kept

## Events
- St. Louis City SC vs San Diego FC (Major League Soccer) 2026-10-31T19:00:00Z · markets 32/32 evaluated · lineups unknown · xG 2.64-1.12 · 1X2 68%/17%/14%
- Sporting Kansas City vs FC Dallas (Major League Soccer) 2026-10-31T19:00:00Z · markets 77/77 evaluated · lineups unknown · xG 1.47-1.79 · 1X2 32%/23%/45%
- Coritiba vs Vitória (Brasileirão Série A) 2026-10-31T19:00:00Z · markets 11/11 evaluated · lineups unknown · xG 1.36-1.13 · 1X2 41%/28%/31%
