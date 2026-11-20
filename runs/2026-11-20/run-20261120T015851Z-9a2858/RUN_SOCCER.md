# RUN SOCCER — 2026-11-20
Run `run-20261120T015851Z-9a2858` generated 2026-11-20T01:59:05.263981Z · filters: {'leagues': [], 'games': ['fx:usa.mls:2026:usa.seattle_sounders:usa.real_salt_lake'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5413** (discovery complete: True)
- contracts evaluated: 79 · excluded mechanically: 2480 · unsupported/unknown: 2854
- **unaccounted contracts: 0**
- by disposition: priced=79, ambiguous_ownership=3, unknown_family=4, unsupported_family=2850, unmapped_event=1053, unmapped_team=51, no_fixture=78, filtered_by_operator=1294, unpriceable=1
- competitions discovered: AFCCL2, ALEAGUEW, APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGAW, CANPL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, ENGWLEAGUECUP, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAPSL, SCOCHAMP, SERIEA, SOCCER, SUPERETTAN, SUPERLIG, SVK1L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-20T01:58:51.780061Z; market_observed_at: 2026-11-20T01:55:06.702376Z; fixtures_observed_at: 2026-11-19T23:42:26.889504Z; results_observed_at: 2026-11-19T23:42:19.804411Z; model_fitted_at: 2026-11-20T01:58:50.253120Z; temporal_guard: {'decision_time': '2026-11-20T01:58:51.780061Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-19T23:42:26.889504Z', 'market_snapshots': '2026-11-20T01:58:42.149642Z', 'reference_odds': '2026-11-19T23:42:27.173519Z', 'results': '2026-11-20T01:58:51.592338Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (10)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Seattle Sounders vs Real Salt Lake · btts · NO @ 0.3800 · fair 53.9% [42.4%–64.9%] · edge +14.2% · P(+) 94% · RESEARCH_ONLY · `KXMLSBTTS-26NOV19SEARSL-BTTS`
- Seattle Sounders vs Real Salt Lake · Total goals over 3.5 · NO @ 0.6200 · fair 76.1% [62.7%–87.2%] · edge +12.5% · P(+) 88% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV19SEARSL-4`
- Seattle Sounders vs Real Salt Lake · away team total over 1.5 · NO @ 0.6300 · fair 75.7% [64.5%–85.6%] · edge +11.1% · P(+) 90% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV19SEARSL-RSL2`
- Seattle Sounders vs Real Salt Lake · away team total over 2.5 · NO @ 0.8600 · fair 92.6% [86.9%–97.0%] · edge +5.7% · P(+) 90% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV19SEARSL-RSL3`
- Seattle Sounders vs Real Salt Lake · First-half total goals over 1.5 · NO @ 0.6000 · fair 70.7% [58.8%–81.2%] · edge +9.0% · P(+) 86% · RESEARCH_ONLY · `KXMLS1HTOTAL-26NOV19SEARSL-2`
- Seattle Sounders vs Real Salt Lake · First-half exact score 0-0 (home-away) · YES @ 0.2500 · fair 34.6% [23.8%–45.2%] · edge +8.3% · P(+) 84% · RESEARCH_ONLY · `KXMLS1HSCORE-26NOV19SEARSL-SEA0RSL0`
- Seattle Sounders vs Real Salt Lake · Exact score 1-0 (home-away) · YES @ 0.0800 · fair 12.9% [8.3%–17.3%] · edge +4.4% · P(+) 89% · RESEARCH_ONLY · `KXMLSSCORE-26NOV19SEARSL-SEA1RSL0`
- Seattle Sounders vs Real Salt Lake · Total goals over 0.5 · NO @ 0.0500 · fair 9.5% [4.6%–14.9%] · edge +4.1% · P(+) 84% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV19SEARSL-1`
- Seattle Sounders vs Real Salt Lake · First-half total goals over 2.5 · NO @ 0.8500 · fair 90.1% [82.9%–96.1%] · edge +4.2% · P(+) 82% · RESEARCH_ONLY · `KXMLS1HTOTAL-26NOV19SEARSL-3`
- Seattle Sounders vs Real Salt Lake · Exact score 2-0 (home-away) · YES @ 0.0700 · fair 9.6% [6.5%–12.8%] · edge +2.1% · P(+) 81% · RESEARCH_ONLY · `KXMLSSCORE-26NOV19SEARSL-SEA2RSL0`

## Expressions removed by the reducer (8)
- `KXMLS1HBTTS-26NOV19SEARSL-BTTS` no: redundant with KXMLS1HTOTAL-26NOV19SEARSL-2/no (corr +0.69); best expression kept
- `KXMLSTEAMTOTAL-26NOV19SEARSL-RSL1` no: dominated by KXMLSBTTS-26NOV19SEARSL-BTTS/no (corr +0.76)
- `KXMLSTOTAL-26NOV19SEARSL-2` no: dominated by KXMLSBTTS-26NOV19SEARSL-BTTS/no (corr +0.62)
- `KXMLS1HTOTAL-26NOV19SEARSL-1` no: dominated by KXMLS1HSCORE-26NOV19SEARSL-SEA0RSL0/yes (corr +1.00)
- `KXMLSSCORE-26NOV19SEARSL-SEA0RSL0` yes: redundant with KXMLSTOTAL-26NOV19SEARSL-1/no (corr +1.00); best expression kept
- `KXMLSTOTAL-26NOV19SEARSL-3` no: redundant with KXMLSTOTAL-26NOV19SEARSL-4/no (corr +0.63); best expression kept
- `KXMLSTOTAL-26NOV19SEARSL-5` no: dominated by KXMLSTOTAL-26NOV19SEARSL-4/no (corr +0.63)
- `KXMLSTOTAL-26NOV19SEARSL-6` no: dominated by KXMLSTOTAL-26NOV19SEARSL-4/no (corr +0.39)

## Events
- Seattle Sounders vs Real Salt Lake (Major League Soccer) 2026-11-20T03:00:00Z · markets 79/80 evaluated · lineups unknown · xG 1.52-0.94 · 1X2 50%/26%/24%
