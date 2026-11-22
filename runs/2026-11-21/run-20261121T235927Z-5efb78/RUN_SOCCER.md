# RUN SOCCER — 2026-11-21
Run `run-20261121T235927Z-5efb78` generated 2026-11-21T23:59:37.644414Z · filters: {'leagues': [], 'games': ['fx:mex.liga_mx:2026:mex.pumas:mex.monterrey'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5275** (discovery complete: True)
- contracts evaluated: 79 · excluded mechanically: 2202 · unsupported/unknown: 2994
- **unaccounted contracts: 0**
- by disposition: priced=79, ambiguous_ownership=18, unknown_family=4, unsupported_family=2990, unmapped_event=990, unmapped_team=14, no_fixture=69, filtered_by_operator=1110, unpriceable=1
- competitions discovered: AFCCL2, ALEAGUEW, APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGAW, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, ENGWLEAGUECUP, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SAPSL, SCOCHAMP, SERIEA, SOCCER, SUPERLIG, SVK1L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-21T23:59:27.832686Z; market_observed_at: 2026-11-21T23:55:41.336056Z; fixtures_observed_at: 2026-11-21T21:57:14.964730Z; results_observed_at: 2026-11-21T21:57:08.457222Z; model_fitted_at: 2026-11-21T23:59:26.770429Z; temporal_guard: {'decision_time': '2026-11-21T23:59:27.832686Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-21T21:57:14.964730Z', 'market_snapshots': '2026-11-21T23:59:22.451046Z', 'reference_odds': '2026-11-21T21:57:15.144650Z', 'results': '2026-11-21T23:59:27.675372Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (5)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Pumas UNAM vs Monterrey · Result: home · YES @ 0.3700 · fair 51.4% [35.7%–66.8%] · edge +12.7% · P(+) 84% · RESEARCH_ONLY · `KXLIGAMXGAME-26NOV21PUMMON-PUM`
- Pumas UNAM vs Monterrey · Result: away · NO @ 0.6400 · fair 75.0% [61.7%–86.5%] · edge +9.3% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMXGAME-26NOV21PUMMON-MON`
- Pumas UNAM vs Monterrey · away wins by more than 1.5 · NO @ 0.8400 · fair 89.7% [81.9%–95.8%] · edge +4.8% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMXSPREAD-26NOV21PUMMON-MON2`
- Pumas UNAM vs Monterrey · away team total over 0.5 · NO @ 0.2400 · fair 33.7% [22.1%–45.7%] · edge +8.4% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV21PUMMON-MON1`
- Pumas UNAM vs Monterrey · First team to score: away · NO @ 0.5300 · fair 63.0% [50.8%–74.2%] · edge +8.2% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMXFTTS-26NOV21PUMMON-MON`

## Expressions removed by the reducer (2)
- `KXLIGAMXSPREAD-26NOV21PUMMON-PUM2` yes: dominated by KXLIGAMXGAME-26NOV21PUMMON-PUM/yes (corr +0.62)
- `KXLIGAMXSPREAD-26NOV21PUMMON-PUM3` yes: dominated by KXLIGAMXGAME-26NOV21PUMMON-PUM/yes (corr +0.39)

## Events
- Pumas UNAM vs Monterrey (Liga MX) 2026-11-22T01:00:00Z · markets 79/80 evaluated · lineups unknown · xG 1.76-1.14 · 1X2 51%/24%/25%
