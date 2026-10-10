# RUN SOCCER — 2026-10-10
Run `run-20261010T223109Z-ae696d` generated 2026-10-10T22:31:14.650974Z · filters: {'leagues': [], 'games': ['fx:mex.liga_mx:2026:mex.juarez:mex.tijuana', 'fx:mex.liga_mx:2026:mex.queretaro:mex.atlante'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **6679** (discovery complete: True)
- contracts evaluated: 111 · excluded mechanically: 3499 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=111, unknown_family=3, unsupported_family=3066, unmapped_event=1102, unmapped_team=99, no_fixture=102, filtered_by_operator=2195, unpriceable=1
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, BELGIANPL, BRASILEIRO, BRASILEIROB, BRASILEIROC, BUNDESLIGA, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, EPL, EREDIVISIE, FA, FIFAW, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAMX, LIGAMX2H, LIGAPORTUGAL, LIGUE1, MLS, MLS2H, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, SERIEA, SOCCER, SUPERLIG, SVK2L, SVKCUP, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-10T22:31:09.055434Z; market_observed_at: 2026-10-10T22:28:30.817284Z; fixtures_observed_at: 2026-10-10T18:53:31.553836Z; results_observed_at: 2026-10-10T18:53:24.641195Z; model_fitted_at: 2026-10-10T22:31:07.685196Z; temporal_guard: {'decision_time': '2026-10-10T22:31:09.055434Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-10T18:53:31.553836Z', 'market_snapshots': '2026-10-10T22:31:02.771423Z', 'reference_odds': '2026-10-10T18:53:31.830324Z', 'results': '2026-10-10T22:31:08.859692Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (11)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Querétaro vs Atlante · away team total over 0.5 · NO @ 0.2800 · fair 50.1% [35.3%–64.5%] · edge +20.7% · P(+) 96% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT10QUEALA-ALA1`
- Querétaro vs Atlante · away team total over 1.5 · NO @ 0.6600 · fair 83.3% [72.0%–92.8%] · edge +15.8% · P(+) 95% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT10QUEALA-ALA2`
- Querétaro vs Atlante · away team total over 2.5 · NO @ 0.8900 · fair 95.6% [91.2%–99.0%] · edge +6.0% · P(+) 93% · RESEARCH_ONLY · `KXLIGAMXTEAMTOTAL-26OCT10QUEALA-ALA3`
- Querétaro vs Atlante · Exact score 1-0 (home-away) · YES @ 0.0900 · fair 15.4% [9.2%–21.5%] · edge +5.8% · P(+) 88% · RESEARCH_ONLY · `KXLIGAMXSCORE-26OCT10QUEALA-QUE1ALA0`
- Querétaro vs Atlante · First-half result: away · NO @ 0.7600 · fair 84.7% [75.9%–93.1%] · edge +7.4% · P(+) 85% · RESEARCH_ONLY · `KXLIGAMX1H-26OCT10QUEALA-ALA`
- Querétaro vs Atlante · Exact score 2-2 (home-away) · NO @ 0.9400 · fair 97.1% [95.4%–98.7%] · edge +2.7% · P(+) 97% · RESEARCH_ONLY · `KXLIGAMXSCORE-26OCT10QUEALA-QUE2ALA2`
- Querétaro vs Atlante · Exact score 2-0 (home-away) · YES @ 0.0700 · fair 11.7% [7.2%–16.0%] · edge +4.2% · P(+) 89% · RESEARCH_ONLY · `KXLIGAMXSCORE-26OCT10QUEALA-QUE2ALA0`
- Querétaro vs Atlante · away wins by more than 1.5 · NO @ 0.9000 · fair 94.5% [89.3%–98.5%] · edge +3.9% · P(+) 85% · RESEARCH_ONLY · `KXLIGAMXSPREAD-26OCT10QUEALA-ALA2`
- Querétaro vs Atlante · First half: both teams to score · NO @ 0.8000 · fair 86.8% [78.9%–94.1%] · edge +5.6% · P(+) 83% · RESEARCH_ONLY · `KXLIGAMX1HBTTS-26OCT10QUEALA-BTTS`
- Querétaro vs Atlante · First half: away wins by more than 1.5 · NO @ 0.9500 · fair 97.5% [94.9%–100.0%] · edge +2.2% · P(+) 85% · RESEARCH_ONLY · `KXLIGAMX1HSPREAD-26OCT10QUEALA-ALA2`
- Querétaro vs Atlante · Total goals over 1.5 · NO @ 0.2200 · fair 34.6% [17.9%–51.4%] · edge +11.4% · P(+) 80% · RESEARCH_ONLY · `KXLIGAMXTOTAL-26OCT10QUEALA-2`

## Expressions removed by the reducer (4)
- `KXLIGAMXBTTS-26OCT10QUEALA-BTTS` no: redundant with KXLIGAMXTEAMTOTAL-26OCT10QUEALA-ALA1/no (corr +0.79); best expression kept
- `KXLIGAMXFTTS-26OCT10QUEALA-ALA` no: dominated by KXLIGAMXTEAMTOTAL-26OCT10QUEALA-ALA1/no (corr +0.62)
- `KXLIGAMXGAME-26OCT10QUEALA-ALA` no: dominated by KXLIGAMXTEAMTOTAL-26OCT10QUEALA-ALA1/no (corr +0.46)
- `KXLIGAMX1HSCORE-26OCT10QUEALA-QUE1ALA1` no: redundant with KXLIGAMX1HBTTS-26OCT10QUEALA-BTTS/no (corr +0.72); best expression kept

## Events
- Querétaro vs Atlante (Liga MX) 2026-10-10T23:00:00Z · markets 79/80 evaluated · lineups unknown · xG 1.60-0.72 · 1X2 56%/26%/18%
- FC Juárez vs Tijuana (Liga MX) 2026-10-10T23:00:00Z · markets 32/32 evaluated · lineups unknown · xG 1.33-1.51 · 1X2 34%/25%/41%
