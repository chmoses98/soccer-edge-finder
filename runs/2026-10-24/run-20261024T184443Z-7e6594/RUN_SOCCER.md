# RUN SOCCER — 2026-10-24
Run `run-20261024T184443Z-7e6594` generated 2026-10-24T18:44:53.341394Z · filters: {'leagues': [], 'games': ['fx:bra.serie_a:2026:bra.internacional:bra.botafogo', 'fx:bra.serie_a:2026:bra.mirassol:bra.sao_paulo', 'fx:bra.serie_a:2026:bra.vitoria:bra.athletico_paranaense', 'fx:usa.mls:2026:usa.columbus_crew:usa.toronto'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **7274** (discovery complete: True)
- contracts evaluated: 119 · excluded mechanically: 4086 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=119, unknown_family=3, unsupported_family=3066, unmapped_event=1367, unmapped_team=291, no_fixture=133, filtered_by_operator=2295
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-24T18:44:43.181512Z; market_observed_at: 2026-10-24T18:40:02.829607Z; fixtures_observed_at: 2026-10-24T18:42:59.815430Z; results_observed_at: 2026-10-24T18:42:57.477580Z; model_fitted_at: 2026-10-24T18:44:41.783538Z; temporal_guard: {'decision_time': '2026-10-24T18:44:43.181512Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-24T18:42:59.815430Z', 'market_snapshots': '2026-10-24T18:42:56.506674Z', 'reference_odds': '2026-10-24T18:43:00.069400Z', 'results': '2026-10-24T18:44:42.972671Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (8)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Columbus Crew vs Toronto FC · btts · NO @ 0.3700 · fair 49.4% [37.8%–60.3%] · edge +10.8% · P(+) 88% · RESEARCH_ONLY · `KXMLSBTTS-26OCT24CLBTOR-BTTS`
- Mirassol vs São Paulo · btts · NO @ 0.4700 · fair 57.6% [46.4%–68.2%] · edge +8.9% · P(+) 85% · RESEARCH_ONLY · `KXBRASILEIROBTTS-26OCT24MIRSPA-BTTS`
- Internacional vs Botafogo · btts · NO @ 0.4300 · fair 54.2% [42.0%–66.1%] · edge +9.5% · P(+) 84% · RESEARCH_ONLY · `KXBRASILEIROBTTS-26OCT24INTBOT-BTTS`
- Columbus Crew vs Toronto FC · Total goals over 3.5 · NO @ 0.5700 · fair 69.1% [53.2%–82.4%] · edge +10.3% · P(+) 83% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT24CLBTOR-4`
- Columbus Crew vs Toronto FC · First-half total goals over 0.5 · NO @ 0.2200 · fair 30.0% [19.8%–40.2%] · edge +6.8% · P(+) 81% · RESEARCH_ONLY · `KXMLS1HTOTAL-26OCT24CLBTOR-1`
- Columbus Crew vs Toronto FC · Total goals over 1.5 · NO @ 0.1500 · fair 24.2% [13.3%–36.1%] · edge +8.3% · P(+) 82% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT24CLBTOR-2`
- Columbus Crew vs Toronto FC · away team total over 1.5 · NO @ 0.6600 · fair 74.7% [62.8%–85.3%] · edge +7.1% · P(+) 80% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT24CLBTOR-TOR2`
- Columbus Crew vs Toronto FC · Total goals over 0.5 · NO @ 0.0400 · fair 7.4% [3.1%–11.8%] · edge +3.1% · P(+) 80% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT24CLBTOR-1`

## Expressions removed by the reducer (5)
- `KXMLSTEAMTOTAL-26OCT24CLBTOR-TOR1` no: dominated by KXMLSBTTS-26OCT24CLBTOR-BTTS/no (corr +0.81)
- `KXMLSTOTAL-26OCT24CLBTOR-3` no: redundant with KXMLSTOTAL-26OCT24CLBTOR-4/no (corr +0.64); best expression kept
- `KXMLSTOTAL-26OCT24CLBTOR-5` no: dominated by KXMLSTOTAL-26OCT24CLBTOR-4/no (corr +0.65)
- `KXMLSTOTAL-26OCT24CLBTOR-6` no: dominated by KXMLSTOTAL-26OCT24CLBTOR-4/no (corr +0.42)
- `KXMLSSCORE-26OCT24CLBTOR-CLB0TOR0` yes: redundant with KXMLSTOTAL-26OCT24CLBTOR-1/no (corr +1.00); best expression kept

## Events
- Columbus Crew vs Toronto FC (Major League Soccer) 2026-10-24T19:30:00Z · markets 77/77 evaluated · lineups unknown · xG 1.83-0.97 · 1X2 56%/23%/20%
- Vitória vs Athletico Paranaense (Brasileirão Série A) 2026-10-24T19:30:00Z · markets 14/14 evaluated · lineups unknown · xG 1.37-1.36 · 1X2 37%/27%/37%
- Mirassol vs São Paulo (Brasileirão Série A) 2026-10-24T19:30:00Z · markets 14/14 evaluated · lineups unknown · xG 1.37-0.88 · 1X2 47%/29%/24%
- Internacional vs Botafogo (Brasileirão Série A) 2026-10-24T19:30:00Z · markets 14/14 evaluated · lineups unknown · xG 1.37-1.00 · 1X2 44%/28%/27%
