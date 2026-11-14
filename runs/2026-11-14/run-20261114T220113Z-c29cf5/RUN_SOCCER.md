# RUN SOCCER — 2026-11-14
Run `run-20261114T220113Z-c29cf5` generated 2026-11-14T22:01:23.191169Z · filters: {'leagues': [], 'games': ['fx:mex.liga_mx:2026:mex.queretaro:mex.monterrey'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **6088** (discovery complete: True)
- contracts evaluated: 79 · excluded mechanically: 3124 · unsupported/unknown: 2885
- **unaccounted contracts: 0**
- by disposition: priced=79, unknown_family=3, unsupported_family=2882, unmapped_event=852, unmapped_team=197, no_fixture=57, filtered_by_operator=2017, unpriceable=1
- competitions discovered: ALEAGUEW, APFDDH, ARGCUP, ARGNACB, ARGPREMDIV, BELGIANPL, BRASILEIRO, BUNDESLIGA, BUNDESLIGAW, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, EFL, EFLCHAMPIONSHIP, EFLL1, EFLL2, EFLTROPHY, EKSTRAKLASA, EPL, EREDIVISIE, FA, INTLFRIENDLY, JLEAGUECUP, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAMXW, LIGAPORTUGAL, LIGAPORTUGAL2, LIGUE1, MLS, MLSEAST, MLSWEST, NWSL, PERLEAGUECUP, PERLIGA1, PREMIERLEAGUE, PRYCUP, SAFF, SERIEA, SOCCER, SUPERLIG, SVK2L, SWPL, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, USLL1, USLSLW, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-11-14T22:01:13.376207Z; market_observed_at: 2026-11-14T21:57:24.453395Z; fixtures_observed_at: 2026-11-14T21:29:04.021942Z; results_observed_at: 2026-11-14T16:36:46.399855Z; model_fitted_at: 2026-11-14T22:01:12.115494Z; temporal_guard: {'decision_time': '2026-11-14T22:01:13.376207Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-11-14T21:29:04.021942Z', 'market_snapshots': '2026-11-14T22:01:00.052437Z', 'reference_odds': '2026-11-14T16:36:53.634568Z', 'results': '2026-11-14T22:01:13.192922Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (8)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Querétaro vs Monterrey · Result: away · NO @ 0.5100 · fair 67.5% [53.7%–80.9%] · edge +14.8% · P(+) 91% · RESEARCH_ONLY · `KXLIGAMXGAME-26NOV14QUEMON-MON`
- Querétaro vs Monterrey · away team total over 1.5 · NO @ 0.5100 · fair 66.3% [51.2%–80.0%] · edge +13.6% · P(+) 88% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV14QUEMON-MON2`
- Querétaro vs Monterrey · away wins by more than 1.5 · NO @ 0.7500 · fair 85.8% [76.7%–93.7%] · edge +9.5% · P(+) 91% · RESEARCH_ONLY · `KXLIGAMXSPREAD-26NOV14QUEMON-MON2`
- Querétaro vs Monterrey · First-half result: away · NO @ 0.6300 · fair 74.3% [63.8%–84.2%] · edge +9.7% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMX1H-26NOV14QUEMON-MON`
- Querétaro vs Monterrey · away team total over 2.5 · NO @ 0.7800 · fair 87.0% [77.3%–94.9%] · edge +7.8% · P(+) 86% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV14QUEMON-MON3`
- Querétaro vs Monterrey · away team total over 0.5 · NO @ 0.2000 · fair 31.4% [19.4%–43.8%] · edge +10.3% · P(+) 86% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26NOV14QUEMON-MON1`
- Querétaro vs Monterrey · away wins by more than 2.5 · NO @ 0.9000 · fair 95.0% [90.3%–98.4%] · edge +4.4% · P(+) 89% · RESEARCH_ONLY · `KXLIGAMXSPREAD-26NOV14QUEMON-MON3`
- Querétaro vs Monterrey · First half: away wins by more than 1.5 · NO @ 0.8900 · fair 93.7% [88.9%–98.1%] · edge +4.0% · P(+) 87% · RESEARCH_ONLY · `KXLIGAMX1HSPREAD-26NOV14QUEMON-MON2`

## Expressions removed by the reducer (4)
- `KXLIGAMXGAME-26NOV14QUEMON-QUE` yes: redundant with KXLIGAMXGAME-26NOV14QUEMON-MON/no (corr +0.58); best expression kept
- `KXLIGAMXFTTS-26NOV14QUEMON-MON` no: dominated by KXLIGAMXGAME-26NOV14QUEMON-MON/no (corr +0.60)
- `KXLIGAMXSPREAD-26NOV14QUEMON-QUE2` yes: dominated by KXLIGAMXGAME-26NOV14QUEMON-MON/no (corr +0.35)
- `KXLIGAMXFTTS-26NOV14QUEMON-QUE` yes: dominated by KXLIGAMXGAME-26NOV14QUEMON-MON/no (corr +0.48)

## Events
- Querétaro vs Monterrey (Liga MX) 2026-11-14T23:00:00Z · markets 79/80 evaluated · lineups unknown · xG 1.42-1.21 · 1X2 41%/26%/32%
