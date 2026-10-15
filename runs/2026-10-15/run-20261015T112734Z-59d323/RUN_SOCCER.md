# RUN SOCCER — 2026-10-15
Run `run-20261015T112734Z-59d323` generated 2026-10-15T11:27:39.954437Z · filters: {'leagues': [], 'games': ['fx:arg.primera:2026:arg.boca_juniors:arg.talleres', 'fx:arg.primera:2026:arg.defensa_y_justicia:arg.instituto', 'fx:esp.la_liga:2026-27:esp.deportivo:esp.levante', 'fx:fra.ligue_1:2026-27:fra.le_mans:fra.toulouse', 'fx:ger.bundesliga:2026-27:ger.frankfurt:ger.koln', 'fx:ita.serie_a:2026-27:ita.frosinone:ita.sassuolo', 'fx:mex.liga_mx:2026:mex.atlante:mex.pumas', 'fx:mex.liga_mx:2026:mex.tijuana:mex.puebla'], 'window_hours': 41, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5481** (discovery complete: True)
- contracts evaluated: 121 · excluded mechanically: 2291 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=121, unknown_family=3, unsupported_family=3066, unmapped_event=1097, unmapped_team=57, no_fixture=183, filtered_by_operator=954
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BRASILEIROC, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, EPL, EREDIVISIE, ESOCCER, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SAPSL, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-15T11:27:34.515170Z; market_observed_at: 2026-10-15T11:24:45.394197Z; fixtures_observed_at: 2026-10-15T11:27:32.316319Z; results_observed_at: 2026-10-15T11:27:26.537270Z; model_fitted_at: 2026-10-15T11:27:32.582824Z; temporal_guard: {'decision_time': '2026-10-15T11:27:34.515170Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-15T11:27:32.316319Z', 'market_snapshots': '2026-10-15T11:27:25.840559Z', 'reference_odds': '2026-10-15T11:27:33.624214Z', 'results': '2026-10-15T11:27:33.313139Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (3)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Tijuana vs Puebla · btts · NO @ 0.4500 · fair 59.6% [48.1%–71.0%] · edge +12.9% · P(+) 93% · RESEARCH_ONLY · `KXLIGAMXBTTS-26OCT16TIJPUE-BTTS`
- Tijuana vs Puebla · Total goals over 3.5 · NO @ 0.6900 · fair 79.6% [66.2%–91.0%] · edge +9.1% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26OCT16TIJPUE-4`
- Tijuana vs Puebla · Total goals over 1.5 · NO @ 0.2300 · fair 34.6% [20.2%–49.3%] · edge +10.3% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26OCT16TIJPUE-2`

## Expressions removed by the reducer (2)
- `KXLIGAMXTOTAL-26OCT16TIJPUE-3` no: redundant with KXLIGAMXTOTAL-26OCT16TIJPUE-4/no (corr +0.62); best expression kept
- `KXLIGAMXTOTAL-26OCT16TIJPUE-5` no: dominated by KXLIGAMXTOTAL-26OCT16TIJPUE-4/no (corr +0.63)

## Events
- Deportivo La Coruña vs Levante (La Liga) 2026-10-16T19:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.74-1.12 · 1X2 51%/24%/26%
- Tijuana vs Puebla (Liga MX) 2026-10-17T03:00:00Z · markets 32/32 evaluated · lineups unknown · xG 1.51-0.77 · 1X2 53%/27%/20%
- Atlante vs Pumas UNAM (Liga MX) 2026-10-17T03:00:00Z · markets 77/77 evaluated · lineups unknown · xG 1.41-1.17 · 1X2 42%/27%/31%
- Eintracht Frankfurt vs 1. FC Köln (Bundesliga) 2026-10-16T18:30:00Z · markets 3/3 evaluated · lineups unknown · xG 2.37-1.16 · 1X2 63%/19%/19%
- Frosinone vs Sassuolo (Serie A) 2026-10-16T18:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.65-1.00 · 1X2 52%/24%/24%
- Le Mans vs Toulouse (Ligue 1) 2026-10-16T18:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.73-1.33 · 1X2 46%/23%/31%
