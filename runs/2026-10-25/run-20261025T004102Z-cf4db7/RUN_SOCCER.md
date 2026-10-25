# RUN SOCCER — 2026-10-25
Run `run-20261025T004102Z-cf4db7` generated 2026-10-25T00:41:14.124330Z · filters: {'leagues': [], 'games': ['fx:usa.mls:2026:usa.colorado_rapids:usa.vancouver_whitecaps', 'fx:usa.mls:2026:usa.real_salt_lake:usa.st_louis_city'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **7132** (discovery complete: True)
- contracts evaluated: 109 · excluded mechanically: 3954 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=109, unknown_family=3, unsupported_family=3066, unmapped_event=1289, unmapped_team=383, no_fixture=157, filtered_by_operator=2125
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, AUTBUNDES, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, BUNDESLIGAW, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FRAPLW, HUNNB1, INDSL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAF, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, ROML1, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UCLW, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-25T00:41:02.424770Z; market_observed_at: 2026-10-25T00:37:44.479254Z; fixtures_observed_at: 2026-10-25T00:40:46.893699Z; results_observed_at: 2026-10-25T00:40:38.997799Z; model_fitted_at: 2026-10-25T00:41:00.727658Z; temporal_guard: {'decision_time': '2026-10-25T00:41:02.424770Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-25T00:40:46.893699Z', 'market_snapshots': '2026-10-25T00:40:37.691318Z', 'reference_odds': '2026-10-25T00:40:47.258202Z', 'results': '2026-10-25T00:41:02.170646Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (11)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Colorado Rapids vs Vancouver Whitecaps · Total goals over 3.5 · NO @ 0.6800 · fair 82.0% [70.5%–90.9%] · edge +12.5% · P(+) 92% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT24COLVAN-4`
- Colorado Rapids vs Vancouver Whitecaps · Total goals over 1.5 · NO @ 0.2200 · fair 36.8% [23.7%–49.5%] · edge +13.6% · P(+) 91% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT24COLVAN-2`
- Colorado Rapids vs Vancouver Whitecaps · away team total over 1.5 · NO @ 0.5500 · fair 69.1% [55.3%–80.9%] · edge +12.4% · P(+) 89% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT24COLVAN-VAN2`
- Colorado Rapids vs Vancouver Whitecaps · First-half exact score 0-0 (home-away) · YES @ 0.2800 · fair 39.2% [28.8%–50.2%] · edge +9.8% · P(+) 88% · RESEARCH_ONLY · `KXMLS1HSCORE-26OCT24COLVAN-COL0VAN0`
- Colorado Rapids vs Vancouver Whitecaps · away team total over 2.5 · NO @ 0.8100 · fair 88.9% [80.5%–95.3%] · edge +6.8% · P(+) 87% · RESEARCH_ONLY · `KXMLSTEAMTOTAL-26OCT24COLVAN-VAN3`
- Colorado Rapids vs Vancouver Whitecaps · First-half total goals over 1.5 · NO @ 0.6500 · fair 75.2% [64.8%–84.2%] · edge +8.6% · P(+) 85% · RESEARCH_ONLY · `KXMLS1HTOTAL-26OCT24COLVAN-2`
- Colorado Rapids vs Vancouver Whitecaps · Exact score 0-0 (home-away) · YES @ 0.0600 · fair 12.9% [7.0%–19.3%] · edge +6.6% · P(+) 93% · RESEARCH_ONLY · `KXMLSSCORE-26OCT24COLVAN-COL0VAN0`
- Colorado Rapids vs Vancouver Whitecaps · Total goals over 5.5 · NO @ 0.9400 · fair 97.1% [94.0%–99.2%] · edge +2.7% · P(+) 88% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT24COLVAN-6`
- Colorado Rapids vs Vancouver Whitecaps · Exact score 1-0 (home-away) · YES @ 0.0700 · fair 11.4% [7.2%–15.6%] · edge +3.9% · P(+) 88% · RESEARCH_ONLY · `KXMLSSCORE-26OCT24COLVAN-COL1VAN0`
- Colorado Rapids vs Vancouver Whitecaps · First-half total goals over 2.5 · NO @ 0.8800 · fair 92.5% [86.9%–97.1%] · edge +3.7% · P(+) 83% · RESEARCH_ONLY · `KXMLS1HTOTAL-26OCT24COLVAN-3`
- Real Salt Lake vs St. Louis City SC · Total goals over 0.5 · NO @ 0.0400 · fair 7.3% [3.1%–11.8%] · edge +3.0% · P(+) 81% · RESEARCH_ONLY · `KXMLSTOTAL-26OCT24RSLSTL-1`

## Expressions removed by the reducer (7)
- `KXMLSBTTS-26OCT24COLVAN-BTTS` no: redundant with KXMLSTOTAL-26OCT24COLVAN-2/no (corr +0.66); best expression kept
- `KXMLSTEAMTOTAL-26OCT24COLVAN-VAN1` no: dominated by KXMLSTOTAL-26OCT24COLVAN-2/no (corr +0.53)
- `KXMLSTEAMTOTAL-26OCT24COLVAN-COL1` no: dominated by KXMLSTOTAL-26OCT24COLVAN-2/no (corr +0.51)
- `KXMLSTOTAL-26OCT24COLVAN-1` no: dominated by KXMLSSCORE-26OCT24COLVAN-COL0VAN0/yes (corr +1.00)
- `KXMLS1HTOTAL-26OCT24COLVAN-1` no: dominated by KXMLS1HSCORE-26OCT24COLVAN-COL0VAN0/yes (corr +1.00)
- `KXMLSTOTAL-26OCT24COLVAN-3` no: redundant with KXMLSTOTAL-26OCT24COLVAN-4/no (corr +0.62); best expression kept
- `KXMLSTOTAL-26OCT24COLVAN-5` no: dominated by KXMLSTOTAL-26OCT24COLVAN-4/no (corr +0.62)

## Events
- Real Salt Lake vs St. Louis City SC (Major League Soccer) 2026-10-25T01:30:00Z · markets 32/32 evaluated · lineups unknown · xG 1.49-1.34 · 1X2 40%/26%/34%
- Colorado Rapids vs Vancouver Whitecaps (Major League Soccer) 2026-10-25T01:30:00Z · markets 77/77 evaluated · lineups unknown · xG 1.04-1.13 · 1X2 33%/30%/37%
