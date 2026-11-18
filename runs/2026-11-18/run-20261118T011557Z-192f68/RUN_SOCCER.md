# RUN SOCCER — 2026-11-18
Run `run-20261118T011557Z-192f68` generated 2026-11-18T01:16:11.279942Z · filters: {'leagues': [], 'games': ['fx:bra.serie_a:2026:bra.sao_paulo:bra.fluminense', 'fx:usa.mls:2026:usa.orlando_city:usa.cincinnati'], 'window_hours': 49, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4490** (discovery complete: True)
- contracts evaluated: 93 · excluded mechanically: 1544 · unsupported/unknown: 2853
- **unaccounted contracts: 0**
- by disposition: priced=93, unknown_family=3, unsupported_family=2850, unmapped_event=580, unmapped_team=39, no_fixture=48, filtered_by_operator=876, unpriceable=1
- competitions discovered: ALEAGUEW, APFDDH, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGAW, CANPL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, ENGWLEAGUECUP, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, INTLFRIENDLY, KNVB, LALIGA, LALIGA2, LIGAF, LIGAMX, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SCOCHAMP, SERIEA, SOCCER, SUPERETTAN, SUPERLIG, SVK1L, SVKCUP, SWPL, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-18T01:15:57.763527Z; market_observed_at: 2026-11-18T01:12:31.583716Z; fixtures_observed_at: 2026-11-17T23:39:05.257558Z; results_observed_at: 2026-11-17T23:38:58.139917Z; model_fitted_at: 2026-11-18T01:15:56.358706Z; temporal_guard: {'decision_time': '2026-11-18T01:15:57.763527Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-17T23:39:05.257558Z', 'market_snapshots': '2026-11-18T01:15:53.455192Z', 'reference_odds': '2026-11-17T23:39:05.571731Z', 'results': '2026-11-18T01:15:57.567410Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (5)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Orlando City vs FC Cincinnati · Result: home · YES @ 0.4000 · fair 61.2% [45.5%–76.1%] · edge +19.5% · P(+) 94% · RESEARCH_ONLY · `KXMLSGAME-26NOV19ORLCIN-ORL`
- Orlando City vs FC Cincinnati · First-half result: away · NO @ 0.6900 · fair 79.2% [69.8%–88.2%] · edge +8.7% · P(+) 89% · RESEARCH_ONLY · `KXMLS1H-26NOV19ORLCIN-CIN`
- Orlando City vs FC Cincinnati · away wins by more than 2.5 · NO @ 0.9200 · fair 96.5% [93.2%–99.0%] · edge +4.0% · P(+) 92% · RESEARCH_ONLY · `KXMLSSPREAD-26NOV19ORLCIN-CIN3`
- Orlando City vs FC Cincinnati · home team total over 1.5 · YES @ 0.5800 · fair 70.7% [55.0%–84.5%] · edge +11.0% · P(+) 81% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV19ORLCIN-ORL2`
- Orlando City vs FC Cincinnati · Result: draw · NO @ 0.7700 · fair 82.1% [77.3%–87.0%] · edge +3.9% · P(+) 84% · RESEARCH_ONLY · `KXMLSGAME-26NOV19ORLCIN-TIE`

## Expressions removed by the reducer (5)
- `KXMLSGAME-26NOV19ORLCIN-CIN` no: dominated by KXMLSGAME-26NOV19ORLCIN-ORL/yes (corr +0.65)
- `KXMLSSPREAD-26NOV19ORLCIN-ORL2` yes: dominated by KXMLSGAME-26NOV19ORLCIN-ORL/yes (corr +0.67)
- `KXMLSSPREAD-26NOV19ORLCIN-CIN2` no: dominated by KXMLSGAME-26NOV19ORLCIN-ORL/yes (corr +0.40)
- `KXMLSSPREAD-26NOV19ORLCIN-ORL3` yes: dominated by KXMLSGAME-26NOV19ORLCIN-ORL/yes (corr +0.45)
- `KXMLSTEAMTOTAL-26NOV19ORLCIN-ORL3` yes: dominated by KXMLSGAME-26NOV19ORLCIN-ORL/yes (corr +0.56)

## Events
- Orlando City vs FC Cincinnati (Major League Soccer) 2026-11-20T00:30:00Z · markets 79/80 evaluated · lineups unknown · xG 2.57-1.43 · 1X2 61%/18%/21%
- São Paulo vs Fluminense (Brasileirão Série A) 2026-11-20T00:30:00Z · markets 14/14 evaluated · lineups unknown · xG 1.23-1.17 · 1X2 37%/28%/34%
