# RUN SOCCER — 2026-11-23
Run `run-20261123T235827Z-eb16ef` generated 2026-11-23T23:58:33.780759Z · filters: {'leagues': [], 'games': ['fx:usa.mls:2026:usa.st_louis_city:usa.lafc'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4203** (discovery complete: True)
- contracts evaluated: 32 · excluded mechanically: 1215 · unsupported/unknown: 2956
- **unaccounted contracts: 0**
- by disposition: priced=32, ambiguous_ownership=27, unknown_family=4, unsupported_family=2952, unmapped_event=347, unmapped_team=48, no_fixture=104, filtered_by_operator=689
- competitions discovered: AFCCL2, APFDDH, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BRASILEIRO, BULFL, BUNDESLIGA, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, HUNNB1, INDSL, ISRNL, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAMX, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, PERLIGA1, PREMIERLEAGUE, ROML1, SAPSL, SERIEA, SOCCER, SUPERLIG, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-23T23:58:27.740242Z; market_observed_at: 2026-11-23T23:55:00.082842Z; fixtures_observed_at: 2026-11-23T19:33:58.009271Z; results_observed_at: 2026-11-23T19:33:52.901344Z; model_fitted_at: 2026-11-23T23:58:26.435751Z; temporal_guard: {'decision_time': '2026-11-23T23:58:27.740242Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-23T19:33:58.009271Z', 'market_snapshots': '2026-11-23T23:58:17.924200Z', 'reference_odds': '2026-11-23T19:33:58.305721Z', 'results': '2026-11-23T23:58:27.510196Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (10)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- St. Louis City SC vs Los Angeles FC · away team total over 1.5 · NO @ 0.5700 · fair 75.6% [63.5%–85.9%] · edge +16.8% · P(+) 96% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV23STLLAFC-LAFC2`
- St. Louis City SC vs Los Angeles FC · away team total over 0.5 · NO @ 0.2200 · fair 40.0% [27.9%–51.9%] · edge +16.8% · P(+) 96% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV23STLLAFC-LAFC1`
- St. Louis City SC vs Los Angeles FC · Result: away · NO @ 0.6400 · fair 78.8% [68.4%–88.5%] · edge +13.2% · P(+) 93% · RESEARCH_ONLY · `KXMLSGAME-26NOV23STLLAFC-LAFC`
- St. Louis City SC vs Los Angeles FC · Result: home · YES @ 0.3700 · fair 55.0% [39.8%–69.8%] · edge +16.4% · P(+) 92% · RESEARCH_ONLY · `KXMLSGAME-26NOV23STLLAFC-STL`
- St. Louis City SC vs Los Angeles FC · away wins by more than 1.5 · NO @ 0.8300 · fair 92.4% [86.8%–96.9%] · edge +8.4% · P(+) 95% · RESEARCH_ONLY · `KXMLSSPREAD-26NOV23STLLAFC-LAFC2`
- St. Louis City SC vs Los Angeles FC · away team total over 2.5 · NO @ 0.8300 · fair 92.4% [86.2%–97.1%] · edge +8.4% · P(+) 94% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV23STLLAFC-LAFC3`
- St. Louis City SC vs Los Angeles FC · First-half result: away · NO @ 0.7100 · fair 81.7% [72.8%–89.2%] · edge +9.2% · P(+) 91% · RESEARCH_ONLY · `KXMLS1H-26NOV23STLLAFC-LAFC`
- St. Louis City SC vs Los Angeles FC · Second-half result: away · NO @ 0.6900 · fair 80.2% [70.7%–89.2%] · edge +9.7% · P(+) 90% · RESEARCH_ONLY · `KXMLS2H-26NOV23STLLAFC-LAFC`
- St. Louis City SC vs Los Angeles FC · away wins by more than 2.5 · NO @ 0.9400 · fair 97.8% [95.7%–99.4%] · edge +3.4% · P(+) 95% · RESEARCH_ONLY · `KXMLSSPREAD-26NOV23STLLAFC-LAFC3`
- St. Louis City SC vs Los Angeles FC · First half: away wins by more than 1.5 · NO @ 0.9300 · fair 96.4% [92.9%–99.1%] · edge +3.0% · P(+) 86% · RESEARCH_ONLY · `KXMLS1HSPREAD-26NOV23STLLAFC-LAFC2`

## Expressions removed by the reducer (3)
- `KXMLSSPREAD-26NOV23STLLAFC-STL2` yes: dominated by KXMLSGAME-26NOV23STLLAFC-STL/yes (corr +0.61)
- `KXMLSSPREAD-26NOV23STLLAFC-STL3` yes: dominated by KXMLSGAME-26NOV23STLLAFC-STL/yes (corr +0.38)
- `KXMLSBTTS-26NOV23STLLAFC-BTTS` no: dominated by KXMLSTEAMTOTAL-26NOV23STLLAFC-LAFC1/no (corr +0.79)

## Events
- St. Louis City SC vs Los Angeles FC (Major League Soccer) 2026-11-24T01:00:00Z · markets 32/32 evaluated · lineups unknown · xG 1.73-0.95 · 1X2 55%/24%/21%
