# Roadmap (ordered by expected improvement, not ease)

1. **Keep the taxonomy current.** Done for the 2026-09-27 surface (v2). Each discovery commits an
   `unknown_body_histogram`; review it weekly and add tokens with their verified rules text.
   Register the lower-league competition codes that carry match markets (APFDDH, ARGNACB,
   BRASILEIROB/C, CANPL, ...) once a fixture source for them exists.
2. **Calibrate uncertainty.** Fit `sigma_model_log_rate`, decay, and priors so the 80% interval on
   P(home) covers the market-as-oracle ~80% and the O/U 2.5 ECE drops below 0.02. Re-run
   `walk_forward_v1` → `v2` with a frozen comparison to v1's hash.
3. **Market-informed production family.** Since HYBRID collapses to the market, the useful production
   question is "where does Kalshi's *thin* book disagree with a sharp reference?" Ingest
   football-data.co.uk `fixtures.csv` (current bookmaker odds, reachable from runners) as a
   MARKET_ONLY reference at capture time; evaluate `Kalshi mid` vs `reference` vs `DATA_ONLY`
   prospectively. This is the only route to an edge that the research supports.
4. **Closing-line research.** Runner-side fetch of football-data.co.uk seasons ≥2019-20 with
   `B365C*`/`PSC*` columns → true closing benchmark and CLV for the research families.
5. **xG-input strength model** (football-data.co.uk HxG/AxG; `data_only.xg_dc_v1`) as a genuinely
   different DATA_ONLY family; compare on aligned samples.
6. **ESPN fixture + lineup adapter** → UEFA/international fixtures, confirmed lineups, first-scorer
   and player-goal settlement inputs; wire `LineupProvider` into `MatchContext`.
7. **Multi-league hierarchical strength** so UCL/UEL fixtures can be modelled.
8. **Prospective shadow accrual**: keep `run-soccer` + `kalshi-capture` + `settle-evaluate` running;
   review `ModelHealthV1` monthly; first authority decision only after ≥300 settled in a cell.
9. **Positions/settlement import** (`PositionV1`, importer CLI + validator) when the owner decides to
   route soccer fills; then the safe half of the router change.
10. **Player layer research**: per-player goal shares from event data (needs a licensed source).
11. **Archive compaction + size guard** on `data-archive`; shared sim cache across jobs.
12. **Exact score / margin / HT-FT pricers** (trivial from the joint distribution) once such
    families are observed live.
