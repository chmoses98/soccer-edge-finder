# Model families

| id | kind | what it is | status |
|---|---|---|---|
| `data_only.dc_laplace_v1` | DATA_ONLY | Dixon-Coles MAP with time decay (ξ=0.0065/day), per-team Gaussian shrinkage priors, Laplace posterior; analytic score matrix integrated over posterior samples | benchmark family; used in walk-forward research |
| `data_only.world_sim_v1` | DATA_ONLY | same posterior → correlated worlds → minute-level simulator; prices every supported family incl. HT, first goal, ET/pens | production pricing family; RESEARCH_ONLY |
| `market_only.bet365_prematch_v1` | MARKET_ONLY | proportional de-vig of Bet365 pre-match 1X2 and O/U 2.5 | research benchmark (not closing) |
| `market_only.kalshi_mid_v1` | MARKET_ONLY | Kalshi YES mid normalised across mutually exclusive legs | defined; wired into evaluation once captures accrue |
| `hybrid.logit_blend_v1` | HYBRID | softmax(w·log p_market + (1−w)·log p_data), w fitted walk-forward on earlier seasons only | research; weights reported per season |
| `baseline.league_base_rates` | baseline | prior seasons' 1X2 frequencies | research |
| `baseline.home_advantage_only` | baseline | league-average Poisson with fitted home advantage | research |
| `data_only.multi_league_v1` | DATA_ONLY | hierarchical multi-league Dixon-Coles: absolute team effects, per-league latent offset as the prior mean (sd 0.30), promotion/relegation and UEFA rows as cross-league evidence, Laplace posterior; leagues E0,E1,SP1,SP2,D1,D2,I1,I2,F1,F2 | RESEARCH_ONLY candidate; `docs/MULTI_LEAGUE_MODEL.md` |
| `data_only.multi_league_v1_ext16` | DATA_ONLY | same model, 16 leagues (+P1,N1,B1,T1,SC0,G1) so more UEFA fixtures are priceable | RESEARCH_ONLY |
| `data_only.multi_league_v1_elo_prior` | DATA_ONLY | same model with ClubElo-informed prior means for new teams and league offsets (Elo->log-rate mapping fitted on pre-window data) | RESEARCH_ONLY; third information set |
| `ablation.pooled_no_league_offset` | ablation | multi-league model with the offset prior collapsed to 0 (all leagues shrink to one pool) | ablation only, never a candidate |

Rules: no fake diversity (families differ in information set or mechanism, not in a tuning knob);
no closing prices leak into earlier horizons (MARKET_ONLY at time t uses only quotes observed
before t); DATA_ONLY is preserved so the value of market information can be measured.

Frozen baselines: `config/frozen_baselines.json` records the family id, config hash and the
research result hash it must be compared against; a change to a family bumps its version rather
than mutating the frozen entry.

Genuinely different research families on the roadmap (each needs its own out-of-sample case):
bivariate-Poisson / negative-binomial totals; xG-input strength (football-data.co.uk xG columns);
hierarchical multi-league strength for UEFA fixtures; Elo-derived probabilities as a third
information set.

## `data_only.xg_strength_v1` (Phase 11) — RESEARCH_ONLY, **NOT_EVALUATED**

Source: `src/soccer_edge/model/xg_family.py`. Same Dixon-Coles machinery as the benchmark; each match's
intensity target is `0.7·xG + 0.3·goals` where football-data.co.uk supplies `HxG/AxG` (2026-27 files for
E0/E1/SP1/D1/I1/F1/N1/P1), goals otherwise. Ingested through `FootballDataCoUkProvider.results_with_xg`
(`MatchResult.home_xg/away_xg`, `xg_source=football_data_couk`).

Evidence: none. There is no free historical xG for the 2018-19 → 2025-26 benchmark window
(`docs/XG_DATA_AUDIT.md`), so the family cannot be compared walk-forward to the frozen benchmark. It is not
priced, not promoted, and must not be until at least two full seasons of xG exist and the comparison in
`docs/CALIBRATION.md` has been run. Recorded as a negative/insufficient-data result, not a model.
