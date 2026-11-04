# RUN SOCCER — 2026-11-04
Run `run-20261104T220001Z-ddfb0d` generated 2026-11-04T22:00:05.337074Z · filters: {'leagues': [], 'games': ['fx:bra.serie_a:2026:bra.athletico_paranaense:bra.vasco', 'fx:bra.serie_a:2026:bra.flamengo:bra.gremio'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4280** (discovery complete: True)
- contracts evaluated: 28 · excluded mechanically: 1279 · unsupported/unknown: 2973
- **unaccounted contracts: 0**
- by disposition: priced=28, unknown_family=3, unsupported_family=2970, unmapped_event=490, unmapped_team=56, no_fixture=186, filtered_by_operator=547
- competitions discovered: APFDDH, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EKSTRAKLASA, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAPORTUGAL, LIGUE1, MLS, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-04T22:00:01.120985Z; market_observed_at: 2026-11-04T21:57:18.081624Z; fixtures_observed_at: 2026-11-04T18:28:30.464359Z; results_observed_at: 2026-11-04T18:28:23.466525Z; model_fitted_at: 2026-11-04T21:59:59.451554Z; temporal_guard: {'decision_time': '2026-11-04T22:00:01.120985Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-04T18:28:30.464359Z', 'market_snapshots': '2026-11-04T21:59:53.200683Z', 'reference_odds': '2026-11-04T18:28:32.539319Z', 'results': '2026-11-04T22:00:00.927528Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (7)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Athletico Paranaense vs Vasco da Gama · Result: home · YES @ 0.4000 · fair 58.1% [42.0%–73.5%] · edge +16.4% · P(+) 90% · RESEARCH_ONLY · `KXBRASILEIROGAME-26NOV04CAPVDG-CAP`
- Athletico Paranaense vs Vasco da Gama · Result: away · NO @ 0.6750 · fair 80.2% [69.1%–90.2%] · edge +11.1% · P(+) 90% · RESEARCH_ONLY · `KXBRASILEIROGAME-26NOV04CAPVDG-VDG`
- Flamengo vs Grêmio · home wins by more than 2.5 · NO @ 0.5300 · fair 68.9% [52.3%–83.8%] · edge +14.2% · P(+) 87% · RESEARCH_ONLY · `KXBRASILEIROSPREAD-26NOV04FLAGPA-FLA3`
- Flamengo vs Grêmio · Total goals over 3.5 · NO @ 0.4700 · fair 62.3% [44.1%–79.3%] · edge +13.6% · P(+) 83% · RESEARCH_ONLY · `KXBRASILEIROTOTAL-26NOV04FLAGPA-4`
- Athletico Paranaense vs Vasco da Gama · away wins by more than 1.5 · NO @ 0.8700 · fair 92.3% [86.6%–97.0%] · edge +4.5% · P(+) 85% · RESEARCH_ONLY · `KXBRASILEIROSPREAD-26NOV04CAPVDG-VDG2`
- Flamengo vs Grêmio · Total goals over 0.5 · NO @ 0.0200 · fair 5.6% [2.1%–10.2%] · edge +3.5% · P(+) 89% · RESEARCH_ONLY · `KXBRASILEIROTOTAL-26NOV04FLAGPA-1`
- Flamengo vs Grêmio · Total goals over 1.5 · NO @ 0.1100 · fair 19.7% [9.2%–31.9%] · edge +8.0% · P(+) 82% · RESEARCH_ONLY · `KXBRASILEIROTOTAL-26NOV04FLAGPA-2`

## Expressions removed by the reducer (8)
- `KXBRASILEIROSPREAD-26NOV04FLAGPA-FLA2` no: redundant with KXBRASILEIROSPREAD-26NOV04FLAGPA-FLA3/no (corr +0.65); best expression kept
- `KXBRASILEIROGAME-26NOV04FLAGPA-FLA` no: redundant with KXBRASILEIROSPREAD-26NOV04FLAGPA-FLA3/no (corr +0.40); best expression kept
- `KXBRASILEIROGAME-26NOV04FLAGPA-TIE` yes: redundant with KXBRASILEIROSPREAD-26NOV04FLAGPA-FLA3/no (corr +0.31); best expression kept
- `KXBRASILEIROTOTAL-26NOV04FLAGPA-3` no: dominated by KXBRASILEIROTOTAL-26NOV04FLAGPA-4/no (corr +0.65)
- `KXBRASILEIROTOTAL-26NOV04FLAGPA-5` no: dominated by KXBRASILEIROTOTAL-26NOV04FLAGPA-4/no (corr +0.67)
- `KXBRASILEIROSPREAD-26NOV04CAPVDG-CAP2` yes: dominated by KXBRASILEIROGAME-26NOV04CAPVDG-CAP/yes (corr +0.63)
- `KXBRASILEIROSPREAD-26NOV04CAPVDG-CAP3` yes: dominated by KXBRASILEIROGAME-26NOV04CAPVDG-CAP/yes (corr +0.41)
- `KXBRASILEIROGAME-26NOV04CAPVDG-TIE` no: dominated by KXBRASILEIROGAME-26NOV04CAPVDG-CAP/yes (corr +0.63)

## Events
- Flamengo vs Grêmio (Brasileirão Série A) 2026-11-04T22:30:00Z · markets 14/14 evaluated · lineups unknown · xG 2.41-0.70 · 1X2 74%/17%/9%
- Athletico Paranaense vs Vasco da Gama (Brasileirão Série A) 2026-11-04T22:30:00Z · markets 14/14 evaluated · lineups unknown · xG 2.02-1.06 · 1X2 58%/22%/20%
