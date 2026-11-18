# RUN SOCCER — 2026-11-18
Run `run-20261118T012105Z-b39209` generated 2026-11-18T01:22:10.199061Z · filters: {'leagues': [], 'games': [], 'window_hours': 48, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **7433** (discovery complete: True)
- contracts evaluated: 392 · excluded mechanically: 3996 · unsupported/unknown: 3045
- **unaccounted contracts: 0**
- by disposition: priced=392, started=61, ambiguous_ownership=72, unknown_family=195, unsupported_family=2850, unmapped_event=1809, unmapped_team=504, no_fixture=373, out_of_window=1176, unpriceable=1
- competitions discovered: AFCCL, ALEAGUE, ALEAGUEW, ALLSVENSKAN, APFDDH, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BOLPDIV, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGA2, BUNDESLIGAW, CANPL, CHLLDP, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, COPPAITALIA, CZEFL, CZEFNL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EERSTEDIV, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ELITESERIEN, ENGNL, ENGWLEAGUECUP, EPL, EREDIVISIE, EREDIVISIEW, EWSL, FA, FRAPLW, GER3L, HNL, HUNNB1, IDNSL, INDSL, INTLFRIENDLY, J2LEAGUE, JLEAGUE, K2LEAGUE, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAF, LIGAMX, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, LIGUE2, MLS, MLS2H, MLSEAST, MLSWEST, MYSL, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAUDIPL, SCOCHAMP, SCOTTISHPREM, SERIEA, SERIEAW, SERIEB, SERIEC, SGPPL, SLGREECE, SOCCER, SRBCUP, SRBSL, SUPERETTAN, SUPERLIG, SVK1L, SVKCUP, SVNCUP, SVNPL, SWISSLEAGUE, SWPL, TACAPORT, TFF1LIG, THAIL1, TWEEDEDIV, UAEPL, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, VLEAGUE1, WC, WCW

## Freshness
- as_of: 2026-11-18T01:21:05.397331Z; market_observed_at: 2026-11-18T01:05:43.379463Z; fixtures_observed_at: 2026-11-18T01:05:41.616578Z; results_observed_at: 2026-11-18T01:05:33.920538Z; model_fitted_at: 2026-11-18T01:05:42.176248Z; temporal_guard: {'decision_time': '2026-11-18T01:21:05.397331Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-18T01:05:41.616578Z', 'market_snapshots': '2026-11-18T01:21:03.936006Z', 'reference_odds': '2026-11-18T01:21:04.119041Z', 'results': '2026-11-18T01:05:43.370172Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (6)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Orlando City vs FC Cincinnati · match_winner_2way · NO @ 0.5200 · fair 79.0% [65.8%–90.2%] · edge +25.3% · P(+) 99% · RESEARCH_ONLY · `KXMLSADVANCE-26NOV19ORLCIN-CIN`
- Orlando City vs FC Cincinnati · away wins by more than 2.5 · NO @ 0.9200 · fair 96.5% [93.2%–99.0%] · edge +4.0% · P(+) 92% · RESEARCH_ONLY · `KXMLSSPREAD-26NOV19ORLCIN-CIN3`
- Vitória vs Red Bull Bragantino · btts · NO @ 0.4200 · fair 53.4% [41.6%–64.6%] · edge +9.7% · P(+) 86% · RESEARCH_ONLY · `KXBRASILEIROBTTS-26NOV19VITRBB-BTTS`
- Orlando City vs FC Cincinnati · away team total over 1.5 · NO @ 0.4600 · fair 58.7% [43.9%–72.6%] · edge +11.0% · P(+) 84% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV19ORLCIN-CIN2`
- Orlando City vs FC Cincinnati · home team total over 1.5 · YES @ 0.5800 · fair 70.7% [55.0%–84.5%] · edge +11.0% · P(+) 81% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV19ORLCIN-ORL2`
- Orlando City vs FC Cincinnati · Result: draw · NO @ 0.7700 · fair 82.1% [77.3%–87.0%] · edge +3.9% · P(+) 84% · RESEARCH_ONLY · `KXMLSGAME-26NOV19ORLCIN-TIE`

## Expressions removed by the reducer (6)
- `KXMLSGAME-26NOV19ORLCIN-ORL` yes: dominated by KXMLSADVANCE-26NOV19ORLCIN-CIN/no (corr +0.65)
- `KXMLSGAME-26NOV19ORLCIN-CIN` no: dominated by KXMLSADVANCE-26NOV19ORLCIN-CIN/no (corr +1.00)
- `KXMLSSPREAD-26NOV19ORLCIN-ORL2` yes: dominated by KXMLSADVANCE-26NOV19ORLCIN-CIN/no (corr +0.43)
- `KXMLSSPREAD-26NOV19ORLCIN-CIN2` no: dominated by KXMLSADVANCE-26NOV19ORLCIN-CIN/no (corr +0.62)
- `KXMLSSPREAD-26NOV19ORLCIN-ORL3` yes: dominated by KXMLSADVANCE-26NOV19ORLCIN-CIN/no (corr +0.29)
- `KXMLSTEAMTOTAL-26NOV19ORLCIN-ORL3` yes: dominated by KXMLSADVANCE-26NOV19ORLCIN-CIN/no (corr +0.41)

## Events
- Nicaragua vs Montserrat (CONCACAF Nations League) 2026-11-18T03:00:00Z · markets 25/25 evaluated · lineups unknown · xG 1.21-1.60 · 1X2 30%/25%/46%
- Mexico vs Jamaica (CONCACAF Nations League) 2026-11-18T02:30:00Z · markets 25/25 evaluated · lineups unknown · xG 1.52-1.16 · 1X2 44%/26%/30%
- São Paulo vs Fluminense (Brasileirão Série A) 2026-11-20T00:30:00Z · markets 29/29 evaluated · lineups unknown · xG 1.23-1.17 · 1X2 37%/28%/34%
- Vitória vs Red Bull Bragantino (Brasileirão Série A) 2026-11-19T22:30:00Z · markets 29/29 evaluated · lineups unknown · xG 1.16-1.20 · 1X2 35%/29%/36%
- Vasco da Gama vs Internacional (Brasileirão Série A) 2026-11-19T22:30:00Z · markets 29/29 evaluated · lineups unknown · xG 1.65-0.99 · 1X2 51%/26%/23%
- Grêmio vs Bahia (Brasileirão Série A) 2026-11-19T00:30:00Z · markets 29/29 evaluated · lineups unknown · xG 1.42-1.21 · 1X2 41%/27%/32%
- Corinthians vs Botafogo (Brasileirão Série A) 2026-11-19T00:30:00Z · markets 29/29 evaluated · lineups unknown · xG 1.47-0.95 · 1X2 48%/28%/24%
- Flamengo vs Athletico Paranaense (Brasileirão Série A) 2026-11-18T23:30:00Z · markets 29/29 evaluated · lineups unknown · xG 2.55-0.89 · 1X2 71%/17%/12%
- Cruzeiro vs Palmeiras (Brasileirão Série A) 2026-11-18T23:30:00Z · markets 29/29 evaluated · lineups unknown · xG 1.24-1.32 · 1X2 34%/27%/38%
- Remo vs Chapecoense (Brasileirão Série A) 2026-11-18T23:00:00Z · markets 29/29 evaluated · lineups unknown · xG 1.96-0.96 · 1X2 59%/22%/18%
- Coritiba vs Santos (Brasileirão Série A) 2026-11-18T22:30:00Z · markets 29/29 evaluated · lineups unknown · xG 1.29-1.35 · 1X2 35%/27%/38%
- Orlando City vs FC Cincinnati (Major League Soccer) 2026-11-20T00:30:00Z · markets 81/82 evaluated · lineups unknown · xG 2.57-1.43 · 1X2 61%/18%/21%
