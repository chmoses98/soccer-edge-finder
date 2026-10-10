# RUN SOCCER — 2026-10-10
Run `run-20261010T172843Z-f2ebb6` generated 2026-10-10T17:28:46.612402Z · filters: {'leagues': [], 'games': ['fx:usa.mls:2026:usa.chicago_fire:usa.nycfc'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **6788** (discovery complete: True)
- contracts evaluated: 79 · excluded mechanically: 3640 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=79, unknown_family=3, unsupported_family=3066, unmapped_event=1066, unmapped_team=99, no_fixture=102, filtered_by_operator=2372, unpriceable=1
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, BELGIANPL, BRASILEIRO, BRASILEIROB, BRASILEIROC, BUNDESLIGA, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FIFAW, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, SERIEA, SOCCER, SUPERLIG, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-10T17:28:43.045602Z; market_observed_at: 2026-10-10T17:25:06.324864Z; fixtures_observed_at: 2026-10-10T13:17:42.346443Z; results_observed_at: 2026-10-10T13:17:35.856347Z; model_fitted_at: 2026-10-10T17:28:41.328676Z; temporal_guard: {'decision_time': '2026-10-10T17:28:43.045602Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-10T13:17:42.346443Z', 'market_snapshots': '2026-10-10T17:27:38.270066Z', 'reference_odds': '2026-10-10T13:17:42.645991Z', 'results': '2026-10-10T17:28:42.803252Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (7)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Chicago Fire vs New York City FC · btts · NO @ 0.3600 · fair 52.0% [40.4%–63.5%] · edge +14.3% · P(+) 94% · RESEARCH_ONLY · `KXMLSBTTS-26OCT10CHINYC-BTTS`
- Chicago Fire vs New York City FC · away team total over 1.5 · NO @ 0.6200 · fair 75.6% [63.5%–85.9%] · edge +11.9% · P(+) 90% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT10CHINYC-NYC2`
- Chicago Fire vs New York City FC · away team total over 2.5 · NO @ 0.8600 · fair 92.4% [86.3%–97.1%] · edge +5.5% · P(+) 88% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT10CHINYC-NYC3`
- Chicago Fire vs New York City FC · Total goals over 1.5 · NO @ 0.1600 · fair 27.3% [14.9%–39.8%] · edge +10.4% · P(+) 85% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT10CHINYC-2`
- Chicago Fire vs New York City FC · Total goals over 3.5 · NO @ 0.6000 · fair 72.3% [56.4%–85.6%] · edge +10.7% · P(+) 83% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT10CHINYC-4`
- Chicago Fire vs New York City FC · First half: both teams to score · NO @ 0.7600 · fair 82.7% [74.7%–90.2%] · edge +5.5% · P(+) 81% · RESEARCH_ONLY · `KXMLS1HBTTS-26OCT10CHINYC-BTTS`
- Chicago Fire vs New York City FC · Total goals over 0.5 · NO @ 0.0400 · fair 8.2% [3.5%–13.8%] · edge +4.0% · P(+) 84% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT10CHINYC-1`

## Expressions removed by the reducer (6)
- `KXMLS1HTOTAL-26OCT10CHINYC-2` no: redundant with KXMLS1HBTTS-26OCT10CHINYC-BTTS/no (corr +0.66); best expression kept
- `KXMLSTEAMTOTAL-26OCT10CHINYC-NYC1` no: dominated by KXMLSBTTS-26OCT10CHINYC-BTTS/no (corr +0.79)
- `KXMLSSCORE-26OCT10CHINYC-CHI1NYC0` yes: dominated by KXMLSTOTAL-26OCT10CHINYC-2/no (corr +0.60)
- `KXMLSTOTAL-26OCT10CHINYC-5` no: dominated by KXMLSTOTAL-26OCT10CHINYC-4/no (corr +0.64)
- `KXMLSTOTAL-26OCT10CHINYC-6` no: dominated by KXMLSTOTAL-26OCT10CHINYC-4/no (corr +0.41)
- `KXMLSTOTAL-26OCT10CHINYC-3` no: redundant with KXMLSTOTAL-26OCT10CHINYC-4/no (corr +0.64); best expression kept

## Events
- Chicago Fire vs New York City FC (Major League Soccer) 2026-10-10T18:30:00Z · markets 79/80 evaluated · lineups unknown · xG 1.69-0.94 · 1X2 54%/24%/22%
