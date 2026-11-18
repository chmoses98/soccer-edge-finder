# RUN SOCCER — 2026-11-18
Run `run-20261118T105431Z-658a69` generated 2026-11-18T10:54:43.925611Z · filters: {'leagues': [], 'games': ['fx:usa.mls:2026:usa.seattle_sounders:usa.real_salt_lake'], 'window_hours': 42, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4443** (discovery complete: True)
- contracts evaluated: 79 · excluded mechanically: 1511 · unsupported/unknown: 2853
- **unaccounted contracts: 0**
- by disposition: priced=79, unknown_family=3, unsupported_family=2850, unmapped_event=598, unmapped_team=8, no_fixture=45, filtered_by_operator=859, unpriceable=1
- competitions discovered: ALEAGUEW, APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGAW, CANPL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, ENGWLEAGUECUP, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SCOCHAMP, SERIEA, SOCCER, SUPERETTAN, SUPERLIG, SVK1L, SVKCUP, SWPL, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-18T10:54:31.218488Z; market_observed_at: 2026-11-18T10:51:01.248056Z; fixtures_observed_at: 2026-11-18T10:54:28.352366Z; results_observed_at: 2026-11-18T10:54:20.696227Z; model_fitted_at: 2026-11-18T10:54:28.690518Z; temporal_guard: {'decision_time': '2026-11-18T10:54:31.218488Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-18T10:54:28.352366Z', 'market_snapshots': '2026-11-18T10:54:19.618591Z', 'reference_odds': '2026-11-18T10:54:30.488773Z', 'results': '2026-11-18T10:54:30.139623Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (9)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Seattle Sounders vs Real Salt Lake · btts · NO @ 0.3700 · fair 53.9% [42.5%–64.9%] · edge +15.3% · P(+) 96% · RESEARCH_ONLY · `KXMLSBTTS-26NOV19SEARSL-BTTS`
- Seattle Sounders vs Real Salt Lake · Total goals over 3.5 · NO @ 0.6000 · fair 76.1% [62.7%–87.2%] · edge +14.5% · P(+) 92% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV19SEARSL-4`
- Seattle Sounders vs Real Salt Lake · away team total over 1.5 · NO @ 0.6300 · fair 75.7% [64.6%–85.6%] · edge +11.1% · P(+) 90% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV19SEARSL-RSL2`
- Seattle Sounders vs Real Salt Lake · First-half total goals over 1.5 · NO @ 0.5900 · fair 70.7% [59.8%–81.2%] · edge +10.0% · P(+) 89% · RESEARCH_ONLY · `KXMLS1HTOTAL-26NOV19SEARSL-2`
- Seattle Sounders vs Real Salt Lake · First-half exact score 0-0 (home-away) · YES @ 0.2400 · fair 34.5% [23.8%–45.2%] · edge +9.2% · P(+) 86% · RESEARCH_ONLY · `KXMLS1HSCORE-26NOV19SEARSL-SEA0RSL0`
- Seattle Sounders vs Real Salt Lake · away team total over 2.5 · NO @ 0.8700 · fair 92.6% [86.9%–97.0%] · edge +4.8% · P(+) 88% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV19SEARSL-RSL3`
- Seattle Sounders vs Real Salt Lake · Exact score 1-0 (home-away) · YES @ 0.0800 · fair 12.9% [8.3%–17.3%] · edge +4.4% · P(+) 89% · RESEARCH_ONLY · `KXMLSSCORE-26NOV19SEARSL-SEA1RSL0`
- Seattle Sounders vs Real Salt Lake · First-half total goals over 2.5 · NO @ 0.8400 · fair 90.2% [83.9%–96.1%] · edge +5.2% · P(+) 87% · RESEARCH_ONLY · `KXMLS1HTOTAL-26NOV19SEARSL-3`
- Seattle Sounders vs Real Salt Lake · Total goals over 0.5 · NO @ 0.0500 · fair 9.5% [4.6%–14.9%] · edge +4.1% · P(+) 84% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV19SEARSL-1`

## Expressions removed by the reducer (7)
- `KXMLSTOTAL-26NOV19SEARSL-2` no: dominated by KXMLSBTTS-26NOV19SEARSL-BTTS/no (corr +0.62)
- `KXMLSTEAMTOTAL-26NOV19SEARSL-RSL1` no: dominated by KXMLSBTTS-26NOV19SEARSL-BTTS/no (corr +0.76)
- `KXMLS1HTOTAL-26NOV19SEARSL-1` no: dominated by KXMLS1HSCORE-26NOV19SEARSL-SEA0RSL0/yes (corr +1.00)
- `KXMLSSCORE-26NOV19SEARSL-SEA0RSL0` yes: dominated by KXMLSTOTAL-26NOV19SEARSL-1/no (corr +1.00)
- `KXMLSTOTAL-26NOV19SEARSL-3` no: redundant with KXMLSTOTAL-26NOV19SEARSL-4/no (corr +0.63); best expression kept
- `KXMLSTOTAL-26NOV19SEARSL-5` no: dominated by KXMLSTOTAL-26NOV19SEARSL-4/no (corr +0.63)
- `KXMLSTOTAL-26NOV19SEARSL-6` no: dominated by KXMLSTOTAL-26NOV19SEARSL-4/no (corr +0.39)

## Events
- Seattle Sounders vs Real Salt Lake (Major League Soccer) 2026-11-20T03:00:00Z · markets 79/80 evaluated · lineups unknown · xG 1.52-0.94 · 1X2 50%/26%/24%
