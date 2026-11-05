# RUN SOCCER — 2026-11-05
Run `run-20261105T220316Z-5ec570` generated 2026-11-05T22:03:18.788025Z · filters: {'leagues': [], 'games': ['fx:arg.primera:2026:arg.gimnasia_la_plata:arg.belgrano', 'fx:bra.serie_a:2026:bra.palmeiras:bra.remo'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5403** (discovery complete: True)
- contracts evaluated: 14 · excluded mechanically: 2416 · unsupported/unknown: 2973
- **unaccounted contracts: 0**
- by disposition: priced=14, unknown_family=3, unsupported_family=2970, unmapped_event=859, unmapped_team=100, no_fixture=174, filtered_by_operator=1283
- competitions discovered: APFDDH, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EKSTRAKLASA, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, INTLFRIENDLY, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAFF, SERIEA, SOCCER, SUPERLIG, SVK1L, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, UKRPL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-05T22:03:16.995067Z; market_observed_at: 2026-11-05T22:00:00.057635Z; fixtures_observed_at: 2026-11-05T21:08:06.671544Z; results_observed_at: 2026-11-05T21:07:59.969299Z; model_fitted_at: 2026-11-05T22:03:15.628753Z; temporal_guard: {'decision_time': '2026-11-05T22:03:16.995067Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-05T21:08:06.671544Z', 'market_snapshots': '2026-11-05T22:03:07.294032Z', 'reference_odds': '2026-11-05T21:08:06.969237Z', 'results': '2026-11-05T22:03:16.818247Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (4)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Palmeiras vs Remo · Total goals over 2.5 · NO @ 0.3700 · fair 56.5% [39.1%–72.8%] · edge +17.9% · P(+) 91% · RESEARCH_ONLY · `KXBRASILEIROTOTAL-26NOV05PALCR-3`
- Palmeiras vs Remo · Total goals over 1.5 · NO @ 0.1700 · fair 31.2% [17.7%–45.6%] · edge +13.2% · P(+) 89% · RESEARCH_ONLY · `KXBRASILEIROTOTAL-26NOV05PALCR-2`
- Palmeiras vs Remo · Result: draw · YES @ 0.1250 · fair 21.5% [13.4%–29.6%] · edge +8.3% · P(+) 90% · RESEARCH_ONLY · `KXBRASILEIROGAME-26NOV05PALCR-TIE`
- Palmeiras vs Remo · btts · NO @ 0.5700 · fair 65.6% [54.4%–75.9%] · edge +6.9% · P(+) 80% · RESEARCH_ONLY · `KXBRASILEIROBTTS-26NOV05PALCR-BTTS`

## Expressions removed by the reducer (7)
- `KXBRASILEIROTOTAL-26NOV05PALCR-4` no: dominated by KXBRASILEIROTOTAL-26NOV05PALCR-3/no (corr +0.63)
- `KXBRASILEIROTOTAL-26NOV05PALCR-5` no: dominated by KXBRASILEIROTOTAL-26NOV05PALCR-3/no (corr +0.40)
- `KXBRASILEIROTOTAL-26NOV05PALCR-6` no: dominated by KXBRASILEIROTOTAL-26NOV05PALCR-3/no (corr +0.26)
- `KXBRASILEIROSPREAD-26NOV05PALCR-PAL3` no: dominated by KXBRASILEIROTOTAL-26NOV05PALCR-3/no (corr +0.61)
- `KXBRASILEIROSPREAD-26NOV05PALCR-PAL2` no: dominated by KXBRASILEIROTOTAL-26NOV05PALCR-3/no (corr +0.38)
- `KXBRASILEIROTOTAL-26NOV05PALCR-1` no: redundant with KXBRASILEIROGAME-26NOV05PALCR-TIE/yes (corr +0.64); best expression kept
- `KXBRASILEIROGAME-26NOV05PALCR-PAL` no: redundant with KXBRASILEIROGAME-26NOV05PALCR-TIE/yes (corr +0.77); best expression kept

## Events
- Palmeiras vs Remo (Brasileirão Série A) 2026-11-05T22:30:00Z · markets 14/14 evaluated · lineups unknown · xG 1.90-0.54 · 1X2 68%/22%/10%
