# International data rebuild and `intl_hier_v1` (remediation phases 16-17; audit §E)

## Verdict

`intl_hier_v1` **beats the current international pool model and a point-in-time Elo on the frozen
2022-2026 holdout** (paired log-loss differences with 95 % CIs entirely below zero, overall and on
competitive matches, neutral sites and cross-confederation ties), but it **fails three of the eight
pre-registered acceptance criteria** (friendlies vs Elo, individual heavy-favourite pricing at Elo gaps
>= 400, neutral-site goal calibration). Under the audit's rule the family therefore stays gated:
`RunConfig.intl_shadows_enabled = False` keeps every international-pool record out of every shadow list
(the records are still archived as evidence), and `intl_hier_v1` is **not** promoted to production
pricing. The result is preserved as is; the holdout was used once and is not to be reused for tuning.

## Data (phase 16)

* Source: the CC0 "International football results from 1872 to today" dataset (Mart Jurisoo),
  pinned by sha256 in `data/international/MANIFEST.json` (fetched by `providers/international_results.py`
  through GitHub raw; licence CC0 1.0 verified in the upstream repository, recorded in the manifest).
* `data/international/results_v1.csv.gz`: 48,249 of the 49,547 source matches (1872-11-30 to 2026-08-26)
  after filtering to teams in the confederation map (231 current members), each with `date, home, away, hg, ag, tournament,
  neutral, city, country`, a `competitive` flag (non-friendly), confederation of each team
  (`data/international/confederations.json`) and a point-in-time Elo (World-Football-Elo style: K by tournament class, goal-difference
  multiplier, home advantage 100 and 0 at neutral venues, computed strictly from earlier rows).
* Neutral sites: the dataset's `neutral` flag; for live ESPN fixtures `providers/espn.py::infer_neutral_site`
  compares the venue country to the home team's name for international leagues (`INTERNATIONAL_LEAGUE_PREFIXES`).
* Nothing is recomputed from Kalshi or any paid source; the file is regenerable with
  `python -m soccer_edge.providers.international_results <results.csv>` (the source hash is pinned; a newer
  snapshot needs `--allow-unpinned` and a manifest review).

## Model (phase 17): `model/intl_hier.py::IntlHierFitter`

Poisson goals with `log lambda_home = kappa + a_home - d_away + h * (1 - neutral) + c_att[conf_home] - c_def[conf_away]
+ beta_elo * (elo_home - elo_away)/400`, symmetric for the away side; Laplace-approximated posterior with
hierarchical shrinkage of team attack/defence towards their confederation offset (no fixed "minnow
penalty"), exponential time decay with a half-life in years, friendlies down-weighted by `friendly_weight`,
strict point-in-time inputs (`strict_point_in_time`). Every prediction carries `prediction_flags`
(`low_connectivity` when a team met fewer than 3 cross-confederation opponents in the last 4 years;
8.3 % of holdout matches involve such a team).

## Protocol (pre-registered in `research/intl_hier.py`)

* Selection window 2014-2021 (train from 2000), yearly refits, 12-point grid
  `friendly_weight in {0.4, 0.6, 0.8, 1.0} x half_life_years in {1, 2, 3}`, ranked by log loss:

| config | ll_hier | pool | elo |
|---|---|---|---|
| w1.0_h3.0 (chosen) | 0.87870 | 0.97824 | 0.88298 |
| w1.0_h2.0 | 0.87899 | | |
| w0.8_h3.0 | 0.87901 | | |
| w0.4_h1.0 (worst) | 0.88138 | | |

  n = 6,865 matches; every configuration beats the pool and Elo on the selection window.
* ONE-TIME holdout 2022-01-01 to 2026-08-26 (n = 4,563), chosen configuration frozen at
  2026-09-28T19:36Z (`data/research/intl_hier_selection.json`).

## Holdout result (`data/research/intl_hier_holdout.json`)

| metric | intl_hier_v1 | pool (current) | elo |
|---|---|---|---|
| log loss (1X2), n=4,563 | **0.8671** | 0.9716 | 0.8739 |
| paired vs pool, mean [95 % CI] | -0.1045 [-0.1164, -0.0912] | | |
| paired vs Elo | -0.0067 [-0.0127, -0.0012] | | |
| competitive (n=3,307) | 0.8555 | 0.9653 | 0.8638 |
| friendlies (n=1,256) | 0.8977 | 0.9882 | 0.9004 |
| neutral sites (n=1,580) | 0.9041 | 1.0249 | 0.9148 |
| cross-confederation (n=769) | 0.8778 | 1.0112 | 0.9095 |
| ECE home / draw / away | 0.022 / 0.010 / 0.026 | 0.031 / 0.019 / 0.047 | 0.015 / 0.014 / 0.015 |

Mismatch bands (underdog probability vs realised underdog win rate): Elo gap 300-400 (n=597) 7.8 % priced
vs 8.2 % realised; gap >= 400 (n=591) 3.3 % priced vs 2.9 % realised.

Acceptance (all eight must pass):

| criterion | result |
|---|---|
| beats pool, CI upper < 0 | PASS |
| beats Elo, CI upper < 0 | PASS |
| beats both on competitive matches | PASS |
| beats both on friendlies | **FAIL** (vs Elo: -0.0026 [-0.0134, +0.0089]) |
| mismatch bands calibrated within 2 pt | PASS |
| no gap >= 400 match priced at > 2x the band's realised underdog rate | **FAIL** (95 of 591 matches; max 27.3 % priced vs 2.9 % realised band rate) |
| ECE <= 0.03 each outcome | PASS |
| neutral-site expected goals within 0.05 of realised | **FAIL** (listed-first team: 1.209 predicted vs 1.373 realised; listed-second: 1.167 vs 1.233) |

## Reading the failures (no tuning was done against the holdout)

* **Neutral sites.** At neutral venues the team listed first scores 0.16 goals more than the model
  expects. In this dataset "home" at a neutral venue is frequently the tournament host, the higher seed
  or the designated home side of a two-legged tie, so a residual listed-first advantage exists; the model
  sets the home effect to zero there. A neutral-site listed-first term is a legitimate next step but has
  to be fitted on the design window and evaluated on data that has not been seen, i.e. prospectively.
* **Heavy favourites.** The band as a whole is calibrated (3.3 % vs 2.9 %), but individual matches are
  priced up to 27 % for the underdog: the hierarchical shrinkage keeps under-connected minnows near their
  confederation mean. The pre-registered criterion is per match and it fails.
* **Friendlies.** The model is better than the pool but not distinguishable from Elo; friendlies carry
  full weight in the chosen configuration (w = 1.0 ranked first on the selection window).

## What is wired and what is not

* Wired: dataset + manifest, provider, fitter, study harness (`python research/intl_hier.py all`),
  `tests/test_international.py` (dataset integrity, point-in-time Elo, fitter properties incl. the
  Albania/San Marino pin, neutral handling, connectivity flags), ESPN neutral inference, pipeline gate.
* Not wired: `intl_hier_v1` is not a production model family; `intl_shadows_enabled` stays False; the
  international pool remains as-is for archival pricing (evidence only, never a shadow).
* Next step for an owner (not done here): approve a v1.1 design with a neutral listed-first term and a
  connectivity-aware favourite cap, fit it on 2000-2021 and evaluate it prospectively on matches after
  2026-08-26. Re-running this holdout with a changed model would be tuning against the holdout.
