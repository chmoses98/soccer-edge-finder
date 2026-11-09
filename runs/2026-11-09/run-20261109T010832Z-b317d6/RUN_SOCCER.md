# RUN SOCCER — 2026-11-09
Run `run-20261109T010832Z-b317d6` generated 2026-11-09T01:08:46.466409Z · filters: {'leagues': [], 'games': ['fx:mex.liga_mx:2026:mex.leon:mex.guadalajara'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4438** (discovery complete: True)
- contracts evaluated: 77 · excluded mechanically: 1388 · unsupported/unknown: 2973
- **unaccounted contracts: 0**
- by disposition: priced=77, unknown_family=3, unsupported_family=2970, unmapped_event=426, unmapped_team=51, no_fixture=144, filtered_by_operator=767
- competitions discovered: APFDDH, ARGPREMDIV, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CHLLDP, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EFLTROPHY, EKSTRAKLASA, EPL, EREDIVISIE, FA, FRAPLW, INTLFRIENDLY, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SAFF, SERIEA, SOCCER, SUPERLIG, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-09T01:08:32.897255Z; market_observed_at: 2026-11-09T01:05:24.562970Z; fixtures_observed_at: 2026-11-09T00:32:21.448824Z; results_observed_at: 2026-11-09T00:32:13.894395Z; model_fitted_at: 2026-11-09T01:08:31.283094Z; temporal_guard: {'decision_time': '2026-11-09T01:08:32.897255Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-09T00:32:21.448824Z', 'market_snapshots': '2026-11-09T01:08:22.692688Z', 'reference_odds': '2026-11-09T00:32:21.886697Z', 'results': '2026-11-09T01:08:32.628092Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (10)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- León vs Guadalajara · away team total over 1.5 · NO @ 0.4800 · fair 66.3% [51.1%–78.9%] · edge +16.5% · P(+) 92% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG2`
- León vs Guadalajara · away team total over 0.5 · NO @ 0.1800 · fair 31.2% [19.3%–42.5%] · edge +12.2% · P(+) 91% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG1`
- León vs Guadalajara · Total goals over 2.5 · NO @ 0.4300 · fair 57.9% [42.1%–72.1%] · edge +13.2% · P(+) 86% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26NOV08LEOCDG-3`
- León vs Guadalajara · First half: away wins by more than 1.5 · NO @ 0.8700 · fair 93.2% [87.9%–98.1%] · edge +5.4% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMX1HSPREAD-26NOV08LEOCDG-CDG2`
- León vs Guadalajara · Result: away · NO @ 0.5000 · fair 63.0% [47.9%–76.3%] · edge +11.2% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMXGAME-26NOV08LEOCDG-CDG`
- León vs Guadalajara · Exact score 1-0 (home-away) · YES @ 0.0600 · fair 10.7% [6.4%–15.1%] · edge +4.3% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMXSCORE-26NOV08LEOCDG-LEO1CDG0`
- León vs Guadalajara · First-half result: away · NO @ 0.6300 · fair 72.2% [60.8%–82.2%] · edge +7.5% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMX1H-26NOV08LEOCDG-CDG`
- León vs Guadalajara · First-half total goals over 1.5 · NO @ 0.6300 · fair 71.7% [59.8%–82.2%] · edge +7.0% · P(+) 80% · RESEARCH_ONLY · `KXLIGAMX1HTOTAL-26NOV08LEOCDG-2`
- León vs Guadalajara · First-half total goals over 2.5 · NO @ 0.8600 · fair 90.6% [83.9%–96.1%] · edge +3.8% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMX1HTOTAL-26NOV08LEOCDG-3`
- León vs Guadalajara · Exact score 0-0 (home-away) · YES @ 0.0600 · fair 10.4% [5.1%–16.2%] · edge +4.0% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMXSCORE-26NOV08LEOCDG-LEO0CDG0`

## Expressions removed by the reducer (9)
- `KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG3` no: dominated by KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG2/no (corr +0.54)
- `KXLIGAMXSPREAD-26NOV08LEOCDG-CDG2` no: dominated by KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG2/no (corr +0.62)
- `KXLIGAMXSPREAD-26NOV08LEOCDG-CDG3` no: dominated by KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG2/no (corr +0.35)
- `KXLIGAMXBTTS-26NOV08LEOCDG-BTTS` no: dominated by KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG1/no (corr +0.63)
- `KXLIGAMXTOTAL-26NOV08LEOCDG-2` no: dominated by KXLIGAMXTEAMTOTAL-26NOV08LEOCDG-CDG1/no (corr +0.51)
- `KXLIGAMXTOTAL-26NOV08LEOCDG-1` no: dominated by KXLIGAMXSCORE-26NOV08LEOCDG-LEO0CDG0/yes (corr +1.00)
- `KXLIGAMXTOTAL-26NOV08LEOCDG-4` no: dominated by KXLIGAMXTOTAL-26NOV08LEOCDG-3/no (corr +0.63)
- `KXLIGAMXTOTAL-26NOV08LEOCDG-5` no: redundant with KXLIGAMXTOTAL-26NOV08LEOCDG-3/no (corr +0.39); best expression kept
- `KXLIGAMXTOTAL-26NOV08LEOCDG-6` no: redundant with KXLIGAMXTOTAL-26NOV08LEOCDG-3/no (corr +0.24); best expression kept

## Events
- León vs Guadalajara (Liga MX) 2026-11-09T02:10:00Z · markets 77/77 evaluated · lineups unknown · xG 1.17-1.20 · 1X2 35%/28%/37%
