# RUN SOCCER — 2026-10-10
Run `run-20261010T000010Z-9c9ace` generated 2026-10-10T00:00:13.897121Z · filters: {'leagues': [], 'games': ['fx:mex.liga_mx:2026:mex.puebla:mex.leon'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **6924** (discovery complete: True)
- contracts evaluated: 79 · excluded mechanically: 3776 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=79, unknown_family=3, unsupported_family=3066, unmapped_event=1226, unmapped_team=99, no_fixture=126, filtered_by_operator=2324, unpriceable=1
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, BELGIANPL, BRASILEIRO, BRASILEIROB, BRASILEIROC, BUNDESLIGA, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FIFAW, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, SERIEA, SOCCER, SUPERLIG, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-10T00:00:10.675911Z; market_observed_at: 2026-10-09T23:56:57.954718Z; fixtures_observed_at: 2026-10-09T22:44:11.823114Z; results_observed_at: 2026-10-09T20:40:29.027365Z; model_fitted_at: 2026-10-10T00:00:08.927078Z; temporal_guard: {'decision_time': '2026-10-10T00:00:10.675911Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-09T22:44:11.823114Z', 'market_snapshots': '2026-10-09T23:59:30.726328Z', 'reference_odds': '2026-10-09T20:40:38.005458Z', 'results': '2026-10-10T00:00:10.453395Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (9)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Puebla vs León · away team total over 0.5 · NO @ 0.2300 · fair 39.1% [25.6%–52.0%] · edge +14.9% · P(+) 92% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT09PUELEO-LEO1`
- Puebla vs León · away team total over 1.5 · NO @ 0.5900 · fair 74.4% [60.5%–86.0%] · edge +13.7% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT09PUELEO-LEO2`
- Puebla vs León · Exact score 1-0 (home-away) · YES @ 0.0800 · fair 13.2% [8.3%–17.8%] · edge +4.7% · P(+) 89% · RESEARCH_ONLY · `KXLIGAMXSCORE-26OCT09PUELEO-PUE1LEO0`
- Puebla vs León · away team total over 2.5 · NO @ 0.8600 · fair 91.6% [84.2%–97.1%] · edge +4.8% · P(+) 84% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT09PUELEO-LEO3`
- Puebla vs León · Exact score 1-2 (home-away) · NO @ 0.9100 · fair 94.1% [91.7%–96.3%] · edge +2.5% · P(+) 91% · RESEARCH_ONLY · `KXLIGAMXSCORE-26OCT09PUELEO-PUE1LEO2`
- Puebla vs León · Total goals over 3.5 · NO @ 0.7200 · fair 80.8% [67.3%–91.5%] · edge +7.4% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26OCT09PUELEO-4`
- Puebla vs León · First-half result: away · NO @ 0.6900 · fair 77.5% [66.8%–87.2%] · edge +7.0% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMX1H-26OCT09PUELEO-LEO`
- Puebla vs León · First half: away wins by more than 1.5 · NO @ 0.9200 · fair 95.3% [90.9%–99.1%] · edge +2.8% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMX1HSPREAD-26OCT09PUELEO-LEO2`
- Puebla vs León · Exact score 2-0 (home-away) · YES @ 0.0500 · fair 8.2% [4.6%–12.1%] · edge +2.9% · P(+) 85% · RESEARCH_ONLY · `KXLIGAMXSCORE-26OCT09PUELEO-PUE2LEO0`

## Expressions removed by the reducer (8)
- `KXLIGAMXTOTAL-26OCT09PUELEO-3` no: redundant with KXLIGAMXTOTAL-26OCT09PUELEO-4/no (corr +0.62); best expression kept
- `KXLIGAMXTOTAL-26OCT09PUELEO-5` no: dominated by KXLIGAMXTOTAL-26OCT09PUELEO-4/no (corr +0.62)
- `KXLIGAMXBTTS-26OCT09PUELEO-BTTS` no: dominated by KXLIGAMXTEAMTOTAL-26OCT09PUELEO-LEO1/no (corr +0.69)
- `KXLIGAMXGAME-26OCT09PUELEO-LEO` no: dominated by KXLIGAMXTEAMTOTAL-26OCT09PUELEO-LEO1/no (corr +0.51)
- `KXLIGAMXTOTAL-26OCT09PUELEO-2` no: dominated by KXLIGAMXTEAMTOTAL-26OCT09PUELEO-LEO1/no (corr +0.48)
- `KXLIGAMXFTTS-26OCT09PUELEO-LEO` no: dominated by KXLIGAMXTEAMTOTAL-26OCT09PUELEO-LEO1/no (corr +0.64)
- `KXLIGAMXSPREAD-26OCT09PUELEO-LEO3` no: dominated by KXLIGAMXTEAMTOTAL-26OCT09PUELEO-LEO3/no (corr +0.64)
- `KXLIGAMXSPREAD-26OCT09PUELEO-LEO2` no: dominated by KXLIGAMXTEAMTOTAL-26OCT09PUELEO-LEO2/no (corr +0.60)

## Events
- Puebla vs León (Liga MX) 2026-10-10T01:00:00Z · markets 79/80 evaluated · lineups unknown · xG 1.25-0.98 · 1X2 42%/29%/29%
