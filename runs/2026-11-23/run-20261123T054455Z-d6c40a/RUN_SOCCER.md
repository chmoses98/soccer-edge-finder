# RUN SOCCER — 2026-11-23
Run `run-20261123T054455Z-d6c40a` generated 2026-11-23T05:45:08.896759Z · filters: {'leagues': [], 'games': ['fx:eng.premier_league:2026-27:eng.brentford:eng.everton', 'fx:esp.la_liga:2026-27:esp.levante:esp.elche', 'fx:ita.serie_a:2026-27:ita.monza:ita.fiorentina', 'fx:usa.mls:2026:usa.san_jose_earthquakes:usa.houston_dynamo'], 'window_hours': 47, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4214** (discovery complete: True)
- contracts evaluated: 82 · excluded mechanically: 1156 · unsupported/unknown: 2976
- **unaccounted contracts: 0**
- by disposition: priced=82, started=3, ambiguous_ownership=27, unknown_family=4, unsupported_family=2972, unmapped_event=383, unmapped_team=48, no_fixture=51, filtered_by_operator=643, unpriceable=1
- competitions discovered: AFCCL2, APFDDH, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BRASILEIRO, BULFL, BUNDESLIGA, BUNDESLIGAW, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, HUNNB1, INDSL, ISRNL, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, PERLIGA1, PREMIERLEAGUE, ROML1, SAPSL, SCOCHAMP, SERIEA, SOCCER, SUPERLIG, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-23T05:44:55.142821Z; market_observed_at: 2026-11-23T05:41:26.449936Z; fixtures_observed_at: 2026-11-23T05:44:51.952968Z; results_observed_at: 2026-11-23T05:44:45.923438Z; model_fitted_at: 2026-11-23T05:44:52.215601Z; temporal_guard: {'decision_time': '2026-11-23T05:44:55.142821Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-23T05:44:51.952968Z', 'market_snapshots': '2026-11-23T05:44:44.979921Z', 'reference_odds': '2026-11-23T05:44:54.037318Z', 'results': '2026-11-23T05:44:53.704783Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (7)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- San Jose Earthquakes vs Houston Dynamo · btts · NO @ 0.4100 · fair 58.4% [47.5%–69.1%] · edge +15.7% · P(+) 96% · RESEARCH_ONLY · `KXMLSBTTS-26NOV24SJHOU-BTTS`
- San Jose Earthquakes vs Houston Dynamo · Total goals over 2.5 · NO @ 0.4300 · fair 61.7% [46.7%–75.2%] · edge +17.0% · P(+) 92% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV24SJHOU-3`
- San Jose Earthquakes vs Houston Dynamo · away team total over 1.5 · NO @ 0.6600 · fair 78.3% [68.2%–87.5%] · edge +10.7% · P(+) 91% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV24SJHOU-HOU2`
- San Jose Earthquakes vs Houston Dynamo · First-half total goals over 1.5 · NO @ 0.6500 · fair 74.4% [63.8%–84.2%] · edge +7.8% · P(+) 84% · RESEARCH_ONLY · `KXMLS1HTOTAL-26NOV24SJHOU-2`
- San Jose Earthquakes vs Houston Dynamo · away team total over 2.5 · NO @ 0.8900 · fair 93.7% [89.1%–97.6%] · edge +4.0% · P(+) 88% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV24SJHOU-HOU3`
- San Jose Earthquakes vs Houston Dynamo · Exact score 1-0 (home-away) · YES @ 0.1000 · fair 14.6% [9.9%–19.2%] · edge +3.9% · P(+) 86% · RESEARCH_ONLY · `KXMLSSCORE-26NOV24SJHOU-SJ1HOU0`
- San Jose Earthquakes vs Houston Dynamo · Total goals over 0.5 · NO @ 0.0700 · fair 11.7% [5.9%–18.2%] · edge +4.2% · P(+) 82% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV24SJHOU-1`

## Expressions removed by the reducer (6)
- `KXMLSTOTAL-26NOV24SJHOU-2` no: dominated by KXMLSBTTS-26NOV24SJHOU-BTTS/no (corr +0.63)
- `KXMLSTEAMTOTAL-26NOV24SJHOU-HOU1` no: dominated by KXMLSBTTS-26NOV24SJHOU-BTTS/no (corr +0.73)
- `KXMLSTOTAL-26NOV24SJHOU-4` no: dominated by KXMLSTOTAL-26NOV24SJHOU-3/no (corr +0.62)
- `KXMLSTOTAL-26NOV24SJHOU-5` no: dominated by KXMLSTOTAL-26NOV24SJHOU-3/no (corr +0.38)
- `KXMLSTOTAL-26NOV24SJHOU-6` no: dominated by KXMLSTOTAL-26NOV24SJHOU-3/no (corr +0.23)
- `KXMLSSCORE-26NOV24SJHOU-SJ0HOU0` yes: redundant with KXMLSTOTAL-26NOV24SJHOU-1/no (corr +1.00); best expression kept

## Events
- San Jose Earthquakes vs Houston Dynamo (Major League Soccer) 2026-11-25T03:00:00Z · markets 79/80 evaluated · lineups unknown · xG 1.35-0.86 · 1X2 48%/28%/24%
- Monza vs Fiorentina (Serie A) 2026-11-23T17:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.54-1.44 · 1X2 40%/23%/37%
