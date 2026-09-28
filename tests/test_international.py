"""International dataset (phase 16), intl_hier_v1 (phase 17), ESPN neutral inference, shadow gate."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from soccer_edge.model.analytic import outcome_probs, score_matrix
from soccer_edge.model.intl_hier import IntlHierConfig, IntlHierFitter, IntlMatchRow
from soccer_edge.providers.espn import infer_neutral_site
from soccer_edge.providers.international_results import (
    PINNED_SHA256,
    TEAM_TO_CONFEDERATION,
    compute_point_in_time_elo,
    load_source,
    normalise,
    read_dataset,
    team_id,
    write_dataset,
)


def _source_csv(path: Path, rows):
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "date",
                "home_team",
                "away_team",
                "home_score",
                "away_score",
                "tournament",
                "city",
                "country",
                "neutral",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _row(d, h, a, hs, as_, tour="Friendly", neutral="FALSE"):
    return {
        "date": d,
        "home_team": h,
        "away_team": a,
        "home_score": hs,
        "away_score": as_,
        "tournament": tour,
        "city": "x",
        "country": h,
        "neutral": neutral,
    }


def test_loader_pins_the_source_hash(tmp_path):
    p = tmp_path / "results.csv"
    _source_csv(p, [_row("2020-01-01", "Spain", "France", 1, 0)])
    with pytest.raises(ValueError, match="pinned"):
        load_source(p)
    rows, digest = load_source(p, allow_unpinned=True)
    assert (
        len(rows) == 1
        and digest == hashlib.sha256(p.read_bytes()).hexdigest()
        and digest != PINNED_SHA256
    )


def test_normalise_excludes_non_fifa_and_builds_reproducible_dataset(tmp_path):
    rows = [
        _row("2020-01-01", "Spain", "France", 2, 1, "UEFA Nations League"),
        _row("2020-01-02", "Brazil", "Argentina", 0, 0, "Friendly", "TRUE"),
        _row("2020-01-03", "Jersey", "Guernsey", 3, 1),  # non-FIFA
        _row("2020-01-04", "Spain", "Padania", 1, 0),  # one non-FIFA side
    ]
    ms, stats = normalise(rows)
    assert [m.home_team for m in ms] == ["Spain", "Brazil"]
    assert stats["excluded_rows_non_fifa"] == 2 and set(stats["excluded_teams"]) == {
        "Jersey",
        "Guernsey",
        "Padania",
    }
    assert ms[0].competitive and not ms[0].neutral and ms[0].home_conf == "UEFA"
    assert not ms[1].competitive and ms[1].neutral and ms[1].home_conf == "CONMEBOL"
    assert (
        ms[0].home_id == "intl:spain"
        and team_id("Bosnia and Herzegovina") == "intl:bosnia_and_herzegovina"
    )
    man = write_dataset(ms, tmp_path / "ds", source_sha256="abc", stats=stats)
    h1 = hashlib.sha256((tmp_path / "ds" / "results_v1.csv.gz").read_bytes()).hexdigest()
    write_dataset(ms, tmp_path / "ds", source_sha256="abc", stats=stats)
    assert hashlib.sha256((tmp_path / "ds" / "results_v1.csv.gz").read_bytes()).hexdigest() == h1
    back = read_dataset(tmp_path / "ds")
    assert len(back) == 2 and back[0]["home_goals"] == 2 and back[1]["neutral"] is True
    assert man["rows"] == 2 and man["source_license"].startswith("CC0")
    assert (
        json.loads((tmp_path / "ds" / "MANIFEST.json").read_text())["pinned_sha256"]
        == PINNED_SHA256
    )


def test_confederation_map_covers_every_current_fifa_member_used_by_kalshi_pools():
    for t in (
        "Kazakhstan",
        "Slovakia",
        "United States",
        "Mexico",
        "Brazil",
        "Japan",
        "Nigeria",
        "New Zealand",
        "Curaçao",
        "Kosovo",
    ):
        assert t in TEAM_TO_CONFEDERATION, t


def test_point_in_time_elo_uses_only_earlier_days():
    rows = [
        _row("2020-01-01", "A", "B", 3, 0),
        _row("2020-01-01", "C", "D", 0, 3),
        _row("2020-01-02", "A", "C", 1, 1),
    ]
    elos = compute_point_in_time_elo(rows)
    assert elos[0] == (1500.0, 1500.0) and elos[1] == (1500.0, 1500.0)  # same day: no leakage
    a_pre, c_pre = elos[2]
    assert a_pre > 1500 > c_pre  # A won, C lost on the previous day


# ------------------------------------------------------------------ intl_hier_v1


def _world(seed=0, n_per_conf=12, years=6):
    """Two confederations with different levels; a few minnows; neutral tournament matches; friendlies."""
    rng = np.random.default_rng(seed)
    confs = {"UEFA": 0.25, "OFC": -0.35}
    teams = {}
    for c, level in confs.items():
        for i in range(n_per_conf):
            strength = level + rng.normal(0, 0.25)
            if i == 0:
                strength = level - 0.9  # a minnow
            teams[f"intl:{c.lower()}_{i}"] = (c, strength)
    names = list(teams)
    rows = []
    elo = {t: 1500.0 for t in names}
    d0 = date(2015, 1, 1)
    for k in range(years * 40):
        d = d0 + timedelta(days=int(k * 365 / 40))
        for _ in range(6):
            h, a = rng.choice(names, 2, replace=False)
            ch, sh = teams[h]
            ca, sa = teams[a]
            same = ch == ca
            neutral = bool(rng.random() < (0.5 if not same else 0.15))
            friendly = bool(rng.random() < 0.4)
            gamma = 0.0 if neutral else 0.2
            lam = (
                np.exp(0.15 + sh - (-sa) * 0.0 - sa + gamma)
                if False
                else np.exp(0.15 + (sh - sa) / 2 + gamma)
            )
            mu = np.exp(0.15 + (sa - sh) / 2)
            hg, ag = int(rng.poisson(lam)), int(rng.poisson(mu))
            rows.append(
                IntlMatchRow(d, h, a, hg, ag, neutral, not friendly, ch, ca, elo[h], elo[a])
            )
            # simple elo update (point-in-time: used for the NEXT matches)
            exp_h = 1 / (1 + 10 ** (-((elo[h] - elo[a]) + (0 if neutral else 100)) / 400))
            res = 1.0 if hg > ag else 0.5 if hg == ag else 0.0
            delta = 30 * (res - exp_h)
            elo[h] += delta
            elo[a] -= delta
    return teams, rows


def test_intl_hier_recovers_structure_and_shrinks_minnows_to_the_right_centre():
    teams, rows = _world()
    post = IntlHierFitter(IntlHierConfig(half_life_years=3.0, friendly_weight=0.6)).fit(
        rows, as_of=date(2021, 1, 1)
    )
    d = post.diagnostics
    assert (
        d["conf_attack"]["UEFA"] > d["conf_attack"]["OFC"]
    )  # level identified by cross-conf matches
    assert d["beta_attack"] > 0 and d["gamma_competitive"] > 0
    # minnow vs a mid team of the same confederation: heavy underdog, not "average national team"
    lam, mu = post.expected_goals("intl:uefa_0", "intl:uefa_5")
    p = outcome_probs(score_matrix(lam, mu, d["rho"]))
    lam_m, mu_m = post.expected_goals("intl:uefa_3", "intl:uefa_5")
    p_mid = outcome_probs(score_matrix(lam_m, mu_m, d["rho"]))
    assert p["home"] < 0.30 and p["home"] < p_mid["home"] - 0.15
    # neutral: home advantage off
    lam_n, _ = post.expected_goals("intl:uefa_3", "intl:uefa_5", neutral=True)
    lam_h, _ = post.expected_goals("intl:uefa_3", "intl:uefa_5", neutral=False)
    assert lam_h / lam_n == pytest.approx(np.exp(d["gamma_competitive"]))
    assert post.prediction_flags("intl:uefa_3", "intl:uefa_5") == []
    assert post.prediction_flags("intl:uefa_3", "intl:nobody") == ["intl:nobody:unknown_team"]


def test_intl_hier_laplace_gives_wider_uncertainty_to_sparse_teams():
    teams, rows = _world(seed=2)
    # make one team sparse: drop most of its matches
    sparse = "intl:ofc_4"
    kept = [
        r
        for r in rows
        if not ((r.home == sparse or r.away == sparse) and np.random.default_rng(1).random() < 0.0)
    ]
    kept = [
        r for i, r in enumerate(kept) if not ((r.home == sparse or r.away == sparse) and i % 5 != 0)
    ]
    post = IntlHierFitter().fit(kept, as_of=date(2021, 1, 1), laplace=True)
    sd = np.sqrt(np.diag(post.cov))
    assert sd[post.idx_alpha(sparse)] > sd[post.idx_alpha("intl:uefa_5")]
    assert post.effective_matches[sparse] < post.effective_matches["intl:uefa_5"]
    s = post.sample(50, np.random.default_rng(0))
    assert s.shape == (50, len(post.mean))


def test_intl_hier_friendly_weight_and_strict_point_in_time():
    _, rows = _world(seed=3)
    heavy = IntlHierFitter(IntlHierConfig(friendly_weight=1.0)).fit(rows, as_of=date(2020, 6, 1))
    light = IntlHierFitter(IntlHierConfig(friendly_weight=0.4)).fit(rows, as_of=date(2020, 6, 1))
    assert heavy.n_matches == light.n_matches
    assert sum(heavy.effective_matches.values()) > sum(light.effective_matches.values())
    from soccer_edge.core.temporal import FutureInformationError

    with pytest.raises(FutureInformationError):
        IntlHierFitter().fit(rows, as_of=date(2016, 1, 1), strict_point_in_time=True)
    # default mode filters to the lookback window strictly before as_of (walk-forward convenience)
    assert IntlHierFitter().fit(rows, as_of=date(2016, 6, 1)).n_matches > 0


# ------------------------------------------------------------------ ESPN neutral inference


def test_espn_neutral_inference_rules():
    assert infer_neutral_site("fifa.friendly", False, "Mexico", "United States") == (
        True,
        "venue_country_mismatch",
    )
    assert infer_neutral_site("fifa.friendly", False, "United States", "USA") == (
        False,
        "venue_country_matches_home",
    )
    assert infer_neutral_site("uefa.nations", False, "England", "United Kingdom") == (
        False,
        "venue_country_matches_home",
    )
    assert infer_neutral_site("uefa.nations", True, "England", "Germany") == (True, "espn_flag")
    assert infer_neutral_site("uefa.nations", False, "Slovakia", None) == (False, "unknown")
    assert infer_neutral_site("eng.1", False, "Arsenal", "United States") == (
        False,
        "club",
    )  # never for clubs


def test_espn_scoreboard_marks_neutral_from_venue_country():
    from soccer_edge.providers.espn import parse_scoreboard

    body = {
        "events": [
            {
                "id": "1",
                "date": "2026-10-10T18:00Z",
                "season": {"year": 2026, "slug": "2026"},
                "competitions": [
                    {
                        "competitors": [
                            {
                                "homeAway": "home",
                                "score": "1",
                                "team": {"id": "10", "displayName": "Mexico"},
                            },
                            {
                                "homeAway": "away",
                                "score": "0",
                                "team": {"id": "20", "displayName": "Colombia"},
                            },
                        ],
                        "status": {"type": {"state": "post", "name": "STATUS_FULL_TIME"}},
                        "venue": {
                            "fullName": "AT&T Stadium",
                            "address": {"city": "Arlington", "country": "United States"},
                        },
                    }
                ],
            }
        ]
    }
    (ev,) = parse_scoreboard("fifa.friendly", body)
    assert ev.neutral_site is True


# ------------------------------------------------------------------ shadow gate (audit §E6)


def test_intl_pool_records_are_gated_out_of_shadows_until_validated():
    from soccer_edge.run.pipeline import INTL_POOL_COMPETITIONS, RunConfig

    assert RunConfig(run_date=date(2026, 10, 10)).intl_shadows_enabled is False
    assert "uefa.nations_league" in INTL_POOL_COMPETITIONS
