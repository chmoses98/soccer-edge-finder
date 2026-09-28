"""xg_strength_v1 (phase 20): joint goals + xG pseudo-likelihood through the v2 fitter, and the
pre-registered walk-forward evaluation's mechanics on a synthetic history."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from research.xg_strength_eval import fit_rows, paired, walk_forward

from soccer_edge.model.strength import MatchRow
from soccer_edge.model.strength_v2 import DixonColesFitterV2


def _matches(seed=0, n_teams=8, seasons=("2016", "2017"), rounds=14, xg_edge_team="t0"):
    rng = np.random.default_rng(seed)
    teams = [f"t{i}" for i in range(n_teams)]
    att = rng.normal(0, 0.2, n_teams)
    out = []
    for s_i, s in enumerate(seasons):
        d0 = date(2016 + s_i, 8, 10)
        for r in range(rounds):
            perm = rng.permutation(n_teams)
            for i in range(0, n_teams, 2):
                h, a = teams[perm[i]], teams[perm[i + 1]]
                lam = 1.4 * np.exp(att[perm[i]] - att[perm[i + 1]] * 0.5)
                mu = 1.1 * np.exp(att[perm[i + 1]] - att[perm[i]] * 0.5)
                hg, ag = int(rng.poisson(lam)), int(rng.poisson(mu))
                # xG tracks the true rate; the "unlucky" team's goals under-shoot its xG
                hxg = lam * (1.6 if h == xg_edge_team else 1.0) * rng.uniform(0.85, 1.15)
                axg = mu * (1.6 if a == xg_edge_team else 1.0) * rng.uniform(0.85, 1.15)
                out.append(
                    {
                        "division": "X1",
                        "date": d0 + timedelta(days=7 * r),
                        "home": h,
                        "away": a,
                        "hg": hg,
                        "ag": ag,
                        "hxg": float(hxg),
                        "axg": float(axg),
                        "season": s,
                    }
                )
    return out


def test_xg_rows_enter_as_weighted_pseudo_observations_without_dc_correction():
    ms = _matches()
    rows0 = fit_rows(ms, 0.0)
    rows5 = fit_rows(ms, 0.5)
    assert len(rows5) == 2 * len(rows0)
    xg_rows = [r for r in rows5 if not r.dc_correction]
    assert all(r.weight == 0.5 for r in xg_rows) and any(
        r.home_goals != int(r.home_goals) for r in xg_rows
    )
    as_of = date(2018, 6, 1)
    p0 = DixonColesFitterV2().fit(rows0, as_of=as_of)
    p5 = DixonColesFitterV2().fit(rows5, as_of=as_of)
    # the team whose xG exceeds its goals gets a higher attack under the joint likelihood
    a0 = p0.mean[p0.idx_attack("t0")] - p0.mean.mean()
    a5 = p5.mean[p5.idx_attack("t0")] - p5.mean.mean()
    assert a5 > a0
    # integer-only rows are unaffected by the flag (identical fit)
    p0b = DixonColesFitterV2().fit(
        [MatchRow(r.date, r.home, r.away, r.home_goals, r.away_goals) for r in rows0], as_of=as_of
    )
    assert np.allclose(p0.mean, p0b.mean)


def test_walk_forward_scores_only_the_requested_seasons_and_pairs_records():
    ms = _matches(seasons=("2016", "2017", "2018"), rounds=10)
    r0 = walk_forward("X1", ms, 0.0, ("2018",))
    r1 = walk_forward("X1", ms, 0.5, ("2018",))
    assert r0["records"] and len(r0["records"]) == len(r1["records"])
    assert {r["season"] for r in r0["records"]} == {"2018"}
    assert all(np.isfinite(r["ll_1x2"]) and np.isfinite(r["ll_ou25"]) for r in r0["records"])
    d = paired(r0["records"], r1["records"], "ll_1x2")
    assert d["n"] == len(r0["records"]) and len(d["ci95"]) == 2
