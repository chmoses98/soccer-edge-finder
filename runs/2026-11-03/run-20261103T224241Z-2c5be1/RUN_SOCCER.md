# RUN SOCCER — 2026-11-03
Run `run-20261103T224241Z-2c5be1` generated 2026-11-03T22:42:43.604301Z · filters: {'leagues': [], 'games': ['fx:arg.primera:2026:arg.gimnasia_la_plata:arg.belgrano', 'fx:bra.serie_a:2026:bra.palmeiras:bra.remo'], 'window_hours': 49, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4169** (discovery complete: True)
- contracts evaluated: 14 · excluded mechanically: 1182 · unsupported/unknown: 2973
- **unaccounted contracts: 0**
- by disposition: priced=14, unknown_family=3, unsupported_family=2970, unmapped_event=364, unmapped_team=58, no_fixture=171, filtered_by_operator=589
- competitions discovered: APFDDH, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAPORTUGAL, LIGUE1, MLS, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SERIEA, SOCCER, SUPERLIG, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-03T22:42:41.985701Z; market_observed_at: 2026-11-03T22:40:03.678567Z; fixtures_observed_at: 2026-11-03T19:37:40.374061Z; results_observed_at: 2026-11-03T19:04:02.247660Z; model_fitted_at: 2026-11-03T22:42:40.990170Z; temporal_guard: {'decision_time': '2026-11-03T22:42:41.985701Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-03T19:37:40.374061Z', 'market_snapshots': '2026-11-03T22:42:38.995039Z', 'reference_odds': '2026-11-03T19:04:10.912651Z', 'results': '2026-11-03T22:42:41.853656Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (4)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Palmeiras vs Remo · Total goals over 3.5 · NO @ 0.6000 · fair 75.8% [60.8%–88.5%] · edge +14.1% · P(+) 89% · RESEARCH_ONLY · `KXBRASILEIROTOTAL-26NOV05PALCR-4`
- Palmeiras vs Remo · Result: draw · YES @ 0.1300 · fair 21.5% [13.4%–29.4%] · edge +7.7% · P(+) 89% · RESEARCH_ONLY · `KXBRASILEIROGAME-26NOV05PALCR-TIE`
- Palmeiras vs Remo · Total goals over 1.5 · NO @ 0.1800 · fair 30.4% [17.0%–44.5%] · edge +11.4% · P(+) 86% · RESEARCH_ONLY · `KXBRASILEIROTOTAL-26NOV05PALCR-2`
- Palmeiras vs Remo · home wins by more than 1.5 · NO @ 0.4300 · fair 56.7% [40.1%–72.9%] · edge +12.0% · P(+) 82% · RESEARCH_ONLY · `KXBRASILEIROSPREAD-26NOV05PALCR-PAL2`

## Expressions removed by the reducer (4)
- `KXBRASILEIROGAME-26NOV05PALCR-PAL` no: redundant with KXBRASILEIROGAME-26NOV05PALCR-TIE/yes (corr +0.77); best expression kept
- `KXBRASILEIROTOTAL-26NOV05PALCR-3` no: redundant with KXBRASILEIROTOTAL-26NOV05PALCR-4/no (corr +0.64); best expression kept
- `KXBRASILEIROTOTAL-26NOV05PALCR-5` no: dominated by KXBRASILEIROTOTAL-26NOV05PALCR-4/no (corr +0.64)
- `KXBRASILEIROTOTAL-26NOV05PALCR-6` no: dominated by KXBRASILEIROTOTAL-26NOV05PALCR-4/no (corr +0.40)

## Events
- Palmeiras vs Remo (Brasileirão Série A) 2026-11-05T22:30:00Z · markets 14/14 evaluated · lineups unknown · xG 1.92-0.55 · 1X2 68%/22%/10%
