# RUN SOCCER — 2026-10-31
Run `run-20261031T031308Z-a7c987` generated 2026-10-31T03:13:18.925478Z · filters: {'leagues': [], 'games': ['fx:usa.mls:2026:usa.portland_timbers:usa.houston_dynamo'], 'window_hours': 49, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **6881** (discovery complete: True)
- contracts evaluated: 77 · excluded mechanically: 3831 · unsupported/unknown: 2973
- **unaccounted contracts: 0**
- by disposition: priced=77, unknown_family=3, unsupported_family=2970, unmapped_event=1574, unmapped_team=102, no_fixture=108, filtered_by_operator=2047
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EFLTROPHY, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAPSL, SERIEA, SOCCER, SUPERLIG, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-31T03:13:08.617335Z; market_observed_at: 2026-10-31T03:10:01.895815Z; fixtures_observed_at: 2026-10-31T01:42:18.248966Z; results_observed_at: 2026-10-31T01:42:11.243908Z; model_fitted_at: 2026-10-31T03:13:06.773421Z; temporal_guard: {'decision_time': '2026-10-31T03:13:08.617335Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-31T01:42:18.248966Z', 'market_snapshots': '2026-10-31T03:13:02.479034Z', 'reference_odds': '2026-10-31T01:42:18.600091Z', 'results': '2026-10-31T03:13:08.183820Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (3)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Portland Timbers vs Houston Dynamo · Total goals over 3.5 · NO @ 0.6200 · fair 77.3% [64.1%–88.8%] · edge +13.7% · P(+) 90% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV01PORHOU-4`
- Portland Timbers vs Houston Dynamo · btts · NO @ 0.4000 · fair 54.2% [42.5%–65.4%] · edge +12.6% · P(+) 92% · RESEARCH_ONLY · `KXMLSBTTS-26NOV01PORHOU-BTTS`
- Portland Timbers vs Houston Dynamo · Total goals over 0.5 · NO @ 0.0600 · fair 10.5% [5.2%–16.8%] · edge +4.1% · P(+) 82% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV01PORHOU-1`

## Expressions removed by the reducer (4)
- `KXMLSTOTAL-26NOV01PORHOU-2` no: redundant with KXMLSBTTS-26NOV01PORHOU-BTTS/no (corr +0.62); best expression kept
- `KXMLSTOTAL-26NOV01PORHOU-3` no: redundant with KXMLSTOTAL-26NOV01PORHOU-4/no (corr +0.63); best expression kept
- `KXMLSTOTAL-26NOV01PORHOU-5` no: dominated by KXMLSTOTAL-26NOV01PORHOU-4/no (corr +0.63)
- `KXMLSTOTAL-26NOV01PORHOU-6` no: redundant with KXMLSTOTAL-26NOV01PORHOU-4/no (corr +0.39); best expression kept

## Events
- Portland Timbers vs Houston Dynamo (Major League Soccer) 2026-11-02T02:45:00Z · markets 77/77 evaluated · lineups unknown · xG 1.44-0.96 · 1X2 47%/28%/25%
