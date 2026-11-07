# RUN SOCCER — 2026-11-07
Run `run-20261107T205849Z-7dd2fc` generated 2026-11-07T20:59:00.933279Z · filters: {'leagues': [], 'games': ['fx:usa.mls:2026:usa.cincinnati:usa.nashville'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **6423** (discovery complete: True)
- contracts evaluated: 77 · excluded mechanically: 3373 · unsupported/unknown: 2973
- **unaccounted contracts: 0**
- by disposition: priced=77, unknown_family=3, unsupported_family=2970, unmapped_event=1042, unmapped_team=95, no_fixture=143, filtered_by_operator=2093
- competitions discovered: APFDDH, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EFLTROPHY, EKSTRAKLASA, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INTLFRIENDLY, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAFF, SERIEA, SOCCER, SUPERLIG, SVK1L, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, UKRPL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-07T20:58:49.181584Z; market_observed_at: 2026-11-07T20:55:29.312025Z; fixtures_observed_at: 2026-11-07T17:32:43.124954Z; results_observed_at: 2026-11-07T16:11:37.413139Z; model_fitted_at: 2026-11-07T20:58:48.000502Z; temporal_guard: {'decision_time': '2026-11-07T20:58:49.181584Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-07T17:32:43.124954Z', 'market_snapshots': '2026-11-07T20:58:41.575162Z', 'reference_odds': '2026-11-07T16:11:44.271735Z', 'results': '2026-11-07T20:58:48.941761Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (3)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- FC Cincinnati vs Nashville SC · btts · NO @ 0.3300 · fair 45.6% [33.6%–57.2%] · edge +11.0% · P(+) 88% · RESEARCH_ONLY · `KXMLSBTTS-26NOV07CINNSH-BTTS`
- FC Cincinnati vs Nashville SC · Total goals over 3.5 · NO @ 0.5700 · fair 69.6% [54.6%–82.4%] · edge +10.9% · P(+) 83% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV07CINNSH-4`
- FC Cincinnati vs Nashville SC · Total goals over 0.5 · NO @ 0.0400 · fair 7.3% [3.3%–11.9%] · edge +3.1% · P(+) 81% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV07CINNSH-1`

## Expressions removed by the reducer (4)
- `KXMLSTOTAL-26NOV07CINNSH-3` no: redundant with KXMLSTOTAL-26NOV07CINNSH-4/no (corr +0.64); best expression kept
- `KXMLSTOTAL-26NOV07CINNSH-5` no: dominated by KXMLSTOTAL-26NOV07CINNSH-4/no (corr +0.65)
- `KXMLSTOTAL-26NOV07CINNSH-6` no: dominated by KXMLSTOTAL-26NOV07CINNSH-4/no (corr +0.42)
- `KXMLSSCORE-26NOV07CINNSH-CIN0NSH0` yes: dominated by KXMLSTOTAL-26NOV07CINNSH-1/no (corr +1.00)

## Events
- FC Cincinnati vs Nashville SC (Major League Soccer) 2026-11-07T21:00:00Z · markets 77/77 evaluated · lineups unknown · xG 1.29-1.47 · 1X2 33%/26%/41%
