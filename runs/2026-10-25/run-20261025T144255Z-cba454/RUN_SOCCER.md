# RUN SOCCER — 2026-10-25
Run `run-20261025T144255Z-cba454` generated 2026-10-25T14:42:59.789683Z · filters: {'leagues': [], 'games': ['fx:arg.primera:2026:arg.barracas_central:arg.estudiantes_rio_cuarto', 'fx:eng.premier_league:2026-27:eng.sunderland:eng.leeds', 'fx:esp.la_liga:2026-27:esp.barcelona:esp.real_madrid', 'fx:esp.la_liga:2026-27:esp.celta_vigo:esp.real_betis', 'fx:esp.la_liga:2026-27:esp.real_sociedad:esp.levante', 'fx:esp.la_liga:2026-27:esp.sevilla:esp.osasuna', 'fx:fra.ligue_1:2026-27:fra.angers:fra.lorient', 'fx:fra.ligue_1:2026-27:fra.auxerre:fra.le_mans', 'fx:fra.ligue_1:2026-27:fra.marseille:fra.le_havre', 'fx:fra.ligue_1:2026-27:fra.psg:fra.lyon', 'fx:fra.ligue_1:2026-27:fra.rennes:fra.strasbourg', 'fx:fra.ligue_1:2026-27:fra.toulouse:fra.troyes', 'fx:ger.bundesliga:2026-27:ger.freiburg:ger.bayern', 'fx:ita.serie_a:2026-27:ita.lecce:ita.juventus', 'fx:ita.serie_a:2026-27:ita.udinese:ita.milan'], 'window_hours': 31, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5801** (discovery complete: True)
- contracts evaluated: 27 · excluded mechanically: 2705 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=27, started=15, unknown_family=3, unsupported_family=3066, unmapped_event=931, unmapped_team=338, no_fixture=119, filtered_by_operator=1302
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SERIEA, SOCCER, SUPERLIG, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-25T14:42:55.953139Z; market_observed_at: 2026-10-25T14:40:00.072920Z; fixtures_observed_at: 2026-10-25T12:37:42.216640Z; results_observed_at: 2026-10-25T12:37:35.890315Z; model_fitted_at: 2026-10-25T14:42:54.125026Z; temporal_guard: {'decision_time': '2026-10-25T14:42:55.953139Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-25T12:37:42.216640Z', 'market_snapshots': '2026-10-25T14:42:50.745105Z', 'reference_odds': '2026-10-25T12:37:42.519621Z', 'results': '2026-10-25T14:42:55.705309Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (6)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Paris Saint-Germain vs Lyon · Result: home · NO @ 0.3000 · fair 48.4% [28.7%–67.9%] · edge +16.9% · P(+) 87% · RESEARCH_ONLY · `KXLIGUE1GAME-26OCT25PSGOL-PSG`
- SC Freiburg vs Bayern Munich · Result: away · NO @ 0.3600 · fair 54.2% [34.7%–73.0%] · edge +16.6% · P(+) 86% · RESEARCH_ONLY · `KXBUNDESLIGAGAME-26OCT25SCFBMU-BMU`
- Udinese vs AC Milan · Result: home · YES @ 0.2100 · fair 34.9% [19.7%–51.4%] · edge +12.8% · P(+) 84% · RESEARCH_ONLY · `KXSERIEAGAME-26OCT25UDIACM-UDI`
- Paris Saint-Germain vs Lyon · Result: draw · YES @ 0.1700 · fair 23.5% [16.7%–29.9%] · edge +5.5% · P(+) 86% · RESEARCH_ONLY · `KXLIGUE1GAME-26OCT25PSGOL-TIE`
- Paris Saint-Germain vs Lyon · Result: away · YES @ 0.1300 · fair 24.9% [11.4%–40.6%] · edge +11.1% · P(+) 84% · RESEARCH_ONLY · `KXLIGUE1GAME-26OCT25PSGOL-OL`
- Udinese vs AC Milan · Result: away · NO @ 0.4800 · fair 60.9% [43.3%–76.4%] · edge +11.1% · P(+) 81% · RESEARCH_ONLY · `KXSERIEAGAME-26OCT25UDIACM-ACM`

## Expressions removed by the reducer (1)
- `KXBUNDESLIGAGAME-26OCT25SCFBMU-SCF` yes: redundant with KXBUNDESLIGAGAME-26OCT25SCFBMU-BMU/no (corr +0.65); best expression kept

## Events
- Angers vs Lorient (Ligue 1) 2026-10-25T16:15:00Z · markets 3/3 evaluated · lineups unknown · xG 1.24-1.09 · 1X2 39%/28%/33%
- AJ Auxerre vs Le Mans (Ligue 1) 2026-10-25T16:15:00Z · markets 3/3 evaluated · lineups unknown · xG 1.78-1.26 · 1X2 49%/23%/28%
- Marseille vs Le Havre (Ligue 1) 2026-10-25T16:15:00Z · markets 3/3 evaluated · lineups unknown · xG 1.70-0.93 · 1X2 54%/24%/21%
- Rennes vs Strasbourg (Ligue 1) 2026-10-25T16:15:00Z · markets 3/3 evaluated · lineups unknown · xG 2.01-1.51 · 1X2 49%/21%/30%
- Paris Saint-Germain vs Lyon (Ligue 1) 2026-10-25T19:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.74-1.10 · 1X2 51%/24%/25%
- Lecce vs Juventus (Serie A) 2026-10-25T17:00:00Z · markets 3/3 evaluated · lineups unknown · xG 0.89-1.41 · 1X2 25%/27%/49%
- Udinese vs AC Milan (Serie A) 2026-10-25T19:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.23-1.31 · 1X2 35%/26%/39%
- SC Freiburg vs Bayern Munich (Bundesliga) 2026-10-25T16:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.61-1.94 · 1X2 33%/21%/46%
- Sunderland vs Leeds United (Premier League) 2026-10-25T16:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.28-1.24 · 1X2 38%/27%/36%
