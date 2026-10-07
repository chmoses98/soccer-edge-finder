# SIFT Soccer handoff (for the later SIFT session; nothing here was changed in SIFT)

Backend spec: `docs/GAME_SCRIPTS.md`. Everything below reads published files only.

## 0. Prerequisites in SIFT (not done here)

* `src/data/sports.ts`: SOCCER is tier `listed` (no explorer / game screens). Promote to `secondary` so
  `resolveSource` loads `health.json` + `explorer/index.json` from
  `https://raw.githubusercontent.com/chmoses98/soccer-edge-finder/data-archive/app/latest`.
* Game route: `useDirectory` -> `index.events[]` -> `repo.eventResearch(eventId)` (already generic). Add a switch on
  `extensions.soccer_script_engine` (like `extensions.script_engine` for CFB) to render the soccer page.
* Prices: `repo.eventDetail(eventId)` (board.json -> `detail_path`) for live asks, as CFB does; join on `ticker`.

## 1. Page hierarchy (mobile first) and fields

| section | component | fields (`p = extensions.soccer_script_engine`) |
|---|---|---|
| HERO | generic `GameHero` | `event` (generic), `p.glance.h_d_a` (three-way bar: Home / Draw / Away, never binary), `p.glance.competition` (name, type, stage, flags chips), kickoff, venue |
| THE GAME IN 10 SECONDS | new `SoccerGlance` | `glance.story.sentence`; `glance.expected_goals` (label "model goal rate", never xG); `glance.primary_script` / `secondary_script` (title + share); `glance.primary_mismatch.label`; `glance.lineup.status`; `glance.data_confidence` chip; `glance.best_robust_expression` or the `no_compelling_edge_reason` |
| HOW THIS GAME CAN HAPPEN | new `SoccerScriptCards` (reuse the visual grammar of CFB `EngineScriptsPanel`, but WITH shares, like NFL `ScriptsPanel`) | `scripts.cards[]` in `scripts.order`: `title`, `simulation_share` (+ `share_low/high`), `definition`, `primary` (H/D/A, xG, `typical_scores`), `markets_helped` / `markets_hurt`; immaterial cards (`material=false`) collapsed, never hidden |
| WHAT SURVIVES | new `SoccerSurvivors` (adapt CFB `EngineSurvivorsPanel`) | `survivability.rows` where `category == ROBUST_ACROSS_SCRIPTS`, one row per `thesis_group` (show `thesis_groups[].best_expression`, fold the other members under it); per row: `description`, side, live ask, `label`, `supporting_scripts`/`material_scripts`, `weighted_support_share`, the `stance` strip (one cell per script, S/O/N/-), `counter_case.statement` |
| WHAT NEEDS A SPECIFIC GAME | same component, second list | rows with `category == SCRIPT_SPECIFIC_UPSIDE`; headline = `strongest_support.script` ("needs Home control") |
| WHY | new `SoccerMatchup` | `matchup.matchups.HOME_ATTACK_vs_AWAY_DEFENSE` / `AWAY_ATTACK_vs_HOME_DEFENSE`: label, both percentiles, `z_gap`, `p_attack_advantage`, `evidence_quality`; team cards from `matchup.home/away` (attack/defence percentile, expected scored/conceded vs average opponent, schedule strength, raw form clearly labelled unadjusted) |
| MATCH CONTEXT | new `SoccerContext` | `context` fields with their `status` (KNOWN/DERIVED shown, UNAVAILABLE as a muted chip), `context.flags`, `context.model_effect` |
| ALL MARKETS | generic `MarketBoard` + new matrix view | `matrix.rows` (script x market heat map, YES side; NO = 1 - p), `markets.json` `extensions.script_robustness` per side |
| DATA & PROVENANCE | generic `Notice` / `Info` | `freshness` (model / scripts / market / lineup / context / reference clocks), `data_confidence.gates/reasons`, `data_gaps[]` as chips, `methodology`, `provenance`, `authority` (RESEARCH_ONLY banner) |

Lineup sheet: `lineup_rescripting` (status, time, `model_uses_lineups=false` with reason, pre/current shares and
deltas, `statement`). Show "XI confirmed - probabilities unchanged (no player model)" when deltas are zero.

## 2. Rules the UI must keep

* Three-way always: Home / Draw / Away; double chance, DNB, +0.5 are separate expressions, never collapsed.
* Freshness: after `freshness.market.current_until` every edge is stale. Either hide edges or recompute them at the
  live ask: `edge_S = p_side(S) - (ask + fee(ask))`, with `p_side(S)` from `matrix.rows[..].p_yes_by_script`
  (NO side: 1 - p) and `methodology.fee_model`; recompute the stance with band 0.02 and the label with
  `methodology.survivability.labels`. A fresh price with `freshness.model.validity != VALID` is NOT an edge.
* Research only: show `authority.status`; no "bet" language, no stake units.
* Labels are descriptive; always show the components under a label (support count, stance strip, counter-case).
* Shares are "modelled likelihood" (simulation share), not calibrated probabilities.
* Do not present six correlated rows as six discoveries: group by `thesis_group`.

## 3. Reuse vs soccer-specific

Reusable as is: `GameHero`, `MarketBoard`, live quote overlay, `LineHistoryPanel`, `Movement`, `Stratum`, `Notice`,
`PanelHead`, `Info`, `ViewAll`, the explorer loaders (`repo.eventResearch`, `repo.profile`, `pathFor`).
Reusable with soccer copy: the CFB engine's panel layouts (read / scripts / survivors / confidence) - the soccer
payload adds shares and a quantitative counter-case, and has no football dimensions (`EDGE_DIMENSIONS`,
`winsWhenText`, margin bands do not apply).
Soccer-specific: three-way hero bar, script x market matrix, stance strip, thesis-group folding, matchup panel
(attack vs defence percentiles), context field chips, lineup re-scripting sheet.

## 4. Fixtures for SIFT tests

`tests/test_game_scripts.py::test_explorer_publishes_the_script_engine_per_event` builds a full `app/latest` with
the payload from a synthetic run; the live tree on `data-archive` carries real fixtures after the first model run of
this build.
