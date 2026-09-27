# Best market expression

`pricing/expression.py::reduce_expressions(candidates)`.

Input: every (contract, side) that passed the robust-edge bar on a fixture, each with its per-draw
payoff vector computed on the **same simulated draws** (`payoff = 1[win] − price − fee`).

1. **Correlation from shared worlds.** Pairwise correlation of payoff vectors within the fixture.
2. **Groups.** Single-linkage components at |ρ| ≥ 0.6 → `correlation_group` ids
   (`<fixture_id>#g<n>`), exposed on every recommendation.
3. **Dominance.** Within a group, candidates are ordered by (worst-case edge, fee-adjusted edge,
   liquidity). The best is kept; each other is removed with a logged reason: *dominated*
   (best is ≥ on worst case, fee-adjusted edge and P(edge>0)), *redundant* (same exposure, best
   kept), or *opposes* (negatively correlated view of the same fixture, e.g. YES home win vs NO away
   win). The removal ledger is printed in the Markdown report.
4. **No top-N by raw edge.** Ranking is by worst-case edge; the number of outputs is whatever
   survives.

Example from a real-fixture run with the synthetic surface: for Barcelona v Getafe the reducer kept
`home win YES` and `home −1.5 YES` in different groups and removed `draw NO`, `team total 1.5/2.5`
and `−2.5` as dominated (ρ 0.63–0.80) — six overlapping expressions of "Barcelona score a lot"
became two.

## Portfolio layer (`pricing/portfolio.py`)

`portfolio_stats` computes expected profit, covariance/correlation, P(total loss) and the worst
draw for any set of candidates over shared draws. Staking is **disabled**: `stake_units` is null in
every recommendation until externally supplied or authorised. Cross-fixture correlation is
currently zero by construction (independent worlds per fixture); a shared league-environment draw
is on the roadmap.
