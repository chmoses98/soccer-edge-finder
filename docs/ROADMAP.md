# Roadmap (ordered by expected improvement, not ease)

Status after Phase 2 (2026-09-28). ✅ built and running · 🟡 built, evidence pending · ⬜ not started.

1. ✅ **Keep the taxonomy current.** v2.1 leaves 0 unknown bodies on the live surface; each discovery commits an
   `unknown_body_histogram`. Phase 2 registered `fifa.friendly` and `concacaf.nations_league`; tokens with uncertain
   meaning (`FIFAW`, `APFDDH`, `EFL`, …) remain `None` on purpose (`docs/COVERAGE_FORENSICS.md`).
2. 🟡 **Calibrate uncertainty.** Walk-forward recalibration research (`docs/UNCERTAINTY_RECALIBRATION.md`) with the v1
   benchmark frozen; any change ships as a new `StrengthConfig` version, never an edit.
3. ✅ **Reference market at capture time.** football-data.co.uk `fixtures.csv` is captured as point-in-time
   `ReferenceMarketSnapshot` rows (consensus = `Avg*` columns, else mean of Bet365/Pinnacle); prediction records carry
   the reference probability and the Kalshi mid; settlements carry reference close + CLV (`docs/KALSHI_CAPTURE.md`).
4. 🟡 **Closing-line / CLV research.** Infrastructure done (TRUE_CLOSE ≤30 min, NEAR_CLOSE ≤6 h, side-aware
   probability/price/fee-aware CLV). Evidence accrues prospectively; nothing to conclude yet.
5. 🟡 **xG-input family.** `data_only.xg_strength_v1` scaffold + ingestion of 2026-27 `HxG/AxG` (all eight files).
   **NOT_EVALUATED** — no historical xG exists for the benchmark window (`docs/XG_DATA_AUDIT.md`).
6. ✅/🟡 **ESPN fixture + lineup adapter.** Fixtures, FT results, point-in-time lineup snapshots and weather run every
   2 h (`espn-lineups.yml`); identity map is explicit (486 teams). Lineup estimates are computed but **not wired into
   pricing** until confirmation lead time is measured (`docs/LINEUPS.md`). Backfill of results for the Americas
   leagues and the international pool: `espn-backfill.yml` (dispatch once, then incremental).
7. 🟡 **Multi-league hierarchical strength** (`docs/MULTI_LEAGUE_MODEL.md`), RESEARCH_ONLY.
8. ✅ **Prospective shadow accrual** running; `ModelHealthV1` monthly; first authority decision after ≥300 settled in
   a cell. Policy replay (`docs/POLICY_VERSIONING.md`) keeps MODEL / SELECTION / STAKING attributable.
9. ✅ **Positions/settlement importer + validator** built with receipts, idempotency and privacy tests; the router-side
   profile is the owner's call (`docs/ROUTER_INTEGRATION.md`). No live routing.
10. ⬜ **Player layer research** (needs a licensed event source; ESPN has no minutes/xG).
11. 🟡 **Microstructure** summaries published by `settle-evaluate` (`docs/KALSHI_MICROSTRUCTURE.md`); use them to
    decide whether an edge survives spread + fee before any selection-policy change.
12. ⬜ **Archive compaction + size guard**; shared sim cache across jobs.
13. ⬜ **Exact score / HT-FT pricers** for families observed live.

Next concrete steps, in order: (a) dispatch `espn-backfill` once and confirm `usa.mls`, `mex.liga_mx`, `bra.serie_a`,
`arg.primera` and the international pool fit (≥50 results each) so their contracts move from `no_fixture` to
`priced`; (b) after two weeks of `espn-lineups` snapshots, read `confirmation_lead_minutes`; (c) after ~300 settled
shadow recommendations, read CLV by close class and the policy replay before touching any threshold.
