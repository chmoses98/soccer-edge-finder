# RUN SOCCER — 2026-11-22
Run `run-20261122T121724Z-cb14c2` generated 2026-11-22T12:17:29.778833Z · filters: {'leagues': [], 'games': ['fx:arg.primera:2026:arg.gimnasia_la_plata:arg.newells', 'fx:arg.primera:2026:arg.instituto:arg.huracan', 'fx:arg.primera:2026:arg.river_plate:arg.lanus', 'fx:arg.primera:2026:arg.rosario_central:arg.gimnasia_mendoza', 'fx:eng.premier_league:2026-27:eng.brentford:eng.everton', 'fx:eng.premier_league:2026-27:eng.hull:eng.brighton', 'fx:eng.premier_league:2026-27:eng.liverpool:eng.man_united', 'fx:esp.la_liga:2026-27:esp.barcelona:esp.villarreal', 'fx:esp.la_liga:2026-27:esp.getafe:esp.atletico_madrid', 'fx:esp.la_liga:2026-27:esp.levante:esp.elche', 'fx:esp.la_liga:2026-27:esp.osasuna:esp.malaga', 'fx:esp.la_liga:2026-27:esp.racing_santander:esp.real_sociedad', 'fx:fra.ligue_1:2026-27:fra.lorient:fra.rennes', 'fx:fra.ligue_1:2026-27:fra.marseille:fra.le_mans', 'fx:fra.ligue_1:2026-27:fra.paris_fc:fra.angers', 'fx:ger.bundesliga:2026-27:ger.augsburg:ger.mainz', 'fx:ger.bundesliga:2026-27:ger.werder_bremen:ger.hamburg', 'fx:ita.serie_a:2026-27:ita.atalanta:ita.inter', 'fx:ita.serie_a:2026-27:ita.bologna:ita.udinese', 'fx:ita.serie_a:2026-27:ita.milan:ita.frosinone', 'fx:ita.serie_a:2026-27:ita.monza:ita.fiorentina', 'fx:ita.serie_a:2026-27:ita.sassuolo:ita.genoa', 'fx:usa.mls:2026:usa.vancouver_whitecaps:usa.real_salt_lake'], 'window_hours': 33, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4953** (discovery complete: True)
- contracts evaluated: 27 · excluded mechanically: 1932 · unsupported/unknown: 2994
- **unaccounted contracts: 0**
- by disposition: priced=27, started=24, ambiguous_ownership=27, unknown_family=4, unsupported_family=2990, unmapped_event=905, unmapped_team=48, no_fixture=51, filtered_by_operator=877
- competitions discovered: AFCCL2, ALEAGUEW, APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGAW, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, ENGWLEAGUECUP, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SAPSL, SCOCHAMP, SERIEA, SOCCER, SUPERLIG, SVK1L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-22T12:17:24.932364Z; market_observed_at: 2026-11-22T12:13:36.214260Z; fixtures_observed_at: 2026-11-22T12:17:21.678759Z; results_observed_at: 2026-11-22T12:17:15.052325Z; model_fitted_at: 2026-11-22T12:17:22.048416Z; temporal_guard: {'decision_time': '2026-11-22T12:17:24.932364Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-22T12:17:21.678759Z', 'market_snapshots': '2026-11-22T12:17:13.955534Z', 'reference_odds': '2026-11-22T12:17:23.674025Z', 'results': '2026-11-22T12:17:23.468869Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (3)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Atalanta vs Inter Milan · Result: away · NO @ 0.3700 · fair 55.1% [35.6%–73.6%] · edge +16.4% · P(+) 86% · RESEARCH_ONLY · `KXSERIEAGAME-26NOV22ATAINT-INT`
- FC Augsburg vs Mainz 05 · Result: away · NO @ 0.5900 · fair 74.0% [55.3%–89.4%] · edge +13.3% · P(+) 84% · RESEARCH_ONLY · `KXBUNDESLIGAGAME-26NOV22FCAM05-M05`
- Bologna vs Udinese · Result: away · YES @ 0.1900 · fair 30.9% [15.5%–48.2%] · edge +10.8% · P(+) 81% · RESEARCH_ONLY · `KXSERIEAGAME-26NOV22BFCUDI-UDI`

## Expressions removed by the reducer (2)
- `KXSERIEAGAME-26NOV22ATAINT-ATA` yes: dominated by KXSERIEAGAME-26NOV22ATAINT-INT/no (corr +0.62)
- `KXBUNDESLIGAGAME-26NOV22FCAM05-FCA` yes: redundant with KXBUNDESLIGAGAME-26NOV22FCAM05-M05/no (corr +0.62); best expression kept

## Events
- Monza vs Fiorentina (Serie A) 2026-11-23T17:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.54-1.44 · 1X2 40%/24%/36%
- Bologna vs Udinese (Serie A) 2026-11-22T17:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.36-1.09 · 1X2 43%/26%/31%
- AC Milan vs Frosinone (Serie A) 2026-11-22T14:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.40-1.00 · 1X2 45%/26%/28%
- Atalanta vs Inter Milan (Serie A) 2026-11-22T19:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.34-1.66 · 1X2 32%/23%/45%
- Paris FC vs Angers (Ligue 1) 2026-11-22T14:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.83-0.78 · 1X2 60%/23%/17%
- Lorient vs Rennes (Ligue 1) 2026-11-22T16:15:00Z · markets 3/3 evaluated · lineups unknown · xG 1.58-1.28 · 1X2 44%/24%/32%
- Marseille vs Le Mans (Ligue 1) 2026-11-22T19:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.97-1.15 · 1X2 55%/21%/24%
- FC Augsburg vs Mainz 05 (Bundesliga) 2026-11-22T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.92-1.24 · 1X2 52%/22%/26%
- Werder Bremen vs Hamburger SV (Bundesliga) 2026-11-22T16:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.95-0.87 · 1X2 61%/22%/18%
