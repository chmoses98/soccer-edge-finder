# RUN SOCCER — 2026-10-31
Run `run-20261031T220208Z-9d79dd` generated 2026-10-31T22:02:17.666625Z · filters: {'leagues': [], 'games': ['fx:mex.liga_mx:2026:mex.pachuca:mex.tigres'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5670** (discovery complete: True)
- contracts evaluated: 77 · excluded mechanically: 2620 · unsupported/unknown: 2973
- **unaccounted contracts: 0**
- by disposition: priced=77, unknown_family=3, unsupported_family=2970, unmapped_event=872, unmapped_team=102, no_fixture=105, filtered_by_operator=1541
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, CANPL, CHLLDP, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EFLTROPHY, EKSTRAKLASA, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SERIEA, SOCCER, SUPERLIG, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-31T22:02:08.590012Z; market_observed_at: 2026-10-31T21:59:04.306872Z; fixtures_observed_at: 2026-10-31T19:56:17.096785Z; results_observed_at: 2026-10-31T19:56:14.275486Z; model_fitted_at: 2026-10-31T22:02:06.745807Z; temporal_guard: {'decision_time': '2026-10-31T22:02:08.590012Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-31T19:56:17.096785Z', 'market_snapshots': '2026-10-31T22:01:58.081864Z', 'reference_odds': '2026-10-31T19:56:17.457196Z', 'results': '2026-10-31T22:02:08.207534Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (9)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Pachuca vs Tigres UANL · btts · NO @ 0.4100 · fair 58.2% [46.0%–69.0%] · edge +15.5% · P(+) 95% · RESEARCH_ONLY · `KXLIGAMXBTTS-26OCT31PACTIG-BTTS`
- Pachuca vs Tigres UANL · Total goals over 2.5 · NO @ 0.4400 · fair 61.2% [45.4%–75.8%] · edge +15.5% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26OCT31PACTIG-3`
- Pachuca vs Tigres UANL · away team total over 1.5 · NO @ 0.6700 · fair 79.0% [66.9%–88.6%] · edge +10.4% · P(+) 88% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT31PACTIG-TIG2`
- Pachuca vs Tigres UANL · away team total over 2.5 · NO @ 0.8900 · fair 94.0% [88.3%–97.9%] · edge +4.3% · P(+) 87% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT31PACTIG-TIG3`
- Pachuca vs Tigres UANL · First-half total goals over 1.5 · NO @ 0.6400 · fair 73.5% [61.8%–84.2%] · edge +7.9% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMX1HTOTAL-26OCT31PACTIG-2`
- Pachuca vs Tigres UANL · Total goals over 0.5 · NO @ 0.0600 · fair 12.1% [5.8%–18.9%] · edge +5.7% · P(+) 88% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26OCT31PACTIG-1`
- Pachuca vs Tigres UANL · First-half total goals over 0.5 · NO @ 0.2800 · fair 37.7% [25.8%–49.2%] · edge +8.3% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMX1HTOTAL-26OCT31PACTIG-1`
- Pachuca vs Tigres UANL · First-half total goals over 2.5 · NO @ 0.8700 · fair 91.8% [85.9%–97.1%] · edge +4.0% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMX1HTOTAL-26OCT31PACTIG-3`
- Pachuca vs Tigres UANL · Exact score 1-0 (home-away) · YES @ 0.1000 · fair 14.2% [9.0%–19.2%] · edge +3.6% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMXSCORE-26OCT31PACTIG-PAC1TIG0`

## Expressions removed by the reducer (7)
- `KXLIGAMXTEAMTOTAL-26OCT31PACTIG-TIG1` no: dominated by KXLIGAMXBTTS-26OCT31PACTIG-BTTS/no (corr +0.75)
- `KXLIGAMXTOTAL-26OCT31PACTIG-2` no: dominated by KXLIGAMXBTTS-26OCT31PACTIG-BTTS/no (corr +0.62)
- `KXLIGAMXSCORE-26OCT31PACTIG-PAC0TIG0` yes: dominated by KXLIGAMXTOTAL-26OCT31PACTIG-1/no (corr +1.00)
- `KXLIGAMX1HBTTS-26OCT31PACTIG-BTTS` no: redundant with KXLIGAMX1HTOTAL-26OCT31PACTIG-2/no (corr +0.67); best expression kept
- `KXLIGAMXTOTAL-26OCT31PACTIG-4` no: dominated by KXLIGAMXTOTAL-26OCT31PACTIG-3/no (corr +0.62)
- `KXLIGAMXTOTAL-26OCT31PACTIG-5` no: dominated by KXLIGAMXTOTAL-26OCT31PACTIG-3/no (corr +0.39)
- `KXLIGAMXTOTAL-26OCT31PACTIG-6` no: dominated by KXLIGAMXTOTAL-26OCT31PACTIG-3/no (corr +0.24)

## Events
- Pachuca vs Tigres UANL (Liga MX) 2026-10-31T23:00:00Z · markets 77/77 evaluated · lineups unknown · xG 1.41-0.85 · 1X2 49%/28%/23%
