# Pre-launch statistical audit — RUN SOCCER (2026-09-28)

Scope: `main` at `6890830`, archive branch `data-archive` at `7d196d3` (15 commits, 2026-09-27 23:42 →
2026-09-28 13:14 UTC). Read-only audit plus a small set of bug fixes (listed in §S). **No authority, threshold,
routing or model-family change was made.** `config/authority.json` is untouched (`default: RESEARCH_ONLY`).

Evidence convention: **VERIFIED** = reproduced in code/data during this audit; **INFERRED** = strong indirect
evidence, not reproducible from this container; **DESIGN** = proposal for a future versioned change.

---

## A. Executive verdict

**The system is not safe for any real-money use today, in any market family.** Nothing here is close: the
blocker is not a threshold that is almost met, it is that the evidence needed to judge the system *does not yet
exist and, until today, could not accumulate correctly*.

Minimum blockers (all must clear before *any* family can be considered for LIMITED):

1. **Zero settled prospective evidence** (0 settlements, 0 settled shadow recommendations with CLV). And
   `soccer settle` fetches results only for the 8 openfootball leagues, so **93.5% of current prediction
   records (1,342 / 1,435) and 127 / 142 shadow recommendations can never settle** (Nations Leagues,
   friendlies, Ligue 1, Americas are not covered).
2. **The evidence archive was lossy.** `archive_publish.sh` overwrote append-only `.jsonl` day files; the 830
   prediction records of run `4f9bfb` are gone from the archive tip (only in git history). Fixed going forward
   in this change; historical recovery is pending (§O).
3. **The production pricer is not the model that was benchmarked.** Every research number (12,248-match
   walk-forward etc.) scores the *analytic* Dixon-Coles matrix; production prices through `worlds_v1` +
   `minute_engine_v1`, which drops the fitted ρ and adds unfitted game-state/red-card dynamics. No historical
   evidence exists for the production path.
4. **The DATA_ONLY model has a known structural defect** (no scoring intercept: away goals −11%) and, even with
   the best research fix, trails Bet365 by +0.019 log loss with a HYBRID weight of 1.00. It has shown no
   incremental information over a sharp market in any family, league or season.
5. **No sharp near-close reference exists** (reference capture is football-data `fixtures.csv`, updated a few
   times a week; 41/41 rows skipped on the first live capture). Without it there is no TRUE_CLOSE and no
   reference-anchored edge — which is the only edge hypothesis with a plausible mechanism (§G, §H).
6. **Kalshi close capture is too sparse** for TRUE_CLOSE (3 captures in 13.5 h; last at 03:35Z vs earliest
   kickoff 16:00Z); GitHub cron slots were dropped (espn-lineups fired 1 of 4 slots; run-soccer's scheduled
   slots produced no runs — all 6 runs were manual dispatches).

The honest one-line summary: **the infrastructure is impressive and mostly correct; the predictive edge is
unproven and, on all historical evidence, absent for DATA_ONLY; the betting edge is untested.** The fastest
responsible path to real money is *not* fixing DATA_ONLY first — it is (i) making the evidence pipeline
lossless and complete, (ii) acquiring a sharp near-close reference, and (iii) testing a reference-anchored
`edge_v2` on fee-aware CLV. DATA_ONLY fixes run in parallel as research.

---

## B. Critical defects (ranked by severity)

| # | Defect | Status | Evidence | Effect on fair probabilities / evidence |
|---|---|---|---|---|
| B1 | Archive publish overwrote append-only `.jsonl` day files (predictions, lineups, weather) | **VERIFIED, FIXED** (§S1) | `predictions/2026-09-28/predictions.jsonl` = 830 rows (run 4f9bfb) at `7383daa`, 1,318 rows all from run fdefb8 at `7d196d3`; lineups 5→3 rows at `68b1249`; `index.json` references missing records | Destroys the prospective evidence every promotion gate depends on |
| B2 | Production pricer ≠ benchmarked model: engine ignores ρ; game-state (×1.08 trailing / ×0.93 leading) and red-card (0.12/team, ×0.65/×1.25) multipliers applied on top of a λ fitted as a full-match mean; world inflation σ 0.058 | **VERIFIED** (not fixed: model change) | `sim/engine.py` never reads `worlds.rho`; table below; `test_engine_honours_dixon_coles_rho` (strict xfail) | Up to ±1.5 pt on draw, −1.2 pt O2.5 for strong favourites, BTTS +1 to +1.6 pt, favourite goals −3% — same order as the edges being claimed |
| B3 | No scoring intercept in `dc_laplace_v1` | **VERIFIED** (research + this audit) | μ 1.127 vs realised 1.270 in every league; γ̂ 0.295 vs realised log-ratio 0.190; `test_fitted_away_level_matches_training_away_level` (strict xfail); intercept model passes it (ratio 0.995) | P(home) +2.9, P(away) −1.9, P(O2.5) −3.0, BTTS −5, AH home-cover +3.6 pts on *all* matches; away favourites ≥0.7 under-rated by 19.5 pts |
| B4 | Settlement covers only 8 openfootball leagues | **VERIFIED** (not fixed: needs ESPN results wiring) | `cli.py:295-313` | 93.5% of records unsettleable → no evidence for those cells ever |
| B5 | Authority CLV gate was side-agnostic YES drift; CLV and the "market" log-loss benchmark treated empty-book sentinels (bid 0 / ask 1) as prices | **VERIFIED, FIXED** (§S2) | `model_health` averaged `clv_yes_points` over all contracts (cancels across exclusive legs); 27% of snapshot rows have `yes_bid=0`; 411/1,435 records have a sentinel or ≥50¢ book | Promotion would have been decided on noise |
| B6 | Market freshness gate could never fail | **VERIFIED, FIXED** (§S3) | `as_of` taken before the 13-min sweep; `market_observed_at = finished_at` → age −13.2 min on every record | Stale quotes could never be rejected |
| B7 | International pool is a label, not a model: neutral venue dropped in fitting; shrinkage toward the pool mean; club priors and decay; ESPN neutral flag apparently never set | **VERIFIED** (fit drops flag) / **INFERRED** (ESPN extraction) | `rows_from_results` omits `neutral_site`; 0 / 1,014 archived intl results neutral vs **36%** neutral in the CC0 international results dataset since 2022 (34% of friendlies) | San Marino 25% to beat Albania; +50% "edges" at 2¢ |
| B8 | Lineup "confirmed" label ignored capture time | **VERIFIED, FIXED** (§S4) | 1 of 1 "confirmed" XI was captured at 11:01 for an 11:00 kickoff | Backward leakage into any lineup study |
| B9 | NO-side depth always missing; no depth/VWAP or liquidity gate; retail cent-alignment fee not modelled | **VERIFIED**; depth read **FIXED** (§S5) | `no_ask_size` null in 10,342/10,342 snapshot rows; `walk_book` never called; `min_liquidity_contracts = 0` | All 90 NO shadows had `available_size=None`; true break-even up to 1¢ higher for small retail fills (flips 3/142 shadows) |
| B10 | Sim-cache repricing: 20-bin histogram replaced world probabilities; payoff vectors rebuilt from one shared `default_rng(0)` stream (comonotone — mutually exclusive legs look positively correlated) | **VERIFIED, FIXED** (§S6) | P(edge>0) 0.762 → 0.889 on a test case; `expr(a) != expr(b)` between fresh and cached runs before the fix | Dormant (CI cache is always cold) but would flip gates and corrupt the correlated-duplicate reducer |
| B11 | `P(edge>0)` is structurally uninformative | **VERIFIED** (research) | Spearman(bucket, realised) −0.03 / −0.37; selection proxy claims +10.7%, realises −3.3% (de-vig+fee) / −13.6% (Bet365 odds); hit rate falls 36%→19% with the bucket | Ranks model–market disagreement, and the market is right |
| B12 | Research candidates selected on the evaluation sample | **VERIFIED** (process) | intercept/decay/k̂ variants chosen on 2019-26 aligned sample; k̂ OOS group-score gain +0.00027 [−0.00037, +0.00083] | Claimed gains are in-sample until a holdout confirms them |
| B13 | Ledger cannot detect deleted records | **VERIFIED** (not fixed) | `archive/ledger.py:11` promises a manifest that does not exist; `verify()` rehashes surviving lines only | Tampering by deletion — exactly what B1 did — goes unnoticed |
| B14 | `pedge_eval` read the reference from a key records never write; a NO recommendation's reference was read as YES | **VERIFIED, FIXED** (§S7) | `beat_reference` null on all 2,498 rows | Reference comparison silently empty |

### B2 detail — production engine vs the benchmarked analytic model (VERIFIED, this audit)

Identical λ, μ, ρ = −0.10 per row (200k realisations each; script in the audit session scratchpad):

| λ / μ | model | P(H) | P(D) | P(A) | P(O2.5) | BTTS | E[home] / E[away] |
|---|---|---|---|---|---|---|---|
| 1.52 / 1.13 | analytic DC (**benchmarked**) | .450 | .279 | .270 | .494 | .541 | 1.52 / 1.13 |
| | engine, dynamics off (ρ ignored) | .462 | .256 | .282 | .496 | .531 | 1.523 / 1.131 |
| | engine, production `worlds_v1` | .452 | .272 | .275 | .491 | .547 | 1.503 / 1.135 |
| 2.30 / 0.80 | analytic DC | .703 | .191 | .106 | .599 | .504 | 2.30 / 0.80 |
| | engine, production | .700 | .188 | .111 | **.587** | .512 | **2.225** / 0.821 |
| 1.00 / 1.90 | analytic DC | .184 | .242 | .574 | .554 | .548 | 1.00 / 1.90 |
| | engine, production | .189 | .239 | .572 | .547 | .554 | 1.013 / **1.855** |

The game-state dynamics happen to re-create ~60–70% of the missing ρ draw inflation, by coincidence, and they are
not mean-preserving: the favourite's expected goals fall 2–3%. The existing test
`test_sim_matches_analytic_when_dynamics_disabled` compares against ρ = 0 and therefore hides this.

---

## C. Model audit

### C1. Dependency map (production path, `run-soccer`)

```
football-data redistribution (E0,SP1,D1,I1,F1,…)  ─┐                          ESPN archive (Americas + intl pool)
openfootball current season (8 leagues)            ├─► MatchResult rows ──────────┘   (neutral_site: never true; dropped anyway)
                                                    │   rows_from_results(): date, home, away, goals   [weight=1, NO neutral]
                                                    ▼
                         fit_competition(): lookback 730 d, r.date < as_of (today's results excluded)
                                                    ▼
      DixonColesFitter (dc_laplace_v1)  MAP + Laplace
        log λ = a_h − d_a + γ          log μ = a_a − d_h          τ_DC(x,y; λ, μ, ρ)
        priors a,d ~ N(0,.35²) | new team (<8 eff. matches) N(−.15,.45²); γ ~ N(.25,.15²); ρ ~ N(0,.08²)
        soft Σa = Σd = 0 (sd .05/√n)  ◄── the missing-intercept defect      decay e^(−.0065·days)
        cov = inverse finite-difference Hessian (+1e-6 I), eigen-clipped when sampled
                                                    ▼
      WorldGenerator (worlds_v1), 1,000 worlds                                                    [lineups: never populated]
        θ_w ~ N(θ̂, Σ)  → λ_w, μ_w, ρ_w (ρ_w unused downstream)
        × lineup mult (1 − .6·min(Σ absent importance, .35))                                     [no-op in production]
        × env e^N(0,.03²) × model e^N(0,.05²) (shared by both teams)
        red hazard ~ Gamma(20, .12/20)/90 per team; trailing ~ N(1.08,.04²), leading ~ N(.93,.04²)
                                                    ▼
      minute_engine_v1: 100 draws/world, 90 × Poisson(rate·profile(t)·state·red); profile: 2nd-half share .54,
        ±12.5% ramp; HT at 45'; first goal (same-minute coin flip); ET = one Poisson(30·rate·.85); pens .5
                                                    ▼
      semantics.settle(outcome) → indicator (N draws) → pricer: p_w = mean over draws in world w;
        fair = mean_w p_w; 80% interval = world quantiles; coherence audit (1-pt tolerance)
                                                    ▼
      edge_v1: be = ask + fee(ask, C=1); fee_adj = fair − be; P(edge>0) = mean_w[p_w > be]; worst = Q.20(p_w) − be
        robust = fee_adj ≥ .02 ∧ P ≥ .80 ∧ worst > 0      (last two are ≈ the same condition)
                                                    ▼
      expression reducer (payoff corr ≥ .6 single-linkage per fixture) → authority matrix (all RESEARCH_ONLY)
        → shadow list; prediction ledger; app contract
```

### C2. Constants: fitted vs configured

**Fitted per run (MAP):** attack/defence per team, γ, ρ, Laplace covariance — per competition, independently.

**Configured, never fitted or validated for the production path** (each is a candidate for a walk-forward
estimate or an explicit prior justification):

| constant | value | where | validation status |
|---|---|---|---|
| decay ξ | 0.0065/day (half-life 107 d) | `StrengthConfig` | research: 0.003 better (−0.0068 LL, CI excl. 0) — in-sample |
| team prior sd | 0.35 (new 0.45) | `StrengthConfig` | research: 0.60 better (−0.0028) — in-sample |
| new-team mean / threshold | −0.15 / 8 eff. matches | `StrengthConfig` | research: LL moves < 0.001; H3 rejected |
| γ prior | N(0.25, 0.15²) | `StrengthConfig` | absorbs the missing intercept |
| ρ prior / clip | N(0, 0.08²) / ±0.29 fit, ±0.3 sample | `strength.py` | **fitted then discarded by the engine** |
| identifiability penalty | sd 0.05/√n on Σa, Σd | `strength.py:220` | **root cause of B3** |
| lookback | 730 d | `modeling.py` | negligible under ξ |
| σ_model, σ_env | 0.05, 0.03 | `WorldConfig` | research: no effect on P(home) width (<0.001) |
| red-card rate, effects | 0.12/team, ×0.65 own, ×1.25 opp | `WorldConfig` | literature; not fitted |
| game-state multipliers | 1.08 / 0.93 ± 0.04 | `WorldConfig` | literature; **not mean-preserving** |
| 2nd-half share, ramp | 0.54, 0.25 | `SimConfig` | literature; football-data HTHG/HTAG could fit it |
| ET intensity, penalties | 0.85, P(home)=0.5 | `SimConfig` | unvalidated |
| lineup cap, non-recovery | 0.35, 0.6 | `worlds.py` | unvalidated (and unused) |
| interval level | 0.80 | `RunConfig` | — |
| edge gates | 0.02 / 0.80 / Q0.20 | `EdgeConfig` | proxy: selection loses 3.3–13.6% |
| coherence tolerance | 1 pt | `pricing/coherence.py` | engineering |

### C3. Assumptions and where uncertainty is arbitrary

* Independence: goals per minute Poisson and conditionally independent given state; the only home–away coupling is
  game state, red cards and the shared world inflation — ρ (the fitted coupling) is dropped. ET and pens ignore
  red-card and state history. Players available independently (unused).
* Arbitrary uncertainty: σ_model and σ_env are hand-set; the posterior scale is the raw Laplace covariance
  (outcome-estimated k̂ = 0.81 not adopted); p_w carries binomial MC noise from 100 draws (median 13.5% of p_w
  variance, p90 50% — the "worst case" gate is partly Monte-Carlo noise); P(edge>0) has no term for model bias vs
  a sharp reference.
* Potential double counting: game-state dynamics on top of a λ that already contains average game-state
  behaviour; ρ fitted (absorbing low-score dependence) but the engine re-creates dependence differently; the two
  robust-edge gates `P ≥ 0.8` and `Q.20 > be` are one condition counted twice.
* Research ≠ production: benchmark = analytic DC, weekly refit, no lookback; production = engine, daily refit,
  730-d lookback, per-competition fits, ESPN-pooled internationals with no benchmark.

### C4. Leakage audit

* **No market information reaches DATA_ONLY** (VERIFIED): `MatchRow` has no odds field; `inputs.py` uses
  `hm.result` only; odds are used only in MARKET_ONLY/HYBRID de-vig and research; hybrid weights are fitted on
  earlier seasons only.
* Point-in-time: `r.date < as_of` (date granularity) excludes all of today's results — conservative, cannot leak.
  A priced fixture is never in training (kickoff ≤ as_of → STARTED disposition).
* Leakage risks found: lineup "confirmed" label (B8, fixed); HTTP fetch cache can serve a 6 h-old response
  stamped with its original fetch time (runners start cold, dormant); research model selection on the
  evaluation sample (B12).
* Guard to add: any future xG, lineup or reference feature must carry an `observed_at` strictly before the
  prediction `as_of`, enforced by a schema check (see §P step 3).

---

## D. Home/away fix (DESIGN — versioned `dc_laplace_v2`, never edits v1)

**Is the missing intercept truly the root cause?** Yes, by likelihood argument and evidence. With Σa = Σd = 0
enforced, mean log μ = mean(a) − mean(d) = 0, so the away baseline is exp(0) = 1.0 whatever the league; γ must
then fit the *home level* (log 1.53 ≈ 0.43, pulled to 0.295 by its prior) instead of the home/away *ratio*
(realised 0.190). Every downstream symptom follows: μ −11% in all leagues, bias scales with the league's away
rate (D1 1.42 → largest; SP1 1.11 → smallest), and one extra parameter removes the >10-pt bucket bias
(+0.061 → +0.007). Alternatives compared:

| alternative | identifiable? | assessment |
|---|---|---|
| global scoring intercept κ | yes | **the fix**; per-league fits make it league-specific automatically |
| league-specific κ_c in a pooled/multi-league fit | yes | required once leagues are pooled (multi_league_v1 has only one γ and centres att/def on the same L_k, so its per-league scoring level is only prior-regularised — re-check its μ bias) |
| season-level drift κ_{c,s} (random walk, sd τ) | yes with prior | test; 2020-21 empty stadiums show γ/level drift; decay partially absorbs it |
| home/away-specific intercepts κ_H, κ_A | **same model** as κ + γ (reparameterisation) | not a separate candidate; do not "test" it as one |
| team-specific home advantage γ_i ~ N(γ, 0.1²) | yes with prior | secondary candidate after κ |
| hard vs soft sum-to-zero on a, d | likelihood-identical | use hard centring (drop one dof) *with* κ free; soft penalty is fine once κ exists |

**Proposed `dc_laplace_v2`:**

```
log λ_ij = κ_c + a_i − d_j + γ_c · (1 − neutral_ij)       log μ_ij = κ_c + a_j − d_i
Σ_i a_i = Σ_i d_i = 0 (hard, per competition)   κ_c ~ N(log(mean away goals of prior seasons), 0.3²)
a_i, d_i ~ N(0, s²)   s ∈ {0.35, 0.50, 0.60} (pre-registered grid)   γ_c ~ N(0.20, 0.10²)   ρ ~ N(0, 0.08²)
decay ξ ∈ {0.0065, 0.004, 0.003} (grid)   MatchRow gains `neutral` (default False)
```

`research/dc_intercept.py` is the reference implementation of κ.

**Acceptance test (pre-registered, fails closed):**

1. *Protocol*: model-selection seasons 2019-20 … 2023-24 (grid chosen here only); **confirmation holdout
   2024-25 + 2025-26**, scored once with the chosen configuration. Same aligned sample definition as
   `walk_forward_v1`.
2. *Likelihood*: penalised log-likelihood gain of κ per league-season reported; the in-sample LR statistic must
   exceed χ²₁ 99% (6.63) in ≥ 90% of league-season fits.
3. *Level calibration (holdout)*: |mean μ̂ / mean away goals − 1| ≤ 2% and same for λ̂ in every league;
   O/U 2.5 mean bias ≤ 1.0 pt; away-over-0.5 bias ≤ 1.5 pt; BTTS mean bias ≤ 1.5 pt.
4. *Calibration*: home ECE ≤ 0.020 (v1 0.033); >10-pt disagreement-bucket bias |data − realised| ≤ 0.02.
5. *Walk-forward skill*: paired 1X2 LL vs v1 on the holdout, 95% bootstrap CI upper bound < 0; O/U 2.5 LL
   CI upper < 0.
6. *Market-relative*: gap to Bet365 (and to Pinnacle close, §H) reported with CI — **no requirement to beat the
   market**; HYBRID weight reported.
7. *Regression tests*: `test_fitted_away_level_matches_training_away_level` must pass (remove its strict xfail).
8. Re-run `research/recalibration.py` on v2 (k̂ is a property of the fitted posterior).

---

## E. International model fix (DESIGN — `intl_hier_v1`)

**Current state (VERIFIED):** the "distinct family" is `data_only.world_sim_v1.intl_pool` — an id only. The
fit is the club `DixonColesFitter` with club priors on an ESPN pool of ~1,000 results since 2024, weight 1 for
friendlies, neutral dropped (and never set), 107-day half-life (a national team's effective sample ≈ 4.7 matches,
so almost every team sits on the new-team prior), sum-to-zero over ~200 nations — minnows shrink toward an
*average national team*, not toward where minnows are. This is the actual mechanism behind "minnows not shrunk
enough": the shrinkage target is wrong, not the shrinkage strength. `uefa.euro`, `fifa.world_cup`,
`copa_america`, `gold_cup` have no pool → NO_MODEL.

**Data**: `martj42/international_results` (CC0; 49,547 matches 1872 → 2026-08-26; columns date, teams, score,
tournament, city, country, **neutral**; reachable from this container). This gives the historical walk-forward
benchmark that does not exist today and the neutral flag ESPN is not providing. ESPN remains the live
fixture/results feed; map team ids through the alias registry.

**Hierarchy:**

```
log λ = κ + a_h − d_a + γ_T · home_h        log μ = κ + a_a − d_h + γ_T · home_a      (home_x = 1 only if x plays at home, non-neutral)
a_i = A_{conf(i)} + β_a · e_i(t) + α_i        d_i = D_{conf(i)} + β_d · e_i(t) + δ_i
A_c, D_c ~ N(0, 0.30²), soft Σ_c = 0           α_i, δ_i ~ N(0, s_T²) (s_T small: 0.15–0.25)
e_i(t) = standardised point-in-time Elo computed from the same archive (never an external rating snapshot)
γ_T by match type T ∈ {competitive, friendly}; tournament-host flag = home
likelihood weight w_T: w_competitive = 1, w_friendly ∈ {0.4, 0.6, 0.8, 1.0} (grid; tempering, not a heuristic)
decay: half-life ∈ {1, 2, 3} years; optional per-team random walk on α_i (sd 0.05/yr) instead of pure decay
```

* **Sparse teams** shrink toward `A_conf + β·Elo` (the right centre) with the Laplace covariance widening
  automatically; teams with < 10 weighted matches get their prior sd inflated ×1.5.
* **Confederation strength** is identified only by cross-confederation matches; report the count per
  confederation pair and let the prior carry the rest (the multi-league null-direction argument).
* **Connectivity**: compute the match graph per fit; teams outside the giant component or with < 3
  cross-confederation opponents in 4 years are flagged `LOW_CONNECTIVITY` and never surface as shadows.
* **Era drift**: decay + random walk; no manual era cuts.
* No minnow penalty, no rank-based override — every effect is a parameter with a prior and a likelihood.

**Acceptance test:**

1. Walk-forward, monthly refit, 2014 → 2026; selection 2014–2021, **holdout 2022–2026** (≈ 4,700 matches).
2. Baselines: (a) ordinal-logit on point-in-time Elo difference + home/neutral; (b) current `intl_pool` config
   refitted on the same data. `intl_hier_v1` must beat both on holdout 3-way LL (paired CI upper < 0), separately
   for competitive matches and friendlies.
3. Mismatch calibration: for Elo gap ≥ 300, |mean predicted underdog-win − realised| ≤ 2 pts (n reported); no
   single match with Elo gap ≥ 400 priced with P(underdog win) > 2× the holdout realised rate for that bin.
4. Neutral handling: γ̂ on non-neutral competitive matches reported; neutral matches predicted with γ = 0;
   listed-home goals on neutral matches (1.415) vs away (1.263) reproduced within MC error.
5. ECE ≤ 0.03 per outcome; coverage of every Kalshi intl competition in the 48 h window.
6. Until all pass, `intl_pool` records stay out of every shadow list (not only out of evidence cells).

---

## F. Uncertainty fix

**Current defect:** `worlds_v1` uses the raw Laplace covariance (k = 1) plus hand-set inflation; P(home) 80%
intervals contain the de-vigged market 92.9% of the time.

**Is k = 0.81 defensible?** As a single global scalar for `dc_laplace_v1`, yes — it passed a pre-registered,
outcome-based rule (CI 0.73–0.89, 6/7 seasons below 1) and did not target the market. But it is too crude to
carry forward:

* it is estimated on a misspecified model (the de-meaning step only partly removes the missing-intercept bias);
* per-season k̂ ranges 0.0 → 1.04; SP1 alone is 0.53; the OOS proper score gain is not significant;
* it barely changes fair means (1X2 LL 1.00100 → 1.00068) and cannot fix P(edge>0), whose problem is bias;
* league / family / favourite / horizon / lineup-state scales **cannot be estimated historically** (one
  pre-match snapshot per match, no horizon, no lineups) and should not be invented.

**Recommendation — decompose, then scale:**

1. Keep `worlds_v1` frozen. Do **not** adopt 0.81 into production now.
2. In `worlds_v2` (on `dc_laplace_v2`): (a) parameter uncertainty = Laplace × k, with k re-estimated by the same
   grouped-residual estimator on v2; (b) remove per-world MC noise by computing p_w **analytically** from the
   per-world DC matrix for full-time families (exact p_w, 1,000 worlds, no binomial noise); (c) add a separate
   **structural term** σ_struct(family): the walk-forward sd of (model − sharp reference) in logit units, by
   family, used only by `edge_v2` (§G) — this is the uncertainty that actually decides bets.
3. Horizon- and lineup-state scales: left at k (conservative) until ≥ 1 season of prospective data; then
   estimate with the same grouped estimator on settled records.
4. Acceptance: k̂ CI excludes 1 and ≥ 5/7 seasons same side (as R2); totals PIT variance z within ±3 on holdout;
   interval coverage vs *outcomes* via the grouped estimator; market-inside rate is a sanity diagnostic only
   (expected 75–88%).

---

## G. edge_v2

**Should `P(edge>0)` survive?** Not as a decision variable. It is **correctly computed but improperly named and
evaluated against the wrong target**: it is the share of the model's own posterior worlds in which the model
beats the price, so it measures the distance between the model's centre and the price in units of the model's
own dispersion. Against a market that is sharper than the model, the largest values select the model's
largest errors (claimed-minus-realised gap grows +0.07 → +0.17 across buckets). Rename it
`model_posterior_edge_share`, keep it as a diagnostic, remove it from `robust`.

**Definition (`edge_v2`, versioned; RESEARCH_ONLY until §Q):**

```
p_ref(t)   = de-vigged sharp reference for the same contract & side (Pinnacle if present, else consensus; power de-vig),
             observed within 15 min of the decision; else edge_v2 = NOT_EVALUATED
p*         = p_ref + w_family · (p_model − p_ref)          w_family from walk-forward stacking; today w = 0 ⇒ p* = p_ref
be_exec    = VWAP(ask, target size) + fee_retail(VWAP, C) / C     (cent-aligned retail fee, §S5 note)
EV_net     = p* − be_exec                                  (probability points per $1 contract)
σ_edge²    = σ_devig² (spread between proportional/power/Shin de-vig + cross-book dispersion)
           + σ_stale² (reference age × empirical drift/min)
           + w² · σ_struct²(family)
edge_v2_lcb = EV_net − 1.645 · σ_edge
select iff  edge_v2_lcb ≥ 0.010  ∧  EV_net ≥ 0.020  ∧  depth at be_exec ≥ target size  ∧  spread ≤ 4¢
```

**Evaluation target:** fee-aware CLV against TRUE_CLOSE (reference close) and KALSHI_CLOSE (§K) — the low-variance
proxy for expected value — with realised ROI as a guardrail only. Not ROI optimisation on a small sample.
Alternatives considered: expected log-growth (needs a calibrated p*; derived from EV_net once p* is validated);
P(beat close) (a good *secondary* target once ≥ 500 CLV observations exist, fitted by logistic regression on
EV_net); lower credible bound on EV under the model posterior (rejected: that is edge_v1).

---

## H. Hybrid / market model

**Does DATA_ONLY add information?** On all evidence: **A — no**, for unconditional linear blends at a Bet365
pre-match snapshot: weight 1.00 on the market in every season and every candidate; the disagreement study found
no informative subgroup; logistic stacking gave the model −0.15 … +0.05. The market wins every family, league and
season. Preserve that result.

**What has not been tested** (B cannot be fully excluded until these run):

1. **Movement prediction (`move_v1`)** — the only mechanism by which a weaker model can still earn CLV. The
   direct football-data.co.uk CSVs carry **opening and closing** Pinnacle / Bet365 / average odds for 1X2,
   O/U 2.5 and Asian handicap since 2019-20 (the research used a redistribution with one Bet365 snapshot).
   Pre-registered regression per family:
   `logit p_close − logit p_open = α + β · (logit p_model − logit p_open) + ε`, clustered by matchday.
   β CI > 0 in ≥ 5/7 seasons ⇒ the model predicts where the sharp market moves ⇒ candidate CLV signal.
2. **Benchmark against Pinnacle close** (sharper than Bet365 pre-match); expect the gap to widen; report it.
3. **Residual (shrink-to-market) model**: `logit p = logit p_market + f(x)` with f a ridge-penalised function of
   (model − market, family, league, favourite side, days since refit); walk-forward; must beat market LL with CI.
4. Family- and league-specific stacking (only with ≥ 1,000 matches per cell).
5. Lineup- and horizon-specific blending: **prospective only** (no historical data).

Runner note: football-data.co.uk is blocked from this audit container (proxy 403) but reachable from the
GitHub runners (the probe workflow reached it). Fetch in a workflow, cache as an artifact.

---

## I. Lineups

**Evidence (VERIFIED):** 30 snapshot rows over 13.5 h (tip 25 + 5 recovered from history), 8 ESPN leagues;
6 published XIs, 5 post-hoc; the single "confirmed" XI was captured 1 minute after kickoff (now labelled
post_hoc). Lead time (kickoff − capture, n = 25): min −169 min, median +896 min, p90 +1,211 min; 68% before
kickoff but **none in the 0–120 min window** — every pre-kickoff capture was ≥ 342 min out with empty rosters.
Timestamps are our fetch time (correct), UTC-parsed (no timezone bug). Not wired into pricing anywhere
(`lineup_contexts` is never populated). Cron `17 */2 * * *` gives ~50% chance of a final-hour capture even when
it fires, and GitHub dropped 3 of 4 slots.

**Integration plan:**

1. Capture: kickoff-anchored job — every 10 min, act only on fixtures with Kalshi markets and kickoff in
   [now − 5, now + 90] min; target ≥ 90% of priced fixtures with a confirmed XI captured ≥ 20 min before kickoff.
2. Historical oracle study first (cheap, decisive): ESPN summaries of *completed* events include the XI that
   played. Backfill 2 seasons of post-hoc XIs for the main leagues; fit a player-importance model on minutes
   and team strength; measure the **upper bound** of lineup value (paired LL of lineup-adjusted vs unadjusted
   predictions with the actual XI). If the oracle gain on 1X2 is < 0.002 LL and on totals < 0.002, stop: lineups
   cannot pay for the operational cost.
3. Prospective study (only if the oracle clears): primary endpoint = paired LL (1X2, totals) of pre-XI vs
   post-XI prices on settled matches; secondary = Kalshi and reference price movement in the 60 min after XI
   publication (does the market move toward the lineup-adjusted price?).
4. **Minimum sample**: paired per-match LL differences for lineup adjustments have sd ≈ 0.03–0.05; detecting a
   0.003 gain at one-sided 95% / 80% power needs n ≈ (2.49 · 0.04 / 0.003)² ≈ **1,100 matches with a confirmed
   pre-kickoff XI**, of which ≥ 300 with a regular starter absent. Player markets: not before a separate
   player-level validation (≥ 2,000 player-matches) — keep them UNSUPPORTED.
5. Do not wire into pricing until step 3 passes.

---

## J. xG

**Current ingestion (VERIFIED from the runner probe):** football-data.co.uk `HxG`, `AxG` — match-level, one
value per team — present in all eight 2026-27 files (E0, SP1, D1, I1, F1, E1, N1, P1) and **absent** from
2025-26, 2024-25, 2023-24. Provider undisclosed (no statement of model, penalty inclusion, own-goals, or
consistency across divisions) — treat divisions as not comparable until checked (mean xG vs goals per
division; xG/shot ratio stability). Ingested by `football_data_couk.results_with_xg`; `model/xg_family.py`
(0.7·xG + 0.3·goals, weight unvalidated) is not called by any run path.

**Historical routes:**

| source | coverage | legal / reliable | verdict |
|---|---|---|---|
| football-data.co.uk HxG/AxG | 2026-27 only | yes | **prospective base** |
| FiveThirtyEight `spi_matches.csv` (xg1/xg2, nsxg) | 2016 → mid-2023 top leagues | CC-BY 4.0 | project retired; the endpoint returned **nothing** from this container; the repo's probe also found no xG columns — check a mirrored copy of the final file (e.g. the Internet Archive) from a runner before relying on it |
| StatsBomb open data | top-5 2015/16 only (+ Messi La Liga, a few recent seasons) | research licence | method validation only |
| Understat | 2014 → | ToS does not grant scraping | excluded |
| FBref / Opta | — | advanced stats removed 2025; 403 | excluded |

**Fastest credible path:** (1) try the final FiveThirtyEight file from an archival mirror (one-off download,
hash-pinned) → gives 2017-18 … 2022-23 for a walk-forward `xg_strength_v1` benchmark; (2) regardless, accumulate
football-data HxG/AxG from 2026-27.

**Recommended family `xg_strength_v1`:** `dc_laplace_v2` where team strengths are fitted on a joint likelihood:
Poisson goals + a quasi-Poisson xG pseudo-likelihood with weight ω (grid {0.25, 0.5, 0.75}) chosen walk-forward
— not the fixed 0.7/0.3 blend. **Evaluation sample if prospective-only:** in-season walk-forward from matchday 8
onward; decision after **≥ 1,700 settled matches** (paired LL gain 0.003 at 80% power, sd ≈ 0.05) — about one
full season of the 8 divisions.

---

## K. CLV protocol

Two axes, not one label: **source** ∈ {REFERENCE (sharp book), KALSHI} × **timing** relative to kickoff.

| class | definition |
|---|---|
| TRUE_CLOSE | REFERENCE quote with `captured_at` ∈ [KO − 15 min, KO) |
| NEAR_CLOSE | REFERENCE quote ∈ [KO − 120 min, KO − 15 min) |
| REFERENCE_CLOSE | the reported reference close = TRUE_CLOSE if present, else NEAR_CLOSE (label kept) |
| KALSHI_CLOSE | last **valid** Kalshi book ∈ [KO − 30 min, KO) |
| STALE / NONE | older than the windows / no observation — excluded from CLV, counted |

(The current code uses ≤ 30 min / ≤ 6 h for TRUE/NEAR and does not separate sources; tighten as above.)

* **Valid Kalshi book**: status active, 0 < bid ≤ ask < 1, spread ≤ 10¢, not suspended; otherwise step back to
  the previous valid snapshot inside the window, else NONE. (Sentinel handling is fixed in §S2.)
* **Side-aware conversion**: all CLV in the bought side's probability. YES: p_side = p_yes; NO: p_side = 1 − p_yes;
  Kalshi NO executable = 1 − yes_bid. Reference de-vig: power method primary, proportional reported.
* **Primary metric** — expected value at close: `EV_close = p_side(REFERENCE_CLOSE) − be_entry`, where
  be_entry = entry ask + retail fee. Positive = the bet was +EV against the sharpest available close.
* **Secondary**: fee-aware Kalshi price CLV = (close_ask_side + fee) − (entry_ask + fee); raw probability CLV
  (close mid − entry ask) reported but biased by half the spread; model-signed drift (fixed in §S2) for
  model-vs-market diagnostics.
* **Missing close**: excluded; if a cell's missing-close rate > 20%, the cell cannot promote.
* **Suspended / voided**: excluded from CLV; voided contracts excluded from settlement metrics.
* **Capture requirement**: Kalshi and reference snapshots at KO − 90, − 60, − 30, − 15, − 5 min for every fixture
  with a priced contract (kickoff-anchored scheduler; GitHub cron alone is not reliable enough).

**Minimum evidence (per family cell):** mean EV_close > 0 with cluster-bootstrap (by fixture) 95% lower bound
> 0, point estimate ≥ +1.0 pt, on ≥ 200 selected sides from ≥ 80 distinct fixtures across ≥ 6 matchdays; the
sign must hold in each half of the sample. Rationale: per-bet EV_close sd is expected ≈ 3–5 pts; at sd 4 pts, a
true +1 pt needs n ≈ (2.49 · 4 / 1)² ≈ 100 for 80% power — double it for clustering and multiple families.
Re-estimate the sd from the first 100 observations and recompute n before judging.

---

## L. Market-family readiness

None is a CANDIDATE FOR LIMITED AUTHORITY. "Evidence" columns refer to what must exist before the family can
move up one class.

| family | class today | historical benchmark | known model issue | minimum settled sample (for §Q) | extra requirements |
|---|---|---|---|---|---|
| 3-way result | **PROSPECTIVE SHADOW** (edge_v2 route); DATA_ONLY: NOT ENOUGH EVIDENCE (negative) | yes: loses +0.028 LL | intercept; engine ≠ benchmark | 200 selected / 80 fixtures (CLV); 1,000 contracts for calibration | top-5 + E1 only; reference present |
| totals (O/U) | **PROSPECTIVE SHADOW** | yes: loses +0.014 | O2.5 −3 pts | same | line ∈ {1.5, 2.5, 3.5} only |
| handicaps | RESEARCHABLE | yes (AH): loses +0.024 | push mass −1.9 pts; home cover +3.6 | 300 / 100 | Kalshi semantics ("wins by more than") settled only on whole/half lines |
| team totals | RESEARCHABLE | calibration only | away totals −4 to −5 pts | 300 / 100 | after v2 |
| BTTS | RESEARCHABLE (blocked) | calibration only | **worse than base rate** | 300 / 100 | after v2 + engine fix |
| exact score | NOT READY FOR RESEARCH | none | tail mass; coherence failures (506 contracts) | — | never in LIMITED v1 |
| 1H result | RESEARCHABLE | outcomes only (HTHG/HTAG) | 2nd-half share 0.54 unfitted | 400 / 150 | fit HT split first |
| 1H totals | RESEARCHABLE | outcomes only | same | 400 / 150 | same |
| 1H handicap | NOT READY FOR RESEARCH | none | — | — | — |
| 1H BTTS | NOT READY FOR RESEARCH | none | — | — | — |
| 1H exact score | NOT READY FOR RESEARCH | none | — | — | — |
| 2H result | RESEARCHABLE | outcomes (FT − HT) | same as 1H | 400 / 150 | — |
| first-to-score | NOT READY FOR RESEARCH | no goal times in dataset | same-minute coin flip; refused for knockouts | — | needs goal-time data (ESPN) |
| to-advance | NOT READY FOR RESEARCH | none | ET/pens priors unvalidated; sparse | — | — |

Sample thresholds differ because outcome variance and clustering differ: binary near 0.5 (result sides, totals)
needs fewer than skewed/tail families; derived half-time families add engine-split uncertainty; one fixture
yields many correlated contracts, so fixture counts, not contract counts, bound the evidence.

Per-family calibration / uncertainty requirements for promotion are in §Q (common template, family-specific n).

---

## M. Limited live mode (DESIGN — do not activate)

`LIMITED_v1` applies only to a family cell that passed §Q. Every order must satisfy **all**:

| gate | value |
|---|---|
| model family | `edge_v2` reference-anchored; DATA_ONLY never sole source |
| competitions | E0, SP1, D1, I1, F1 (+ E1 if cell evidence exists); **no international pool, no Americas** until their own cells pass |
| families | only the promoted cell (initially 3-way result or totals 1.5/2.5/3.5) |
| excluded | exact score, player markets, first-to-score, to-advance, all 1H/2H families |
| timing | KO − 90 min … KO − 5 min; confirmed XI captured (both teams) if the cell was promoted on lineup-confirmed evidence |
| reference | sharp reference observed ≤ 15 min ago; |p_model − p_ref| ≤ 0.10 (disagreement larger than that is where the model is historically wrong) |
| price | 0.15 ≤ ask ≤ 0.85; spread ≤ 4¢; book two-sided |
| liquidity | depth at the ask ≥ 3 × intended contracts; VWAP used for be_exec |
| edge | edge_v2_lcb ≥ 0.010 and EV_net ≥ 0.020 after cent-aligned retail fee |
| uncertainty | σ_edge ≤ 0.02 |
| correlation | ≤ 1 position per fixture; no same-fixture opposite or correlated duplicates (reducer, corr ≥ 0.3) |
| sizing | flat stake; ≤ 0.5% of the dedicated bankroll per position; ≤ 3% per matchday; ≤ 10% total open exposure |
| kill switches | freshness violation, incomplete discovery, missing reference, coverage ≠ 0 unaccounted ⇒ no orders; rolling 100-bet EV_close lower bound < 0 or drawdown > 15% of dedicated bankroll ⇒ auto-demote to SHADOW |
| audit | every order linked to its prediction record id, reference snapshot id and close record |

---

## N. Performance

Measured (VERIFIED from run outputs): assemble + fit 7–9 s; **Kalshi exhaustive discovery 13 min 0–8 s
(93% of the run)** at `max_rps = 4` over ~3,100 requests for 6,286 contracts; reference + simulate + price +
reduce 21–27 s for 830–1,318 priced contracts; publish ~3 s; wall time 14–14.5 min. Sim cache never hits
(`run-soccer.yml` creates an empty cache dir each run).

Safe optimisations (completeness preserved):

1. **Split discovery from refresh.** Keep the exhaustive sweep in `kalshi-discover` (daily) and on any
   reconciliation doubt; in `run-soccer`, refresh only the events of fixtures in the window from the last
   catalog (fast mode exists, `kalshi/discovery.py:182`) and run `reconcile` against the catalog —
   `unaccounted_contracts` must still be 0, and any unseen series forces a full sweep. Expected: 13 min → < 1 min.
2. Raise `max_rps` to the documented Kalshi read limit for the account tier (verify, then set ≤ 80% of it).
3. Persist the sim cache with `actions/cache` keyed on posterior hash (now exact after §S6).
4. Kickoff-anchored mini-runs (fixtures in [KO − 90, KO − 5]) reuse the day's fits; target < 2 min end to end.
5. Price full-time families analytically (also fixes B2 and removes MC noise) — the engine only for
   path-dependent families.
6. Emit per-stage timings in `run_output.v1.json` (they are currently inferred from freshness stamps).

---

## O. Archive

**Current:** 30 MB, 65 files after 13.5 h (runs 13 MB, snapshots 8.7 MB, predictions 4.7 MB, results 3 MB);
history 35.3 MB uncompressed / 3.1 MB packed. Largest: `priced_contracts.json` 5.7 MB per run (duplicates
`predictions.jsonl`), capture snapshots up to 5.2 MB, `coverage_diagnostics.json` ~0.9 MB per run,
`last_fingerprints.json` 0.68 MB rewritten per capture. **Projection** if crons fire: 65–100 MB/day
uncompressed, 6–9 MB/day packed ⇒ **2.5–3.5 GB/year in git history** (target in `STORAGE_STRATEGY.md`:
< 500 MB/season).

**Keep forever (immutable evidence):** prediction records, Kalshi capture snapshots (closes come from them),
settlements, evaluation outputs, results, lineups, reference snapshots, `run_output.v1.json`, coverage summary.

**Plan:**

1. Append-merge `.jsonl` (done, §S1). **Recover** the overwritten rows: for every `.jsonl` path, union all
   historical versions from `git log` (dedupe by exact line), write once to the archive tip, commit
   "archive: recover overwritten rows" — owner approval required (§R).
2. Add the missing ledger manifest: per day file, line count + rolling hash, appended per publish; `verify()`
   fails on any missing line.
3. Stop committing: `priced_contracts.json` (keep in the 14-day Actions artifact), `latest.*` copies,
   `coverage_diagnostics.json` (artifact only; keep `coverage.json`), `last_fingerprints.json` (Actions cache).
4. ESPN fixtures: write only on content-hash change.
5. Gzip day files once the UTC day is closed (`.jsonl.gz`, readers accept both).
6. Monthly: compact snapshots to Parquet on a new orphan branch generation with a manifest mapping old paths →
   new; keep the old branch read-only as a tag (point-in-time reproducibility is preserved by the tag).
7. Expected after 3–5: ~10–15 MB/day uncompressed, < 2 MB/day packed.

---

## P. Required Fable implementation (ordered by dependency)

Each step: new versions only; frozen families untouched; tests first; no authority change.

1. **Evidence integrity (blocks everything).**
   a. Recovery script `scripts/archive_recover.py` (union of historical `.jsonl` versions) — run once after owner
      approval. b. Ledger manifest + deletion detection in `archive/ledger.py`; test that deleting a line fails
      `verify()`. c. Stop archiving the redundant files (§O3–4).
2. **Settlement completeness.** `cmd_settle` reads results from the ESPN archive for every competition that
   `run-soccer` prices (Nations Leagues, friendlies, qualifiers, Americas, Ligue 1); a coverage check fails the
   settle job if any record with kickoff < now − 3 h has no result source. Test: every competition in
   `DEFAULT_COMPETITIONS ∪ ESPN_POOLS` has a settle source.
3. **Point-in-time schema guard.** Every feature/reference/lineup row carries `observed_at`; the pipeline refuses
   any with `observed_at ≥ as_of`. Test with a synthetic late row.
4. **Close capture.** Kickoff-anchored capture (Kalshi + reference) at KO − 90/60/30/15/5; `classify_close` split
   into source × timing per §K; valid-book filter. Tests: window edges, suspended book, sentinel book.
5. **Sharp reference source** (after owner decision, §R1): adapter + de-vig (power, proportional, Shin) +
   `σ_devig`; per-contract mapping for 1X2 and totals. Test: synthetic odds round-trip.
6. **`edge_v2`** as in §G (new `EdgeConfig` version; `edge_v1` untouched); cent-aligned retail fee; VWAP via
   `walk_book` (requires capturing orderbook depth for candidate tickers); rename P(edge>0) in the app contract to
   `model_posterior_edge_share` (additive field; keep the old one for one version). Tests: fee rounding table,
   VWAP vs top-of-book, lcb monotonicity in σ.
7. **`move_v1` historical study** (§H1) on direct football-data CSVs (fetched by a workflow): pre-registered
   β regression per family; result JSON + doc.
8. **`dc_laplace_v2`** (§D) with the pre-registered grid and holdout; remove the strict xfail on the away-level
   test when it passes.
9. **`world_sim_v2`**: analytic DC (with ρ, exact per-world p_w) for all full-time families; engine for
   path-dependent families only, with λ scaled so full-time marginals match analytic within 0.5 pt; engine must
   read ρ (remove the strict xfail on `test_engine_honours_dixon_coles_rho`); fit the half-time split on
   football-data HTHG/HTAG.
10. **Re-run recalibration** on v2; adopt `worlds_v2` k only if §F4 passes.
11. **`intl_hier_v1`** (§E) on the CC0 international dataset; fix ESPN neutral-site extraction (inspect a raw
    neutral-venue summary payload from a runner); `MatchRow.neutral`; `rows_from_results` passes it through.
12. **Lineups**: kickoff-anchored capture, then the historical oracle study (§I2); stop if below threshold.
13. **xG**: archival FiveThirtyEight retrieval attempt; else prospective accumulation; `xg_strength_v1` per §J.
14. **Performance**: split discovery/refresh (§N1), persistent sim cache, per-stage timings.
15. **Promotion evaluator**: implement §Q as code (`authority/promotion_v2.py`) producing a report; it may
    *propose* but never write `config/authority.json`.

---

## Q. Promotion criteria — RESEARCH_ONLY → LIMITED (one family cell)

A cell = (edge family, market family, competition group, horizon bucket). **All** must hold, computed by code,
on prospective records only, with the evaluation frozen before looking:

1. **Integrity**: 0 unaccounted contracts in every contributing run; ledger manifest verifies; no freshness
   violations; missing-close rate ≤ 20%; settlement rate ≥ 98% of kickoffs older than 3 h.
2. **Sample**: ≥ the family minimum in §L (e.g. 200 selected sides from ≥ 80 fixtures and ≥ 6 matchdays for
   3-way / totals), spanning ≥ 4 calendar weeks.
3. **CLV (primary)**: mean EV_close vs REFERENCE_CLOSE > 0 with fixture-cluster bootstrap 95% lower bound > 0 and
   point estimate ≥ +1.0 pt; same sign in both halves of the sample; ≥ 70% of CLV observations are TRUE_CLOSE.
4. **Kalshi fee-aware price CLV**: mean ≥ 0 (point estimate) — the Kalshi price itself did not move against us.
5. **Realised return guardrail**: realised ROI 95% lower bound > −10% (cannot prove profit at this n, but must
   not be clearly losing).
6. **Probability quality** of p* on all evaluated contracts of the family (not only selected): LL ≤ Kalshi
   valid-mid LL + 0.005 and ≤ reference LL + 0.010 (paired, CI reported); ECE ≤ 0.04 (10 bins, ≥ 300 contracts).
7. **Uncertainty**: realised coverage of the 80% interval of p* between 0.70 and 0.90 (grouped estimator where
   applicable); σ_edge calibration: z-scores of (EV_close − EV_net)/σ_edge have sd in [0.7, 1.4].
8. **Liquidity**: ≥ 80% of selected sides had depth ≥ 3× intended size at decision; median spread ≤ 3¢.
9. **Data completeness**: reference present for 100% of selected sides; lineup status recorded; no LOW_CONNECTIVITY
   or intl-pool fixtures in the cell.
10. **Governance**: the promotion report is committed, the owner signs off in writing, and the cell enters
    LIMITED under §M only. Automatic demotion rules in §M apply from the first order.

For DATA_ONLY-driven cells (w > 0), add: the §D acceptance tests passed and the `move_v1` β CI > 0 for that family.

---

## R. Owner actions (only what is genuinely required)

1. **Decide the sharp reference source** with near-kickoff timing (a paid odds API such as The Odds API, which
   includes Pinnacle; football-data `fixtures.csv` updates only a few times a week). Without it, only
   KALSHI_CLOSE CLV is possible and no family can meet §Q3. This is the single most important decision.
2. **Approve the one-time archive recovery commit** to `data-archive` (§O1).
3. **Scheduling reliability**: GitHub dropped most cron slots. Approve an external trigger (for example a
   `workflow_dispatch` caller on a small always-on host, or a self-hosted runner) for kickoff-anchored jobs.
4. **Confirm the retail fee rounding** on your own Kalshi account statements (existing fills from other sports):
   is the effective fee cent-aligned per fill? This sets `fee_retail` in `edge_v2`. Do not place a bet to test it.
5. **Set the LIMITED bankroll cap** (the dedicated amount §M percentages apply to) — only when a cell passes §Q.
6. Review and merge the audit branch.

---

## S. Changes made in this audit (bug fixes only)

| # | change | files | test |
|---|---|---|---|
| S1 | `.jsonl` append-merge in archive publishing (keep every archived line; append unseen lines; other files copied) | `scripts/archive_publish.sh` | exercised against a local bare repo: run-1 rows survive run 2, duplicates dropped, re-publish is a no-op |
| S2 | CLV ignores empty-book sentinels; YES mid only for real two-sided books; authority CLV signed by the model's side (`model_signed_clv`); settlement records gain `clv_model_signed_points` | `run/settle.py` | `test_clv_ignores_empty_book_sentinels`, `test_authority_clv_is_signed_by_model_side` |
| S3 | decision `as_of` taken after discovery; market age measured from `discovery.started_at` | `cli.py`, `run/inputs.py` | `test_market_age_is_measured_from_the_start_of_the_sweep` |
| S4 | lineup `confirmed` requires `captured_at < kickoff_utc` | `providers/espn.py` | `test_lineup_captured_after_kickoff_is_never_confirmed` |
| S5 | NO-side depth = `yes_bid_size` when `no_ask_size` is absent; records archive `yes_bid_size` | `kalshi/executable.py`, `run/pipeline.py` | `test_no_side_depth_comes_from_yes_bid_size` |
| S6 | sim cache stores exact per-world probabilities; cached fixtures with candidates are re-simulated deterministically so payoff vectors share draws | `run/simcache.py`, `run/pipeline.py` | `test_sim_cache_keeps_exact_world_probabilities`, `test_cached_repricing_reproduces_draw_level_payoffs` |
| S7 | `pedge_eval` reads `reference.probability_yes`; NO recommendations converted to YES units | `research/pedge_eval.py` | — (research tool) |
| — | strict-xfail pins for the two unfixed model defects | `tests/test_audit_regressions.py` | `test_fitted_away_level_matches_training_away_level`, `test_engine_honours_dixon_coles_rho` |

All five fixed-bug tests were confirmed to **fail on the pre-audit code** and pass after. Full suite:
247 passed, 2 skipped (local research caches), 2 xfailed; `ruff check` and `ruff format --check` clean.

Not changed (by mandate): model families, `StrengthConfig`, `WorldConfig`, `EdgeConfig` thresholds,
`config/authority.json`, routing.

### Further regression tests to add (Fable)

* Laplace covariance: z-score coverage of posterior means vs simulated truth (static league) and a finite-difference
  gradient check of `neg_log_post`.
* International: neutral flag round-trip ESPN → `MatchResult` → `MatchRow`; γ not applied to neutral rows in the fit.
* Calibration: ECE / reliability on a synthetic calibrated source must be ≈ 0; interval coverage on synthetic data
  at the nominal level.
* Close classification: source × timing matrix edges; suspended and one-sided books.
* Fees: cent-aligned retail rounding table (1 contract at 0.05 / 0.40 / 0.50 / 0.99).
* Edge: `edge_v2_lcb` monotone in σ; NOT_EVALUATED without a fresh reference.
* Mapping: every Kalshi soccer series in the catalog maps to a family or an explicit UNKNOWN reason.
* Archive: publishing an older day file never reduces its line count; ledger manifest detects deletion.
