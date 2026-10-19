# RUN SOCCER — 2026-10-19
Run `run-20261019T000108Z-e6f61c` generated 2026-10-19T00:01:13.799605Z · filters: {'leagues': [], 'games': ['fx:mex.liga_mx:2026:mex.monterrey:mex.pachuca'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4776** (discovery complete: True)
- contracts evaluated: 77 · excluded mechanically: 1630 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=77, unknown_family=3, unsupported_family=3066, unmapped_event=597, unmapped_team=15, no_fixture=147, filtered_by_operator=871
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CHLLDP, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, EPL, EREDIVISIE, FA, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SERIEA, SOCCER, SUPERLIG, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-19T00:01:08.400098Z; market_observed_at: 2026-10-18T23:58:17.707421Z; fixtures_observed_at: 2026-10-18T23:06:15.557816Z; results_observed_at: 2026-10-18T23:06:06.804554Z; model_fitted_at: 2026-10-19T00:01:07.217455Z; temporal_guard: {'decision_time': '2026-10-19T00:01:08.400098Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-18T23:06:15.557816Z', 'market_snapshots': '2026-10-19T00:01:01.634056Z', 'reference_odds': '2026-10-18T23:06:15.837177Z', 'results': '2026-10-19T00:01:08.060081Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (9)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Monterrey vs Pachuca · home team total over 1.5 · NO @ 0.3900 · fair 59.0% [41.3%–74.7%] · edge +18.3% · P(+) 91% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT18MONPAC-MON2`
- Monterrey vs Pachuca · home team total over 0.5 · NO @ 0.1300 · fair 25.8% [13.9%–37.9%] · edge +12.0% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT18MONPAC-MON1`
- Monterrey vs Pachuca · Total goals over 3.5 · NO @ 0.6200 · fair 74.6% [60.3%–87.2%] · edge +11.0% · P(+) 84% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26OCT18MONPAC-4`
- Monterrey vs Pachuca · First-half result: home · NO @ 0.5600 · fair 67.4% [53.8%–79.2%] · edge +9.7% · P(+) 84% · RESEARCH_ONLY · `KXLIGAMX1H-26OCT18MONPAC-MON`
- Monterrey vs Pachuca · Total goals over 1.5 · NO @ 0.1800 · fair 29.0% [16.4%–42.4%] · edge +10.0% · P(+) 84% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26OCT18MONPAC-2`
- Monterrey vs Pachuca · Second-half result: home · NO @ 0.5300 · fair 63.9% [49.8%–76.2%] · edge +9.2% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMX2H-26OCT18MONPAC-MON`
- Monterrey vs Pachuca · First half: home wins by more than 1.5 · NO @ 0.8500 · fair 90.6% [83.9%–97.1%] · edge +4.8% · P(+) 84% · RESEARCH_ONLY · `KXLIGAMX1HSPREAD-26OCT18MONPAC-MON2`
- Monterrey vs Pachuca · Total goals over 0.5 · NO @ 0.0500 · fair 9.6% [4.4%–15.7%] · edge +4.3% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26OCT18MONPAC-1`
- Monterrey vs Pachuca · Exact score 0-1 (home-away) · YES @ 0.0500 · fair 8.5% [4.3%–12.9%] · edge +3.2% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMXSCORE-26OCT18MONPAC-MON0PAC1`

## Expressions removed by the reducer (8)
- `KXLIGAMXTOTAL-26OCT18MONPAC-3` no: redundant with KXLIGAMXTOTAL-26OCT18MONPAC-4/no (corr +0.63); best expression kept
- `KXLIGAMXTOTAL-26OCT18MONPAC-5` no: dominated by KXLIGAMXTOTAL-26OCT18MONPAC-4/no (corr +0.64)
- `KXLIGAMXTOTAL-26OCT18MONPAC-6` no: dominated by KXLIGAMXTOTAL-26OCT18MONPAC-4/no (corr +0.41)
- `KXLIGAMXBTTS-26OCT18MONPAC-BTTS` no: dominated by KXLIGAMXTOTAL-26OCT18MONPAC-2/no (corr +0.63)
- `KXLIGAMXTEAMTOTAL-26OCT18MONPAC-MON3` no: dominated by KXLIGAMXTEAMTOTAL-26OCT18MONPAC-MON2/no (corr +0.56)
- `KXLIGAMXSPREAD-26OCT18MONPAC-MON2` no: dominated by KXLIGAMXTEAMTOTAL-26OCT18MONPAC-MON2/no (corr +0.64)
- `KXLIGAMXGAME-26OCT18MONPAC-MON` no: dominated by KXLIGAMXTEAMTOTAL-26OCT18MONPAC-MON2/no (corr +0.61)
- `KXLIGAMXSPREAD-26OCT18MONPAC-MON3` no: dominated by KXLIGAMXTEAMTOTAL-26OCT18MONPAC-MON2/no (corr +0.38)

## Events
- Monterrey vs Pachuca (Liga MX) 2026-10-19T01:00:00Z · markets 77/77 evaluated · lineups unknown · xG 1.43-1.10 · 1X2 44%/27%/29%
