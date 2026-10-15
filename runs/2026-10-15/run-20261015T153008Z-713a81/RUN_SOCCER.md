# RUN SOCCER — 2026-10-15
Run `run-20261015T153008Z-713a81` generated 2026-10-15T15:30:11.882008Z · filters: {'leagues': [], 'games': ['fx:eng.premier_league:2026-27:eng.brentford:eng.liverpool', 'fx:eng.premier_league:2026-27:eng.everton:eng.chelsea', 'fx:eng.premier_league:2026-27:eng.fulham:eng.hull', 'fx:eng.premier_league:2026-27:eng.man_city:eng.ipswich', 'fx:esp.la_liga:2026-27:esp.deportivo:esp.levante', 'fx:esp.la_liga:2026-27:esp.espanyol:esp.atletico_madrid', 'fx:esp.la_liga:2026-27:esp.villarreal:esp.elche', 'fx:fra.ligue_1:2026-27:fra.le_mans:fra.toulouse', 'fx:fra.ligue_1:2026-27:fra.strasbourg:fra.psg', 'fx:ger.bundesliga:2026-27:ger.elversberg:ger.augsburg', 'fx:ger.bundesliga:2026-27:ger.frankfurt:ger.koln', 'fx:ger.bundesliga:2026-27:ger.hamburg:ger.stuttgart', 'fx:ger.bundesliga:2026-27:ger.schalke:ger.mainz', 'fx:ger.bundesliga:2026-27:ger.union_berlin:ger.dortmund', 'fx:ger.bundesliga:2026-27:ger.werder_bremen:ger.paderborn', 'fx:ita.serie_a:2026-27:ita.frosinone:ita.sassuolo', 'fx:ita.serie_a:2026-27:ita.venezia:ita.napoli'], 'window_hours': 49, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5399** (discovery complete: True)
- contracts evaluated: 51 · excluded mechanically: 2279 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=51, unknown_family=3, unsupported_family=3066, unmapped_event=1015, unmapped_team=57, no_fixture=183, filtered_by_operator=1024
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BRASILEIROC, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAPSL, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-15T15:30:08.279525Z; market_observed_at: 2026-10-15T15:27:16.234840Z; fixtures_observed_at: 2026-10-15T15:30:04.660993Z; results_observed_at: 2026-10-15T15:29:56.857245Z; model_fitted_at: 2026-10-15T15:30:04.974310Z; temporal_guard: {'decision_time': '2026-10-15T15:30:08.279525Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-15T15:30:04.660993Z', 'market_snapshots': '2026-10-15T15:29:55.940941Z', 'reference_odds': '2026-10-15T15:30:06.755128Z', 'results': '2026-10-15T15:30:06.456811Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (7)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Strasbourg vs Paris Saint-Germain · Result: away · NO @ 0.3000 · fair 60.2% [41.4%–78.3%] · edge +28.8% · P(+) 98% · RESEARCH_ONLY · `KXLIGUE1GAME-26OCT17RCSPSG-PSG`
- Everton vs Chelsea · Result: away · NO @ 0.5500 · fair 73.2% [58.2%–86.7%] · edge +16.4% · P(+) 91% · RESEARCH_ONLY · `KXEPLGAME-26OCT17EVECFC-CFC`
- Everton vs Chelsea · Result: home · YES @ 0.3000 · fair 49.4% [31.4%–67.6%] · edge +17.9% · P(+) 90% · RESEARCH_ONLY · `KXEPLGAME-26OCT17EVECFC-EVE`
- Espanyol vs Atlético Madrid · Result: away · NO @ 0.4400 · fair 60.8% [43.7%–75.8%] · edge +15.1% · P(+) 88% · RESEARCH_ONLY · `KXLALIGAGAME-26OCT17ESPATM-ATM`
- Fulham vs Hull City · Result: home · NO @ 0.4400 · fair 62.7% [42.4%–81.4%] · edge +17.0% · P(+) 86% · RESEARCH_ONLY · `KXEPLGAME-26OCT17FULHUL-FUL`
- Espanyol vs Atlético Madrid · Result: home · YES @ 0.2000 · fair 35.4% [20.3%–51.9%] · edge +14.3% · P(+) 88% · RESEARCH_ONLY · `KXLALIGAGAME-26OCT17ESPATM-ESP`
- Strasbourg vs Paris Saint-Germain · Result: draw · YES @ 0.1700 · fair 22.7% [18.1%–27.5%] · edge +4.7% · P(+) 91% · RESEARCH_ONLY · `KXLIGUE1GAME-26OCT17RCSPSG-TIE`

## Expressions removed by the reducer (1)
- `KXLIGUE1GAME-26OCT17RCSPSG-RCS` yes: dominated by KXLIGUE1GAME-26OCT17RCSPSG-PSG/no (corr +0.63)

## Events
- Manchester City vs Ipswich Town (Premier League) 2026-10-17T14:00:00Z · markets 3/3 evaluated · lineups unknown · xG 2.86-0.82 · 1X2 76%/14%/10%
- Fulham vs Hull City (Premier League) 2026-10-17T14:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.17-1.10 · 1X2 37%/29%/34%
- Brentford vs Liverpool (Premier League) 2026-10-17T14:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.61-1.13 · 1X2 48%/25%/28%
- Everton vs Chelsea (Premier League) 2026-10-17T11:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.69-1.15 · 1X2 49%/24%/27%
- Union Berlin vs Borussia Dortmund (Bundesliga) 2026-10-17T13:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.09-1.83 · 1X2 23%/23%/54%
- Hamburger SV vs VfB Stuttgart (Bundesliga) 2026-10-17T13:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.34-1.56 · 1X2 33%/24%/43%
- Werder Bremen vs SC Paderborn 07 (Bundesliga) 2026-10-17T13:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.35-0.76 · 1X2 49%/28%/22%
- Schalke 04 vs Mainz 05 (Bundesliga) 2026-10-17T13:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.46-1.14 · 1X2 44%/25%/31%
- SV Elversberg vs FC Augsburg (Bundesliga) 2026-10-17T13:30:00Z · markets 3/3 evaluated · lineups unknown · xG 2.06-1.31 · 1X2 53%/21%/26%
- Eintracht Frankfurt vs 1. FC Köln (Bundesliga) 2026-10-16T18:30:00Z · markets 3/3 evaluated · lineups unknown · xG 2.37-1.16 · 1X2 63%/19%/19%
- Strasbourg vs Paris Saint-Germain (Ligue 1) 2026-10-17T15:15:00Z · markets 3/3 evaluated · lineups unknown · xG 1.60-1.66 · 1X2 37%/23%/40%
- Le Mans vs Toulouse (Ligue 1) 2026-10-16T18:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.73-1.33 · 1X2 46%/23%/31%
- Espanyol vs Atlético Madrid (La Liga) 2026-10-17T12:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.31-1.39 · 1X2 35%/25%/39%
- Villarreal vs Elche (La Liga) 2026-10-17T14:15:00Z · markets 3/3 evaluated · lineups unknown · xG 2.48-1.17 · 1X2 65%/18%/17%
- Deportivo La Coruña vs Levante (La Liga) 2026-10-16T19:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.74-1.12 · 1X2 51%/24%/26%
- Venezia vs Napoli (Serie A) 2026-10-17T13:00:00Z · markets 3/3 evaluated · lineups unknown · xG 0.86-1.97 · 1X2 17%/21%/61%
- Frosinone vs Sassuolo (Serie A) 2026-10-16T18:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.65-1.00 · 1X2 52%/24%/24%
