# RUN SOCCER — 2026-09-29
Run `run-20260929T012637Z-1a0ba3` generated 2026-09-29T01:26:54.156235Z · filters: {'leagues': [], 'games': [], 'window_hours': 48, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **6401** (discovery complete: True)
- contracts evaluated: 797 · excluded mechanically: 2472 · unsupported/unknown: 3132
- **unaccounted contracts: 0**
- by disposition: priced=797, started=43, ambiguous_ownership=42, unsupported_family=3132, unmapped_event=962, unmapped_team=246, no_fixture=176, out_of_window=993, unpriceable=10
- competitions discovered: AFCCL, APFDDH, ARGNACB, ARGPREMDIV, BELGIANPL, BRASILEIRO, BRASILEIROB, BRASILEIROC, BUNDESLIGA, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EERSTEDIV, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, ETTAN, EWSL, FA, FIFAW, INTLFRIENDLY, ISRNL, J2LEAGUE, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAMX, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, SERIEA, SERIEAW, SERIEC, SOCCER, SUPERLIG, SVK2L, SVKCUP, TACAPORT, THAIL1, TWEEDEDIV, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, USLCUP, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-09-29T01:26:37.346523Z; market_observed_at: 2026-09-29T01:13:31.565347Z; fixtures_observed_at: 2026-09-29T01:10:00.230819Z; results_observed_at: 2026-09-29T01:09:52.747492Z; model_fitted_at: 2026-09-29T01:10:00.507889Z; temporal_guard: {'decision_time': '2026-09-29T01:26:37.346523Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-09-29T01:10:00.230819Z', 'market_snapshots': '2026-09-29T01:26:36.109081Z', 'reference_odds': '2026-09-29T01:26:36.256457Z', 'results': '2026-09-29T01:10:01.446745Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (9)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- New York Red Bulls vs St. Louis City SC · away team total over 1.5 · NO @ 0.4400 · fair 65.8% [48.8%–81.2%] · edge +20.1% · P(+) 94% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26SEP30NYRBSTL-STL2`
- New York Red Bulls vs St. Louis City SC · Total goals over 3.5 · NO @ 0.5400 · fair 74.2% [57.8%–88.2%] · edge +18.4% · P(+) 93% · RESEARCH_ONLY · `KXMLSTOTAL-26SEP30NYRBSTL-4`
- New York Red Bulls vs St. Louis City SC · away wins by more than 1.5 · NO @ 0.7000 · fair 86.0% [74.9%–95.1%] · edge +14.6% · P(+) 94% · RESEARCH_ONLY · `KXMLSSPREAD-26SEP30NYRBSTL-STL2`
- New York Red Bulls vs St. Louis City SC · Result: away · NO @ 0.5000 · fair 66.5% [50.8%–81.2%] · edge +14.7% · P(+) 89% · RESEARCH_ONLY · `KXMLSGAME-26SEP30NYRBSTL-STL`
- New York Red Bulls vs St. Louis City SC · away wins by more than 2.5 · NO @ 0.8700 · fair 95.2% [89.9%–99.1%] · edge +7.4% · P(+) 95% · RESEARCH_ONLY · `KXMLSSPREAD-26SEP30NYRBSTL-STL3`
- New York Red Bulls vs St. Louis City SC · First-half total goals over 1.5 · NO @ 0.5500 · fair 67.2% [53.8%–79.2%] · edge +10.5% · P(+) 87% · RESEARCH_ONLY · `KXMLS1HTOTAL-26SEP30NYRBSTL-2`
- New York Red Bulls vs St. Louis City SC · First-half total goals over 0.5 · NO @ 0.2200 · fair 31.8% [20.8%–43.2%] · edge +8.6% · P(+) 83% · RESEARCH_ONLY · `KXMLS1HTOTAL-26SEP30NYRBSTL-1`
- New York Red Bulls vs St. Louis City SC · Total goals over 0.5 · NO @ 0.0400 · fair 9.1% [2.9%–16.1%] · edge +4.8% · P(+) 83% · RESEARCH_ONLY · `KXMLSTOTAL-26SEP30NYRBSTL-1`
- New York Red Bulls vs St. Louis City SC · First-half result: away · NO @ 0.6500 · fair 73.4% [61.8%–83.2%] · edge +6.8% · P(+) 81% · RESEARCH_ONLY · `KXMLS1H-26SEP30NYRBSTL-STL`

## Expressions removed by the reducer (5)
- `KXMLSTOTAL-26SEP30NYRBSTL-5` no: redundant with KXMLSTOTAL-26SEP30NYRBSTL-4/no (corr +0.64); best expression kept
- `KXMLSTOTAL-26SEP30NYRBSTL-3` no: redundant with KXMLSTOTAL-26SEP30NYRBSTL-4/no (corr +0.64); best expression kept
- `KXMLSTOTAL-26SEP30NYRBSTL-2` no: dominated by KXMLSTOTAL-26SEP30NYRBSTL-4/no (corr +0.38)
- `KXMLSTOTAL-26SEP30NYRBSTL-6` no: redundant with KXMLSTOTAL-26SEP30NYRBSTL-4/no (corr +0.40); best expression kept
- `KXMLSBTTS-26SEP30NYRBSTL-BTTS` no: dominated by KXMLSTOTAL-26SEP30NYRBSTL-4/no (corr +0.46)

## Events
- New York Red Bulls vs St. Louis City SC (Major League Soccer) 2026-09-30T23:30:00Z · markets 32/32 evaluated · lineups unknown · xG 1.33-1.22 · 1X2 38%/28%/34%
- Slovakia vs Kazakhstan (UEFA Nations League) 2026-09-29T18:45:00Z · markets 61/62 evaluated · lineups unknown · xG 1.79-1.05 · 1X2 53%/24%/23%
- San Marino vs Albania (UEFA Nations League) 2026-09-29T18:45:00Z · markets 61/62 evaluated · lineups unknown · xG 0.98-1.90 · 1X2 20%/23%/57%
- Slovenia vs North Macedonia (UEFA Nations League) 2026-09-29T18:45:00Z · markets 61/62 evaluated · lineups unknown · xG 1.57-0.68 · 1X2 56%/27%/17%
- Scotland vs Switzerland (UEFA Nations League) 2026-09-29T18:45:00Z · markets 61/62 evaluated · lineups unknown · xG 1.37-1.24 · 1X2 39%/27%/34%
- Luxembourg vs Iceland (UEFA Nations League) 2026-09-29T18:45:00Z · markets 61/62 evaluated · lineups unknown · xG 1.80-0.87 · 1X2 57%/24%/19%
- Spain vs Croatia (UEFA Nations League) 2026-09-29T18:45:00Z · markets 61/62 evaluated · lineups unknown · xG 2.21-1.25 · 1X2 57%/21%/22%
- Czechia vs England (UEFA Nations League) 2026-09-29T18:45:00Z · markets 61/62 evaluated · lineups unknown · xG 1.65-1.35 · 1X2 44%/25%/32%
- Bulgaria vs Estonia (UEFA Nations League) 2026-09-29T18:45:00Z · markets 61/62 evaluated · lineups unknown · xG 1.41-1.35 · 1X2 38%/26%/36%
- Moldova vs Faroe Islands (UEFA Nations League) 2026-09-29T16:00:00Z · markets 61/62 evaluated · lineups unknown · xG 1.21-1.30 · 1X2 34%/28%/38%
- Finland vs Belarus (UEFA Nations League) 2026-09-29T16:00:00Z · markets 61/62 evaluated · lineups unknown · xG 2.61-0.98 · 1X2 68%/18%/14%
- Anguilla vs Aruba (CONCACAF Nations League) 2026-09-29T23:00:00Z · markets 23/23 evaluated · lineups unknown · xG 0.76-1.56 · 1X2 19%/27%/54%
- French Guiana vs Sint Maarten (CONCACAF Nations League) 2026-09-29T21:00:00Z · markets 23/23 evaluated · lineups unknown · xG 1.03-1.01 · 1X2 34%/32%/34%
- Guatemala vs El Salvador (CONCACAF Nations League) 2026-09-29T02:00:00Z · markets 23/23 evaluated · lineups unknown · xG 1.43-1.55 · 1X2 35%/25%/41%
- Lithuania vs Andorra (International Friendlies) 2026-09-30T16:00:00Z · markets 14/14 evaluated · lineups unknown · xG 1.41-0.70 · 1X2 52%/29%/19%
- United States vs Chile (International Friendlies) 2026-09-30T00:00:00Z · markets 23/23 evaluated · lineups unknown · xG 2.26-1.31 · 1X2 56%/20%/23%
- Mexico vs Peru (International Friendlies) 2026-09-30T02:30:00Z · markets 23/23 evaluated · lineups unknown · xG 1.45-0.83 · 1X2 50%/28%/22%
- Australia vs Brazil (International Friendlies) 2026-09-29T10:00:00Z · markets 23/23 evaluated · lineups unknown · xG 1.43-1.27 · 1X2 40%/27%/33%
- Belize vs St. Vincent and the Grenadines (CONCACAF Nations League) 2026-09-30T02:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.87-1.21 · 1X2 50%/23%/26%
