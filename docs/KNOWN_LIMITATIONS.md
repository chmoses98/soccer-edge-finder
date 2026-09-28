# Known limitations (honest list, updated 2026-09-28 after Phase 2)

## Data
1. **Lineups are captured but not used.** ESPN snapshots run every 2 h, but ESPN publishes no XI days ahead
   (probe: empty rosters 31–94 h out) and the publication lead time is still unmeasured, so production prices
   every fixture with `lineup_state=unknown`. No injury source. Player markets stay `UNSUPPORTED_FAMILY`.
2. **International and Americas fixtures depend on the ESPN archive.** The adapter and registry exist
   (Phase 2), but until `espn-backfill` has been run once and `run-soccer` reads `results/espn`, Nations League,
   friendlies, Liga MX, MLS, Brasileirão and Argentina contracts land in `NO_FIXTURE` (honest, counted). UEFA
   club fixtures still need the multi-league model (research only) to be priced.
3. **Kickoff times** from openfootball are local and converted by assumed zone (flagged UNVERIFIED).
4. **xG exists only from 2026-27.** Ingested (`results_with_xg`) but the xG family is NOT_EVALUATED: no
   historical xG for the benchmark window, no free licensed source (`docs/XG_DATA_AUDIT.md`).
5. **Closing lines**: the research benchmark is Bet365 pre-match. Production CLV uses Kalshi's own last
   pre-kickoff snapshot labelled by close class (TRUE_CLOSE ≤30 min is rare at a 2-hourly cadence, so most
   CLV will be NEAR_CLOSE) plus the football-data.co.uk consensus reference where captured.
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
20. The archive branch has no size compaction job; Phase 2 adds `reference/`, `lineups/`, `weather/`,
    `results/espn/`, `fixtures/espn/` writers (all change-suppressed or append-only, but growth is unbounded).
21. The simulation cache is per-run (artifact-restored) rather than shared across jobs.
22. Router importer, settlement importer and validator exist with receipts/idempotency tests, but the router
    profile, token scoping and classifier change are the owner's; no soccer fill is routed anywhere.
23. All authority cells are `RESEARCH_ONLY`; the operator command will say `NO BETS` until
    prospective evidence exists and a human promotes a cell.
25. A production bug shipped in Mission 1 and was fixed in Phase 2: every archived snapshot was labelled
    horizon `T-10m` (raw `minutes_to_kickoff` was correct). Analyses of horizon labels before 2026-09-28
    must recompute the label from `minutes_to_kickoff` (the microstructure summary does).
26. **The international pool model is not validated.** From 2026-09-28 12:42 UTC `run-soccer` prices Nations League,
    CONCACAF NL, friendlies and qualifiers from ESPN-backfilled results (pooled, one home-advantage term, club-style
    priors for national teams). First live run: 830 contracts priced, 43 RESEARCH_ONLY shadow expressions, several
    with absurd fairs (San Marino 25% to beat Albania; +50% "edges" at 2¢ prices) — the priors do not shrink
    minnows enough and no historical benchmark exists for internationals. These records carry the distinct family
    `data_only.world_sim_v1.intl_pool` so they never count toward the club-league evidence cells; they must be
    read as noise until a walk-forward on the pooled international archive exists.

