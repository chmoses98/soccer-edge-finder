# RUN SOCCER — 2026-10-30
Run `run-20261030T214556Z-90e477` generated 2026-10-30T21:46:10.986927Z · filters: {'leagues': [], 'games': ['fx:arg.primera:2026:arg.belgrano:arg.barracas_central', 'fx:arg.primera:2026:arg.newells:arg.union', 'fx:usa.mls:2026:usa.atlanta_united:usa.toronto', 'fx:usa.mls:2026:usa.nashville:usa.ny_red_bulls'], 'window_hours': 49, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **6683** (discovery complete: True)
- contracts evaluated: 118 · excluded mechanically: 3588 · unsupported/unknown: 2977
- **unaccounted contracts: 0**
- by disposition: priced=118, unknown_family=3, unsupported_family=2974, unmapped_event=1623, unmapped_team=102, no_fixture=138, filtered_by_operator=1725
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EFLTROPHY, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAPSL, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-30T21:45:56.232258Z; market_observed_at: 2026-10-30T21:42:56.039030Z; fixtures_observed_at: 2026-10-30T19:35:45.872539Z; results_observed_at: 2026-10-30T19:35:38.921073Z; model_fitted_at: 2026-10-30T21:45:54.566001Z; temporal_guard: {'decision_time': '2026-10-30T21:45:56.232258Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-30T19:35:45.872539Z', 'market_snapshots': '2026-10-30T21:45:50.875045Z', 'reference_odds': '2026-10-30T19:35:46.248262Z', 'results': '2026-10-30T21:45:56.002622Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (6)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Nashville SC vs New York Red Bulls · btts · NO @ 0.4200 · fair 65.8% [55.2%–75.2%] · edge +22.1% · P(+) 99% · RESEARCH_ONLY · `KXMLSBTTS-26NOV01NSHNYRB-BTTS`
- Atlanta United vs Toronto FC · btts · NO @ 0.3400 · fair 47.6% [36.4%–58.8%] · edge +12.0% · P(+) 91% · RESEARCH_ONLY · `KXMLSBTTS-26NOV01ATLTOR-BTTS`
- Nashville SC vs New York Red Bulls · Total goals over 3.5 · NO @ 0.5800 · fair 72.7% [56.5%–86.7%] · edge +13.0% · P(+) 86% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV01NSHNYRB-4`
- Atlanta United vs Toronto FC · Total goals over 3.5 · NO @ 0.5700 · fair 70.4% [55.4%–83.3%] · edge +11.7% · P(+) 86% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV01ATLTOR-4`
- Nashville SC vs New York Red Bulls · Result: away · NO @ 0.8500 · fair 92.0% [86.4%–96.7%] · edge +6.1% · P(+) 92% · RESEARCH_ONLY · `KXMLSGAME-26NOV01NSHNYRB-NYRB`
- Nashville SC vs New York Red Bulls · Total goals over 1.5 · NO @ 0.1600 · fair 27.8% [14.8%–41.8%] · edge +10.8% · P(+) 85% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV01NSHNYRB-2`

## Expressions removed by the reducer (7)
- `KXMLSTOTAL-26NOV01NSHNYRB-3` no: redundant with KXMLSTOTAL-26NOV01NSHNYRB-4/no (corr +0.64); best expression kept
- `KXMLSTOTAL-26NOV01NSHNYRB-5` no: dominated by KXMLSTOTAL-26NOV01NSHNYRB-4/no (corr +0.65)
- `KXMLSTOTAL-26NOV01NSHNYRB-6` no: dominated by KXMLSTOTAL-26NOV01NSHNYRB-4/no (corr +0.41)
- `KXMLSTOTAL-26NOV01ATLTOR-3` no: redundant with KXMLSTOTAL-26NOV01ATLTOR-4/no (corr +0.64); best expression kept
- `KXMLSTOTAL-26NOV01ATLTOR-5` no: dominated by KXMLSTOTAL-26NOV01ATLTOR-4/no (corr +0.66)
- `KXMLSTOTAL-26NOV01ATLTOR-6` no: dominated by KXMLSTOTAL-26NOV01ATLTOR-4/no (corr +0.42)
- `KXMLSTOTAL-26NOV01ATLTOR-2` no: dominated by KXMLSBTTS-26NOV01ATLTOR-BTTS/no (corr +0.61)

## Events
- Nashville SC vs New York Red Bulls (Major League Soccer) 2026-11-01T21:30:00Z · markets 59/59 evaluated · lineups unknown · xG 2.12-0.51 · 1X2 73%/19%/8%
- Atlanta United vs Toronto FC (Major League Soccer) 2026-11-01T21:30:00Z · markets 59/59 evaluated · lineups unknown · xG 1.62-1.12 · 1X2 48%/26%/26%
