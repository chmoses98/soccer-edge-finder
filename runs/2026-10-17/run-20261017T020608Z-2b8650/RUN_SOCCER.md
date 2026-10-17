# RUN SOCCER — 2026-10-17
Run `run-20261017T020608Z-2b8650` generated 2026-10-17T02:06:10.673149Z · filters: {'leagues': [], 'games': ['fx:mex.liga_mx:2026:mex.tijuana:mex.puebla'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **7511** (discovery complete: True)
- contracts evaluated: 32 · excluded mechanically: 4410 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=32, unknown_family=3, unsupported_family=3066, unmapped_event=1645, unmapped_team=124, no_fixture=183, filtered_by_operator=2458
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BRASILEIROC, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAPSL, SERIEA, SOCCER, SUPERLIG, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-17T02:06:08.171009Z; market_observed_at: 2026-10-17T02:03:04.079720Z; fixtures_observed_at: 2026-10-17T01:10:16.001989Z; results_observed_at: 2026-10-17T01:10:09.094627Z; model_fitted_at: 2026-10-17T02:06:06.530998Z; temporal_guard: {'decision_time': '2026-10-17T02:06:08.171009Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-17T01:10:16.001989Z', 'market_snapshots': '2026-10-17T02:05:58.859465Z', 'reference_odds': '2026-10-17T01:10:16.309451Z', 'results': '2026-10-17T02:06:07.944050Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (6)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Tijuana vs Puebla · btts · NO @ 0.4400 · fair 59.6% [47.8%–70.9%] · edge +13.8% · P(+) 94% · RESEARCH_ONLY · `KXLIGAMXBTTS-26OCT16TIJPUE-BTTS`
- Tijuana vs Puebla · Total goals over 3.5 · NO @ 0.6800 · fair 79.7% [65.6%–90.9%] · edge +10.1% · P(+) 85% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26OCT16TIJPUE-4`
- Tijuana vs Puebla · Total goals over 1.5 · NO @ 0.2200 · fair 34.6% [20.1%–49.2%] · edge +11.4% · P(+) 84% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26OCT16TIJPUE-2`
- Tijuana vs Puebla · away team total over 1.5 · NO @ 0.7300 · fair 81.7% [70.7%–90.5%] · edge +7.3% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT16TIJPUE-PUE2`
- Tijuana vs Puebla · First half: both teams to score · NO @ 0.8000 · fair 86.5% [79.9%–93.1%] · edge +5.4% · P(+) 84% · RESEARCH_ONLY · `KXLIGAMX1HBTTS-26OCT16TIJPUE-BTTS`
- Tijuana vs Puebla · away team total over 2.5 · NO @ 0.9200 · fair 95.2% [90.5%–98.4%] · edge +2.6% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT16TIJPUE-PUE3`

## Expressions removed by the reducer (3)
- `KXLIGAMXTOTAL-26OCT16TIJPUE-3` no: redundant with KXLIGAMXTOTAL-26OCT16TIJPUE-4/no (corr +0.63); best expression kept
- `KXLIGAMXTOTAL-26OCT16TIJPUE-5` no: dominated by KXLIGAMXTOTAL-26OCT16TIJPUE-4/no (corr +0.63)
- `KXLIGAMXTEAMTOTAL-26OCT16TIJPUE-PUE1` no: dominated by KXLIGAMXBTTS-26OCT16TIJPUE-BTTS/no (corr +0.78)

## Events
- Tijuana vs Puebla (Liga MX) 2026-10-17T03:05:00Z · markets 32/32 evaluated · lineups unknown · xG 1.51-0.77 · 1X2 53%/27%/20%
