# RUN SOCCER — 2026-10-29
Run `run-20261029T004638Z-0b3494` generated 2026-10-29T00:46:42.826140Z · filters: {'leagues': [], 'games': ['fx:arg.primera:2026:arg.estudiantes_rio_cuarto:arg.gimnasia_la_plata', 'fx:arg.primera:2026:arg.huracan:arg.tigre', 'fx:arg.primera:2026:arg.racing:arg.aldosivi', 'fx:arg.primera:2026:arg.sarmiento:arg.rosario_central', 'fx:bra.serie_a:2026:bra.corinthians:bra.mirassol', 'fx:esp.la_liga:2026-27:esp.villarreal:esp.espanyol', 'fx:fra.ligue_1:2026-27:fra.le_havre:fra.psg', 'fx:fra.ligue_1:2026-27:fra.lille:fra.lens', 'fx:fra.ligue_1:2026-27:fra.nice:fra.rennes', 'fx:ger.bundesliga:2026-27:ger.elversberg:ger.mainz', 'fx:ita.serie_a:2026-27:ita.fiorentina:ita.atalanta', 'fx:ita.serie_a:2026-27:ita.frosinone:ita.lecce'], 'window_hours': 49, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **6108** (discovery complete: True)
- contracts evaluated: 29 · excluded mechanically: 3101 · unsupported/unknown: 2978
- **unaccounted contracts: 0**
- by disposition: priced=29, unknown_family=3, unsupported_family=2975, unmapped_event=942, unmapped_team=287, no_fixture=126, out_of_window=3, filtered_by_operator=1743
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SAPSL, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-29T00:46:38.669092Z; market_observed_at: 2026-10-29T00:43:48.796488Z; fixtures_observed_at: 2026-10-29T00:06:30.855841Z; results_observed_at: 2026-10-29T00:06:23.680806Z; model_fitted_at: 2026-10-29T00:46:37.216623Z; temporal_guard: {'decision_time': '2026-10-29T00:46:38.669092Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-29T00:06:30.855841Z', 'market_snapshots': '2026-10-29T00:46:33.681799Z', 'reference_odds': '2026-10-29T00:06:31.123932Z', 'results': '2026-10-29T00:46:38.465456Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (7)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Le Havre vs Paris Saint-Germain · Result: away · NO @ 0.2100 · fair 54.4% [36.2%–71.5%] · edge +32.2% · P(+) 99% · RESEARCH_ONLY · `KXLIGUE1GAME-26OCT30HACPSG-PSG`
- Le Havre vs Paris Saint-Germain · Result: home · YES @ 0.0800 · fair 28.7% [14.7%–44.4%] · edge +20.2% · P(+) 98% · RESEARCH_ONLY · `KXLIGUE1GAME-26OCT30HACPSG-HAC`
- Le Havre vs Paris Saint-Germain · Result: draw · YES @ 0.1300 · fair 25.7% [19.6%–32.0%] · edge +11.9% · P(+) 98% · RESEARCH_ONLY · `KXLIGUE1GAME-26OCT30HACPSG-TIE`
- SV Elversberg vs Mainz 05 · Result: away · NO @ 0.5600 · fair 73.2% [52.2%–91.0%] · edge +15.5% · P(+) 84% · RESEARCH_ONLY · `KXBUNDESLIGAGAME-26OCT30SVEM05-M05`
- Corinthians vs Mirassol · Result: away · YES @ 0.1900 · fair 29.0% [17.1%–41.6%] · edge +8.9% · P(+) 83% · RESEARCH_ONLY · `KXBRASILEIROGAME-26OCT30CORMIR-MIR`
- Corinthians vs Mirassol · away wins by more than 1.5 · YES @ 0.0600 · fair 11.8% [5.4%–19.6%] · edge +5.4% · P(+) 83% · RESEARCH_ONLY · `KXBRASILEIROSPREAD-26OCT30CORMIR-MIR2`
- Corinthians vs Mirassol · Result: home · NO @ 0.4550 · fair 56.9% [41.8%–71.0%] · edge +9.6% · P(+) 80% · RESEARCH_ONLY · `KXBRASILEIROGAME-26OCT30CORMIR-COR`

## Expressions removed by the reducer (1)
- `KXBUNDESLIGAGAME-26OCT30SVEM05-SVE` yes: redundant with KXBUNDESLIGAGAME-26OCT30SVEM05-M05/no (corr +0.63); best expression kept

## Events
- Corinthians vs Mirassol (Brasileirão Série A) 2026-10-30T23:00:00Z · markets 14/14 evaluated · lineups unknown · xG 1.39-1.07 · 1X2 43%/28%/29%
- Frosinone vs Lecce (Serie A) 2026-10-29T17:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.65-0.75 · 1X2 57%/25%/19%
- Fiorentina vs Atalanta (Serie A) 2026-10-29T19:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.18-1.24 · 1X2 35%/27%/38%
- SV Elversberg vs Mainz 05 (Bundesliga) 2026-10-30T19:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.98-1.29 · 1X2 52%/21%/27%
- Le Havre vs Paris Saint-Germain (Ligue 1) 2026-10-30T18:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.10-1.49 · 1X2 29%/26%/46%
- Lille vs Lens (Ligue 1) 2026-10-30T20:05:00Z · markets 3/3 evaluated · lineups unknown · xG 1.55-1.08 · 1X2 48%/25%/27%
