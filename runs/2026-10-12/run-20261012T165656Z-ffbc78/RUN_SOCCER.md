# RUN SOCCER — 2026-10-12
Run `run-20261012T165656Z-ffbc78` generated 2026-10-12T16:57:15.518908Z · filters: {'leagues': [], 'games': [], 'window_hours': 48, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **8796** (discovery complete: True)
- contracts evaluated: 336 · excluded mechanically: 5243 · unsupported/unknown: 3217
- **unaccounted contracts: 0**
- by disposition: priced=336, started=80, ambiguous_ownership=63, unknown_family=151, unsupported_family=3066, unmapped_event=1483, unmapped_team=840, no_fixture=1328, out_of_window=1446, unpriceable=3
- competitions discovered: AFCCL, ALEAGUE, ALLSVENSKAN, APFDDH, ARGNACB, ARGPREMDIV, BELGIANPL, BOLPDIV, BRASILEIRO, BRASILEIROB, BRASILEIROC, BUNDESLIGA, BUNDESLIGA2, CANPL, CHLLDP, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, CZEFL, CZEFNL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EERSTEDIV, EFL, EFLCHAMPIONSHIP, EFLL1, EGYPL, EKSTRAKLASA, ELITESERIEN, EPL, EPL2H, EREDIVISIE, ETTAN, FA, FIFAW, GER3L, HNL, IDNSL, ISRNL, ISRNLCUP, ISRPL, JLEAGUE, KLEAGUE, KNVB, LALIGA, LALIGA2, LALIGA2H, LIGAEXP, LIGAMX, LIGAPORTUGAL, LIGUE1, LIGUE2, LVAVIR, MLS, MLSEAST, MLSWEST, MYSL, NWSL, PERLIGA1, PREMIERLEAGUE, SAUDIPL, SCOTTISHPREM, SERIEA, SERIEA2H, SERIEB, SERIEC, SGPPL, SLGREECE, SOCCER, SRBSL, SUPERLIG, SVK2L, SVKCUP, SVNPL, TACAPORT, TFF1LIG, THAIL1, UAEPL, UCL, UCL2H, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, USOPENCUP, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-12T16:56:56.005007Z; market_observed_at: 2026-10-12T16:42:51.167246Z; fixtures_observed_at: 2026-10-12T16:42:49.306017Z; results_observed_at: 2026-10-12T16:42:41.536129Z; model_fitted_at: 2026-10-12T16:42:49.849990Z; temporal_guard: {'decision_time': '2026-10-12T16:56:56.005007Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-12T16:42:49.306017Z', 'market_snapshots': '2026-10-12T16:56:54.443001Z', 'reference_odds': '2026-10-12T16:56:54.657486Z', 'results': '2026-10-12T16:42:51.156702Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (10)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Coventry City vs Newcastle United · btts · NO @ 0.3800 · fair 57.5% [40.3%–73.1%] · edge +17.8% · P(+) 91% · RESEARCH_ONLY · `KXEPLBTTS-26OCT12COVNEW-BTTS`
- Red Bull Bragantino vs Cruzeiro · btts · NO @ 0.3900 · fair 50.9% [38.1%–63.7%] · edge +10.2% · P(+) 85% · RESEARCH_ONLY · `KXBRASILEIROBTTS-26OCT12RBBCRU-BTTS`
- Torino vs Udinese · Result: draw · NO @ 0.6900 · fair 75.3% [69.6%–80.5%] · edge +4.8% · P(+) 87% · RESEARCH_ONLY · `KXSERIEAGAME-26OCT12TORUDI-TIE`
- Coventry City vs Newcastle United · First half: both teams to score · NO @ 0.7700 · fair 85.1% [74.9%–94.1%] · edge +6.9% · P(+) 83% · RESEARCH_ONLY · `KXEPL1HBTTS-26OCT12COVNEW-BTTS`
- Levante vs Sevilla · Result: draw · NO @ 0.7000 · fair 75.9% [70.3%–81.4%] · edge +4.5% · P(+) 84% · RESEARCH_ONLY · `KXLALIGAGAME-26OCT12LEVSEV-TIE`
- Coventry City vs Newcastle United · Exact score 2-2 (home-away) · NO @ 0.9400 · fair 96.5% [94.2%–98.4%] · edge +2.1% · P(+) 88% · RESEARCH_ONLY · `KXEPLSCORE-26OCT12COVNEW-COV2NEW2`
- Coventry City vs Newcastle United · First-half total goals over 0.5 · NO @ 0.2600 · fair 37.0% [22.8%–51.2%] · edge +9.6% · P(+) 80% · RESEARCH_ONLY · `KXEPL1HTOTAL-26OCT12COVNEW-1`
- Red Bull Bragantino vs Cruzeiro · home team total over 1.5 · NO @ 0.5000 · fair 62.0% [45.0%–78.1%] · edge +10.2% · P(+) 80% · RESEARCH_ONLY · `KXBRASILEIROTEAMTOTAL-26OCT12RBBCRU-RBB2`
- Levante vs Sevilla · home wins by more than 2.5 · YES @ 0.0500 · fair 11.9% [4.1%–22.5%] · edge +6.6% · P(+) 81% · RESEARCH_ONLY · `KXLALIGASPREAD-26OCT12LEVSEV-LEV3`
- Coventry City vs Newcastle United · Exact score 0-1 (home-away) · YES @ 0.0800 · fair 13.5% [6.4%–20.6%] · edge +4.9% · P(+) 81% · RESEARCH_ONLY · `KXEPLSCORE-26OCT12COVNEW-COV0NEW1`

## Expressions removed by the reducer (11)
- `KXLALIGASPREAD-26OCT12LEVSEV-LEV2` yes: redundant with KXLALIGASPREAD-26OCT12LEVSEV-LEV3/yes (corr +0.62); best expression kept
- `KXLALIGATEAMTOTAL-26OCT12LEVSEV-LEV2` yes: redundant with KXLALIGASPREAD-26OCT12LEVSEV-LEV3/yes (corr +0.38); best expression kept
- `KXLALIGASCORE-26OCT12LEVSEV-LEV1SEV1` no: redundant with KXLALIGAGAME-26OCT12LEVSEV-TIE/no (corr +0.62); best expression kept
- `KXSERIEASCORE-26OCT12TORUDI-TOR1UDI1` no: redundant with KXSERIEAGAME-26OCT12TORUDI-TIE/no (corr +0.62); best expression kept
- `KXEPLTOTAL-26OCT12COVNEW-3` no: dominated by KXEPLBTTS-26OCT12COVNEW-BTTS/no (corr +0.58)
- `KXEPLTOTAL-26OCT12COVNEW-4` no: dominated by KXEPLBTTS-26OCT12COVNEW-BTTS/no (corr +0.45)
- `KXEPLTOTAL-26OCT12COVNEW-2` no: dominated by KXEPLBTTS-26OCT12COVNEW-BTTS/no (corr +0.62)
- `KXEPLTOTAL-26OCT12COVNEW-5` no: dominated by KXEPLBTTS-26OCT12COVNEW-BTTS/no (corr +0.32)
- `KXEPLTEAMTOTAL-26OCT12COVNEW-COV1` no: dominated by KXEPLBTTS-26OCT12COVNEW-BTTS/no (corr +0.71)
- `KXEPLTOTAL-26OCT12COVNEW-6` no: dominated by KXEPLBTTS-26OCT12COVNEW-BTTS/no (corr +0.22)
- `KXEPL1HSCORE-26OCT12COVNEW-COV0NEW0` yes: dominated by KXEPL1HTOTAL-26OCT12COVNEW-1/no (corr +1.00)

## Events
- Levante vs Sevilla (La Liga) 2026-10-12T19:00:00Z · markets 72/73 evaluated · lineups unknown · xG 1.68-1.21 · 1X2 48%/24%/28%
- Torino vs Udinese (Serie A) 2026-10-12T18:45:00Z · markets 79/80 evaluated · lineups unknown · xG 1.45-1.28 · 1X2 41%/25%/34%
- Red Bull Bragantino vs Cruzeiro (Brasileirão Série A) 2026-10-13T00:00:00Z · markets 29/29 evaluated · lineups unknown · xG 1.34-1.18 · 1X2 40%/28%/32%
- Chapecoense vs Athletico Paranaense (Brasileirão Série A) 2026-10-12T22:30:00Z · markets 29/29 evaluated · lineups unknown · xG 1.35-1.77 · 1X2 30%/23%/47%
- Coritiba vs Botafogo (Brasileirão Série A) 2026-10-12T19:00:00Z · markets 29/29 evaluated · lineups unknown · xG 1.65-1.33 · 1X2 44%/25%/31%
- Coventry City vs Newcastle United (Premier League) 2026-10-12T19:00:00Z · markets 84/85 evaluated · lineups unknown · xG 0.98-1.37 · 1X2 28%/27%/46%
- Lanús vs Vélez Sarsfield (Liga Profesional Argentina) 2026-10-12T19:00:00Z · markets 14/14 evaluated · lineups unknown · xG 1.27-1.03 · 1X2 41%/28%/31%
