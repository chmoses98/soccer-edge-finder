# Lineups: ESPN adapter and the lineup uncertainty layer (Phase 3–4)

Status: **built, prospective capture wired, not yet consumed by pricing.** Nothing in this document changes
recommendations or authority. It exists to start accumulating point-in-time lineup evidence now so that
later research can measure what lineup information is worth.

## Source: ESPN public site API (`src/soccer_edge/providers/espn.py`)

Verified 2026-09-28 from the runner (`data/samples/espn_xg_probe.json`; the dev container cannot reach ESPN):

| Endpoint | Verified | Notes |
|---|---|---|
| `/{league}/scoreboard?dates=YYYYMMDD` | yes (all 14 slugs 200) | per-day queries; the range form returned 400 in the first probe (re-probed) |
| `/{league}/summary?event={id}` | yes | `rosters[]` per side with `formation`, `roster[]` entries: `starter`, `formationPlace`, `jersey`, `position`, `subbedIn/Out`, `athlete{id,displayName}`; also `gameInfo`, `header`, `odds` |
| `/{league}/teams` | yes | 20 EPL teams, 36 UCL teams |

Verified league slugs: `eng.1 esp.1 ger.1 ita.1 fra.1 usa.1 uefa.champions uefa.europa uefa.europa.conf fifa.friendly
uefa.nations eng.2 mex.1 usa.nwsl`. Other slugs in `data/mappings/espn_map.json` are ESPN's documented names and
are **not** used until a probe confirms them (`verified_leagues`).

Second probe (2026-09-28 03:06 UTC): summaries fetched 31–94 hours before kickoff (MLS, friendlies, Nations
League) return a `rosters` array with **zero entries** — ESPN does not expose XIs days ahead. **How long before
kickoff the XI appears is still unmeasured**; the prospective capture records `event_state` with every snapshot,
so the archive answers it empirically (`LineupStateTracker.confirmation_lead_minutes`). Until then no fixture is
treated as CONFIRMED for pricing. Also confirmed: the `dates=YYYYMMDD-YYYYMMDD` range form returns 400 for every
league; the adapter queries per day.

No key, no ToS-restricted bulk use: per run, one scoreboard call per league-day and one summary call per fixture
within [-3h, +26h] of now. Provenance (URL, observed_at, content hash) travels with every snapshot.

## Identity: explicit, exact, fail-loud

`data/mappings/espn_map.json` maps ESPN league slugs → `competition_id` and ESPN team ids → canonical `team_id`.
The team rows were produced by **exact alias resolution** (scoped men's / women's / national, no weak or fuzzy
forms) against `data/registry/*.json` from the probe's full team lists for 23 leagues (v2). Ids the registry does
not know are listed under `unmapped_from_probe` and stay unmapped. Anything unmapped is *reported* (`MappingReport.unmapped_team_ids`,
`data/diagnostics/latest_espn_status.json`) and the fixture is skipped. `propose_team_map` writes proposals for a
human to review; it never edits the table.

## Point-in-time lineup snapshots (`espn_lineup_snapshot_v1`)

`capture_lineups` appends one JSONL row per (event, changed content) under `lineups/<date>/<league>.jsonl` on the
private `data-archive` branch, change-suppressed by content hash. Each row carries `captured_at`, `event_state`,
`kickoff_utc`, formations, and the full roster per side.

`lineup_state` per snapshot:

* `unconfirmed` — no XI published at capture;
* `confirmed` — XI published **and** `event_state == "pre"` (captured before kickoff);
* `post_hoc` — XI read at/after kickoff. Valid *history* for later fixtures, **never** a confirmation for the same
  fixture (that would be backward leakage).

## Uncertainty layer (`src/soccer_edge/model/lineups.py`)

Per player, per information state:

* UNCONFIRMED: `P(start)` = recency-weighted starting rate (half-life 42 days) shrunk toward a squad prior
  (0.35 with weight 1 pseudo-sheet); `P(in squad)` from the share of the team's recent sheets the player appeared
  on; `P(unavailable) = 1 − P(in squad)`; `P(bench) = P(in squad) − P(start)`. The three sum to 1.
* CONFIRMED: `P(start) ∈ {0, 1}` from the published XI; `P(unavailable)=0` for named players.
* PROJECTED: reserved for an external projected-XI source (none adopted; nothing free and reliable was found).
* Minutes: `E[min | start] = 80`, `E[min | bench] = 15` priors (ESPN summaries do not expose minutes; the
  `minutes` field is carried so a later source can replace the priors).

`estimate_team` refuses history at/after `as_of` (raises) so a replay cannot leak. `LineupStateTracker` appends
fixture-level transitions (`unconfirmed → confirmed`, with minutes-to-kickoff) prospectively.

`PlayerLineupEstimate.to_availability()` produces the existing `PlayerAvailability` used by `MatchContext`; the
world generator already reads `home_players/away_players` when present. **Wiring the estimates into production
`MatchContext` is deliberately not done in this phase**: the importance weights (share of attack per player) are
research-only placeholders, and the current benchmark must stay frozen for the walk-forward comparison.

## Workflow

`.github/workflows/espn-lineups.yml` (every 2 h + dispatch): `soccer espn-sync` → snapshots and an ESPN fixtures
window to `data-archive` (`lineups/`, `fixtures/espn/`), `STATUS.json` (counts, unmapped ids, map proposals) to
`data/diagnostics/latest_espn_status.json` on the calling branch.

## What would make lineups matter (research plan, not done)

1. Measure confirmation lead time and the share of fixtures confirmed before Kalshi's last pre-kickoff quote.
2. With ≥ 1 season of snapshots: does a strength model with player-availability adjustments reduce log loss
   walk-forward vs the frozen benchmark? Compare on fixtures where a key player (top-3 by minutes) is absent.
3. Only then consider a `lineup_adjusted_v1` family, RESEARCH_ONLY, via the promotion rules in `docs/CALIBRATION.md`.
