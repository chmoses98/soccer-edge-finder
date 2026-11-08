# RUN SOCCER — 2026-11-08
Run `run-20261108T213359Z-1ef073` generated 2026-11-08T21:34:24.592348Z · filters: {'leagues': [], 'games': [], 'window_hours': 48, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5461** (discovery complete: True)
- contracts evaluated: 168 · excluded mechanically: 2275 · unsupported/unknown: 3018
- **unaccounted contracts: 0**
- by disposition: priced=168, started=240, unknown_family=48, unsupported_family=2970, unmapped_event=1030, unmapped_team=122, no_fixture=170, out_of_window=713
- competitions discovered: APFDDH, ARGPREMDIV, BELGIANPL, BOLPDIV, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CHLLDP, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, COUPEDEFRANCE, CZEFNL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EERSTEDIV, EFL, EFLCHAMPIONSHIP, EFLL1, EFLTROPHY, EKSTRAKLASA, ELITESERIEN, EPL, EREDIVISIE, FA, FRAPLW, INTLFRIENDLY, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LALIGA2H, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, LIGUE12H, LVAVIR, MLS, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SAFF, SAUDIPL, SERIEA, SERIEA2H, SERIEC, SOCCER, SUPERLIG, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-08T21:33:59.510963Z; market_observed_at: 2026-11-08T21:19:30.093400Z; fixtures_observed_at: 2026-11-08T21:19:28.331127Z; results_observed_at: 2026-11-08T21:19:20.652298Z; model_fitted_at: 2026-11-08T21:19:28.701490Z; temporal_guard: {'decision_time': '2026-11-08T21:33:59.510963Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-08T21:19:28.331127Z', 'market_snapshots': '2026-11-08T21:33:57.722762Z', 'reference_odds': '2026-11-08T21:33:57.942758Z', 'results': '2026-11-08T21:19:30.083188Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (11)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- León vs Guadalajara · away team total over 1.5 · NO @ 0.5100 · fair 66.4% [52.7%–79.4%] · edge +13.7% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG2`
- Querétaro vs Puebla · btts · NO @ 0.4400 · fair 57.7% [45.8%–69.4%] · edge +12.0% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMXBTTS-26NOV08QUEPUE-BTTS`
- León vs Guadalajara · away team total over 0.5 · NO @ 0.1900 · fair 31.4% [20.3%–43.2%] · edge +11.3% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG1`
- León vs Guadalajara · Total goals over 3.5 · NO @ 0.6600 · fair 77.5% [64.7%–88.5%] · edge +10.0% · P(+) 84% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26NOV08LEOCDG-4`
- Querétaro vs Puebla · Total goals over 3.5 · NO @ 0.6800 · fair 78.6% [65.0%–90.3%] · edge +9.1% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26NOV08QUEPUE-4`
- León vs Guadalajara · Exact score 1-0 (home-away) · YES @ 0.0600 · fair 10.7% [6.4%–15.3%] · edge +4.3% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMXSCORE-26NOV08LEOCDG-LEO1CDG0`
- Querétaro vs Puebla · away team total over 1.5 · NO @ 0.7100 · fair 79.2% [67.6%–89.1%] · edge +6.8% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV08QUEPUE-PUE2`
- Querétaro vs Puebla · Exact score 1-0 (home-away) · YES @ 0.1000 · fair 14.2% [9.1%–19.5%] · edge +3.6% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMXSCORE-26NOV08QUEPUE-QUE1PUE0`
- Querétaro vs Puebla · First-half total goals over 2.5 · NO @ 0.8600 · fair 90.9% [83.9%–97.1%] · edge +4.1% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMX1HTOTAL-26NOV08QUEPUE-3`
- León vs Guadalajara · Total goals over 0.5 · NO @ 0.0600 · fair 10.3% [5.1%–16.1%] · edge +3.9% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26NOV08LEOCDG-1`
- León vs Guadalajara · Exact score 2-0 (home-away) · YES @ 0.0400 · fair 6.4% [3.4%–9.4%] · edge +2.1% · P(+) 80% · RESEARCH_ONLY · `KXLIGAMXSCORE-26NOV08LEOCDG-LEO2CDG0`

## Expressions removed by the reducer (13)
- `KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG3` no: redundant with KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG2/no (corr +0.54); best expression kept
- `KXLIGAMXSPREAD-26NOV08LEOCDG-CDG3` no: dominated by KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG2/no (corr +0.35)
- `KXLIGAMXSPREAD-26NOV08LEOCDG-CDG2` no: dominated by KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG2/no (corr +0.62)
- `KXLIGAMXBTTS-26NOV08LEOCDG-BTTS` no: dominated by KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG1/no (corr +0.63)
- `KXLIGAMXTOTAL-26NOV08LEOCDG-2` no: dominated by KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG1/no (corr +0.51)
- `KXLIGAMXSCORE-26NOV08LEOCDG-LEO0CDG0` yes: redundant with KXLIGAMXTOTAL-26NOV08LEOCDG-1/no (corr +1.00); best expression kept
- `KXLIGAMXTOTAL-26NOV08LEOCDG-3` no: redundant with KXLIGAMXTOTAL-26NOV08LEOCDG-4/no (corr +0.63); best expression kept
- `KXLIGAMXTOTAL-26NOV08LEOCDG-5` no: dominated by KXLIGAMXTOTAL-26NOV08LEOCDG-4/no (corr +0.63)
- `KXLIGAMXTOTAL-26NOV08LEOCDG-6` no: dominated by KXLIGAMXTOTAL-26NOV08LEOCDG-4/no (corr +0.39)
- `KXLIGAMXTEAMTOTAL-26NOV08QUEPUE-PUE1` no: dominated by KXLIGAMXBTTS-26NOV08QUEPUE-BTTS/no (corr +0.76)
- `KXLIGAMXTOTAL-26NOV08QUEPUE-2` no: dominated by KXLIGAMXBTTS-26NOV08QUEPUE-BTTS/no (corr +0.61)
- `KXLIGAMXTOTAL-26NOV08QUEPUE-3` no: redundant with KXLIGAMXTOTAL-26NOV08QUEPUE-4/no (corr +0.63); best expression kept
- `KXLIGAMXTOTAL-26NOV08QUEPUE-5` no: dominated by KXLIGAMXTOTAL-26NOV08QUEPUE-4/no (corr +0.63)

## Events
- León vs Guadalajara (Liga MX) 2026-11-09T02:10:00Z · markets 77/77 evaluated · lineups unknown · xG 1.19-1.20 · 1X2 36%/28%/37%
- Querétaro vs Puebla (Liga MX) 2026-11-09T00:00:00Z · markets 77/77 evaluated · lineups unknown · xG 1.50-0.84 · 1X2 52%/27%/22%
- Central Córdoba vs Lanús (Liga Profesional Argentina) 2026-11-08T22:30:00Z · markets 14/14 evaluated · lineups unknown · xG 0.85-1.44 · 1X2 23%/27%/50%
