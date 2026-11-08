# RUN SOCCER — 2026-11-08
Run `run-20261108T233236Z-423da2` generated 2026-11-08T23:32:44.478921Z · filters: {'leagues': [], 'games': ['fx:mex.liga_mx:2026:mex.queretaro:mex.puebla'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4464** (discovery complete: True)
- contracts evaluated: 77 · excluded mechanically: 1414 · unsupported/unknown: 2973
- **unaccounted contracts: 0**
- by disposition: priced=77, unknown_family=3, unsupported_family=2970, unmapped_event=444, unmapped_team=48, no_fixture=132, filtered_by_operator=790
- competitions discovered: APFDDH, ARGPREMDIV, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CHLLDP, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EFLTROPHY, EKSTRAKLASA, EPL, EREDIVISIE, FA, FRAPLW, INTLFRIENDLY, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SAFF, SERIEA, SOCCER, SUPERLIG, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-08T23:32:36.305325Z; market_observed_at: 2026-11-08T23:29:33.463340Z; fixtures_observed_at: 2026-11-08T18:02:11.793332Z; results_observed_at: 2026-11-08T18:02:07.033923Z; model_fitted_at: 2026-11-08T23:32:35.460224Z; temporal_guard: {'decision_time': '2026-11-08T23:32:36.305325Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-08T18:02:11.793332Z', 'market_snapshots': '2026-11-08T23:32:30.862097Z', 'reference_odds': '2026-11-08T18:02:11.980730Z', 'results': '2026-11-08T23:32:36.137584Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (8)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Querétaro vs Puebla · btts · NO @ 0.4200 · fair 57.7% [45.8%–69.4%] · edge +14.0% · P(+) 93% · RESEARCH_ONLY · `KXLIGAMXBTTS-26NOV08QUEPUE-BTTS`
- Querétaro vs Puebla · Total goals over 3.5 · NO @ 0.6600 · fair 78.6% [65.0%–90.3%] · edge +11.0% · P(+) 86% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26NOV08QUEPUE-4`
- Querétaro vs Puebla · Exact score 2-2 (home-away) · NO @ 0.9400 · fair 96.5% [94.9%–98.0%] · edge +2.1% · P(+) 95% · RESEARCH_ONLY · `KXLIGAMXSCORE-26NOV08QUEPUE-QUE2PUE2`
- Querétaro vs Puebla · First half: both teams to score · NO @ 0.7900 · fair 85.4% [77.9%–93.1%] · edge +5.3% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMX1HBTTS-26NOV08QUEPUE-BTTS`
- Querétaro vs Puebla · away team total over 1.5 · NO @ 0.7100 · fair 79.2% [67.6%–89.1%] · edge +6.8% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV08QUEPUE-PUE2`
- Querétaro vs Puebla · Exact score 1-0 (home-away) · YES @ 0.1000 · fair 14.2% [9.1%–19.5%] · edge +3.6% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMXSCORE-26NOV08QUEPUE-QUE1PUE0`
- Querétaro vs Puebla · Total goals over 0.5 · NO @ 0.0600 · fair 11.1% [5.1%–18.0%] · edge +4.7% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26NOV08QUEPUE-1`
- Querétaro vs Puebla · First-half total goals over 2.5 · NO @ 0.8600 · fair 90.9% [83.9%–97.1%] · edge +4.1% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMX1HTOTAL-26NOV08QUEPUE-3`

## Expressions removed by the reducer (6)
- `KXLIGAMXTOTAL-26NOV08QUEPUE-3` no: redundant with KXLIGAMXTOTAL-26NOV08QUEPUE-4/no (corr +0.63); best expression kept
- `KXLIGAMXTOTAL-26NOV08QUEPUE-5` no: dominated by KXLIGAMXTOTAL-26NOV08QUEPUE-4/no (corr +0.63)
- `KXLIGAMXTOTAL-26NOV08QUEPUE-6` no: dominated by KXLIGAMXTOTAL-26NOV08QUEPUE-4/no (corr +0.39)
- `KXLIGAMXTOTAL-26NOV08QUEPUE-2` no: dominated by KXLIGAMXBTTS-26NOV08QUEPUE-BTTS/no (corr +0.61)
- `KXLIGAMXTEAMTOTAL-26NOV08QUEPUE-PUE1` no: dominated by KXLIGAMXBTTS-26NOV08QUEPUE-BTTS/no (corr +0.76)
- `KXLIGAMXSCORE-26NOV08QUEPUE-QUE0PUE0` yes: dominated by KXLIGAMXTOTAL-26NOV08QUEPUE-1/no (corr +1.00)

## Events
- Querétaro vs Puebla (Liga MX) 2026-11-09T00:00:00Z · markets 77/77 evaluated · lineups unknown · xG 1.50-0.84 · 1X2 52%/27%/22%
