# RUN SOCCER — 2026-11-21
Run `run-20261121T223158Z-20abba` generated 2026-11-21T22:32:08.763046Z · filters: {'leagues': [], 'games': ['fx:mex.liga_mx:2026:mex.santos_laguna:mex.leon'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5393** (discovery complete: True)
- contracts evaluated: 79 · excluded mechanically: 2320 · unsupported/unknown: 2994
- **unaccounted contracts: 0**
- by disposition: priced=79, ambiguous_ownership=18, unknown_family=4, unsupported_family=2990, unmapped_event=1010, unmapped_team=14, no_fixture=69, filtered_by_operator=1208, unpriceable=1
- competitions discovered: AFCCL2, ALEAGUEW, APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGAW, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, ENGWLEAGUECUP, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SAPSL, SCOCHAMP, SERIEA, SOCCER, SUPERLIG, SVK1L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-21T22:31:58.863936Z; market_observed_at: 2026-11-21T22:28:12.149507Z; fixtures_observed_at: 2026-11-21T21:57:14.964730Z; results_observed_at: 2026-11-21T21:57:08.457222Z; model_fitted_at: 2026-11-21T22:31:57.676492Z; temporal_guard: {'decision_time': '2026-11-21T22:31:58.863936Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-21T21:57:14.964730Z', 'market_snapshots': '2026-11-21T22:31:53.360332Z', 'reference_odds': '2026-11-21T21:57:15.144650Z', 'results': '2026-11-21T22:31:58.697090Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (9)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Santos Laguna vs León · away team total over 1.5 · NO @ 0.5900 · fair 74.5% [60.4%–86.0%] · edge +13.8% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV21SLALEO-LEO2`
- Santos Laguna vs León · away team total over 0.5 · NO @ 0.2400 · fair 39.1% [25.6%–52.0%] · edge +13.8% · P(+) 91% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV21SLALEO-LEO1`
- Santos Laguna vs León · away team total over 2.5 · NO @ 0.8300 · fair 91.7% [84.2%–97.1%] · edge +7.7% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV21SLALEO-LEO3`
- Santos Laguna vs León · First half: away wins by more than 1.5 · NO @ 0.9300 · fair 95.9% [91.9%–99.1%] · edge +2.4% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMX1HSPREAD-26NOV21SLALEO-LEO2`
- Santos Laguna vs León · Second-half result: away · NO @ 0.7000 · fair 78.2% [66.8%–88.2%] · edge +6.7% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMX2H-26NOV21SLALEO-LEO`
- Santos Laguna vs León · Exact score 2-0 (home-away) · YES @ 0.0600 · fair 9.3% [5.7%–12.9%] · edge +2.9% · P(+) 85% · RESEARCH_ONLY · `KXLIGAMXSCORE-26NOV21SLALEO-SLA2LEO0`
- Santos Laguna vs León · Exact score 1-0 (home-away) · YES @ 0.0800 · fair 12.3% [7.4%–17.2%] · edge +3.8% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMXSCORE-26NOV21SLALEO-SLA1LEO0`
- Santos Laguna vs León · away wins by more than 1.5 · NO @ 0.8600 · fair 90.8% [83.7%–96.6%] · edge +4.0% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMXSPREAD-26NOV21SLALEO-LEO2`
- Santos Laguna vs León · Total goals over 4.5 · NO @ 0.8100 · fair 87.6% [77.9%–95.7%] · edge +5.5% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26NOV21SLALEO-5`

## Expressions removed by the reducer (3)
- `KXLIGAMXBTTS-26NOV21SLALEO-BTTS` no: redundant with KXLIGAMXTEAMTOTAL-26NOV21SLALEO-LEO1/no (corr +0.76); best expression kept
- `KXLIGAMXTOTAL-26NOV21SLALEO-2` no: dominated by KXLIGAMXTEAMTOTAL-26NOV21SLALEO-LEO1/no (corr +0.45)
- `KXLIGAMXTOTAL-26NOV21SLALEO-4` no: redundant with KXLIGAMXTOTAL-26NOV21SLALEO-5/no (corr +0.64); best expression kept

## Events
- Santos Laguna vs León (Liga MX) 2026-11-21T23:00:00Z · markets 79/80 evaluated · lineups unknown · xG 1.56-0.98 · 1X2 50%/26%/24%
