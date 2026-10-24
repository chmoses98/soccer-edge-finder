# RUN SOCCER — 2026-10-24
Run `run-20261024T210404Z-793f80` generated 2026-10-24T21:04:13.401335Z · filters: {'leagues': [], 'games': ['fx:bra.serie_a:2026:bra.palmeiras:bra.bragantino', 'fx:bra.serie_a:2026:bra.vasco:bra.corinthians', 'fx:usa.mls:2026:usa.ny_red_bulls:usa.inter_miami'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **7249** (discovery complete: True)
- contracts evaluated: 105 · excluded mechanically: 4075 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=105, unknown_family=3, unsupported_family=3066, unmapped_event=1398, unmapped_team=302, no_fixture=133, filtered_by_operator=2242
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-24T21:04:04.425776Z; market_observed_at: 2026-10-24T21:01:00.154360Z; fixtures_observed_at: 2026-10-24T19:10:09.432684Z; results_observed_at: 2026-10-24T18:42:57.477580Z; model_fitted_at: 2026-10-24T21:04:02.868106Z; temporal_guard: {'decision_time': '2026-10-24T21:04:04.425776Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-24T19:10:09.432684Z', 'market_snapshots': '2026-10-24T21:03:53.850755Z', 'reference_odds': '2026-10-24T18:43:00.069400Z', 'results': '2026-10-24T21:04:04.063537Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (10)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- New York Red Bulls vs Inter Miami · Total goals over 3.5 · NO @ 0.4700 · fair 64.5% [49.0%–79.0%] · edge +15.7% · P(+) 90% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT24NYRBMIA-4`
- New York Red Bulls vs Inter Miami · away team total over 1.5 · NO @ 0.3700 · fair 52.3% [36.7%–67.0%] · edge +13.6% · P(+) 87% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT24NYRBMIA-MIA2`
- New York Red Bulls vs Inter Miami · btts · NO @ 0.2800 · fair 41.7% [30.0%–53.6%] · edge +12.2% · P(+) 92% · RESEARCH_ONLY · `KXMLSBTTS-26OCT24NYRBMIA-BTTS`
- New York Red Bulls vs Inter Miami · away team total over 2.5 · NO @ 0.6500 · fair 77.1% [63.6%–88.4%] · edge +10.5% · P(+) 86% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT24NYRBMIA-MIA3`
- New York Red Bulls vs Inter Miami · First-half total goals over 1.5 · NO @ 0.5000 · fair 61.9% [49.8%–74.2%] · edge +10.2% · P(+) 88% · RESEARCH_ONLY · `KXMLS1HTOTAL-26OCT24NYRBMIA-2`
- New York Red Bulls vs Inter Miami · First-half exact score 0-0 (home-away) · YES @ 0.1800 · fair 27.4% [17.8%–38.2%] · edge +8.4% · P(+) 86% · RESEARCH_ONLY · `KXMLS1HSCORE-26OCT24NYRBMIA-NYRB0MIA0`
- Palmeiras vs Red Bull Bragantino · btts · NO @ 0.4800 · fair 58.4% [46.5%–70.1%] · edge +8.6% · P(+) 83% · RESEARCH_ONLY · `KXBRASILEIROBTTS-26OCT24PALRBB-BTTS`
- New York Red Bulls vs Inter Miami · First-half total goals over 2.5 · NO @ 0.7700 · fair 84.7% [75.9%–93.1%] · edge +6.5% · P(+) 83% · RESEARCH_ONLY · `KXMLS1HTOTAL-26OCT24NYRBMIA-3`
- New York Red Bulls vs Inter Miami · Total goals over 0.5 · NO @ 0.0300 · fair 6.1% [2.7%–10.0%] · edge +2.9% · P(+) 84% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT24NYRBMIA-1`
- New York Red Bulls vs Inter Miami · Exact score 1-0 (home-away) · YES @ 0.0400 · fair 6.6% [3.3%–10.1%] · edge +2.3% · P(+) 82% · RESEARCH_ONLY · `KXMLSSCORE-26OCT24NYRBMIA-NYRB1MIA0`

## Expressions removed by the reducer (8)
- `KXMLSTEAMTOTAL-26OCT24NYRBMIA-MIA1` no: dominated by KXMLSBTTS-26OCT24NYRBMIA-BTTS/no (corr +0.61)
- `KXMLSTOTAL-26OCT24NYRBMIA-2` no: dominated by KXMLSBTTS-26OCT24NYRBMIA-BTTS/no (corr +0.61)
- `KXMLSSCORE-26OCT24NYRBMIA-NYRB0MIA0` yes: dominated by KXMLSTOTAL-26OCT24NYRBMIA-1/no (corr +1.00)
- `KXMLS1HBTTS-26OCT24NYRBMIA-BTTS` no: dominated by KXMLS1HTOTAL-26OCT24NYRBMIA-2/no (corr +0.69)
- `KXMLSTOTAL-26OCT24NYRBMIA-5` no: dominated by KXMLSTOTAL-26OCT24NYRBMIA-4/no (corr +0.67)
- `KXMLSTOTAL-26OCT24NYRBMIA-3` no: dominated by KXMLSTOTAL-26OCT24NYRBMIA-4/no (corr +0.65)
- `KXMLSTOTAL-26OCT24NYRBMIA-6` no: dominated by KXMLSTOTAL-26OCT24NYRBMIA-4/no (corr +0.44)
- `KXMLS1HTOTAL-26OCT24NYRBMIA-1` no: dominated by KXMLS1HSCORE-26OCT24NYRBMIA-NYRB0MIA0/yes (corr +1.00)

## Events
- New York Red Bulls vs Inter Miami (Major League Soccer) 2026-10-24T21:30:00Z · markets 77/77 evaluated · lineups unknown · xG 1.37-1.64 · 1X2 32%/24%/44%
- Vasco da Gama vs Corinthians (Brasileirão Série A) 2026-10-24T21:30:00Z · markets 14/14 evaluated · lineups unknown · xG 1.53-0.93 · 1X2 50%/27%/23%
- Palmeiras vs Red Bull Bragantino (Brasileirão Série A) 2026-10-24T21:30:00Z · markets 14/14 evaluated · lineups unknown · xG 1.85-0.71 · 1X2 63%/23%/14%
