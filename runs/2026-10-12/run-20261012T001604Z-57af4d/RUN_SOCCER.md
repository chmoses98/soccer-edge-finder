# RUN SOCCER — 2026-10-12
Run `run-20261012T001604Z-57af4d` generated 2026-10-12T00:16:06.817357Z · filters: {'leagues': [], 'games': ['fx:arg.primera:2026:arg.talleres:arg.independiente', 'fx:mex.liga_mx:2026:mex.pumas:mex.cruz_azul'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **5019** (discovery complete: True)
- contracts evaluated: 79 · excluded mechanically: 1871 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=79, unknown_family=3, unsupported_family=3066, unmapped_event=600, unmapped_team=6, no_fixture=120, filtered_by_operator=1144, unpriceable=1
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, BELGIANPL, BRASILEIRO, BRASILEIROB, BUNDESLIGA, CANPL, CHLLDP, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, EPL, EREDIVISIE, FA, FIFAW, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, SERIEA, SOCCER, SUPERLIG, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-12T00:16:04.203758Z; market_observed_at: 2026-10-12T00:13:26.152347Z; fixtures_observed_at: 2026-10-11T23:56:22.560379Z; results_observed_at: 2026-10-11T22:45:59.352701Z; model_fitted_at: 2026-10-12T00:16:03.079218Z; temporal_guard: {'decision_time': '2026-10-12T00:16:04.203758Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-11T23:56:22.560379Z', 'market_snapshots': '2026-10-12T00:15:54.144406Z', 'reference_odds': '2026-10-11T22:46:07.336130Z', 'results': '2026-10-12T00:16:04.046437Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (11)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Pumas UNAM vs Cruz Azul · Result: home · YES @ 0.2700 · fair 45.7% [30.0%–62.1%] · edge +17.3% · P(+) 92% · RESEARCH_ONLY · `KXLIGAMXGAME-26OCT11PUMCRA-PUM`
- Pumas UNAM vs Cruz Azul · Result: away · NO @ 0.5300 · fair 70.0% [55.9%–82.7%] · edge +15.3% · P(+) 92% · RESEARCH_ONLY · `KXLIGAMXGAME-26OCT11PUMCRA-CRA`
- Pumas UNAM vs Cruz Azul · First team to score: away · NO @ 0.4500 · fair 59.0% [45.8%–71.2%] · edge +12.3% · P(+) 90% · RESEARCH_ONLY · `KXLIGAMXFTTS-26OCT11PUMCRA-CRA`
- Pumas UNAM vs Cruz Azul · First-half result: away · NO @ 0.6400 · fair 75.2% [63.8%–85.2%] · edge +9.6% · P(+) 88% · RESEARCH_ONLY · `KXLIGAMX1H-26OCT11PUMCRA-CRA`
- Pumas UNAM vs Cruz Azul · away wins by more than 2.5 · NO @ 0.9000 · fair 95.0% [90.5%–98.5%] · edge +4.3% · P(+) 89% · RESEARCH_ONLY · `KXLIGAMXSPREAD-26OCT11PUMCRA-CRA3`
- Pumas UNAM vs Cruz Azul · First-half result: home · YES @ 0.2400 · fair 35.3% [22.8%–48.2%] · edge +10.0% · P(+) 85% · RESEARCH_ONLY · `KXLIGAMX1H-26OCT11PUMCRA-PUM`
- Pumas UNAM vs Cruz Azul · First half: away wins by more than 1.5 · NO @ 0.8900 · fair 93.6% [88.8%–98.1%] · edge +3.9% · P(+) 86% · RESEARCH_ONLY · `KXLIGAMX1HSPREAD-26OCT11PUMCRA-CRA2`
- Pumas UNAM vs Cruz Azul · away team total over 2.5 · NO @ 0.7700 · fair 85.0% [74.5%–93.8%] · edge +6.7% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT11PUMCRA-CRA3`
- Pumas UNAM vs Cruz Azul · away team total over 0.5 · NO @ 0.1900 · fair 28.7% [17.4%–40.8%] · edge +8.6% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT11PUMCRA-CRA1`
- Pumas UNAM vs Cruz Azul · Second-half result: away · NO @ 0.6300 · fair 72.9% [59.8%–84.2%] · edge +8.3% · P(+) 82% · RESEARCH_ONLY · `KXLIGAMX2H-26OCT11PUMCRA-CRA`
- Pumas UNAM vs Cruz Azul · away team total over 1.5 · NO @ 0.5100 · fair 63.0% [47.9%–77.4%] · edge +10.3% · P(+) 81% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT11PUMCRA-CRA2`

## Expressions removed by the reducer (7)
- `KXLIGAMXSPREAD-26OCT11PUMCRA-PUM2` yes: dominated by KXLIGAMXGAME-26OCT11PUMCRA-PUM/yes (corr +0.63)
- `KXLIGAMXSPREAD-26OCT11PUMCRA-PUM3` yes: dominated by KXLIGAMXGAME-26OCT11PUMCRA-PUM/yes (corr +0.39)
- `KXLIGAMXTEAMTOTAL-26OCT11PUMCRA-PUM2` yes: dominated by KXLIGAMXGAME-26OCT11PUMCRA-PUM/yes (corr +0.60)
- `KXLIGAMXTEAMTOTAL-26OCT11PUMCRA-PUM3` yes: dominated by KXLIGAMXGAME-26OCT11PUMCRA-PUM/yes (corr +0.50)
- `KXLIGAMXSPREAD-26OCT11PUMCRA-CRA2` no: dominated by KXLIGAMXGAME-26OCT11PUMCRA-CRA/no (corr +0.60)
- `KXLIGAMX1HSCORE-26OCT11PUMCRA-PUM1CRA0` yes: dominated by KXLIGAMX1H-26OCT11PUMCRA-PUM/yes (corr +0.66)
- `KXLIGAMXFTTS-26OCT11PUMCRA-PUM` yes: dominated by KXLIGAMXFTTS-26OCT11PUMCRA-CRA/no (corr +0.88)

## Events
- Pumas UNAM vs Cruz Azul (Liga MX) 2026-10-12T01:15:00Z · markets 79/80 evaluated · lineups unknown · xG 1.69-1.30 · 1X2 46%/25%/30%
