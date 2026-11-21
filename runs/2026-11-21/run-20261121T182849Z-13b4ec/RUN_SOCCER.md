# RUN SOCCER — 2026-11-21
Run `run-20261121T182849Z-13b4ec` generated 2026-11-21T18:28:52.235419Z · filters: {'leagues': [], 'games': ['fx:bra.serie_a:2026:bra.palmeiras:bra.flamengo'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5595** (discovery complete: True)
- contracts evaluated: 14 · excluded mechanically: 2587 · unsupported/unknown: 2994
- **unaccounted contracts: 0**
- by disposition: priced=14, ambiguous_ownership=18, unknown_family=4, unsupported_family=2990, unmapped_event=1077, unmapped_team=14, no_fixture=69, filtered_by_operator=1409
- competitions discovered: AFCCL2, ALEAGUEW, APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELCHALL, BELGIANPL, BRASILEIRO, BRASILEIROB, BULFL, BUNDESLIGA, BUNDESLIGAW, CANPL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EKSTRAKLASA, ENGNL, ENGWLEAGUECUP, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SAPSL, SCOCHAMP, SERIEA, SOCCER, SUPERLIG, SVK1L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEL, UKRPL, URYPD, USL, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-21T18:28:49.931413Z; market_observed_at: 2026-11-21T18:25:04.224619Z; fixtures_observed_at: 2026-11-21T15:45:26.524367Z; results_observed_at: 2026-11-21T15:45:20.555536Z; model_fitted_at: 2026-11-21T18:28:48.607600Z; temporal_guard: {'decision_time': '2026-11-21T18:28:49.931413Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-21T15:45:26.524367Z', 'market_snapshots': '2026-11-21T18:28:44.032541Z', 'reference_odds': '2026-11-21T15:45:26.698325Z', 'results': '2026-11-21T18:28:49.752111Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (4)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Palmeiras vs Flamengo · Result: away · NO @ 0.5400 · fair 73.7% [60.7%–84.9%] · edge +18.0% · P(+) 96% · RESEARCH_ONLY · `KXBRASILEIROGAME-26NOV21PALFLA-FLA`
- Palmeiras vs Flamengo · Result: home · YES @ 0.2700 · fair 47.5% [31.9%–63.2%] · edge +19.1% · P(+) 96% · RESEARCH_ONLY · `KXBRASILEIROGAME-26NOV21PALFLA-PAL`
- Palmeiras vs Flamengo · away wins by more than 1.5 · NO @ 0.7700 · fair 89.4% [81.5%–95.4%] · edge +11.2% · P(+) 95% · RESEARCH_ONLY · `KXBRASILEIROSPREAD-26NOV21PALFLA-FLA2`
- Palmeiras vs Flamengo · away wins by more than 2.5 · NO @ 0.9200 · fair 96.6% [93.1%–99.0%] · edge +4.1% · P(+) 92% · RESEARCH_ONLY · `KXBRASILEIROSPREAD-26NOV21PALFLA-FLA3`

## Expressions removed by the reducer (2)
- `KXBRASILEIROSPREAD-26NOV21PALFLA-PAL2` yes: redundant with KXBRASILEIROGAME-26NOV21PALFLA-PAL/yes (corr +0.61); best expression kept
- `KXBRASILEIROSPREAD-26NOV21PALFLA-PAL3` yes: dominated by KXBRASILEIROGAME-26NOV21PALFLA-PAL/yes (corr +0.37)

## Events
- Palmeiras vs Flamengo (Brasileirão Série A) 2026-11-21T19:30:00Z · markets 14/14 evaluated · lineups unknown · xG 1.54-1.07 · 1X2 47%/26%/26%
