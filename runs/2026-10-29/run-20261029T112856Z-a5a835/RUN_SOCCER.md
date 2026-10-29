# RUN SOCCER — 2026-10-29
Run `run-20261029T112856Z-a5a835` generated 2026-10-29T11:28:57.877750Z · filters: {'leagues': [], 'games': ['fx:arg.primera:2026:arg.estudiantes_rio_cuarto:arg.gimnasia_la_plata', 'fx:arg.primera:2026:arg.huracan:arg.tigre', 'fx:arg.primera:2026:arg.racing:arg.aldosivi', 'fx:arg.primera:2026:arg.sarmiento:arg.rosario_central', 'fx:esp.la_liga:2026-27:esp.villarreal:esp.espanyol', 'fx:fra.ligue_1:2026-27:fra.le_havre:fra.psg', 'fx:fra.ligue_1:2026-27:fra.lille:fra.lens', 'fx:fra.ligue_1:2026-27:fra.nice:fra.rennes', 'fx:ger.bundesliga:2026-27:ger.elversberg:ger.mainz', 'fx:ita.serie_a:2026-27:ita.fiorentina:ita.atalanta', 'fx:ita.serie_a:2026-27:ita.frosinone:ita.lecce'], 'window_hours': 38, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5054** (discovery complete: True)
- contracts evaluated: 15 · excluded mechanically: 2061 · unsupported/unknown: 2978
- **unaccounted contracts: 0**
- by disposition: priced=15, unknown_family=3, unsupported_family=2975, unmapped_event=850, unmapped_team=122, no_fixture=120, out_of_window=3, filtered_by_operator=966
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SAPSL, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-29T11:28:56.396551Z; market_observed_at: 2026-10-29T11:26:10.165412Z; fixtures_observed_at: 2026-10-29T11:28:53.673835Z; results_observed_at: 2026-10-29T11:28:51.292269Z; model_fitted_at: 2026-10-29T11:28:54.066391Z; temporal_guard: {'decision_time': '2026-10-29T11:28:56.396551Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-29T11:28:53.673835Z', 'market_snapshots': '2026-10-29T11:28:50.518910Z', 'reference_odds': '2026-10-29T11:28:55.324603Z', 'results': '2026-10-29T11:28:55.159209Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (4)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Le Havre vs Paris Saint-Germain · Result: away · NO @ 0.2000 · fair 54.4% [36.2%–71.5%] · edge +33.3% · P(+) 99% · RESEARCH_ONLY · `KXLIGUE1GAME-26OCT30HACPSG-PSG`
- Le Havre vs Paris Saint-Germain · Result: home · YES @ 0.0800 · fair 28.7% [14.7%–44.4%] · edge +20.2% · P(+) 98% · RESEARCH_ONLY · `KXLIGUE1GAME-26OCT30HACPSG-HAC`
- Le Havre vs Paris Saint-Germain · Result: draw · YES @ 0.1300 · fair 25.7% [19.6%–32.0%] · edge +11.9% · P(+) 98% · RESEARCH_ONLY · `KXLIGUE1GAME-26OCT30HACPSG-TIE`
- SV Elversberg vs Mainz 05 · Result: away · NO @ 0.5600 · fair 73.2% [52.2%–91.0%] · edge +15.5% · P(+) 84% · RESEARCH_ONLY · `KXBUNDESLIGAGAME-26OCT30SVEM05-M05`

## Expressions removed by the reducer (1)
- `KXBUNDESLIGAGAME-26OCT30SVEM05-SVE` yes: redundant with KXBUNDESLIGAGAME-26OCT30SVEM05-M05/no (corr +0.63); best expression kept

## Events
- Frosinone vs Lecce (Serie A) 2026-10-29T17:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.65-0.75 · 1X2 57%/25%/19%
- Fiorentina vs Atalanta (Serie A) 2026-10-29T19:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.18-1.24 · 1X2 35%/27%/38%
- SV Elversberg vs Mainz 05 (Bundesliga) 2026-10-30T19:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.98-1.29 · 1X2 52%/21%/27%
- Le Havre vs Paris Saint-Germain (Ligue 1) 2026-10-30T18:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.10-1.49 · 1X2 29%/26%/46%
- Lille vs Lens (Ligue 1) 2026-10-30T20:05:00Z · markets 3/3 evaluated · lineups unknown · xG 1.55-1.08 · 1X2 48%/25%/27%
