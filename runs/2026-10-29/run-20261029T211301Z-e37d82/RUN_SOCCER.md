# RUN SOCCER — 2026-10-29
Run `run-20261029T211301Z-e37d82` generated 2026-10-29T21:13:20.042602Z · filters: {'leagues': [], 'games': ['fx:usa.mls:2026:usa.la_galaxy:usa.austin', 'fx:usa.mls:2026:usa.san_jose_earthquakes:usa.real_salt_lake'], 'window_hours': 49, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5675** (discovery complete: True)
- contracts evaluated: 124 · excluded mechanically: 2573 · unsupported/unknown: 2978
- **unaccounted contracts: 0**
- by disposition: priced=124, unknown_family=3, unsupported_family=2975, unmapped_event=1073, unmapped_team=94, no_fixture=120, filtered_by_operator=1286
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAPSL, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-29T21:13:01.791541Z; market_observed_at: 2026-10-29T21:10:07.874370Z; fixtures_observed_at: 2026-10-29T19:48:29.056202Z; results_observed_at: 2026-10-29T17:27:53.076548Z; model_fitted_at: 2026-10-29T21:13:00.630334Z; temporal_guard: {'decision_time': '2026-10-29T21:13:01.791541Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-29T19:48:29.056202Z', 'market_snapshots': '2026-10-29T21:12:57.603839Z', 'reference_odds': '2026-10-29T17:28:00.282933Z', 'results': '2026-10-29T21:13:01.601709Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (8)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- San Jose Earthquakes vs Real Salt Lake · away team total over 1.5 · NO @ 0.5400 · fair 74.8% [63.1%–85.1%] · edge +19.0% · P(+) 96% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT31SJRSL-RSL2`
- San Jose Earthquakes vs Real Salt Lake · btts · NO @ 0.3500 · fair 51.2% [39.5%–62.5%] · edge +14.6% · P(+) 94% · RESEARCH_ONLY · `KXMLSBTTS-26OCT31SJRSL-BTTS`
- San Jose Earthquakes vs Real Salt Lake · Total goals over 3.5 · NO @ 0.5800 · fair 72.5% [57.6%–85.3%] · edge +12.8% · P(+) 87% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT31SJRSL-4`
- San Jose Earthquakes vs Real Salt Lake · Result: away · NO @ 0.6600 · fair 77.9% [67.3%–87.9%] · edge +10.3% · P(+) 89% · RESEARCH_ONLY · `KXMLSGAME-26OCT31SJRSL-RSL`
- San Jose Earthquakes vs Real Salt Lake · away wins by more than 1.5 · NO @ 0.8400 · fair 91.8% [86.2%–96.5%] · edge +6.9% · P(+) 93% · RESEARCH_ONLY · `KXMLSSPREAD-26OCT31SJRSL-RSL2`
- San Jose Earthquakes vs Real Salt Lake · Total goals over 1.5 · NO @ 0.1600 · fair 27.1% [15.2%–39.5%] · edge +10.2% · P(+) 86% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT31SJRSL-2`
- LA Galaxy vs Austin FC · home team total over 1.5 · NO @ 0.3200 · fair 46.2% [29.6%–62.7%] · edge +12.7% · P(+) 83% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT31LAGATX-LAG2`
- San Jose Earthquakes vs Real Salt Lake · away wins by more than 2.5 · NO @ 0.9500 · fair 97.6% [95.4%–99.3%] · edge +2.3% · P(+) 90% · RESEARCH_ONLY · `KXMLSSPREAD-26OCT31SJRSL-RSL3`

## Expressions removed by the reducer (6)
- `KXMLSTOTAL-26OCT31SJRSL-3` no: redundant with KXMLSTOTAL-26OCT31SJRSL-4/no (corr +0.64); best expression kept
- `KXMLSTOTAL-26OCT31SJRSL-5` no: redundant with KXMLSTOTAL-26OCT31SJRSL-4/no (corr +0.65); best expression kept
- `KXMLSTOTAL-26OCT31SJRSL-6` no: dominated by KXMLSTOTAL-26OCT31SJRSL-4/no (corr +0.42)
- `KXMLSTEAMTOTAL-26OCT31LAGATX-LAG3` no: dominated by KXMLSTEAMTOTAL-26OCT31LAGATX-LAG2/no (corr +0.58)
- `KXMLSTOTAL-26OCT31LAGATX-3` no: dominated by KXMLSTEAMTOTAL-26OCT31LAGATX-LAG2/no (corr +0.62)
- `KXMLSTOTAL-26OCT31LAGATX-4` no: dominated by KXMLSTEAMTOTAL-26OCT31LAGATX-LAG2/no (corr +0.52)

## Events
- San Jose Earthquakes vs Real Salt Lake (Major League Soccer) 2026-10-31T21:00:00Z · markets 62/62 evaluated · lineups unknown · xG 1.67-0.96 · 1X2 53%/25%/22%
- LA Galaxy vs Austin FC (Major League Soccer) 2026-10-31T21:00:00Z · markets 62/62 evaluated · lineups unknown · xG 1.85-1.04 · 1X2 55%/24%/21%
