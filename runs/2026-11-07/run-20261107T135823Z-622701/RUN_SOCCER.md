# RUN SOCCER — 2026-11-07
Run `run-20261107T135823Z-622701` generated 2026-11-07T13:58:27.699485Z · filters: {'leagues': [], 'games': ['fx:eng.premier_league:2026-27:eng.arsenal:eng.hull:matchday_10', 'fx:eng.premier_league:2026-27:eng.brighton:eng.brentford:matchday_10', 'fx:eng.premier_league:2026-27:eng.crystal_palace:eng.liverpool:matchday_10', 'fx:eng.premier_league:2026-27:eng.everton:eng.coventry:matchday_10', 'fx:eng.premier_league:2026-27:eng.fulham:eng.newcastle:matchday_10', 'fx:eng.premier_league:2026-27:eng.ipswich:eng.bournemouth:matchday_10', 'fx:eng.premier_league:2026-27:eng.leeds:eng.tottenham:matchday_10', 'fx:eng.premier_league:2026-27:eng.man_united:eng.aston_villa:matchday_10', 'fx:eng.premier_league:2026-27:eng.nottm_forest:eng.man_city:matchday_10', 'fx:eng.premier_league:2026-27:eng.sunderland:eng.chelsea:matchday_10'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **6583** (discovery complete: True)
- contracts evaluated: 27 · excluded mechanically: 3583 · unsupported/unknown: 2973
- **unaccounted contracts: 0**
- by disposition: priced=27, unknown_family=3, unsupported_family=2970, unmapped_event=1250, unmapped_team=98, no_fixture=132, filtered_by_operator=2103
- competitions discovered: APFDDH, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EFLTROPHY, EKSTRAKLASA, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, INTLFRIENDLY, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAFF, SERIEA, SOCCER, SUPERLIG, SVK1L, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, UKRPL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-07T13:58:23.368037Z; market_observed_at: 2026-11-07T13:55:00.066303Z; fixtures_observed_at: 2026-11-07T09:59:26.465634Z; results_observed_at: 2026-11-07T09:59:19.593622Z; model_fitted_at: 2026-11-07T13:58:21.784095Z; temporal_guard: {'decision_time': '2026-11-07T13:58:23.368037Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-07T09:59:26.465634Z', 'market_snapshots': '2026-11-07T13:58:13.221254Z', 'reference_odds': '2026-11-07T09:59:28.356634Z', 'results': '2026-11-07T13:58:23.123809Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (8)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Leeds United vs Tottenham Hotspur · Result: home · YES @ 0.2400 · fair 61.9% [44.3%–78.9%] · edge +36.6% · P(+) 100% · RESEARCH_ONLY · `KXEPLGAME-26NOV07LEETOT-LEE`
- Arsenal vs Hull City · Result: home · NO @ 0.1400 · fair 45.9% [24.1%–67.9%] · edge +31.1% · P(+) 97% · RESEARCH_ONLY · `KXEPLGAME-26NOV07ARSHUL-ARS`
- Crystal Palace vs Liverpool · Result: away · NO @ 0.3800 · fair 57.9% [39.7%–75.8%] · edge +18.2% · P(+) 90% · RESEARCH_ONLY · `KXEPLGAME-26NOV08CRYLFC-LFC`
- Arsenal vs Hull City · Result: away · YES @ 0.0400 · fair 19.6% [6.9%–35.1%] · edge +15.4% · P(+) 95% · RESEARCH_ONLY · `KXEPLGAME-26NOV07ARSHUL-HUL`
- Sunderland vs Chelsea · Result: home · YES @ 0.2600 · fair 46.0% [27.6%–65.2%] · edge +18.7% · P(+) 90% · RESEARCH_ONLY · `KXEPLGAME-26NOV08SUNCFC-SUN`
- Leeds United vs Tottenham Hotspur · Result: away · NO @ 0.7200 · fair 83.6% [72.6%–93.3%] · edge +10.2% · P(+) 88% · RESEARCH_ONLY · `KXEPLGAME-26NOV07LEETOT-TOT`
- Nottingham Forest vs Manchester City · Result: away · NO @ 0.4300 · fair 59.5% [41.5%–76.4%] · edge +14.8% · P(+) 85% · RESEARCH_ONLY · `KXEPLGAME-26NOV07NFOMCI-MCI`
- Nottingham Forest vs Manchester City · Result: home · YES @ 0.2000 · fair 34.3% [18.3%–52.3%] · edge +13.1% · P(+) 84% · RESEARCH_ONLY · `KXEPLGAME-26NOV07NFOMCI-NFO`

## Expressions removed by the reducer (4)
- `KXEPLGAME-26NOV08CRYLFC-CRY` yes: dominated by KXEPLGAME-26NOV08CRYLFC-LFC/no (corr +0.61)
- `KXEPLGAME-26NOV08SUNCFC-CFC` no: dominated by KXEPLGAME-26NOV08SUNCFC-SUN/yes (corr +0.61)
- `KXEPLGAME-26NOV07ARSHUL-TIE` yes: dominated by KXEPLGAME-26NOV07ARSHUL-ARS/no (corr +0.65)
- `KXEPLGAME-26NOV07LEETOT-TIE` no: redundant with KXEPLGAME-26NOV07LEETOT-LEE/yes (corr +0.67); best expression kept

## Events
- Brighton & Hove Albion vs Brentford (Premier League) 2026-11-07T15:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.82-1.10 · 1X2 53%/23%/24%
- Crystal Palace vs Liverpool (Premier League) 2026-11-07T15:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.35-1.55 · 1X2 34%/24%/42%
- Ipswich Town vs Bournemouth (Premier League) 2026-11-07T15:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.32-1.50 · 1X2 34%/25%/41%
- Manchester United vs Aston Villa (Premier League) 2026-11-07T15:00:00Z · markets 3/3 evaluated · lineups unknown · xG 2.03-1.10 · 1X2 57%/21%/22%
- Sunderland vs Chelsea (Premier League) 2026-11-07T15:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.69-1.31 · 1X2 46%/23%/31%
- Arsenal vs Hull City (Premier League) 2026-11-07T15:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.53-0.74 · 1X2 54%/26%/20%
- Fulham vs Newcastle United (Premier League) 2026-11-07T15:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.52-1.26 · 1X2 43%/25%/32%
- Leeds United vs Tottenham Hotspur (Premier League) 2026-11-07T15:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.93-0.82 · 1X2 62%/22%/16%
- Nottingham Forest vs Manchester City (Premier League) 2026-11-07T15:00:00Z · markets 3/3 evaluated · lineups unknown · xG 1.28-1.42 · 1X2 34%/25%/40%
