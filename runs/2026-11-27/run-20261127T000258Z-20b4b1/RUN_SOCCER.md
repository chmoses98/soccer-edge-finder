# RUN SOCCER — 2026-11-27
Run `run-20261127T000258Z-20b4b1` generated 2026-11-27T00:03:08.419393Z · filters: {'leagues': [], 'games': ['fx:mex.liga_mx:2026:mex.pachuca:mex.guadalajara'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5162** (discovery complete: True)
- contracts evaluated: 79 · excluded mechanically: 2082 · unsupported/unknown: 3001
- **unaccounted contracts: 0**
- by disposition: priced=79, unknown_family=52, unsupported_family=2949, unmapped_event=889, no_fixture=21, filtered_by_operator=1171, unpriceable=1
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BOTOLA, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, HUNNB1, INDSL, ISRNL, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAPSL, SERIEA, SOCCER, SUPERLIG, SVK1L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-27T00:02:58.442480Z; market_observed_at: 2026-11-26T23:59:13.734906Z; fixtures_observed_at: 2026-11-26T23:04:44.910552Z; results_observed_at: 2026-11-26T22:12:04.114267Z; model_fitted_at: 2026-11-27T00:02:57.336342Z; temporal_guard: {'decision_time': '2026-11-27T00:02:58.442480Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-26T23:04:44.910552Z', 'market_snapshots': '2026-11-27T00:02:48.193562Z', 'reference_odds': '2026-11-26T22:12:14.156651Z', 'results': '2026-11-27T00:02:58.299019Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (10)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Pachuca vs Guadalajara · away team total over 0.5 · NO @ 0.2500 · fair 39.0% [27.1%–50.8%] · edge +12.7% · P(+) 91% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV26PACCDG-CDG1`
- Pachuca vs Guadalajara · away team total over 1.5 · NO @ 0.6300 · fair 74.5% [62.5%–85.2%] · edge +9.9% · P(+) 86% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV26PACCDG-CDG2`
- Pachuca vs Guadalajara · away wins by more than 1.5 · NO @ 0.8300 · fair 90.0% [83.4%–95.6%] · edge +6.0% · P(+) 88% · RESEARCH_ONLY · `KXLIGAMXSPREAD-26NOV26PACCDG-CDG2`
- Pachuca vs Guadalajara · First-half result: away · NO @ 0.7000 · fair 78.6% [69.7%–87.2%] · edge +7.1% · P(+) 85% · RESEARCH_ONLY · `KXLIGAMX1H-26NOV26PACCDG-CDG`
- Pachuca vs Guadalajara · Exact score 2-0 (home-away) · YES @ 0.0500 · fair 8.8% [5.6%–12.1%] · edge +3.5% · P(+) 93% · RESEARCH_ONLY · `KXLIGAMXSCORE-26NOV26PACCDG-PAC2CDG0`
- Pachuca vs Guadalajara · home wins by more than 1.5 · YES @ 0.1300 · fair 22.7% [11.9%–35.5%] · edge +8.9% · P(+) 84% · RESEARCH_ONLY · `KXLIGAMXSPREAD-26NOV26PACCDG-PAC2`
- Pachuca vs Guadalajara · away team total over 2.5 · NO @ 0.8700 · fair 91.9% [85.6%–96.9%] · edge +4.1% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV26PACCDG-CDG3`
- Pachuca vs Guadalajara · First half: away wins by more than 1.5 · NO @ 0.9300 · fair 95.7% [91.9%–99.1%] · edge +2.2% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMX1HSPREAD-26NOV26PACCDG-CDG2`
- Pachuca vs Guadalajara · Exact score 1-0 (home-away) · YES @ 0.0900 · fair 12.9% [8.5%–17.7%] · edge +3.4% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMXSCORE-26NOV26PACCDG-PAC1CDG0`
- Pachuca vs Guadalajara · home wins by more than 2.5 · YES @ 0.0400 · fair 9.1% [3.4%–16.7%] · edge +4.9% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMXSPREAD-26NOV26PACCDG-PAC3`

## Expressions removed by the reducer (4)
- `KXLIGAMXGAME-26NOV26PACCDG-CDG` no: dominated by KXLIGAMXTEAMTOTAL-26NOV26PACCDG-CDG1/no (corr +0.48)
- `KXLIGAMXGAME-26NOV26PACCDG-PAC` yes: redundant with KXLIGAMXTEAMTOTAL-26NOV26PACCDG-CDG1/no (corr +0.43); best expression kept
- `KXLIGAMXFTTS-26NOV26PACCDG-CDG` no: dominated by KXLIGAMXTEAMTOTAL-26NOV26PACCDG-CDG1/no (corr +0.61)
- `KXLIGAMXFTTS-26NOV26PACCDG-PAC` yes: dominated by KXLIGAMXTEAMTOTAL-26NOV26PACCDG-CDG1/no (corr +0.33)

## Events
- Pachuca vs Guadalajara (Liga MX) 2026-11-27T01:00:00Z · markets 79/80 evaluated · lineups unknown · xG 1.39-0.97 · 1X2 46%/27%/27%
