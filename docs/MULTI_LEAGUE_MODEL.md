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

Source of truth: `data/research/multi_league_v1.json` (result hash
`sha256:a716e7a09fc7df83db10d0271eb04e83b53bca3bafd4f32039dfa5232b0c075e`; assembled 2026-09-28 from the five
variant runs, 41–51 min each). Every number below is copied from that file.

### 5.1 Domestic aligned sample (E0, SP1, D1, I1, F1; 2019-20 → 2025-26; n = 12,338)

| family | log loss | Brier | ECE(home) | paired LL vs `dc_laplace_v1` [95% CI] | paired LL vs market [95% CI] |
|---|---:|---:|---:|---|---|
| `market_only.bet365_prematch_v1` | **0.97273** | 0.57828 | 0.016 | — | — |
| `data_only.multi_league_v1_elo_prior` | 0.99814 | 0.59563 | 0.029 | **−0.0028 [−0.0043, −0.0013]** | +0.0254 [0.0225, 0.0284] |
| `data_only.multi_league_v1` | 0.99876 | 0.59605 | 0.029 | **−0.0022 [−0.0036, −0.0006]** | +0.0260 [0.0231, 0.0292] |
| `data_only.multi_league_v1_ext16` | 0.99936 | 0.59646 | 0.027 | −0.0016 [−0.0032, +0.0002] | +0.0266 [0.0235, 0.0299] |
| `data_only.dc_laplace_v1` (frozen benchmark) | 1.00097 | 0.59769 | 0.032 | — | +0.0282 [0.0250, 0.0315] |
| `ablation.pooled_no_league_offset` | 1.00382 | 0.59959 | 0.027 | +0.0029 [+0.0009, +0.0051] | +0.0311 [0.0278, 0.0347] |

* The hierarchical model is a **small but real improvement on the single-league benchmark** (−0.002 to −0.003
  log loss, CI excluding 0), and the ablation shows the improvement comes from the league offsets: collapsing
  them (pooled) is *worse* than v1.
* It remains **+0.025 behind the market**, and the walk-forward hybrid weight on the market is 1.00 in every
  season for every variant: the extra information is already in the price.
* O/U 2.5 log loss: market 0.671, multi-league 0.682, v1 0.685 (same ordering, same gap).
* League offsets correlate 0.93 (core) / 0.95 (Elo prior) with the leagues' mean ClubElo; implied gaps vs E0:
  SP1 −47, I1 −56, D1 −66, F1 −7 Elo points (core), second divisions −160 to −290.

### 5.2 UEFA out-of-sample (CL/EL/ECL league-phase and knockout matches never used in any fit)

| sample | family | log loss | ECE(home) | vs Elo-difference logistic [95% CI] | vs naive single-league DC [95% CI] |
|---|---|---:|---:|---|---|
| core teams (n = 599) | `multi_league_v1_ext16` | **0.9876** | 0.024 | −0.001 [−0.026, +0.020] | −0.015 [−0.033, +0.003] |
| core teams | `ablation.pooled_no_league_offset` | 0.9878 | 0.041 | −0.001 [−0.024, +0.021] | −0.015 [−0.024, −0.006] |
| core teams | `baseline.elo_diff_logistic` | 0.9887 | 0.049 | — | — |
| core teams | `multi_league_v1` | 0.9922 | 0.045 | +0.003 [−0.022, +0.027] | −0.011 [−0.031, +0.009] |
| core teams | `baseline.naive_single_league_dc` | 1.0027 | 0.034 | — | — |
| core teams | `baseline.uefa_base_rate` | 1.0533 | 0.001 | — | — |
| ext16 teams (n = 1,224) | `baseline.elo_diff_logistic` | **0.9911** | 0.035 | — | — |
| ext16 teams | `multi_league_v1_ext16` | 1.0016 | 0.027 | +0.010 [−0.007, +0.027] | **−0.059 [−0.079, −0.039]** |
| ext16 teams | `ablation.pooled_no_league_offset` | 1.0224 | 0.006 | +0.031 [+0.010, +0.052] | −0.039 [−0.048, −0.029] |
| ext16 teams | `baseline.naive_single_league_dc` | 1.0611 | 0.041 | — | — |

* On UEFA fixtures the hierarchical model is **far better than pricing UEFA ties as if both clubs came from
  equally strong leagues** (−0.06 log loss on the wider sample) and **statistically indistinguishable from a
  one-feature Elo logistic** (CIs straddle 0 in both samples; Elo wins point-wise on the wider sample). In other
  words: the league offsets recover what a public Elo already knows, no more.
* No market benchmark exists for the UEFA sample in the free data, so nothing here says whether either would
  beat a bookmaker on UEFA prices. Pricing UEFA contracts with this family would be research pricing only.

### 5.3 Decision (pre-stated rules)

Rule "beats v1 walk-forward with CI excluding 0": **met** for `multi_league_v1` and `_elo_prior` on the
domestic sample. Rule "beats the market or moves the hybrid weight": **not met** (weight 1.00 everywhere).
Rule for UEFA: "beats the naive single-league combination": **met**; "beats the Elo baseline": **not met**.
Outcome: **RESEARCH_ONLY candidate for UEFA research pricing; not a replacement for v1 in production**
(the domestic gain is a tenth of the gap to the market and does not change any selection).


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
