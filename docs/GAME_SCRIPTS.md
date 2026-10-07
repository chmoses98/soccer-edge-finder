# Soccer game-script engine (`soccer_scripts_v1`)

Status: implemented 2026-10-07. Code: `src/soccer_edge/gamescript/` (taxonomy, kernel, cells, conditional,
survivability, expressions, matchup, context, presentation), `src/soccer_edge/slate/scripts.py`, wiring in
`run/pipeline.py`, `slate/board.py`, `slate/reprice.py`, `app_export.py`, `research_export.py`. Tests:
`tests/test_game_scripts.py`. Everything here is **RESEARCH_ONLY**: no authority, selection policy, action or
production probability changed.

```
MATCH -> MATCHUP -> GAME SCRIPTS -> CONDITIONAL OUTCOMES -> EVERY MARKET -> SCRIPT SURVIVABILITY -> BEST EXPRESSIONS
model board (model time, market-blind)            actionable slate (price time, zero simulations)
```

## 1. What a script is here

A script is a **summary of the modelled joint distribution**, not a narrative. It is a deterministic function of a
modelled realisation (regulation full-time score h-a, first scorer). No language model, no tactical claim, no
market input. Every realisation belongs to exactly one script, so the scripts partition the simulated worlds and
`sum(simulation_share) = 1`. Shares are called `simulation_share` (SIFT may show "modelled likelihood" with this
provenance); they are **not** calibrated frequencies (no empirical check yet; data gap `SCRIPT_SHARES_NOT_CALIBRATED`).

## 2. Taxonomy (`gamescript/taxonomy.py`)

| script | rule | typical scores |
|---|---|---|
| `HOME_CONTROL` | home scores first and wins (not both sides >= 2) | 2-0, 2-1, 3-0, 3-1 |
| `HOME_CHASE` | away scores first; home recovers at least a draw (not both >= 2) | 1-1, 2-1 / 3-1 comebacks |
| `TIGHT_LOW_EVENT` | at most one goal in the match | 0-0, 1-0, 0-1 |
| `OPEN_END_TO_END` | both sides score at least twice | 2-2, 3-2, 2-3 |
| `AWAY_CHASE` | home scores first; away recovers at least a draw | 1-1, 1-2 / 1-3 comebacks |
| `AWAY_CONTROL` | away scores first and wins | 0-2, 1-2, 0-3 |

Canonical order runs home-dominant -> away-dominant, so a script x market matrix reads left (home) to right (away).
Partition proof in the module docstring.

**Why this partition.** The production engine (`world_sim_v2`) draws the full-time score from the fitted per-world
Dixon-Coles matrix and goal times i.i.d. given the count; it has **no game-state dynamics** (they were dropped
because they were unfitted and not mean-preserving; docs/SIMULATION_ENGINE.md). Within that model the facts a
match shape can carry are the score and the order of goals, and the first goal is the one ordering fact every
market family can be conditioned on exactly. Five candidates were compared on the 32 real fixtures of the
2026-10-03 production board (largest share, scripts at or above the materiality floor, mean between-script R^2 over
H, D, A, O2.5, BTTS, home O1.5, away clean sheet, home first, home -1.5, U1.5):

| candidate | mean largest share | material scripts (of K) | mean R^2 |
|---|---|---|---|
| score bands (tight = each side <= 1) | 0.43 | 3.4 / 6 | 0.52 |
| tight = 0-0 / 1-1, comeback wins only | 0.42 | 3.6 / 6 | 0.55 |
| first scorer x result | 0.45 | 3.9 / 5 | 0.56 |
| **soccer_scripts_v1** | **0.36** | **4.9 / 6** | **0.58** |
| v1 + margin split of the control scripts | 0.33 | 5.4 / 8 | 0.64 (rejected: 8 scripts) |

`CHAOTIC_VOLATILE` (lead changed hands) was rejected as a primary script: those worlds are the comeback wins inside
the chase scripts plus part of `OPEN_END_TO_END`, and a separate script would re-slice them by an unfitted timing
assumption. Volatility is published per script instead (temporal profile below).

## 3. Exact conditional pricing (`gamescript/kernel.py`, `cells.py`, `conditional.py`)

`world_sim_v2` implies, given (h, a): each goal falls in the first half independently with the fitted share
s = 0.441 (h1 ~ Bin(h, s), a1 ~ Bin(a, s)), and goals within a half are exchangeable, so the first scorer is home
with probability h1/(h1+a1) (else the second-half analogue). This **timing kernel** P(h1, a1, first | h, a) does not
depend on the world. The joint over (world w, h, a, h1, a1, first) is therefore `mats[w,h,a] x kernel[h,a,h1,a1,first]`
and every script and every supported contract is an exact sum:

```
P_w(S)         = sum_{h,a} mats[w,h,a] T[h,a,S]                       T = P(S | h, a)
P_w(M and S)   = sum mats[w,h,a] kernel[h,a,h1,a1,f] 1_M(h,a,h1,a1,f) 1[S(h,a,f) = S]
share(S)       = mean_w P_w(S)
P(M | S)       = sum_w P_w(M and S) / sum_w P_w(S)
P(M)           = sum_S share(S) P(M | S)        (identity; tested to 1e-12)
interval       = P_w(S)-weighted quantiles of P_w(M and S)/P_w(S)  (the posterior over worlds given S)
```

`1_M` is built by `cells.cell_indicator` with **the same rules as `pricing/semantics.settle_indicator`** for every
family (3-way, totals, team totals, handicaps, BTTS, clean sheet, DNB, exact score, first-half result / total / BTTS
/ handicap / team total / exact score, second-half result, first to score, to-advance); equivalence is a test on
simulated draws. To-advance contracts in knockouts use the engine's own ET (Poisson x 0.85 x 30/90 per world) and
50/50 shoot-out (`cells.advance_home_prob`, exact per world). Families the layer cannot represent exactly (goal
markets including extra time in knockouts, player goals) are not approximated: they appear in `contract_gaps`.

Consequences: no extra simulation, no Monte Carlo noise in shares or conditionals, and for every analytic family
the script-basis P(M) equals the board's P(M) exactly. For draw-priced families (half-time, first scorer, to-advance)
the board's P(M) carries Monte Carlo error; the slate publishes `decomposition_residual = p_script - model_probability`
for every side (0 for analytic families).

**Engine finding (documented, not changed).** In `world_sim_v2` the first-scorer draw is independent of the
half-time split (both marginals are exact, the joint is not: a 0-1 half-time score can carry a home first goal).
Single-market prices are unaffected; the production expression reducer's draw-level correlations between first-
scorer and half-time markets are. The script layer never uses those draws. Fixing the engine would change
first-scorer prices by Monte Carlo noise and is left to a versioned engine change.

## 4. Temporal state (what was added, what was not persisted)

Nothing was added to the engine or to the archive. The minimal temporal state is the kernel's (h1, a1, first) per
score cell, exact. **Descriptive** path statistics per script come from a deterministic, seeded Monte Carlo over goal
orders and times given (h, a, first) (`kernel.temporal_kernel`, 3,000 paths per cell, computed once per process,
~0.5 s): minutes each side led, minutes level, P(lead changed hands), P(each side ever trailed), P(level at 75'),
P(goal after 75'), mean first-goal minute. They feed script cards only, never a price, and are labelled
`MODEL_DERIVED_TIMING_ASSUMPTION (no game-state dynamics)`. Red cards: `world_sim_v2` does not model them, so no
red-card rate is published (gap `RED_CARDS_NOT_MODELLED`). Extra time / penalties: `p_extra_time`, `p_home_advances`
per script in knockouts.

## 5. Script survivability (`gamescript/survivability.py`, `slate/scripts.py`)

Model information (board): shares, P(YES | S) with intervals, overall P. Price information (slate, every reprice):
for a side with break-even b = executable ask + Kalshi fee per contract (`pricing/edge.assess`), p_S = P(side | S):

| field | definition |
|---|---|
| `conditional_edges[S]` | p_S - b |
| `overall_edge` | sum_S share_S (p_S - b) = P(side) - b on the script basis |
| material script | share_S >= 1/(2K) = 1/12 = 8.33 % (half the uniform share; scale-free, deterministic). Minority shares are always published |
| `stance` (one char per script) | S supports (edge >= +0.02), O opposes (<= -0.02), N neutral, - immaterial |
| `weighted_support_share` | sum of supporting material shares / sum of material shares |
| `edge_concentration` | largest positive share x edge / sum of positive contributions |
| `edge_ex_top_script` | (overall - top contribution)/(1 - top share): edge left outside the most valuable script |
| `worst_material_script` | material script with the lowest conditional edge |
| `strongest_support` | script with the largest positive contribution |
| `counter_case` | material script with the most negative contribution: share, p, edge, contribution, reason code (`SCRIPT_SETTLES_AGAINST`: p = 0; `BELOW_BREAKEVEN`; `NO_MATERIAL_OPPOSITION`), one templated sentence |

Labels (first match): `NO_EDGE` (overall <= 0) · `SCRIPT_DEPENDENT` (<= 1 supporting material script, or
>= 75 % of the positive value from one script with share < 25 % and no edge left without it) ·
`VERY_ROBUST` (support >= 0.80 and >= 3 supporting) · `ROBUST` (>= 0.60) · `MIXED` (>= 0.35) · `FRAGILE`.
Categories: `ROBUST_ACROSS_SCRIPTS` (VERY_ROBUST, ROBUST), `MIXED`, `SCRIPT_SPECIFIC_UPSIDE` (FRAGILE,
SCRIPT_DEPENDENT), `NO_EDGE`. No composite score.

Why support and not `edge_ex_top_script` decides dependence: scripts are outcome-defined, so a moneyline side always
wins in its control script; removing that script removes most of any modest edge by construction. The metric is
published, but labelling every moneyline "dependent" would describe the taxonomy, not the price. It does decide
dependence together with concentration when the carrying script is low-frequency: on the first live board an
Over 5.5 at 7c was +2.4 pts in the largest script (HOME_CONTROL) but drew 86 % of its value from
OPEN_END_TO_END (16.5 %); it is SCRIPT_DEPENDENT, while a BTTS-No whose value sits in a 29 % TIGHT_LOW_EVENT
script stays ROBUST.

**Zero simulations.** A reprice reads the cached conditionals and the side's break-even; a price move changes edges,
stances, labels, rankings and groups and never a share (tests `test_quote_only_reprice_runs_zero_simulations_and_moves_survivability`,
`test_kalshi_prices_never_change_scripts`).

## 6. Expressions and same-thesis detection (`gamescript/expressions.py`)

Research edges: sides with a CURRENT price, a VALID model and a script-basis fee-adjusted edge >= 0.02 (the
selection policy's minimum edge; the lists never feed the selection). Ranking is lexicographic and transparent:
label, then worst-case (q0.20) edge > 0, then `edge_ex_top_script`, then overall edge (`robust_rank`, 1 = best).

Same thesis: payoff correlation phi under the exact joint (rebuilt at reprice time from the board's mean score
grid x the kernel; to-advance via the stored advance table). Groups are formed in rank order: a side joins the
first group whose best expression it tracks with phi >= 0.5, else it leads a new group (leader grouping: every
member is a correlated re-expression of its group's best side; single linkage chained 16-17 loosely related sides
into one group on the first live board). Each group has an `anchor_script` (largest summed positive contribution) and a `best_expression` (top-ranked
member). Home ML, home -0.5, home team O1.5 land in one dominant-home group (test). The fixture summary gives
`robust_edges`, `mixed_edges`, `script_specific_edges`, `thesis_groups`, `best_robust_expression`,
`best_script_specific_expression`, and an explicit `no_compelling_edge` with its reason.

## 7. Opponent-adjusted matchup intelligence (`gamescript/matchup.py`)

From the production posterior that priced the fixture (`dc_laplace_v1`): attack / defence posterior mean and sd
(Dixon-Coles latent log rates, jointly fitted with time decay over the pool, hence opponent- and schedule-
adjusted), z-score and percentile within the pool's reference teams (>= 3 effective matches), net rating, expected
goals scored / conceded against an average pool opponent (neutral, home, away), effective matches and sample
quality, schedule strength (decay-weighted mean net rating of opponents faced in the 730-day fit window) and raw
form (365-day goals per match, labelled unadjusted context). Matchups `HOME_ATTACK_vs_AWAY_DEFENSE` and
`AWAY_ATTACK_vs_HOME_DEFENSE`: both z's, percentiles, log-rate advantage vs an average pairing with sd,
P(advantage > 0), model expected goals, label (`ELITE_VS_ELITE`, `WEAK_VS_WEAK`, `MAJOR_HOME_ATTACK_EDGE`,
`HOME_ATTACK_EDGE`, `AWAY_DEFENSIVE_EDGE`, ..., `BALANCED`, from the z gap at 0.75 / 1.5) and evidence quality;
`primary_mismatch` = largest |z gap|. Never called xG.

## 8. Competition / motivation context (`gamescript/context.py`) — display only

Each field is `{value, status: KNOWN | DERIVED | UNAVAILABLE, source}`: competition type (LEAGUE, DOMESTIC_CUP,
CONTINENTAL_CLUB, INTERNATIONAL_COMPETITIVE, INTERNATIONAL_FRIENDLY, CLUB_FRIENDLY, UNKNOWN from the registry
format and team kind), format, stage and stage kind, knockout, requires_winner, leg number, aggregate, neutral site,
rest days, rotation uncertainty (friendlies: `ELEVATED_UNQUANTIFIED`), and `flags` (FRIENDLY, KNOCKOUT,
SECOND_LEG, FINAL, NEUTRAL_SITE, INTERNATIONAL_COMPETITIVE). `standings_implications`, `must_win`, `draw_utility`
are `UNAVAILABLE` (no standings / scenario input; never guessed). The fixture feed does not supply leg / aggregate
today, so knockout legs show those as UNAVAILABLE. Friendlies lower `data_confidence` to LOW (gate
`competitive_fixture`) because rotation and motivation differ from the competitive matches the model is fitted on
and the size of that effect is not measured.

Model effect: none beyond what production already used (`neutral_site`, `requires_winner`). A context-aware model
would be a separately versioned RESEARCH_ONLY family with a stated hypothesis and a frozen holdout; none is enabled.

## 9. Lineups

A published XI changes the lineup key -> the cached fixture is INVALIDATED at the next reprice (NO ACTION) -> the
next model run re-prices it. The board merge keeps the earlier model state as `lineup_history` (only when the
lineup key genuinely changed). The payload's `lineup_rescripting` reports status, time, invalidation, refresh,
pre/current script shares and key probabilities with deltas, `model_uses_lineups: false` and why. Today the model
has no validated player-strength adjustment, so deltas are zero and the statement says so; no player effect is
invented. Per-contract survivability before the XI is not stored (`survivability_change: null` with the reason).

## 10. Freshness and fail-closed behaviour

Separate clocks in the payload: model (generated_at, validity, freshness), scripts (computed_at = model time,
market-blind), market (Kalshi observed_at, current_until, stale_after), lineup, context, reference. A stale price or
an invalidated model yields `no_compelling_edge` with the reason and empty edge lists (tests). A started fixture
leaves the slate (no pregame script edge survives kickoff). Survivability never changes `action` or `bet_permitted`.

## 11. Publication and discovery (no guessed paths)

| where | what | contract |
|---|---|---|
| `runs/latest.model_board.v1.json` fixtures[fid] | `scripts` (shares, intervals, profiles, temporal, score grid, contract_gaps), `matchup`, `match_context`, `lineup_history`; contracts[t].`sc` {p, sp[6], lo[6], hi[6]}, `k` | model_board.v1 (additive) |
| `runs/latest.actionable_slate.v1.json` | fixtures[].`scripts` (SlateFixtureScriptsV1), contracts[].`script_robustness` (ScriptRobustnessV1) | actionable_slate.v1, schema 1.1.0 (additive; `docs/schemas/ActionableSlateV1.schema.json`) |
| `app/latest/markets.json` items[].extensions.`script_robustness` | compact label / category / edge / support / stance per side | edge_finder.app.v1 extensions |
| `app/latest/events.json` items[].extensions.`scripts` | shares, primary/secondary, best robust expression | edge_finder.app.v1 extensions |
| `app/latest/explorer/events/<evt>.json` `extensions.soccer_script_engine` | the full SIFT payload `soccer_script_engine.v1` | edge_finder.app.v1 `event_research.extensions` |

Discovery for SIFT: `explorer/index.json` -> `events[]` (event_id, path) -> the event document -> `extensions.soccer_script_engine`.
The shared contract was **not** changed: its explorer file kinds are closed (`KINDS`, `path_for`, and
`publish_explorer` prunes unknown files), and `event_research.extensions` is the contract's designated sport-specific
slot (the CFB Script Engine uses the same slot). The payload is held under 75 KB inside the 145 KB event budget; if
it would exceed it, deep evidence is trimmed in a fixed order and listed in `trimmed`.

### Payload `soccer_script_engine.v1` (tiers)

```
contract, status (OK | UNAVAILABLE + reason), research_only
glance            PRIMARY: h_d_a, expected_goals (basis: DC model rates, not xG), primary/secondary script,
                  primary_mismatch, data_confidence, lineup, competition, best_robust_expression,
                  best_script_specific_expression, no_compelling_edge (+reason), story {sentence, parts}
scripts           SECONDARY: order (by share), canonical_order, cards[] {script_id, title, definition, rank,
                  simulation_share, share_low/high, material, primary{H/D/A, xG, typical_scores}, profile,
                  temporal, markets_helped[3], markets_hurt[3], evidence}, overall_profile
survivability     priced_at, price_status, research_edge_min, robust_edges, mixed_edges, script_specific_edges,
                  thesis_groups, rows[] {key, ticker, side, description, price, break_even, fair_probability,
                  fee_adjusted_ev, worst_case_edge, action, authority, label, category, overall_edge, p_script,
                  decomposition_residual, stance, conditional_edges, ..., counter_case, thesis_group, robust_rank}
matrix            DEEP: scripts, columns, rows [ticker, family, description, p_yes, p_yes_by_script[6],
                  low_by_script[6], high_by_script[6]], gaps
matchup, context, lineup_rescripting, data_confidence {level, gates, reasons, rule}, data_gaps [{code, detail}],
methodology {versions, survivability rules, expression rank basis, scripts, fee_model, evidence}, freshness,
authority, provenance
```

`methodology.fee_model` and the matrix let a client recompute every conditional edge at a fresher ask
(edge_S = p_side(S) - break_even(ask)) without the backend.

## 12. Evidence status

| output | status |
|---|---|
| taxonomy | DESCRIPTIVE_MODEL_DERIVED |
| script share | SIMULATION_DERIVED (not calibrated) |
| P(contract given script) | MODEL_DERIVED |
| survivability, robust ranking, thesis groups | MODEL + CURRENT PRICE derived; research presentation |
| temporal profile | MODEL_DERIVED_TIMING_ASSUMPTION |
| matchup metrics | MODEL_DERIVED (production posterior; not xG) |
| context | KNOWN / DERIVED / UNAVAILABLE per field; display only |
| tactical interpretation | UNAVAILABLE |

## 13. Tests (`tests/test_game_scripts.py`)

Partition (every reachable cell one script; impossible states rejected) · shares sum to 1 · kernel vs engine draws
(half-time, first scorer) · cell settlement == `settle_indicator` for 18 family/period cases · exact decomposition
(1e-12) and board reconciliation (analytic families identical, draw families within MC error) · three-way and
ladder coherence per script · reproducibility · cache hit serves scripts with no simulation · old cache rebuilds
worlds only · Kalshi prices never move scripts · quote-only reprice: zero simulations, survivability moves ·
overall edge = share-weighted conditional edges · label rules · same-thesis grouping · stale price / invalidated
model fail closed · authority never granted · started fixtures leave · temporal guard · lineup history · context
classification (friendly, knockout second leg, league, final) · knockout advance decomposition · matchup labels ·
payload tiers and size · explorer end to end (index -> event -> payload, `verify_explorer` clean) · v1 engine
publishes UNAVAILABLE · board block size bounds.

## 14. Performance (this container, 10 EPL fixtures, 1,000 worlds x 100 draws, 240 contract sides)

| | main | this build |
|---|---|---|
| model run, cold (simulate + price + scripts) | 4.29 s | 4.36 s (script layer ~0.1 s / fixture after a one-off 0.5 s kernel build) |
| model run, sim-cache hit | 0.65 s | 0.67 s (scripts served from the cache) |
| reprice (median of 5) | 0.138 s | 0.16-0.18 s (survivability + groups; 0 simulations) |
| model board | 159 KB | 316 KB (+16 KB / fixture: profiles, score grid, conditionals) |
| actionable slate (compact) | 416 KB | 514 KB (+24 %; full survivability only on sides with an edge) |
| peak traced memory, cold run | 53 MB | 40 MB |
| explorer event document | n/a | payload < 75 KB enforced; event doc <= 145 KB enforced |

## 15. Known limitations

* Shares are simulation shares of a model without game-state dynamics; chase scripts reflect goal order only.
* No empirical calibration of script frequencies yet (needs goal-minute history; ESPN scoreboards carry goal minutes).
* Leg / aggregate / standings inputs are not supplied by the fixture feed; context fields say UNAVAILABLE.
* Player markets: no production player layer; such contracts carry no script conditionals.
* On a sim-cache hit the pre-existing expression reducer still re-simulates every fixture with a quoted side
  (pipeline `fixtures_resimulated_for_reducer`); scripts never need it. Worth fixing separately.
* Explorer survivability is as fresh as the last research export (gated at 60 min unless new events arrive); the
  payload's `freshness.market.current_until` says when to stop trusting it, and the matrix + fee model allow a
  client-side recompute at a live ask.

## 16. Live proof (2026-10-07, production data-archive, this branch's workflows)

1. **RUN SOCCER** `run-20261007T013102Z-b79365` (on the branch, exhaustive-reconciled fast
   sweep, 96 h window): 59 real fixtures across Brasileirão, Premier League, La Liga, Ligue 1, Bundesliga, Serie A,
   Liga MX, MLS, CONCACAF Nations League (French Guiana v Belize, neutral, INTERNATIONAL_COMPETITIVE) and an
   international friendly (Mexico v Chile, FRIENDLY + NEUTRAL_SITE, data confidence LOW). No knockout / second-leg
   fixture was listed, so those contexts are covered by tests only. All 59 board entries carry `scripts`;
   decomposition over 547 priced contracts: max |sum share x P(M|S) - P(M)| = 2.0e-5 (rounding of published
   values); max |script-basis P - board P| = 0.0022 (half-time / first-scorer families, board Monte Carlo error;
   analytic families identical). 59 explorer events carry `soccer_script_engine` with status OK; `verify_explorer`
   clean; largest event document 139.9 KB (budget 145 KB), largest payload 71.6 KB.
   (The first attempt, run 37554747664, computed everything but its publish was refused by the archive size guard
   scanning `.git`; the same failure had stopped every scheduled RUN SOCCER since 2026-10-04. Fixed in
   `scripts/archive_publish.sh`.)
2. **Quote-only reprice** (kalshi-capture on the branch, slate `slate-20261007T013724Z-23473c`): mode
   `reprice_only`, `simulations_run` 0, Odds API calls 0, reprice 0.28 s, board unchanged (01:31:02Z); shares of
   all 12 slate fixtures identical to the model run; 18 sides moved price and 2 changed survivability on price
   alone, e.g. Botafogo v Vasco "home wins by more than 1.5" YES 0.15 -> 0.16 (model 0.2582 unchanged): stance
   `SNONOO` -> `SNOOOO` (AWAY_CHASE neutral -> opposes).
3. **Second RUN SOCCER** `run-20261007T014252Z-ceb98c`: all 59 fixtures `fixtures_reused_from_cache` with their
   scripts served from the simulation cache. Its 59 re-simulations are the pre-existing expression-reducer path,
   which re-simulates every cache-hit fixture that has any quoted side (see section 15).

Example (Botafogo v Vasco da Gama, Brasileirão, 2026-10-07 23:30Z): H/D/A 0.478 / 0.256 / 0.266; shares HOME_CONTROL
0.277, TIGHT_LOW_EVENT 0.258, OPEN_END_TO_END 0.141, AWAY_CONTROL 0.133, HOME_CHASE 0.104, AWAY_CHASE 0.086.
P(home win | S) = [1.00, 0.44, 0.40, 0.36, 0.00, 0.00]; P(O2.5 | S) = [0.70, 0.44, 0.00, 1.00, 0.33, 0.68] in the
canonical order; sum share x conditional = 0.4782 and 0.5002 = the board's analytic prices. Robust expression:
NO on "away wins by more than 1.5" at 0.82 (break-even 0.830, fair 0.890), VERY_ROBUST, supported in 5 of 6 material
scripts (weighted support 0.87); counter-case "Away control is 13% of simulations and prices NO on 'away wins by
more than 1.5' at 31% conditional fair probability against a 83% break-even." Script-specific: YES "home wins by
more than 1.5" at 0.15, SCRIPT_DEPENDENT (only HOME_CONTROL supports it; TIGHT_LOW_EVENT settles it at 0 %). The six
home-side rows (home ML, home -1.5/-2.5, away not winning, away not winning by 2+/3+) form one HOME_CONTROL thesis
group.
4. **After merge to main** (`112c726`): kalshi-capture on main at 02:36Z, slate `slate-20261007T023638Z-aa9d3b`
   (`reprice_only`, 0 simulations, 0 Odds API calls); the explorer rebuilt at 02:36:24Z with the merged rules:
   `verify_explorer` clean, 59 / 59 v1 events carry the payload (10 priced CURRENT inside the 48 h slate window, 49
   `OUTSIDE_SLATE_LOOKAHEAD`), largest event file 101.5 KB, thesis groups of 1-4 sides, every `markets.json` item
   carries `extensions.script_robustness`.
