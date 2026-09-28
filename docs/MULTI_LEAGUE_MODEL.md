# Hierarchical multi-league strength model (`multi_league_v1`) — RESEARCH_ONLY

Module `src/soccer_edge/model/multi_league.py`; harness `research/multi_league.py`; result
`data/research/multi_league_v1.json` (result hash inside); frozen entry
`config/frozen_baselines.json#multi_league_v1`; tests `tests/test_multi_league.py`.
Nothing here changes `StrengthConfig` v1, `dc_laplace_v1` or any production path.

## 1. Why

`dc_laplace_v1` fits one league at a time. Inside a closed league only *relative* strength is
identified: adding a constant to every team's attack and defence leaves the likelihood unchanged.
Consequences: (a) UEFA fixtures cannot be priced (two teams from two leagues have no shared
scale); (b) a promoted side arrives with a "new team" prior instead of the strength it actually
earned in the division below. Both problems are one missing quantity: how strong each league is.

## 2. Model

For home team i, away team j, goals (x, y):

```
log lambda_home = att_i - def_j + home * (1 - neutral)
log mu_away     = att_j - def_i
P(x, y)         = tau_DC(x, y | lambda, mu, rho) * Poisson(x | lambda) * Poisson(y | mu)
```

Team effects are **absolute** and shared across every competition and division a team plays
in. The league structure enters through the prior:

```
att_i ~ N(L_k(i) + m_i, s_i^2)       def_i ~ N(L_k(i) + m_i, s_i^2)
L_k   ~ N(0, 0.30^2)                   soft sum_k L_k = 0  (sd 0.05)
home  ~ N(0.25, 0.15^2)                rho ~ N(0, 0.08^2)
```

where k(i) is the league team i currently belongs to (its most recent domestic match before the
fit date), s_i = 0.35 (0.45 with m_i = −0.15 for teams with < 8 decayed matches, exactly the
`StrengthConfig` v1 values). Writing att_i = a_i + L_k(i) with a_i league-relative gives the
familiar additive form

```
log lambda = a_i + L(league_i) - d_j - L(league_j) + home
```

so L_k is the league strength on the log-goal-rate scale, applied to both attack and defence:
a league-mean side from league k beats one from league m by 2·(L_k − L_m) in log goal-rate
ratio. The absolute parametrisation is what makes **promotion/relegation evidence**: a promoted
team keeps its parameter vector, and its results against first-division sides then identify
L(E0) − L(E1) exactly as a UEFA fixture would. No special "transition" machinery is needed;
both forms of cross-league evidence enter through the ordinary likelihood.

Time decay: the same exponential weights as v1 (ξ = 0.0065/day, half-life ≈ 107 d); rows older
than 730 days (weight < 0.9 %) are dropped for speed. Fitting: L-BFGS-B on the penalised
log-likelihood with the analytic gradient; the posterior covariance is the inverse observed
information (central differences of the gradient), i.e. the same Laplace construction as v1.
Runtime: ≈1–3 s per fit at 230–330 teams / 8–12k rows (P ≈ 470–680 parameters).

### Why the offset uncertainty is honest by construction

Within a closed league the direction (att_k + c, def_k + c, L_k + c) is a null direction of the
likelihood. The Laplace covariance along it is set only by the N(0, 0.30²) prior, so for a league
with no cross-play and no transferring teams the posterior sd of L_k stays ≈ 0.30 and shrinks as
cross-league rows accumulate. `MultiLeaguePosterior.offset_difference(a, b)` reports L_a − L_b
with its posterior sd from the full covariance (test: `test_offset_uncertainty_wider_without_cross_play`).

### Prior choices (documented, not tuned on the evaluation sample)

* `prior_sd_league = 0.30`: a 1-sd offset is a ~35 % goal-rate gap between league means, roughly
  the E0–E1 gap one expects a priori; the data dominate wherever cross-play exists.
* Team-effect priors: v1 values, so the within-league behaviour is as close as possible to the
  benchmark; the only structural additions are the offsets and the shared absolute scale.
* One shared home-advantage term (finals are neutral; the 2019-20 single-venue final-eight
  tournaments are treated as neutral). UEFA-specific home advantage is a known simplification.

### Elo-informed prior variant (`multi_league_v1_elo_prior`)

Pre-match ClubElo (point-in-time by construction) sets prior *means* only:
m_i = γ·(Elo_i − mean Elo of league k) for thin-history teams, and the league prior centre
l_k = γ·(mean Elo of league k − mean Elo of all modelled teams). γ is **estimated, not asserted**:
a Poisson regression of each side's goals on γ·(own Elo − opponent Elo) with a home term, fitted
on the 83,970 EXT16-league matches with Elo dated before 2017-07-01 (outside every evaluation
window). Fitted mapping (see `generated_from.elo_mapping` in the JSON):

| quantity | value |
|---|---|
| OLS goal difference per Elo point | 0.00484 goals/pt (home intercept 0.396) |
| Poisson γ (log goal-rate per pt, per side) | 0.00185 |
| implied total-strength (att+def) per pt | 0.00370 |
| Poisson home advantage | 0.308 |

So 100 Elo points ≈ 0.48 goals of expected goal difference between two average sides, and a
league-offset gap dL corresponds to an Elo gap of dL/γ points. Elo is results-derived, so the
variant stays DATA_ONLY; it is a third information set and is versioned separately.

## 3. Data and identity

* Domestic: `data/cache/Matches.csv`, leagues E0,E1,SP1,SP2,D1,D2,I1,I2,F1,F2 (core10) and
  +P1,N1,B1,T1,SC0,G1 (ext16), from 2017-07-01 (burn-in season 2017-18). Names resolve through
  the alias registry with the league's country as scope; unknown names get a **country-scoped**
  provisional id (`prov.fd.<ccc>.<slug>`) so a club keeps one id across divisions (the production
  provider keys provisional ids by division, which would break continuity — research-only choice,
  documented here; 266 provisional ids, none of them UEFA participants of the top-5 leagues).
* Cross-league: openfootball `champions-league` repo (the `europe-champions-league` repo is a
  mirror with identical files). Files that exist and were used: cl.txt 2014-15…2025-26,
  el.txt 2020-21…2024-25, conf.txt 2021-22…2024-25 (no 2025-26 el/conf, no 2026-27 files).
  Parser: stage headers (▪/»), date lines (year inferred as the candidate nearest the previous
  date, which handles per-group restarts and the August-2020 COVID finals), 90-minute scores
  (for a.e.t. lines the first bracketed pair), `[awarded]`/`[cancelled]` dropped.
  3,011 matches parsed, 220 distinct names, **0 unmapped** after `data/registry/uefa_clubs.json`
  (131 clubs outside the top-5 leagues, seed ids untouched, `ambiguous_team_aliases()` empty) plus
  an explicit three-entry table for openfootball spellings of seed clubs (`Bor. Mönchengladbach`,
  `1899 Hoffenheim`, `Lazio Roma`). No fuzzy matching anywhere.
* UEFA rows enter a fit only when both clubs have domestic history in the model; matches against
  clubs from unmodelled leagues are neither fitted nor scored.

## 4. Evaluation protocol

Chronological, strictly point-in-time, negative results kept. Cadence: core10 and the Elo
variant weekly (same as v1), ext16 and the pooled ablation every 14 days (between refits the last
posterior is used, which only makes the model staler). Probabilities are integrated over 100
posterior draws (the frozen v1 setting) with a vectorised score matrix that is exact for the
Dixon-Coles distribution.

(i) **Domestic aligned sample** — the walk_forward_v1 sample re-derived in-script: E0,SP1,D1,I1,F1,
Bet365 1X2 present, both teams seen ≥ 5 times in that league, seasons 2019-20…2025-26 (hybrid
weights fitted on seasons < S, ≥ 500 prior predictions). Single-league `dc_laplace_v1` is
recomputed with the v1 rules; the frozen numbers are quoted alongside for reference.

(ii) **UEFA out of sample** — CL/EL/ECL matches 2018-19…2025-26 where both clubs are modelled,
scored on the 90-minute 1X2 with no odds available, against: the UEFA base rate of earlier
seasons; a multinomial logistic on the latest domestic pre-match Elo difference (+ home flag),
fitted on the previous two domestic seasons plus earlier UEFA matches; and a *naive
single-league DC* that combines two per-league v1 posteriors as if the leagues were equally
strong (the gap the offsets are supposed to close).

## 5. Results

RESULTS_PLACEHOLDER

## 6. Validation state and limitations

* **Status: RESEARCH_ONLY.** Candidate for research pricing of UEFA fixtures only after the UEFA
  out-of-sample case above is reproduced on a further season prospectively; no production path
  reads this module.
* Cups and UEFA qualifying rounds are absent from the data, so league-only decayed weights
  slightly understate a European club's recent activity; the openfootball files start at the
  group/league phase.
* One shared home-advantage and rho across leagues and competitions.
* Second-division identity relies on football-data.co.uk spelling consistency across divisions
  (one diacritic variant, Preußen Münster, is normalised by the alias normaliser).
* Elo variant: the "latest domestic Elo" used as a UEFA feature lags by one domestic match.
* Aligned-sample comparison uses a 730-day window for the multi-league model vs all data since
  2017-07 for v1; the decayed weight beyond 730 days is < 0.9 %, so this is immaterial.
* Nothing here is evidence about Kalshi prices; the market benchmark is Bet365 pre-match.
