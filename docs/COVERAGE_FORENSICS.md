# Coverage forensics (Phase 2)

Machine-readable source: `data/diagnostics/latest_coverage_diagnostics.json` (written by
`.github/workflows/diagnostics.yml`, `soccer run --window 340`). All counts are **contracts** on the live
Kalshi surface; `unaccounted_contracts` stayed 0 throughout — nothing here was ever dropped, only classified.

## Baseline (run `disc-20260928T024650Z-290fa9`, 2026-09-28 02:46 UTC, international break)

Disposition × time-to-kickoff:

| disposition | next 72h | next 14d | later |
|---|---:|---:|---:|
| priced | 0 | 9 | 108 |
| no_fixture | 372 | 465 | — |
| unmapped_event (competition not registered) | 476 | 657 | — |
| unmapped_team | 258 | 805 | 111 |
| unsupported_family (futures/specials) | — | 164 | 2,968 |
| ambiguous_ownership | — | — | 18 |
| out_of_window | — | — | 12 |

Current-tradable match-scope loss by competition token (top): `UEFANL` no_fixture 837 + unmapped_team 809;
`CONCACAFNL` unmapped_event 333; `LIGAMX` unmapped_team 161; `INTLFRIENDLY` unmapped_event 163; `USL` 106;
`BRASILEIRO` unmapped_team 85; `EFLL1` 86; `ISRNL` 80; `MLS` unmapped_team 76; `BRASILEIROB` 67; `COPADELREY` 25.

Root causes, in order of contracts:

1. **International windows are invisible to the data layer.** The registry knew 81 national teams but had
   no fixture/results provider for national-team competitions, and 19 UEFA Nations League participants were
   missing outright (Kazakhstan, North Macedonia, Latvia, Finland, San Marino, Moldova, Luxembourg, Bulgaria,
   Armenia, Malta, Israel, Azerbaijan, Estonia, Cyprus, Belarus, Kosovo, Iceland, Faroe Islands, Montenegro).
2. **No Americas clubs in the registry at all** (Liga MX, MLS, Brasileirão, Argentina) — every one of their
   match contracts failed on the first unresolved side. Kalshi spells them tersely (`New York RB`,
   `Saint Louis`, `Los Angeles F`, `Club Necaxa`/`Necaxa`, `Sao Paulo`).
3. **Unregistered competitions** the taxonomy classifies but the registry has no id for: CONCACAF Nations
   League, international friendlies, USL Championship, EFL League One, Israeli league, Série B, ….
4. Five European alias gaps: `Bilbao`, `Atletico`, `Stade Brest 29`, `Parma Calcio`, ``M´gladbach`` (acute
   accent, not an apostrophe).
5. Copa del Rey first-round minnows (5 clubs, 25 contracts): out of scope — no data source models them.

## Actions taken (explicit, no fuzzy matching)

* `data/registry/americas_and_nations.json`: 23 national teams, 18 Liga MX, 30 MLS, 28 Brasileirão, 5
  Argentine clubs with Kalshi spellings as aliases; `seed.json` alias patches for the five European gaps.
  Team resolution stays country-scoped (`Santos` → `mex.santos_laguna` under MEX, `bra.santos` under BRA).
* ESPN fixture adapter (`docs/LINEUPS.md`) with explicit `data/mappings/espn_map.json`; the probe now fetches
  full ESPN team lists for 23 leagues so the map can be extended by exact alias resolution offline.
* Diagnostics now also list `unknown_teams_current` (ranked by contracts) and `unregistered_competitions_current`.

Expected effect of the registry change alone: `unmapped_team` contracts for the competitions above move to
`no_fixture` (honest: the team is known, the match is not in any provider yet). Pricing them additionally
requires a fixture **and** a results history for strength fitting — the ESPN adapter supplies fixtures and FT
scores for `usa.1`, `mex.1`, `bra.1`, `arg.1`, `uefa.nations`, `fifa.friendly` once the runner-side backfill has
run (see `docs/ROADMAP.md`). No competition was mapped speculatively: tokens whose meaning is not certain
(`FIFAW`, `APFDDH`, `EFL`) stay `None` in the taxonomy table.

## Re-measurement (run `disc-20260928T030600Z-1c2fe8`, 2026-09-28 03:06 UTC, registry slice 2 only)

Same workflow, same 340 h window, 20 minutes later (6,338 contracts on the surface; 0 unaccounted):

| disposition | next 72h | next 14d | later | change vs baseline |
|---|---:|---:|---:|---|
| priced | 0 | 9 | 123 | +15 later (fixtures newly in window) |
| no_fixture | 577 | 1,245 | 87 | +205 / +780 / +87 — the ex-`unmapped_team` contracts, now honestly "known team, no fixture" |
| unmapped_event | 444 | 657 | — | unchanged (competitions registered in slice 3: `CONCACAFNL`, `INTLFRIENDLY`) |
| **unmapped_team** | **0** | **28** | **6** | **from 258 / 805 / 111 → 0 / 28 / 6** |
| unsupported_family | — | 164 | 2,968 | unchanged (futures/specials, by design) |

Remaining unknown team names on the current surface (8): five Copa del Rey first-round minnows (out of
scope), `Atlante` (Liga MX; added in slice 3), `Instituto Cordoba` (added in slice 3), `Los Angeles G`
(Kalshi truncation of LA Galaxy; alias added). Current-tradable match-scope loss: 3,174 → 3,074 contracts,
and its composition changed from "we don't know who is playing" to "we know who, we have no fixture/model":

* `UEFANL` 1,646 contracts are now `no_fixture` — served by the ESPN international pool once
  `espn-backfill` has run (fixtures come from `uefa.nations` per-day scoreboards; strengths from pooled
  international results).
* `LIGAMX` 105, `BRASILEIRO` 85, `MLS` (now in window) — same path via `mex.1`, `bra.1`, `usa.1`.
* `CONCACAFNL` 362 / `INTLFRIENDLY` 163 move from `unmapped_event` to `no_fixture` after slice 3, same path.
* `USL` 131, `EFLL1` 86, `ISRNL` 80, `BRASILEIROB` 67: ESPN has slugs (`usa.usl.1`, `eng.3`, `isr.1`, `bra.2`)
  but no registry teams yet; deliberately not mapped until a team-list probe covers them.

What did **not** change and must not be over-read: nothing new is priced by identity work alone. Pricing
needs the ESPN results backfill (owner dispatches `espn-backfill.yml` once; then `run-soccer` picks up
`results/espn` automatically) and, for the international pool, at least ~50 results per pool.
