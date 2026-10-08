# RUN SOCCER — 2026-10-08
Run `run-20261008T185901Z-46aaff` generated 2026-10-08T18:59:02.986138Z · filters: {'leagues': [], 'games': ['fx:arg.primera:2026:arg.barracas_central:arg.huracan', 'fx:fra.ligue_1:2026-27:fra.brest:fra.angers', 'fx:fra.ligue_1:2026-27:fra.lorient:fra.paris_fc', 'fx:fra.ligue_1:2026-27:fra.monaco:fra.toulouse', 'fx:fra.ligue_1:2026-27:fra.psg:fra.le_mans', 'fx:ita.serie_a:2026-27:ita.napoli:ita.frosinone'], 'window_hours': 49, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5466** (discovery complete: True)
- contracts evaluated: 15 · excluded mechanically: 2382 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=15, unknown_family=3, unsupported_family=3066, unmapped_event=986, unmapped_team=3, no_fixture=132, filtered_by_operator=1261
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, BELGIANPL, BRASILEIRO, BRASILEIROB, BRASILEIROC, BUNDESLIGA, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FIFAW, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-08T18:59:01.929081Z; market_observed_at: 2026-10-08T18:56:31.094220Z; fixtures_observed_at: 2026-10-08T16:58:26.970839Z; results_observed_at: 2026-10-08T16:58:19.515966Z; model_fitted_at: 2026-10-08T18:59:00.536638Z; temporal_guard: {'decision_time': '2026-10-08T18:59:01.929081Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-08T16:58:26.970839Z', 'market_snapshots': '2026-10-08T18:58:58.058456Z', 'reference_odds': '2026-10-08T16:58:28.609535Z', 'results': '2026-10-08T18:59:01.780396Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (4)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Napoli vs Frosinone · Result: home · NO @ 0.3400 · fair 56.0% [34.4%–77.3%] · edge +20.4% · P(+) 88% · RESEARCH_ONLY · `KXSERIEAGAME-26OCT10NAPFRO-NAP`
- Paris Saint-Germain vs Le Mans · Result: home · NO @ 0.1000 · fair 31.9% [11.4%–53.7%] · edge +21.3% · P(+) 92% · RESEARCH_ONLY · `KXLIGUE1GAME-26OCT10PSGMAN-PSG`
- Napoli vs Frosinone · Result: away · YES @ 0.1500 · fair 28.9% [12.2%–48.5%] · edge +13.0% · P(+) 82% · RESEARCH_ONLY · `KXSERIEAGAME-26OCT10NAPFRO-FRO`
- Napoli vs Frosinone · Result: draw · YES @ 0.2000 · fair 27.1% [19.1%–35.6%] · edge +6.0% · P(+) 83% · RESEARCH_ONLY · `KXSERIEAGAME-26OCT10NAPFRO-TIE`

## Expressions removed by the reducer (2)
- `KXLIGUE1GAME-26OCT10PSGMAN-TIE` yes: redundant with KXLIGUE1GAME-26OCT10PSGMAN-PSG/no (corr +0.67); best expression kept
- `KXLIGUE1GAME-26OCT10PSGMAN-MAN` yes: dominated by KXLIGUE1GAME-26OCT10PSGMAN-PSG/no (corr +0.60)

## Events
- Napoli vs Frosinone (Serie A) 2026-10-10T18:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.33-0.98 · 1X2 44%/27%/29%
- Paris Saint-Germain vs Le Mans (Ligue 1) 2026-10-10T18:45:00Z · markets 3/3 evaluated · lineups unknown · xG 2.49-0.94 · 1X2 68%/17%/15%
- AS Monaco vs Toulouse (Ligue 1) 2026-10-10T18:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.99-0.97 · 1X2 60%/22%/19%
- Lorient vs Paris FC (Ligue 1) 2026-10-10T18:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.26-1.16 · 1X2 39%/27%/34%
- Brest vs Angers (Ligue 1) 2026-10-10T18:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.53-0.99 · 1X2 49%/26%/25%
