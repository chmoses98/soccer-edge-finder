# RUN SOCCER — 2026-11-01
Run `run-20261101T234954Z-be1cdc` generated 2026-11-01T23:50:04.361077Z · filters: {'leagues': [], 'games': ['fx:usa.mls:2026:usa.new_england:usa.inter_miami'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4797** (discovery complete: True)
- contracts evaluated: 77 · excluded mechanically: 1747 · unsupported/unknown: 2973
- **unaccounted contracts: 0**
- by disposition: priced=77, unknown_family=3, unsupported_family=2970, unmapped_event=524, unmapped_team=114, no_fixture=172, filtered_by_operator=937
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, CHLLDP, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EFLTROPHY, EKSTRAKLASA, EPL, EREDIVISIE, FA, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SERIEA, SOCCER, SUPERLIG, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-01T23:49:54.438234Z; market_observed_at: 2026-11-01T23:46:53.895375Z; fixtures_observed_at: 2026-11-01T21:26:59.203120Z; results_observed_at: 2026-11-01T21:26:50.264233Z; model_fitted_at: 2026-11-01T23:49:52.638669Z; temporal_guard: {'decision_time': '2026-11-01T23:49:54.438234Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-01T21:26:59.203120Z', 'market_snapshots': '2026-11-01T23:49:43.440969Z', 'reference_odds': '2026-11-01T21:26:59.517263Z', 'results': '2026-11-01T23:49:54.195915Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (12)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- New England Revolution vs Inter Miami · away team total over 1.5 · NO @ 0.4200 · fair 61.8% [47.2%–75.0%] · edge +18.1% · P(+) 94% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV01NEMIA-MIA2`
- New England Revolution vs Inter Miami · away team total over 2.5 · NO @ 0.6800 · fair 84.3% [73.9%–92.7%] · edge +14.8% · P(+) 95% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV01NEMIA-MIA3`
- New England Revolution vs Inter Miami · away wins by more than 1.5 · NO @ 0.7500 · fair 88.1% [79.9%–94.3%] · edge +11.8% · P(+) 96% · RESEARCH_ONLY · `KXMLSSPREAD-26NOV01NEMIA-MIA2`
- New England Revolution vs Inter Miami · away team total over 0.5 · NO @ 0.1300 · fair 27.5% [17.0%–38.3%] · edge +13.7% · P(+) 96% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV01NEMIA-MIA1`
- New England Revolution vs Inter Miami · Second-half result: away · NO @ 0.6100 · fair 75.3% [63.8%–85.2%] · edge +12.7% · P(+) 93% · RESEARCH_ONLY · `KXMLS2H-26NOV01NEMIA-MIA`
- New England Revolution vs Inter Miami · First-half result: away · NO @ 0.6400 · fair 76.2% [65.8%–85.2%] · edge +10.5% · P(+) 91% · RESEARCH_ONLY · `KXMLS1H-26NOV01NEMIA-MIA`
- New England Revolution vs Inter Miami · away wins by more than 2.5 · NO @ 0.8900 · fair 95.6% [91.7%–98.5%] · edge +5.9% · P(+) 95% · RESEARCH_ONLY · `KXMLSSPREAD-26NOV01NEMIA-MIA3`
- New England Revolution vs Inter Miami · First half: away wins by more than 1.5 · NO @ 0.8800 · fair 93.9% [88.9%–98.1%] · edge +5.1% · P(+) 91% · RESEARCH_ONLY · `KXMLS1HSPREAD-26NOV01NEMIA-MIA2`
- New England Revolution vs Inter Miami · Second-half result: home · YES @ 0.3200 · fair 43.2% [29.8%–56.2%] · edge +9.6% · P(+) 83% · RESEARCH_ONLY · `KXMLS2H-26NOV01NEMIA-NE`
- New England Revolution vs Inter Miami · Exact score 3-0 (home-away) · YES @ 0.0200 · fair 4.6% [2.4%–6.7%] · edge +2.4% · P(+) 94% · RESEARCH_ONLY · `KXMLSSCORE-26NOV01NEMIA-NE3MIA0`
- New England Revolution vs Inter Miami · Exact score 2-0 (home-away) · YES @ 0.0400 · fair 7.0% [4.3%–9.9%] · edge +2.8% · P(+) 90% · RESEARCH_ONLY · `KXMLSSCORE-26NOV01NEMIA-NE2MIA0`
- New England Revolution vs Inter Miami · First-half result: home · YES @ 0.2900 · fair 39.1% [26.8%–52.2%] · edge +8.7% · P(+) 81% · RESEARCH_ONLY · `KXMLS1H-26NOV01NEMIA-NE`

## Expressions removed by the reducer (6)
- `KXMLSBTTS-26NOV01NEMIA-BTTS` no: dominated by KXMLSTEAMTOTAL-26NOV01NEMIA-MIA1/no (corr +0.78)
- `KXMLSGAME-26NOV01NEMIA-MIA` no: redundant with KXMLSSPREAD-26NOV01NEMIA-MIA2/no (corr +0.61); best expression kept
- `KXMLSGAME-26NOV01NEMIA-NE` yes: redundant with KXMLSSPREAD-26NOV01NEMIA-MIA2/no (corr +0.37); best expression kept
- `KXMLSSPREAD-26NOV01NEMIA-NE2` yes: redundant with KXMLSSPREAD-26NOV01NEMIA-MIA2/no (corr +0.24); best expression kept
- `KXMLSSPREAD-26NOV01NEMIA-NE3` yes: dominated by KXMLSSPREAD-26NOV01NEMIA-MIA2/no (corr +0.15)
- `KXMLS1HSCORE-26NOV01NEMIA-NE1MIA0` yes: dominated by KXMLS1H-26NOV01NEMIA-NE/yes (corr +0.62)

## Events
- New England Revolution vs Inter Miami (Major League Soccer) 2026-11-02T00:00:00Z · markets 77/77 evaluated · lineups unknown · xG 1.95-1.34 · 1X2 51%/22%/26%
