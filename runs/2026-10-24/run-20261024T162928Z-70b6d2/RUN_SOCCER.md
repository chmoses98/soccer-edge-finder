# RUN SOCCER — 2026-10-24
Run `run-20261024T162928Z-70b6d2` generated 2026-10-24T16:29:34.075151Z · filters: {'leagues': [], 'games': ['fx:usa.mls:2026:usa.cf_montreal:usa.nashville'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **7368** (discovery complete: True)
- contracts evaluated: 77 · excluded mechanically: 4222 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=77, unknown_family=3, unsupported_family=3066, unmapped_event=1472, unmapped_team=291, no_fixture=133, filtered_by_operator=2326
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, QSTARS, ROML1, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-24T16:29:28.399099Z; market_observed_at: 2026-10-24T16:25:00.031694Z; fixtures_observed_at: 2026-10-24T12:38:22.554809Z; results_observed_at: 2026-10-24T12:38:20.500016Z; model_fitted_at: 2026-10-24T16:29:27.435361Z; temporal_guard: {'decision_time': '2026-10-24T16:29:28.399099Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-24T12:38:22.554809Z', 'market_snapshots': '2026-10-24T16:27:53.768950Z', 'reference_odds': '2026-10-24T12:38:22.783655Z', 'results': '2026-10-24T16:29:28.237087Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (8)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- CF Montréal vs Nashville SC · Total goals over 2.5 · NO @ 0.3900 · fair 59.6% [44.4%–73.2%] · edge +19.0% · P(+) 95% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT24MTLNSH-3`
- CF Montréal vs Nashville SC · First-half exact score 0-0 (home-away) · YES @ 0.2400 · fair 37.1% [25.8%–48.2%] · edge +11.8% · P(+) 91% · RESEARCH_ONLY · `KXMLS1HSCORE-26OCT24MTLNSH-MTL0NSH0`
- CF Montréal vs Nashville SC · First-half total goals over 1.5 · NO @ 0.6000 · fair 72.9% [61.8%–83.2%] · edge +11.2% · P(+) 92% · RESEARCH_ONLY · `KXMLS1HTOTAL-26OCT24MTLNSH-2`
- CF Montréal vs Nashville SC · away team total over 0.5 · NO @ 0.1200 · fair 23.5% [13.5%–33.6%] · edge +10.7% · P(+) 92% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT24MTLNSH-NSH1`
- CF Montréal vs Nashville SC · First-half total goals over 2.5 · NO @ 0.8500 · fair 91.4% [84.9%–97.1%] · edge +5.5% · P(+) 89% · RESEARCH_ONLY · `KXMLS1HTOTAL-26OCT24MTLNSH-3`
- CF Montréal vs Nashville SC · Exact score 0-1 (home-away) · YES @ 0.0900 · fair 14.6% [9.5%–19.6%] · edge +5.0% · P(+) 90% · RESEARCH_ONLY · `KXMLSSCORE-26OCT24MTLNSH-MTL0NSH1`
- CF Montréal vs Nashville SC · Exact score 1-0 (home-away) · YES @ 0.0400 · fair 7.6% [4.1%–11.2%] · edge +3.3% · P(+) 89% · RESEARCH_ONLY · `KXMLSSCORE-26OCT24MTLNSH-MTL1NSH0`
- CF Montréal vs Nashville SC · First half: away wins by more than 1.5 · NO @ 0.8300 · fair 88.8% [80.9%–95.1%] · edge +4.8% · P(+) 84% · RESEARCH_ONLY · `KXMLS1HSPREAD-26OCT24MTLNSH-NSH2`

## Expressions removed by the reducer (17)
- `KXMLSTEAMTOTAL-26OCT24MTLNSH-NSH2` no: dominated by KXMLSTOTAL-26OCT24MTLNSH-3/no (corr +0.62)
- `KXMLSTOTAL-26OCT24MTLNSH-4` no: dominated by KXMLSTOTAL-26OCT24MTLNSH-3/no (corr +0.63)
- `KXMLSTEAMTOTAL-26OCT24MTLNSH-NSH3` no: dominated by KXMLSTOTAL-26OCT24MTLNSH-3/no (corr +0.61)
- `KXMLSTOTAL-26OCT24MTLNSH-2` no: dominated by KXMLSTOTAL-26OCT24MTLNSH-3/no (corr +0.58)
- `KXMLSTOTAL-26OCT24MTLNSH-5` no: dominated by KXMLSTOTAL-26OCT24MTLNSH-3/no (corr +0.39)
- `KXMLSBTTS-26OCT24MTLNSH-BTTS` no: dominated by KXMLSTOTAL-26OCT24MTLNSH-3/no (corr +0.54)
- `KXMLSTOTAL-26OCT24MTLNSH-6` no: dominated by KXMLSTOTAL-26OCT24MTLNSH-3/no (corr +0.24)
- `KXMLSSPREAD-26OCT24MTLNSH-NSH3` no: dominated by KXMLSTOTAL-26OCT24MTLNSH-3/no (corr +0.45)
- `KXMLSSPREAD-26OCT24MTLNSH-NSH2` no: dominated by KXMLSTOTAL-26OCT24MTLNSH-3/no (corr +0.26)
- `KXMLSGAME-26OCT24MTLNSH-TIE` yes: dominated by KXMLSTOTAL-26OCT24MTLNSH-3/no (corr +0.32)
- `KXMLSSCORE-26OCT24MTLNSH-MTL1NSH1` yes: dominated by KXMLSTOTAL-26OCT24MTLNSH-3/no (corr +0.30)
- `KXMLSGAME-26OCT24MTLNSH-NSH` no: dominated by KXMLSTOTAL-26OCT24MTLNSH-3/no (corr +0.24)
- `KXMLSSCORE-26OCT24MTLNSH-MTL0NSH0` yes: redundant with KXMLSTEAMTOTAL-26OCT24MTLNSH-NSH1/no (corr +0.64); best expression kept
- `KXMLSTOTAL-26OCT24MTLNSH-1` no: redundant with KXMLSTEAMTOTAL-26OCT24MTLNSH-NSH1/no (corr +0.64); best expression kept
- `KXMLS1HTOTAL-26OCT24MTLNSH-1` no: dominated by KXMLS1HSCORE-26OCT24MTLNSH-MTL0NSH0/yes (corr +1.00)
- `KXMLS1H-26OCT24MTLNSH-TIE` yes: dominated by KXMLS1HSCORE-26OCT24MTLNSH-MTL0NSH0/yes (corr +0.84)
- `KXMLS1H-26OCT24MTLNSH-NSH` no: dominated by KXMLS1HSCORE-26OCT24MTLNSH-MTL0NSH0/yes (corr +0.59)

## Events
- CF Montréal vs Nashville SC (Major League Soccer) 2026-10-24T17:30:00Z · markets 77/77 evaluated · lineups unknown · xG 0.80-1.51 · 1X2 20%/27%/53%
