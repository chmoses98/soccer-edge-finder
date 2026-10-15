# RUN SOCCER — 2026-10-15
Run `run-20261015T002730Z-02c865` generated 2026-10-15T00:27:39.217066Z · filters: {'leagues': [], 'games': ['fx:usa.mls:2026:usa.colorado_rapids:usa.minnesota_united', 'fx:usa.mls:2026:usa.real_salt_lake:usa.san_jose_earthquakes'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **6350** (discovery complete: True)
- contracts evaluated: 158 · excluded mechanically: 3123 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=158, unknown_family=3, unsupported_family=3066, unmapped_event=1080, unmapped_team=60, no_fixture=138, filtered_by_operator=1843, unpriceable=2
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BRASILEIROC, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, EPL, EREDIVISIE, ESOCCER, FA, FRAPLW, HUNNB1, INDSL, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SAPSL, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-15T00:27:30.397595Z; market_observed_at: 2026-10-15T00:24:37.611542Z; fixtures_observed_at: 2026-10-14T23:18:26.993024Z; results_observed_at: 2026-10-14T22:52:00.486187Z; model_fitted_at: 2026-10-15T00:27:28.744246Z; temporal_guard: {'decision_time': '2026-10-15T00:27:30.397595Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-14T23:18:26.993024Z', 'market_snapshots': '2026-10-15T00:27:20.474146Z', 'reference_odds': '2026-10-14T22:52:10.440450Z', 'results': '2026-10-15T00:27:30.202821Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (10)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Real Salt Lake vs San Jose Earthquakes · btts · NO @ 0.3400 · fair 49.4% [37.5%–60.9%] · edge +13.8% · P(+) 93% · RESEARCH_ONLY · `KXMLSBTTS-26OCT14RSLSJ-BTTS`
- Real Salt Lake vs San Jose Earthquakes · Total goals over 3.5 · NO @ 0.5700 · fair 72.1% [57.2%–85.3%] · edge +13.4% · P(+) 88% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT14RSLSJ-4`
- Real Salt Lake vs San Jose Earthquakes · First-half total goals over 0.5 · NO @ 0.2200 · fair 31.9% [21.8%–43.2%] · edge +8.7% · P(+) 84% · RESEARCH_ONLY · `KXMLS1HTOTAL-26OCT14RSLSJ-1`
- Real Salt Lake vs San Jose Earthquakes · away team total over 1.5 · NO @ 0.5900 · fair 70.4% [56.3%–82.3%] · edge +9.7% · P(+) 83% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT14RSLSJ-SJ2`
- Real Salt Lake vs San Jose Earthquakes · First-half total goals over 1.5 · NO @ 0.5600 · fair 67.3% [54.8%–79.2%] · edge +9.5% · P(+) 85% · RESEARCH_ONLY · `KXMLS1HTOTAL-26OCT14RSLSJ-2`
- Real Salt Lake vs San Jose Earthquakes · First-half total goals over 2.5 · NO @ 0.8200 · fair 88.0% [79.9%–95.1%] · edge +5.0% · P(+) 81% · RESEARCH_ONLY · `KXMLS1HTOTAL-26OCT14RSLSJ-3`
- Real Salt Lake vs San Jose Earthquakes · Total goals over 0.5 · NO @ 0.0400 · fair 8.2% [3.5%–13.7%] · edge +4.0% · P(+) 86% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT14RSLSJ-1`
- Real Salt Lake vs San Jose Earthquakes · away team total over 2.5 · NO @ 0.8400 · fair 89.6% [81.3%–95.8%] · edge +4.7% · P(+) 82% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT14RSLSJ-SJ3`
- Real Salt Lake vs San Jose Earthquakes · Exact score 1-0 (home-away) · YES @ 0.0700 · fair 10.9% [6.5%–15.4%] · edge +3.4% · P(+) 83% · RESEARCH_ONLY · `KXMLSSCORE-26OCT14RSLSJ-RSL1SJ0`
- Real Salt Lake vs San Jose Earthquakes · home team total over 0.5 · NO @ 0.1400 · fair 22.8% [12.0%–35.0%] · edge +7.9% · P(+) 81% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT14RSLSJ-RSL1`

## Expressions removed by the reducer (7)
- `KXMLS1HBTTS-26OCT14RSLSJ-BTTS` no: dominated by KXMLS1HTOTAL-26OCT14RSLSJ-2/no (corr +0.69)
- `KXMLS1HSCORE-26OCT14RSLSJ-RSL0SJ0` yes: dominated by KXMLS1HTOTAL-26OCT14RSLSJ-1/no (corr +1.00)
- `KXMLSTOTAL-26OCT14RSLSJ-2` no: dominated by KXMLSBTTS-26OCT14RSLSJ-BTTS/no (corr +0.62)
- `KXMLSTEAMTOTAL-26OCT14RSLSJ-SJ1` no: dominated by KXMLSBTTS-26OCT14RSLSJ-BTTS/no (corr +0.74)
- `KXMLSTOTAL-26OCT14RSLSJ-3` no: redundant with KXMLSTOTAL-26OCT14RSLSJ-4/no (corr +0.64); best expression kept
- `KXMLSTOTAL-26OCT14RSLSJ-5` no: redundant with KXMLSTOTAL-26OCT14RSLSJ-4/no (corr +0.65); best expression kept
- `KXMLSTOTAL-26OCT14RSLSJ-6` no: dominated by KXMLSTOTAL-26OCT14RSLSJ-4/no (corr +0.42)

## Events
- Real Salt Lake vs San Jose Earthquakes (Major League Soccer) 2026-10-15T01:30:00Z · markets 79/80 evaluated · lineups unknown · xG 1.56-1.10 · 1X2 47%/26%/27%
- Colorado Rapids vs Minnesota United (Major League Soccer) 2026-10-15T01:30:00Z · markets 79/80 evaluated · lineups unknown · xG 1.71-0.98 · 1X2 53%/25%/22%
