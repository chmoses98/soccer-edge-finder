# RUN SOCCER — 2026-11-05
Run `run-20261105T143136Z-54b4d7` generated 2026-11-05T14:31:42.147465Z · filters: {'leagues': [], 'games': ['fx:arg.primera:2026:arg.banfield:arg.atletico_tucuman', 'fx:arg.primera:2026:arg.barracas_central:arg.racing', 'fx:arg.primera:2026:arg.tigre:arg.sarmiento', 'fx:eng.premier_league:2026-27:eng.everton:eng.coventry', 'fx:eng.premier_league:2026-27:eng.leeds:eng.tottenham', 'fx:esp.la_liga:2026-27:esp.malaga:esp.racing_santander', 'fx:esp.la_liga:2026-27:esp.sevilla:esp.alaves', 'fx:fra.ligue_1:2026-27:fra.toulouse:fra.strasbourg', 'fx:ger.bundesliga:2026-27:ger.dortmund:ger.elversberg', 'fx:ger.bundesliga:2026-27:ger.hamburg:ger.gladbach', 'fx:ger.bundesliga:2026-27:ger.leipzig:ger.augsburg', 'fx:ger.bundesliga:2026-27:ger.mainz:ger.bayern', 'fx:ger.bundesliga:2026-27:ger.paderborn:ger.frankfurt', 'fx:ita.serie_a:2026-27:ita.cagliari:ita.frosinone', 'fx:ita.serie_a:2026-27:ita.torino:ita.lecce', 'fx:ita.serie_a:2026-27:ita.venezia:ita.udinese'], 'window_hours': 49, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4581** (discovery complete: True)
- contracts evaluated: 33 · excluded mechanically: 1575 · unsupported/unknown: 2973
- **unaccounted contracts: 0**
- by disposition: priced=33, unknown_family=3, unsupported_family=2970, unmapped_event=619, unmapped_team=110, no_fixture=174, out_of_window=3, filtered_by_operator=669
- competitions discovered: APFDDH, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EKSTRAKLASA, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, INTLFRIENDLY, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-05T14:31:36.867384Z; market_observed_at: 2026-11-05T14:28:43.419552Z; fixtures_observed_at: 2026-11-05T14:31:33.587189Z; results_observed_at: 2026-11-05T14:31:26.447581Z; model_fitted_at: 2026-11-05T14:31:34.078251Z; temporal_guard: {'decision_time': '2026-11-05T14:31:36.867384Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-05T14:31:33.587189Z', 'market_snapshots': '2026-11-05T14:31:25.346981Z', 'reference_odds': '2026-11-05T14:31:35.691905Z', 'results': '2026-11-05T14:31:35.491555Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (6)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Leeds United vs Tottenham Hotspur · Result: home · YES @ 0.3600 · fair 62.0% [44.4%–79.0%] · edge +24.3% · P(+) 96% · RESEARCH_ONLY · `KXEPLGAME-26NOV07LEETOT-LEE`
- Leeds United vs Tottenham Hotspur · Result: away · NO @ 0.6500 · fair 83.7% [72.9%–93.3%] · edge +17.1% · P(+) 96% · RESEARCH_ONLY · `KXEPLGAME-26NOV07LEETOT-TOT`
- Mainz 05 vs Bayern Munich · Result: away · NO @ 0.2600 · fair 47.0% [26.5%–67.1%] · edge +19.6% · P(+) 89% · RESEARCH_ONLY · `KXBUNDESLIGAGAME-26NOV07M05BMU-BMU`
- Venezia vs Udinese · Result: away · YES @ 0.3100 · fair 51.7% [29.8%–74.2%] · edge +19.2% · P(+) 86% · RESEARCH_ONLY · `KXSERIEAGAME-26NOV06VENUDI-UDI`
- Mainz 05 vs Bayern Munich · Result: draw · YES @ 0.1400 · fair 19.7% [14.3%–25.1%] · edge +4.8% · P(+) 88% · RESEARCH_ONLY · `KXBUNDESLIGAGAME-26NOV07M05BMU-TIE`
- SC Paderborn 07 vs Eintracht Frankfurt · Result: away · NO @ 0.5700 · fair 71.4% [51.3%–87.9%] · edge +12.7% · P(+) 82% · RESEARCH_ONLY · `KXBUNDESLIGAGAME-26NOV07PADSGE-SGE`

## Expressions removed by the reducer (2)
- `KXBUNDESLIGAGAME-26NOV07M05BMU-M05` yes: dominated by KXBUNDESLIGAGAME-26NOV07M05BMU-BMU/no (corr +0.65)
- `KXSERIEAGAME-26NOV06VENUDI-VEN` no: dominated by KXSERIEAGAME-26NOV06VENUDI-UDI/yes (corr +0.61)

## Events
- Borussia Dortmund vs SV Elversberg (Bundesliga) 2026-11-07T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 2.36-0.85 · 1X2 67%/18%/14%
- RB Leipzig vs FC Augsburg (Bundesliga) 2026-11-07T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 2.08-1.10 · 1X2 58%/21%/21%
- Mainz 05 vs Bayern Munich (Bundesliga) 2026-11-07T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.50-2.20 · 1X2 27%/20%/53%
- SC Paderborn 07 vs Eintracht Frankfurt (Bundesliga) 2026-11-07T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.42-1.03 · 1X2 45%/26%/29%
- Hamburger SV vs Borussia Mönchengladbach (Bundesliga) 2026-11-06T19:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.76-1.23 · 1X2 49%/23%/28%
- Cagliari vs Frosinone (Serie A) 2026-11-07T14:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.07-1.02 · 1X2 36%/29%/34%
- Torino vs Lecce (Serie A) 2026-11-07T14:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.49-0.99 · 1X2 48%/26%/26%
- Venezia vs Udinese (Serie A) 2026-11-06T19:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.16-1.82 · 1X2 26%/22%/52%
- Leeds United vs Tottenham Hotspur (Premier League) 2026-11-07T15:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.93-0.81 · 1X2 62%/22%/16%
- Everton vs Coventry City (Premier League) 2026-11-07T15:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.67-0.63 · 1X2 60%/25%/15%
- Toulouse vs Strasbourg (Ligue 1) 2026-11-06T19:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.74-1.47 · 1X2 44%/23%/34%
