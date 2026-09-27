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
