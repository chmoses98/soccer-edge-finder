# Market pricing: from joint outcomes to fee-adjusted, robust edge

## 1. Contract semantics (`pricing/semantics.py`)

A `ContractSpec` (from the taxonomy) plus the fixture association resolves to `Semantics`:
family, period (regulation / first half / incl. ET / incl. pens), side (`home|away|draw`), line,
player slot. `Semantics.settle(JointOutcome)` returns the YES indicator per realisation. Titles are
never read at settlement time; if the side or line cannot be resolved the contract is
`UNPRICEABLE`/`UNSUPPORTED_FAMILY` and counted.

Supported today: 3-way result, handicap ("wins by more than N.5"), total goals, team total, BTTS,
clean sheet, draw-no-bet (void on draw), first-half total/result, to-advance (ET+pens),
first team to score, player K+ goals (only when a lineup context exists → not in production yet).

Kalshi's soccer ladder convention (observed live): ticker leg `N` ↔ `floor_strike = N − 0.5` ↔
"over N−0.5". The API `floor_strike` is preferred over the title and the leg number.

## 2. Fair probability (`pricing/pricer.py`)

```
p_w      = mean of YES indicator over the draws of world w
fair     = mean_w p_w                       (reported as fair_probability_mean)
median   = median_w p_w
interval = [q_0.10(p_w) − z·mc_se, q_0.90(p_w) + z·mc_se]   (80% by default)
param_sd = sd_w p_w  ;  mc_se = sqrt(fair(1−fair)/N)
```
Each `PricedProbability` records n_worlds, n_draws, effective draws, model/version, world hash,
sim seed, data_as_of and model_as_of (via the prediction record).

## 3. Executable price (`kalshi/executable.py`)

Buy YES at `yes_ask`; buy NO at `no_ask`. Never the midpoint, never `1 − yes_ask` for NO.
Zero-size or $0/$1 books are not quotes (`NO_QUOTE`). With an order book, `walk_book` gives the
VWAP for a requested size by consuming resting bids on the opposite side (`price = 1 − bid`).

## 4. Fees (`kalshi/fees.py`) — verified mechanics

```
raw_fee   = coef × fee_multiplier × contracts × P × (1 − P)
trade fee = ceil(raw_fee, $0.000001)              per fill
coef      = 0.07 (taker) ; 0.0175 (maker, only if fee_type == quadratic_with_maker_fees)
```
Verification chain: Kalshi's July-2026 fee schedule as transcribed by the CFB and NFL repos
(`cfb-edge-finder/src/.../kalshi/fee_schedule.py`, `nfl-edge-finder/config/kalshi_fee_schedule.json`),
and a live hand-recomputed probe in `cfb-edge-finder/docs/evidence/kalshi_fee_and_override_probe.txt`.
Two other sibling repos used ceil-to-whole-cent; CFB measured that as 2.75×–14× too high on small
fees, so it is not used here. `fee_type` outside `{quadratic, quadratic_with_maker_fees}` raises
`FeeMechanicsUnverifiedError` and the contract is dispositioned `FEE_UNVERIFIED`. Every prediction
record stores `FEE_SCHEDULE_VERSION = kalshi_fee_schedule_2026-07_transcribed_v1`. A runner-side
re-verification against live `/series` `fee_type`/`fee_multiplier` fields happens on every
discovery (the fields are captured per series).

Break-even: `p* = price + fee_per_contract(price)`.

## 5. Robust edge (`pricing/edge.py`)

```
point_edge          = fair − price
fee_adjusted_edge   = fair − p*
p_edge_positive     = P_w( p_w > p* )
worst_case_edge     = q_0.20(p_w) − p*
robust_positive_ev  = fee_adjusted_edge ≥ 0.02  AND  p_edge_positive ≥ 0.80  AND  worst_case_edge > 0
bet_up_to_price     = max cent price such that q_0.20(p_w) ≥ p*(price)
```
NO side mirrors with `q_w = 1 − p_w`. Thresholds live in `EdgeConfig` (versioned `edge_v1`);
they are decision hygiene, not calibration claims.

Worked example (from `tests/test_pricing.py::test_edge_assessment_and_bet_up_to`): worlds
N(0.60, 0.03), YES at 0.50 → p* ≈ 0.5175, fee-adjusted edge ≈ +0.08, P(edge>0) > 0.95,
bet-up-to ≈ 0.55–0.57. At 0.59 the same worlds fail the bar.

## 6. Coherence audit (`pricing/coherence.py`)

Ladders monotone, 3-way legs sum to 1, means inside intervals, bounds in [0,1]. A failure marks
every contract on that fixture `UNPRICEABLE` and raises a warning — it is a semantics bug detector.

## 7. What is *not* priced yet

Exact score, winning margin, HT/FT, first-half correct score, cards, corners, shots, assists,
season futures, tournament advancement beyond one leg, combos. They are classified (or `UNKNOWN`),
counted under `UNSUPPORTED_FAMILY`/`UNKNOWN_FAMILY`, and listed in every run's coverage report.
