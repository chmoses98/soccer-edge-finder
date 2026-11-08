# RUN SOCCER — 2026-11-08
Run `run-20261108T101335Z-17c9c8` generated 2026-11-08T10:13:42.149560Z · filters: {'leagues': [], 'games': ['fx:eng.premier_league:2026-27:eng.brighton:eng.brentford', 'fx:eng.premier_league:2026-27:eng.crystal_palace:eng.liverpool', 'fx:eng.premier_league:2026-27:eng.ipswich:eng.bournemouth', 'fx:eng.premier_league:2026-27:eng.man_united:eng.aston_villa', 'fx:eng.premier_league:2026-27:eng.sunderland:eng.chelsea', 'fx:esp.la_liga:2026-27:esp.atletico_madrid:esp.barcelona', 'fx:esp.la_liga:2026-27:esp.celta_vigo:esp.levante', 'fx:esp.la_liga:2026-27:esp.elche:esp.real_betis', 'fx:esp.la_liga:2026-27:esp.real_sociedad:esp.rayo_vallecano', 'fx:esp.la_liga:2026-27:esp.villarreal:esp.getafe', 'fx:fra.ligue_1:2026-27:fra.angers:fra.nice', 'fx:fra.ligue_1:2026-27:fra.brest:fra.lyon', 'fx:fra.ligue_1:2026-27:fra.le_havre:fra.lorient', 'fx:fra.ligue_1:2026-27:fra.le_mans:fra.monaco', 'fx:fra.ligue_1:2026-27:fra.lens:fra.marseille', 'fx:fra.ligue_1:2026-27:fra.rennes:fra.lille', 'fx:ger.bundesliga:2026-27:ger.freiburg:ger.union_berlin', 'fx:ger.bundesliga:2026-27:ger.hoffenheim:ger.schalke', 'fx:ger.bundesliga:2026-27:ger.koln:ger.leverkusen', 'fx:ita.serie_a:2026-27:ita.fiorentina:ita.juventus', 'fx:ita.serie_a:2026-27:ita.genoa:ita.milan', 'fx:ita.serie_a:2026-27:ita.inter:ita.como', 'fx:ita.serie_a:2026-27:ita.monza:ita.atalanta', 'fx:ita.serie_a:2026-27:ita.napoli:ita.lazio'], 'window_hours': 11, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4776** (discovery complete: True)
- contracts evaluated: 57 · excluded mechanically: 1746 · unsupported/unknown: 2973
- **unaccounted contracts: 0**
- by disposition: priced=57, started=15, unknown_family=3, unsupported_family=2970, unmapped_event=750, unmapped_team=62, no_fixture=140, filtered_by_operator=779
- competitions discovered: APFDDH, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGAW, CHLLDP, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EFLTROPHY, EKSTRAKLASA, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INTLFRIENDLY, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAFF, SERIEA, SOCCER, SUPERLIG, SVK1L, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, UKRPL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-08T10:13:35.229509Z; market_observed_at: 2026-11-08T10:10:20.515927Z; fixtures_observed_at: 2026-11-08T10:13:31.260778Z; results_observed_at: 2026-11-08T10:13:24.263420Z; model_fitted_at: 2026-11-08T10:13:31.821396Z; temporal_guard: {'decision_time': '2026-11-08T10:13:35.229509Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-08T10:13:31.260778Z', 'market_snapshots': '2026-11-08T10:13:23.507982Z', 'reference_odds': '2026-11-08T10:13:33.297071Z', 'results': '2026-11-08T10:13:33.103292Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (4)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Angers vs Nice · Result: away · NO @ 0.5400 · fair 74.1% [58.6%–87.0%] · edge +18.4% · P(+) 94% · RESEARCH_ONLY · `KXLIGUE1GAME-26NOV08ANGNIC-NIC`
- Angers vs Nice · Result: home · YES @ 0.2700 · fair 46.2% [28.2%–63.9%] · edge +17.8% · P(+) 90% · RESEARCH_ONLY · `KXLIGUE1GAME-26NOV08ANGNIC-ANG`
- Elche vs Real Betis · Result: away · NO @ 0.5000 · fair 63.5% [47.6%–78.9%] · edge +11.7% · P(+) 83% · RESEARCH_ONLY · `KXLALIGAGAME-26NOV08ELCRBB-RBB`
- Le Mans vs AS Monaco · Result: home · YES @ 0.1900 · fair 36.1% [14.6%–59.7%] · edge +16.0% · P(+) 82% · RESEARCH_ONLY · `KXLIGUE1GAME-26NOV08MANASM-MAN`

## Expressions removed by the reducer (1)
- `KXLALIGAGAME-26NOV08ELCRBB-ELC` yes: redundant with KXLALIGAGAME-26NOV08ELCRBB-RBB/no (corr +0.60); best expression kept

## Events
- Elche vs Real Betis (La Liga) 2026-11-08T12:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.46-1.40 · 1X2 39%/25%/37%
- Real Sociedad vs Rayo Vallecano (La Liga) 2026-11-08T12:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.85-1.26 · 1X2 51%/22%/27%
- Celta Vigo vs Levante (La Liga) 2026-11-08T12:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.75-1.02 · 1X2 54%/24%/23%
- Villarreal vs Getafe (La Liga) 2026-11-08T12:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.66-0.78 · 1X2 57%/25%/18%
- Atlético Madrid vs FC Barcelona (La Liga) 2026-11-08T12:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.63-1.89 · 1X2 34%/21%/45%
- 1. FC Köln vs Bayer Leverkusen (Bundesliga) 2026-11-08T14:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.44-1.60 · 1X2 35%/24%/42%
- SC Freiburg vs Union Berlin (Bundesliga) 2026-11-08T16:30:00Z · markets 3/3 evaluated · lineups unknown · xG 2.66-0.90 · 1X2 73%/16%/12%
- TSG Hoffenheim vs Schalke 04 (Bundesliga) 2026-11-08T18:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.93-1.03 · 1X2 56%/22%/22%
- Napoli vs Lazio (Serie A) 2026-11-08T11:30:00Z · markets 3/3 evaluated · lineups unknown · xG 1.32-0.94 · 1X2 45%/28%/27%
- Genoa vs AC Milan (Serie A) 2026-11-08T14:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.01-1.34 · 1X2 29%/27%/44%
- Monza vs Atalanta (Serie A) 2026-11-08T14:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.24-1.59 · 1X2 31%/24%/45%
- Inter Milan vs Como (Serie A) 2026-11-08T17:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.99-1.33 · 1X2 52%/21%/27%
- Fiorentina vs Juventus (Serie A) 2026-11-08T19:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.08-1.44 · 1X2 29%/26%/45%
- Rennes vs Lille (Ligue 1) 2026-11-08T14:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.41-1.23 · 1X2 41%/26%/33%
- Angers vs Nice (Ligue 1) 2026-11-08T16:15:00Z · markets 3/3 evaluated · lineups unknown · xG 1.34-0.90 · 1X2 46%/28%/26%
- Brest vs Lyon (Ligue 1) 2026-11-08T16:15:00Z · markets 3/3 evaluated · lineups unknown · xG 1.34-1.46 · 1X2 35%/25%/40%
- Le Havre vs Lorient (Ligue 1) 2026-11-08T16:15:00Z · markets 3/3 evaluated · lineups unknown · xG 1.31-1.06 · 1X2 42%/28%/31%
- Le Mans vs AS Monaco (Ligue 1) 2026-11-08T16:15:00Z · markets 3/3 evaluated · lineups unknown · xG 1.46-1.57 · 1X2 36%/24%/40%
- Lens vs Marseille (Ligue 1) 2026-11-08T19:45:00Z · markets 3/3 evaluated · lineups unknown · xG 1.96-1.15 · 1X2 55%/22%/23%
