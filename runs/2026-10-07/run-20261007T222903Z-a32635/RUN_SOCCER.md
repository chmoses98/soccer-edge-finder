# RUN SOCCER — 2026-10-07
Run `run-20261007T222903Z-a32635` generated 2026-10-07T22:29:04.169329Z · filters: {'leagues': [], 'games': ['fx:bra.serie_a:2026:bra.botafogo:bra.vasco'], 'window_hours': 3, 'confirmed_lineups_only': False}

## Coverage
- contracts discovered: **4985** (discovery complete: True)
- contracts evaluated: 14 · excluded mechanically: 1902 · unsupported/unknown: 3069
- **unaccounted contracts: 0**
- by disposition: priced=14, unknown_family=3, unsupported_family=3066, unmapped_event=847, unmapped_team=3, no_fixture=117, filtered_by_operator=935
- competitions discovered: APFDDH, ARGNACB, ARGPREMDIV, BELGIANPL, BRASILEIRO, BRASILEIROB, BRASILEIROC, BUNDESLIGA, CANPL, CHLLDP, CHNL1, CHNSL, CONCACAFGC, CONCACAFNL, CONMEBOLLIB, CONMEBOLSUD, COPAAMERICA, COPADELREY, COPADOBRASIL, DENSUPERLIGA, DFBPOKAL, DIMAYOR, ECULP, EFL, EFLCHAMPIONSHIP, EFLL1, EKSTRAKLASA, ENGNL, EPL, EREDIVISIE, FA, FIFAW, ISRNL, KLEAGUE, KNVB, LALIGA, LALIGA2, LIGAEXP, LIGAMX, LIGAPORTUGAL, LIGUE1, MLS, MLSEAST, MLSWEST, NWSL, PERLIGA1, PREMIERLEAGUE, SERIEA, SOCCER, SUPERLIG, SVK2L, TACAPORT, THAIL1, UCL, UCLLEAGUE, UECL, UEFAEURO, UEFANL, UEFANLGROUP, UEL, URYPD, USL, VENFUTVE, WC, WCW

## Freshness
- as_of: 2026-10-07T22:29:03.674161Z; market_observed_at: 2026-10-07T22:26:29.641015Z; fixtures_observed_at: 2026-10-07T18:55:34.293709Z; results_observed_at: 2026-10-07T18:55:24.925540Z; model_fitted_at: 2026-10-07T22:29:01.911113Z; temporal_guard: {'decision_time': '2026-10-07T22:29:03.674161Z', 'checked': {'fixtures': 1, 'market_snapshots': 2, 'reference_odds': 1, 'results': 15}, 'latest_observed_at': {'fixtures': '2026-10-07T18:55:34.293709Z', 'market_snapshots': '2026-10-07T22:28:49.317900Z', 'reference_odds': '2026-10-07T18:55:36.318949Z', 'results': '2026-10-07T22:29:03.496845Z'}, 'violations': [], 'ok': True}
- no freshness violations

## Recommendations
**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations.

## Shadow / research-only expressions (5)
These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations.
- Botafogo vs Vasco da Gama · Result: away · NO @ 0.5800 · fair 73.4% [60.4%–85.1%] · edge +13.7% · P(+) 91% · RESEARCH_ONLY · `KXBRASILEIROGAME-26OCT07BOTVDG-VDG`
- Botafogo vs Vasco da Gama · Result: home · YES @ 0.3200 · fair 47.8% [32.1%–63.9%] · edge +14.3% · P(+) 88% · RESEARCH_ONLY · `KXBRASILEIROGAME-26OCT07BOTVDG-BOT`
- Botafogo vs Vasco da Gama · away wins by more than 1.5 · NO @ 0.8000 · fair 89.0% [81.1%–95.4%] · edge +7.9% · P(+) 90% · RESEARCH_ONLY · `KXBRASILEIROSPREAD-26OCT07BOTVDG-VDG2`
- Botafogo vs Vasco da Gama · away wins by more than 2.5 · NO @ 0.9200 · fair 96.4% [92.9%–99.0%] · edge +3.9% · P(+) 91% · RESEARCH_ONLY · `KXBRASILEIROSPREAD-26OCT07BOTVDG-VDG3`
- Botafogo vs Vasco da Gama · btts · NO @ 0.3800 · fair 48.3% [35.6%–60.5%] · edge +8.7% · P(+) 81% · RESEARCH_ONLY · `KXBRASILEIROBTTS-26OCT07BOTVDG-BTTS`

## Expressions removed by the reducer (2)
- `KXBRASILEIROSPREAD-26OCT07BOTVDG-BOT2` yes: redundant with KXBRASILEIROGAME-26OCT07BOTVDG-BOT/yes (corr +0.62); best expression kept
- `KXBRASILEIROSPREAD-26OCT07BOTVDG-BOT3` yes: dominated by KXBRASILEIROGAME-26OCT07BOTVDG-BOT/yes (corr +0.38)

## Events
- Botafogo vs Vasco da Gama (Brasileirão Série A) 2026-10-07T23:30:00Z · markets 14/14 evaluated · lineups unknown · xG 1.60-1.11 · 1X2 48%/25%/27%
