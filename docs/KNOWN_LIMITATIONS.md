# Known limitations (honest list, 2026-09-27)

## Data
1. **No lineup / injury provider.** Production prices every fixture with `lineup_state=unknown`.
   The lineup layer exists and is tested, but it is fed nothing. Player markets are therefore
   `UNSUPPORTED_FAMILY` in production.
2. **UEFA / international fixtures are not in openfootball.** UCL/UEL/UECL/Nations League contracts
   are discovered and counted but mostly land in `UNMAPPED_EVENT` / `NO_FIXTURE` until an ESPN (or
   other) fixture adapter exists. A multi-league strength model is also needed to price them.
3. **Kickoff times** from openfootball are local and converted by assumed zone (flagged UNVERIFIED).
4. **No xG inputs yet.** The posterior uses goals only. football-data.co.uk now publishes HxG/AxG;
   ingestion is on the roadmap.
5. **Closing lines** are not in the GitHub redistribution; the research benchmark is Bet365
   pre-match, and CLV in production will use Kalshi's own last pre-kickoff snapshot.
6. **Historical coverage** for the walk-forward uses 5 leagues, 2017-18 → 2025-26. Other divisions
   in the dataset are loadable but unregistered teams get provisional ids.

## Model
7. **DATA_ONLY is worse than the market** (log loss 1.001 vs 0.973 on 12,248 aligned matches) and
   the walk-forward hybrid weight is 1.0 every season. There is currently no evidence that this
   model adds information to a bookmaker's pre-match 1X2. Kalshi's soccer books are much thinner
   than Bet365's, which is the only reason to keep measuring.
8. **Intervals look too wide** (mean 80% width on P(home) ≈ 0.29; the de-vigged market sits inside
   them 92.9% of the time against an 80% target). `sigma_model_log_rate`, the decay rate and priors need a
   calibration pass before P(edge>0) can be trusted even directionally.
9. Game-state, red-card, ET intensity and shoot-out parameters are configured priors, not fitted.
10. The Dixon-Coles low-score correction is applied analytically in the benchmark family but only
    approximated by state dynamics in the simulator family.
11. Home advantage is a single per-competition parameter; no team-specific or time-trend term.
12. Promoted-team priors are configured (−0.15 / sd 0.45), not estimated.
13. No cross-fixture correlation (worlds are independent per fixture).

## Kalshi
14. The taxonomy was rebuilt from the first complete live discovery (6,694 contracts): 3-way,
    totals, spreads, team totals, BTTS, exact score, first-half families and first-to-score are
    observed and priced; season futures, player-season and specials are observed and counted but
    not priced. New tokens Kalshi adds later land in `UNKNOWN` until the next taxonomy pass. Check
    `data/catalog/latest_index.json` (`unknown_body_histogram`) for what is currently unclassified.
15. Fee mechanics are transcribed from Kalshi's schedule via sibling repos and a live probe, not
    reconciled against a fill in this repo (no account is used here).
16. Team codes inside tickers are not a stable identity; association relies on event titles and
    the registry. Unusual titles fall to `unmapped_event` and are reported.
17. `/milestones` for soccer is probed advisory-only; its `details` shape is unverified.
18. Combos / multivariate collections are discovered as series if tagged but not priced.

## Operations
19. GitHub cron is unreliable; horizon coverage per fixture will be uneven. No self-chaining
    conductor is used on purpose (storm risk); the cost is missed horizons, which are reported.
20. The archive branch is created lazily by the first writer; there is no size compaction job yet.
21. The simulation cache is per-run (artifact-restored) rather than shared across jobs.
22. No router integration; positions/settlement import are contracts only.
23. All authority cells are `RESEARCH_ONLY`; the operator command will say `NO BETS` until
    prospective evidence exists and a human promotes a cell.
