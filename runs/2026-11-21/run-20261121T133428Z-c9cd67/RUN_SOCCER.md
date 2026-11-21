# RUN SOCCER — 2026-11-21
Run `run-20261121T133428Z-c9cd67` generated 2026-11-21T13:34:31.447409Z · filters: {'leagues': [], 'games': ['fx:ger.bundesliga:2026-27:ger.elversberg:ger.freiburg:matchday_10', 'fx:ger.bundesliga:2026-27:ger.frankfurt:ger.hoffenheim:matchday_10', 'fx:ger.bundesliga:2026-27:ger.gladbach:ger.dortmund:matchday_10', 'fx:ger.bundesliga:2026-27:ger.leverkusen:ger.paderborn:matchday_10', 'fx:ger.bundesliga:2026-27:ger.union_berlin:ger.leipzig:matchday_10'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **6076** (discovery complete: True)
- contracts evaluated: 15 · excluded mechanically: 3067 · unsupported/unknown: 2994
- **unaccounted contracts: 0**
- by disposition: priced=15, ambiguous_ownership=18, unknown_family=4, unsupported_family=2990, unmapped_event=1510, unmapped_team=14, no_fixture=69, filtered_by_operator=1456
- competitions discovered: AFCCL2, ALEAGUEW, APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGAW, CANPL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, ENGWLEAGUECUP, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAPSL, SCOCHAMP, SERIEA, SOCCER, SUPERETTAN, SUPERLIG, SVK1L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-21T13:34:28.655329Z; market_observed_at: 2026-11-21T13:30:33.154767Z; fixtures_observed_at: 2026-11-21T12:46:43.739564Z; results_observed_at: 2026-11-21T09:41:08.760614Z; model_fitted_at: 2026-11-21T13:34:26.950547Z; temporal_guard: {'decision_time': '2026-11-21T13:34:28.655329Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-21T12:46:43.739564Z', 'market_snapshots': '2026-11-21T13:34:15.211508Z', 'reference_odds': '2026-11-21T09:41:17.240713Z', 'results': '2026-11-21T13:34:28.426230Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (3)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Union Berlin vs RB Leipzig · Result: away · NO @ 0.3600 · fair 54.8% [31.7%–75.2%] · edge +17.2% · P(+) 84% · RESEARCH_ONLY · `KXBUNDESLIGAGAME-26NOV21UNIRBL-RBL`
- SV Elversberg vs SC Freiburg · Result: home · YES @ 0.2700 · fair 50.8% [24.2%–79.2%] · edge +22.5% · P(+) 84% · RESEARCH_ONLY · `KXBUNDESLIGAGAME-26NOV21SVESCF-SVE`
- Bayer Leverkusen vs SC Paderborn 07 · Result: draw · YES @ 0.1500 · fair 23.6% [11.3%–34.2%] · edge +7.7% · P(+) 81% · RESEARCH_ONLY · `KXBUNDESLIGAGAME-26NOV21LEVPAD-TIE`

## Expressions removed by the reducer (2)
- `KXBUNDESLIGAGAME-26NOV21UNIRBL-UNI` yes: redundant with KXBUNDESLIGAGAME-26NOV21UNIRBL-RBL/no (corr +0.63); best expression kept
- `KXBUNDESLIGAGAME-26NOV21SVESCF-SCF` no: dominated by KXBUNDESLIGAGAME-26NOV21SVESCF-SVE/yes (corr +0.63)

## Events
- Bayer Leverkusen vs SC Paderborn 07 (Bundesliga) 2026-11-21T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.78-0.69 · 1X2 61%/23%/16%
- Eintracht Frankfurt vs TSG Hoffenheim (Bundesliga) 2026-11-21T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 2.38-1.48 · 1X2 56%/19%/25%
- Union Berlin vs RB Leipzig (Bundesliga) 2026-11-21T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.44-1.76 · 1X2 33%/22%/45%
- Borussia Mönchengladbach vs Borussia Dortmund (Bundesliga) 2026-11-21T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.10-1.81 · 1X2 24%/23%/53%
- SV Elversberg vs SC Freiburg (Bundesliga) 2026-11-21T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.92-1.28 · 1X2 51%/21%/28%
