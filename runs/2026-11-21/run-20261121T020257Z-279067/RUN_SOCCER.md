# RUN SOCCER — 2026-11-21
Run `run-20261121T020257Z-279067` generated 2026-11-21T02:03:10.691400Z · filters: {'leagues': [], 'games': ['fx:mex.liga_mx:2026:mex.juarez:mex.atlas'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **6242** (discovery complete: True)
- contracts evaluated: 79 · excluded mechanically: 3169 · unsupported/unknown: 2994
- **unaccounted contracts: 0**
- by disposition: priced=79, ambiguous_ownership=18, unknown_family=4, unsupported_family=2990, unmapped_event=1479, unmapped_team=62, no_fixture=72, filtered_by_operator=1537, unpriceable=1
- competitions discovered: AFCCL2, ALEAGUEW, APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGAW, CANPL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, ENGWLEAGUECUP, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAPSL, SCOCHAMP, SERIEA, SOCCER, SUPERETTAN, SUPERLIG, SVK1L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-21T02:02:57.597193Z; market_observed_at: 2026-11-21T01:59:04.450759Z; fixtures_observed_at: 2026-11-20T22:31:04.654084Z; results_observed_at: 2026-11-20T22:30:56.183176Z; model_fitted_at: 2026-11-21T02:02:55.996707Z; temporal_guard: {'decision_time': '2026-11-21T02:02:57.597193Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-20T22:31:04.654084Z', 'market_snapshots': '2026-11-21T02:02:46.276275Z', 'reference_odds': '2026-11-20T22:31:05.007030Z', 'results': '2026-11-21T02:02:57.374798Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (9)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- FC Juárez vs Atlas · Result: away · NO @ 0.5000 · fair 64.5% [49.1%–79.4%] · edge +12.8% · P(+) 85% · RESEARCH_ONLY · `KXLIGAMXGAME-26NOV20JUAATL-ATL`
- FC Juárez vs Atlas · First team to score: away · NO @ 0.4300 · fair 54.7% [41.8%–67.2%] · edge +10.0% · P(+) 85% · RESEARCH_ONLY · `KXLIGAMXFTTS-26NOV20JUAATL-ATL`
- FC Juárez vs Atlas · Result: home · YES @ 0.2500 · fair 39.5% [24.6%–56.1%] · edge +13.2% · P(+) 86% · RESEARCH_ONLY · `KXLIGAMXGAME-26NOV20JUAATL-JUA`
- FC Juárez vs Atlas · away team total over 1.5 · NO @ 0.4800 · fair 60.8% [45.0%–75.6%] · edge +11.0% · P(+) 84% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV20JUAATL-ATL2`
- FC Juárez vs Atlas · Exact score 2-0 (home-away) · YES @ 0.0300 · fair 6.3% [3.4%–9.4%] · edge +3.1% · P(+) 92% · RESEARCH_ONLY · `KXLIGAMXSCORE-26NOV20JUAATL-JUA2ATL0`
- FC Juárez vs Atlas · away wins by more than 2.5 · NO @ 0.8900 · fair 93.4% [87.1%–98.0%] · edge +3.7% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMXSPREAD-26NOV20JUAATL-ATL3`
- FC Juárez vs Atlas · away team total over 0.5 · NO @ 0.1800 · fair 26.9% [15.8%–38.9%] · edge +7.9% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV20JUAATL-ATL1`
- FC Juárez vs Atlas · First half: away wins by more than 1.5 · NO @ 0.8800 · fair 92.3% [85.9%–97.1%] · edge +3.6% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMX1HSPREAD-26NOV20JUAATL-ATL2`
- FC Juárez vs Atlas · First-half result: away · NO @ 0.6300 · fair 71.6% [58.8%–82.2%] · edge +7.0% · P(+) 80% · RESEARCH_ONLY · `KXLIGAMX1H-26NOV20JUAATL-ATL`

## Expressions removed by the reducer (4)
- `KXLIGAMXSPREAD-26NOV20JUAATL-JUA2` yes: dominated by KXLIGAMXGAME-26NOV20JUAATL-JUA/yes (corr +0.61)
- `KXLIGAMXSPREAD-26NOV20JUAATL-ATL2` no: dominated by KXLIGAMXGAME-26NOV20JUAATL-ATL/no (corr +0.61)
- `KXLIGAMXTEAMTOTAL-26NOV20JUAATL-ATL3` no: dominated by KXLIGAMXGAME-26NOV20JUAATL-ATL/no (corr +0.47)
- `KXLIGAMXFTTS-26NOV20JUAATL-JUA` yes: dominated by KXLIGAMXFTTS-26NOV20JUAATL-ATL/no (corr +0.87)

## Events
- FC Juárez vs Atlas (Liga MX) 2026-11-21T03:00:00Z · markets 79/80 evaluated · lineups unknown · xG 1.46-1.38 · 1X2 39%/25%/36%
