# RUN SOCCER — 2026-10-21
Run `run-20261021T005601Z-b5974b` generated 2026-10-21T00:56:16.444266Z · filters: {'leagues': [], 'games': ['fx:mex.liga_mx:2026:mex.juarez:mex.atlante', 'fx:mex.liga_mx:2026:mex.san_luis:mex.queretaro'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5558** (discovery complete: True)
- contracts evaluated: 154 · excluded mechanically: 2335 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=154, unknown_family=3, unsupported_family=3066, unmapped_event=750, unmapped_team=54, no_fixture=123, filtered_by_operator=1408
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SERIEA, SOCCER, SUPERLIG, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-21T00:56:01.297108Z; market_observed_at: 2026-10-21T00:53:12.981249Z; fixtures_observed_at: 2026-10-21T00:41:23.102578Z; results_observed_at: 2026-10-20T19:53:32.693317Z; model_fitted_at: 2026-10-21T00:55:59.727938Z; temporal_guard: {'decision_time': '2026-10-21T00:56:01.297108Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-21T00:41:23.102578Z', 'market_snapshots': '2026-10-21T00:55:54.720212Z', 'reference_odds': '2026-10-20T19:53:41.879516Z', 'results': '2026-10-21T00:56:01.103508Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (4)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Atlético San Luis vs Querétaro · btts · NO @ 0.4100 · fair 53.7% [40.7%–65.9%] · edge +11.0% · P(+) 86% · RESEARCH_ONLY · `KXLIGAMXBTTS-26OCT20ASLQUE-BTTS`
- FC Juárez vs Atlante · away team total over 0.5 · NO @ 0.2100 · fair 31.4% [18.1%–45.2%] · edge +9.3% · P(+) 80% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT20JUAALA-ALA1`
- FC Juárez vs Atlante · away team total over 1.5 · NO @ 0.5400 · fair 66.1% [49.0%–81.1%] · edge +10.3% · P(+) 80% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT20JUAALA-ALA2`
- Atlético San Luis vs Querétaro · Total goals over 5.5 · NO @ 0.9300 · fair 95.7% [91.0%–99.0%] · edge +2.2% · P(+) 80% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26OCT20ASLQUE-6`

## Expressions removed by the reducer (1)
- `KXLIGAMXTEAMTOTAL-26OCT20ASLQUE-QUE1` no: dominated by KXLIGAMXBTTS-26OCT20ASLQUE-BTTS/no (corr +0.70)

## Events
- FC Juárez vs Atlante (Liga MX) 2026-10-21T01:00:00Z · markets 77/77 evaluated · lineups unknown · xG 1.32-1.22 · 1X2 38%/27%/34%
- Atlético San Luis vs Querétaro (Liga MX) 2026-10-21T01:00:00Z · markets 77/77 evaluated · lineups unknown · xG 1.34-1.06 · 1X2 42%/28%/29%
