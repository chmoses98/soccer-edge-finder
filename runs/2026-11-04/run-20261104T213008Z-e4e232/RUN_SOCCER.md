# RUN SOCCER — 2026-11-04
Run `run-20261104T213008Z-e4e232` generated 2026-11-04T21:30:12.447564Z · filters: {'leagues': [], 'games': ['fx:bra.serie_a:2026:bra.athletico_paranaense:bra.vasco', 'fx:bra.serie_a:2026:bra.flamengo:bra.gremio'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4294** (discovery complete: True)
- contracts evaluated: 28 · excluded mechanically: 1293 · unsupported/unknown: 2973
- **unaccounted contracts: 0**
- by disposition: priced=28, unknown_family=3, unsupported_family=2970, unmapped_event=504, unmapped_team=56, no_fixture=186, filtered_by_operator=547
- competitions discovered: APFDDH, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAPORTUGAL, LIGUE1, MLS, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-04T21:30:08.489881Z; market_observed_at: 2026-11-04T21:27:18.372142Z; fixtures_observed_at: 2026-11-04T18:28:30.464359Z; results_observed_at: 2026-11-04T18:28:23.466525Z; model_fitted_at: 2026-11-04T21:30:06.960923Z; temporal_guard: {'decision_time': '2026-11-04T21:30:08.489881Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-04T18:28:30.464359Z', 'market_snapshots': '2026-11-04T21:29:54.756717Z', 'reference_odds': '2026-11-04T18:28:32.539319Z', 'results': '2026-11-04T21:30:08.304327Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (5)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Flamengo vs Grêmio · home wins by more than 1.5 · NO @ 0.3200 · fair 48.1% [31.2%–64.7%] · edge +14.6% · P(+) 86% · RESEARCH_ONLY · `KXBRASILEIROSPREAD-26NOV04FLAGPA-FLA2`
- Athletico Paranaense vs Vasco da Gama · home wins by more than 1.5 · YES @ 0.2100 · fair 36.0% [20.3%–52.8%] · edge +13.8% · P(+) 86% · RESEARCH_ONLY · `KXBRASILEIROSPREAD-26NOV04CAPVDG-CAP2`
- Flamengo vs Grêmio · Total goals over 2.5 · NO @ 0.2600 · fair 41.2% [24.4%–58.8%] · edge +13.9% · P(+) 84% · RESEARCH_ONLY · `KXBRASILEIROTOTAL-26NOV04FLAGPA-3`
- Athletico Paranaense vs Vasco da Gama · Result: away · NO @ 0.7100 · fair 80.2% [69.1%–90.2%] · edge +7.7% · P(+) 83% · RESEARCH_ONLY · `KXBRASILEIROGAME-26NOV04CAPVDG-VDG`
- Flamengo vs Grêmio · Total goals over 1.5 · NO @ 0.1100 · fair 19.7% [9.2%–31.9%] · edge +8.0% · P(+) 82% · RESEARCH_ONLY · `KXBRASILEIROTOTAL-26NOV04FLAGPA-2`

## Expressions removed by the reducer (8)
- `KXBRASILEIROGAME-26NOV04FLAGPA-FLA` no: redundant with KXBRASILEIROSPREAD-26NOV04FLAGPA-FLA2/no (corr +0.62); best expression kept
- `KXBRASILEIROSPREAD-26NOV04FLAGPA-FLA3` no: dominated by KXBRASILEIROSPREAD-26NOV04FLAGPA-FLA2/no (corr +0.65)
- `KXBRASILEIROGAME-26NOV04FLAGPA-TIE` yes: redundant with KXBRASILEIROSPREAD-26NOV04FLAGPA-FLA2/no (corr +0.47); best expression kept
- `KXBRASILEIROTOTAL-26NOV04FLAGPA-4` no: dominated by KXBRASILEIROTOTAL-26NOV04FLAGPA-3/no (corr +0.65)
- `KXBRASILEIROTOTAL-26NOV04FLAGPA-5` no: dominated by KXBRASILEIROTOTAL-26NOV04FLAGPA-3/no (corr +0.43)
- `KXBRASILEIROTOTAL-26NOV04FLAGPA-6` no: dominated by KXBRASILEIROTOTAL-26NOV04FLAGPA-3/no (corr +0.29)
- `KXBRASILEIROGAME-26NOV04CAPVDG-CAP` yes: dominated by KXBRASILEIROSPREAD-26NOV04CAPVDG-CAP2/yes (corr +0.63)
- `KXBRASILEIROSPREAD-26NOV04CAPVDG-CAP3` yes: dominated by KXBRASILEIROSPREAD-26NOV04CAPVDG-CAP2/yes (corr +0.64)

## Events
- Flamengo vs Grêmio (Brasileirão Série A) 2026-11-04T22:30:00Z · markets 14/14 evaluated · lineups unknown · xG 2.41-0.70 · 1X2 74%/17%/9%
- Athletico Paranaense vs Vasco da Gama (Brasileirão Série A) 2026-11-04T22:30:00Z · markets 14/14 evaluated · lineups unknown · xG 2.02-1.06 · 1X2 58%/22%/20%
