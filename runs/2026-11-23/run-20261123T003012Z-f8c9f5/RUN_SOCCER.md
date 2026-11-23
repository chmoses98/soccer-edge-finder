# RUN SOCCER — 2026-11-23
Run `run-20261123T003012Z-f8c9f5` generated 2026-11-23T00:30:24.533245Z · filters: {'leagues': [], 'games': ['fx:usa.mls:2026:usa.vancouver_whitecaps:usa.real_salt_lake'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4436** (discovery complete: True)
- contracts evaluated: 79 · excluded mechanically: 1381 · unsupported/unknown: 2976
- **unaccounted contracts: 0**
- by disposition: priced=79, ambiguous_ownership=27, unknown_family=4, unsupported_family=2972, unmapped_event=369, unmapped_team=48, no_fixture=51, filtered_by_operator=885, unpriceable=1
- competitions discovered: AFCCL2, ALEAGUEW, APFDDH, ARGNACB, ARGPREMDIV, BELGIANPL, BRASILEIRO, BUNDESLIGA, BUNDESLIGAW, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, INDSL, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, PERLIGA1, PREMIERLEAGUE, ROML1, SAPSL, SCOCHAMP, SERIEA, SOCCER, SUPERLIG, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-23T00:30:12.004155Z; market_observed_at: 2026-11-23T00:26:38.720419Z; fixtures_observed_at: 2026-11-22T20:59:30.389368Z; results_observed_at: 2026-11-22T20:59:23.528085Z; model_fitted_at: 2026-11-23T00:30:10.862509Z; temporal_guard: {'decision_time': '2026-11-23T00:30:12.004155Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-22T20:59:30.389368Z', 'market_snapshots': '2026-11-23T00:30:03.382474Z', 'reference_odds': '2026-11-22T20:59:30.621651Z', 'results': '2026-11-23T00:30:11.800187Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (9)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Vancouver Whitecaps vs Real Salt Lake · btts · NO @ 0.3800 · fair 55.2% [44.2%–66.4%] · edge +15.6% · P(+) 96% · RESEARCH_ONLY · `KXMLSBTTS-26NOV22VANRSL-BTTS`
- Vancouver Whitecaps vs Real Salt Lake · away team total over 1.5 · NO @ 0.7000 · fair 83.0% [74.0%–90.8%] · edge +11.5% · P(+) 94% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV22VANRSL-RSL2`
- Vancouver Whitecaps vs Real Salt Lake · away team total over 2.5 · NO @ 0.9000 · fair 95.7% [92.2%–98.5%] · edge +5.1% · P(+) 94% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV22VANRSL-RSL3`
- Vancouver Whitecaps vs Real Salt Lake · Total goals over 2.5 · NO @ 0.3100 · fair 45.3% [28.7%–61.3%] · edge +12.8% · P(+) 84% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV22VANRSL-3`
- Vancouver Whitecaps vs Real Salt Lake · Total goals over 1.5 · NO @ 0.1300 · fair 22.8% [11.5%–34.7%] · edge +9.0% · P(+) 83% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV22VANRSL-2`
- Vancouver Whitecaps vs Real Salt Lake · First half: both teams to score · NO @ 0.7600 · fair 83.2% [74.8%–90.2%] · edge +5.9% · P(+) 84% · RESEARCH_ONLY · `KXMLS1HBTTS-26NOV22VANRSL-BTTS`
- Vancouver Whitecaps vs Real Salt Lake · Exact score 2-0 (home-away) · YES @ 0.0900 · fair 12.4% [9.0%–15.7%] · edge +2.8% · P(+) 87% · RESEARCH_ONLY · `KXMLSSCORE-26NOV22VANRSL-VAN2RSL0`
- Vancouver Whitecaps vs Real Salt Lake · First-half total goals over 1.5 · NO @ 0.5300 · fair 63.5% [49.8%–76.2%] · edge +8.7% · P(+) 81% · RESEARCH_ONLY · `KXMLS1HTOTAL-26NOV22VANRSL-2`
- Vancouver Whitecaps vs Real Salt Lake · Exact score 0-0 (home-away) · YES @ 0.0300 · fair 6.4% [2.5%–11.1%] · edge +3.2% · P(+) 83% · RESEARCH_ONLY · `KXMLSSCORE-26NOV22VANRSL-VAN0RSL0`

## Expressions removed by the reducer (6)
- `KXMLSTEAMTOTAL-26NOV22VANRSL-RSL1` no: dominated by KXMLSBTTS-26NOV22VANRSL-BTTS/no (corr +0.88)
- `KXMLSTOTAL-26NOV22VANRSL-4` no: dominated by KXMLSTOTAL-26NOV22VANRSL-3/no (corr +0.65)
- `KXMLSTOTAL-26NOV22VANRSL-6` no: redundant with KXMLSTOTAL-26NOV22VANRSL-3/no (corr +0.28); best expression kept
- `KXMLSTOTAL-26NOV22VANRSL-5` no: dominated by KXMLSTOTAL-26NOV22VANRSL-3/no (corr +0.43)
- `KXMLSSCORE-26NOV22VANRSL-VAN1RSL0` yes: redundant with KXMLSTOTAL-26NOV22VANRSL-2/no (corr +0.68); best expression kept
- `KXMLSTOTAL-26NOV22VANRSL-1` no: dominated by KXMLSSCORE-26NOV22VANRSL-VAN0RSL0/yes (corr +1.00)

## Events
- Vancouver Whitecaps vs Real Salt Lake (Major League Soccer) 2026-11-23T01:30:00Z · markets 79/80 evaluated · lineups unknown · xG 2.18-0.73 · 1X2 69%/19%/12%
