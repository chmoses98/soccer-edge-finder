# RUN SOCCER — 2026-11-19
Run `run-20261119T144019Z-47e7bc` generated 2026-11-19T14:40:22.576065Z · filters: {'leagues': [], 'games': ['fx:ger.bundesliga:2026-27:ger.elversberg:ger.freiburg', 'fx:ger.bundesliga:2026-27:ger.frankfurt:ger.hoffenheim', 'fx:ger.bundesliga:2026-27:ger.gladbach:ger.dortmund', 'fx:ger.bundesliga:2026-27:ger.leverkusen:ger.paderborn', 'fx:ger.bundesliga:2026-27:ger.union_berlin:ger.leipzig'], 'window_hours': 49, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4811** (discovery complete: True)
- contracts evaluated: 15 · excluded mechanically: 1942 · unsupported/unknown: 2854
- **unaccounted contracts: 0**
- by disposition: priced=15, unknown_family=4, unsupported_family=2850, unmapped_event=812, unmapped_team=51, no_fixture=72, filtered_by_operator=1007
- competitions discovered: ALEAGUEW, APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGAW, CANPL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, ENGWLEAGUECUP, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SCOCHAMP, SERIEA, SOCCER, SUPERETTAN, SUPERLIG, SVK1L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-19T14:40:19.374739Z; market_observed_at: 2026-11-19T14:36:50.647133Z; fixtures_observed_at: 2026-11-19T10:54:38.461471Z; results_observed_at: 2026-11-19T10:54:31.494943Z; model_fitted_at: 2026-11-19T14:40:17.753771Z; temporal_guard: {'decision_time': '2026-11-19T14:40:19.374739Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-19T10:54:38.461471Z', 'market_snapshots': '2026-11-19T14:40:14.624424Z', 'reference_odds': '2026-11-19T10:54:40.508852Z', 'results': '2026-11-19T14:40:19.179304Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (3)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- SV Elversberg vs SC Freiburg · Result: away · NO @ 0.5200 · fair 72.4% [48.6%–91.7%] · edge +18.6% · P(+) 85% · RESEARCH_ONLY · `KXBUNDESLIGAGAME-26NOV21SVESCF-SCF`
- Union Berlin vs RB Leipzig · Result: away · NO @ 0.3700 · fair 54.8% [31.9%–75.2%] · edge +16.1% · P(+) 84% · RESEARCH_ONLY · `KXBUNDESLIGAGAME-26NOV21UNIRBL-RBL`
- Bayer Leverkusen vs SC Paderborn 07 · Result: draw · YES @ 0.1400 · fair 23.6% [11.4%–34.2%] · edge +8.8% · P(+) 83% · RESEARCH_ONLY · `KXBUNDESLIGAGAME-26NOV21LEVPAD-TIE`

## Expressions removed by the reducer (2)
- `KXBUNDESLIGAGAME-26NOV21UNIRBL-UNI` yes: dominated by KXBUNDESLIGAGAME-26NOV21UNIRBL-RBL/no (corr +0.63)
- `KXBUNDESLIGAGAME-26NOV21SVESCF-SVE` yes: redundant with KXBUNDESLIGAGAME-26NOV21SVESCF-SCF/no (corr +0.63); best expression kept

## Events
- Bayer Leverkusen vs SC Paderborn 07 (Bundesliga) 2026-11-21T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.78-0.68 · 1X2 61%/23%/16%
- Eintracht Frankfurt vs TSG Hoffenheim (Bundesliga) 2026-11-21T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 2.38-1.48 · 1X2 56%/19%/25%
- Union Berlin vs RB Leipzig (Bundesliga) 2026-11-21T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.44-1.76 · 1X2 32%/22%/45%
- Borussia Mönchengladbach vs Borussia Dortmund (Bundesliga) 2026-11-21T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.10-1.81 · 1X2 24%/22%/53%
- SV Elversberg vs SC Freiburg (Bundesliga) 2026-11-21T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.93-1.29 · 1X2 51%/21%/28%
