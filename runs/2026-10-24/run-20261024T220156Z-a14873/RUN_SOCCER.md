# RUN SOCCER — 2026-10-24
Run `run-20261024T220156Z-a14873` generated 2026-10-24T22:02:04.857695Z · filters: {'leagues': [], 'games': ['fx:arg.primera:2026:arg.san_lorenzo:arg.newells', 'fx:bra.serie_a:2026:bra.chapecoense:bra.fluminense', 'fx:mex.liga_mx:2026:mex.leon:mex.toluca'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **7113** (discovery complete: True)
- contracts evaluated: 91 · excluded mechanically: 3953 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=91, unknown_family=3, unsupported_family=3066, unmapped_event=1313, unmapped_team=313, no_fixture=133, filtered_by_operator=2194
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-24T22:01:56.891401Z; market_observed_at: 2026-10-24T21:58:51.240308Z; fixtures_observed_at: 2026-10-24T19:10:09.432684Z; results_observed_at: 2026-10-24T18:42:57.477580Z; model_fitted_at: 2026-10-24T22:01:55.635800Z; temporal_guard: {'decision_time': '2026-10-24T22:01:56.891401Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-24T19:10:09.432684Z', 'market_snapshots': '2026-10-24T22:01:44.903895Z', 'reference_odds': '2026-10-24T18:43:00.069400Z', 'results': '2026-10-24T22:01:56.666762Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (8)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- León vs Toluca · away team total over 1.5 · NO @ 0.4100 · fair 59.5% [42.8%–74.6%] · edge +16.8% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT24LEOTOL-TOL2`
- León vs Toluca · away team total over 2.5 · NO @ 0.7000 · fair 82.5% [69.8%–92.5%] · edge +11.0% · P(+) 88% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT24LEOTOL-TOL3`
- León vs Toluca · away team total over 0.5 · NO @ 0.1400 · fair 26.0% [14.7%–37.9%] · edge +11.2% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT24LEOTOL-TOL1`
- León vs Toluca · First-half result: away · NO @ 0.6000 · fair 71.4% [58.8%–82.2%] · edge +9.7% · P(+) 86% · RESEARCH_ONLY · `KXLIGAMX1H-26OCT24LEOTOL-TOL`
- León vs Toluca · away wins by more than 2.5 · NO @ 0.8700 · fair 93.1% [86.8%–97.8%] · edge +5.3% · P(+) 87% · RESEARCH_ONLY · `KXLIGAMXSPREAD-26OCT24LEOTOL-TOL3`
- León vs Toluca · Result: home · YES @ 0.2500 · fair 38.8% [23.5%–55.8%] · edge +12.5% · P(+) 85% · RESEARCH_ONLY · `KXLIGAMXGAME-26OCT24LEOTOL-LEO`
- León vs Toluca · First half: away wins by more than 1.5 · NO @ 0.8700 · fair 92.1% [85.9%–97.1%] · edge +4.3% · P(+) 85% · RESEARCH_ONLY · `KXLIGAMX1HSPREAD-26OCT24LEOTOL-TOL2`
- León vs Toluca · Second-half result: away · NO @ 0.5900 · fair 68.9% [55.8%–81.2%] · edge +8.2% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMX2H-26OCT24LEOTOL-TOL`

## Expressions removed by the reducer (2)
- `KXLIGAMXGAME-26OCT24LEOTOL-TOL` no: redundant with KXLIGAMXTEAMTOTAL-26OCT24LEOTOL-TOL3/no (corr +0.48); best expression kept
- `KXLIGAMXSPREAD-26OCT24LEOTOL-TOL2` no: dominated by KXLIGAMXTEAMTOTAL-26OCT24LEOTOL-TOL3/no (corr +0.61)

## Events
- León vs Toluca (Liga MX) 2026-10-24T23:00:00Z · markets 77/77 evaluated · lineups unknown · xG 1.47-1.41 · 1X2 39%/25%/36%
- Chapecoense vs Fluminense (Brasileirão Série A) 2026-10-24T22:30:00Z · markets 14/14 evaluated · lineups unknown · xG 1.15-1.74 · 1X2 25%/24%/51%
