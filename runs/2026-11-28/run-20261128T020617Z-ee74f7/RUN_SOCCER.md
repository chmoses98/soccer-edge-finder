# RUN SOCCER — 2026-11-28
Run `run-20261128T020617Z-ee74f7` generated 2026-11-28T02:06:29.349683Z · filters: {'leagues': [], 'games': ['fx:usa.mls:2026:usa.real_salt_lake:usa.vancouver_whitecaps'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5816** (discovery complete: True)
- contracts evaluated: 79 · excluded mechanically: 2736 · unsupported/unknown: 3001
- **unaccounted contracts: 0**
- by disposition: priced=79, ambiguous_ownership=6, unknown_family=52, unsupported_family=2949, unmapped_event=1242, unmapped_team=111, no_fixture=24, filtered_by_operator=1352, unpriceable=1
- competitions discovered: AFCCL2, APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BOTOLA, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FIFAW, HUNNB1, INDSL, ISRNL, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SAPSL, SCOCHAMP, SERIEA, SOCCER, SUPERLIG, SVK1L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-28T02:06:17.018488Z; market_observed_at: 2026-11-28T02:02:22.218231Z; fixtures_observed_at: 2026-11-28T02:06:07.792858Z; results_observed_at: 2026-11-28T02:06:00.910235Z; model_fitted_at: 2026-11-28T02:06:15.675768Z; temporal_guard: {'decision_time': '2026-11-28T02:06:17.018488Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-28T02:06:07.792858Z', 'market_snapshots': '2026-11-28T02:05:59.981692Z', 'reference_odds': '2026-11-28T02:06:07.996021Z', 'results': '2026-11-28T02:06:16.826567Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (7)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Real Salt Lake vs Vancouver Whitecaps · btts · NO @ 0.3800 · fair 51.9% [40.3%–63.2%] · edge +12.3% · P(+) 91% · RESEARCH_ONLY · `KXMLSBTTS-26NOV27RSLVAN-BTTS`
- Real Salt Lake vs Vancouver Whitecaps · Total goals over 3.5 · NO @ 0.6300 · fair 76.4% [63.6%–87.2%] · edge +11.7% · P(+) 88% · RESEARCH_ONLY · `KXMLSTOTAL-26NOV27RSLVAN-4`
- Real Salt Lake vs Vancouver Whitecaps · away team total over 1.5 · NO @ 0.5300 · fair 64.6% [51.5%–76.9%] · edge +9.8% · P(+) 84% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV27RSLVAN-VAN2`
- Real Salt Lake vs Vancouver Whitecaps · away team total over 2.5 · NO @ 0.7900 · fair 86.2% [77.5%–93.6%] · edge +6.0% · P(+) 83% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26NOV27RSLVAN-VAN3`
- Real Salt Lake vs Vancouver Whitecaps · First-half total goals over 0.5 · NO @ 0.2600 · fair 34.7% [23.8%–46.2%] · edge +7.3% · P(+) 81% · RESEARCH_ONLY · `KXMLS1HTOTAL-26NOV27RSLVAN-1`
- Real Salt Lake vs Vancouver Whitecaps · Exact score 0-1 (home-away) · YES @ 0.0700 · fair 11.0% [6.6%–15.6%] · edge +3.6% · P(+) 84% · RESEARCH_ONLY · `KXMLSSCORE-26NOV27RSLVAN-RSL0VAN1`
- Real Salt Lake vs Vancouver Whitecaps · Exact score 1-0 (home-away) · YES @ 0.0700 · fair 10.4% [6.6%–14.3%] · edge +2.9% · P(+) 83% · RESEARCH_ONLY · `KXMLSSCORE-26NOV27RSLVAN-RSL1VAN0`

## Expressions removed by the reducer (7)
- `KXMLS1HSCORE-26NOV27RSLVAN-RSL0VAN0` yes: dominated by KXMLS1HTOTAL-26NOV27RSLVAN-1/no (corr +1.00)
- `KXMLSTOTAL-26NOV27RSLVAN-2` no: dominated by KXMLSBTTS-26NOV27RSLVAN-BTTS/no (corr +0.65)
- `KXMLSTEAMTOTAL-26NOV27RSLVAN-VAN1` no: dominated by KXMLSBTTS-26NOV27RSLVAN-BTTS/no (corr +0.63)
- `KXMLSTEAMTOTAL-26NOV27RSLVAN-RSL1` no: dominated by KXMLSBTTS-26NOV27RSLVAN-BTTS/no (corr +0.66)
- `KXMLSTOTAL-26NOV27RSLVAN-3` no: redundant with KXMLSTOTAL-26NOV27RSLVAN-4/no (corr +0.63); best expression kept
- `KXMLSTOTAL-26NOV27RSLVAN-5` no: dominated by KXMLSTOTAL-26NOV27RSLVAN-4/no (corr +0.63)
- `KXMLSTOTAL-26NOV27RSLVAN-6` no: dominated by KXMLSTOTAL-26NOV27RSLVAN-4/no (corr +0.40)

## Events
- Real Salt Lake vs Vancouver Whitecaps (Major League Soccer) 2026-11-28T03:00:00Z · markets 79/80 evaluated · lineups unknown · xG 1.19-1.26 · 1X2 35%/27%/38%
