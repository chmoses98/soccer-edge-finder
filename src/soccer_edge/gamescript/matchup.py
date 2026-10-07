"""Opponent-adjusted matchup intelligence from the PRODUCTION posterior that priced the fixture.

What the numbers are (and are not): Dixon-Coles latent log-rate parameters of `dc_laplace_v1`
(lambda_home = exp(attack_h - defence_a + home_adv), mu_away = exp(attack_a - defence_h)). They are fitted jointly
over every match in the competition pool with time decay, so a goal scored against a strong defence moves attack
more than one against a weak defence: they are opponent- and schedule-adjusted by construction. They are NOT xG
and are never labelled xG. Recent raw form is published separately as context (`raw_form`), never as quality.

Per team: attack / defence posterior mean and sd (log rate), z-score and percentile within the pool's reference
teams (effective weighted matches >= REFERENCE_MIN_MATCHES), net rating (attack + defence), expected goals scored /
conceded against an average pool opponent at a neutral venue, at home and away, and schedule strength (decay-weighted
mean net rating of the opponents faced in the fit window, when the fit supplied it).

Per matchup (HOME_ATTACK_vs_AWAY_DEFENSE, AWAY_ATTACK_vs_HOME_DEFENSE): both z-scores and percentiles, the
log-rate advantage relative to an average pairing with its sd, P(advantage > 0) under the Laplace posterior,
the model's expected goals for that side in this fixture, and a deterministic label from the z gap.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

MATCHUP_VERSION = "dc_matchup_v1"
REFERENCE_MIN_MATCHES = 3.0
SAMPLE_HIGH, SAMPLE_MEDIUM = 20.0, 8.0


def _r(x: Any, d: int = 4) -> float | None:
    if x is None:
        return None
    x = float(x)
    return round(x, d) if math.isfinite(x) else None


def _pct(values: np.ndarray, v: float) -> float:
    return float((values < v).mean() + 0.5 * (values == v).mean())


def _sample_quality(eff: float) -> str:
    return "HIGH" if eff >= SAMPLE_HIGH else ("MEDIUM" if eff >= SAMPLE_MEDIUM else "LOW")


def _label(side: str, opp: str, z_att: float, z_def: float) -> str:
    gap = z_att - z_def
    if z_att >= 1.0 and z_def >= 1.0:
        return "ELITE_VS_ELITE"
    if z_att <= -1.0 and z_def <= -1.0:
        return "WEAK_VS_WEAK"
    if gap >= 1.5:
        return f"MAJOR_{side}_ATTACK_EDGE"
    if gap >= 0.75:
        return f"{side}_ATTACK_EDGE"
    if gap <= -1.5:
        return f"MAJOR_{opp}_DEFENSIVE_EDGE"
    if gap <= -0.75:
        return f"{opp}_DEFENSIVE_EDGE"
    return "BALANCED"


def matchup_block(
    posterior: Any,
    home: str,
    away: str,
    *,
    neutral: bool,
    team_context: dict[str, dict[str, Any]] | None = None,
    pool_label: str = "",
) -> dict[str, Any]:
    teams = list(posterior.teams)
    n = len(teams)
    mean = np.asarray(posterior.mean)
    att = mean[:n]
    dfn = mean[n : 2 * n]
    gamma = float(mean[posterior.idx_home])
    eff = np.array([float(posterior.effective_matches.get(t, 0.0)) for t in teams])
    ref = eff >= REFERENCE_MIN_MATCHES
    if ref.sum() < 4:
        ref = np.ones(n, dtype=bool)
    ra, rd = att[ref], dfn[ref]
    ma, sa = float(ra.mean()), float(ra.std() or 1.0)
    md, sd_ = float(rd.mean()), float(rd.std() or 1.0)
    net = ra + rd
    mn, sn = float(net.mean()), float(net.std() or 1.0)
    team_context = team_context or {}

    def team(t: str) -> dict[str, Any]:
        i = teams.index(t)
        a, d = float(att[i]), float(dfn[i])
        a_sd = float(np.sqrt(posterior.cov[i, i]))
        d_sd = float(np.sqrt(posterior.cov[n + i, n + i]))
        ctx = team_context.get(t, {})
        return {
            "team_id": t,
            "attack": {
                "log_rate": _r(a),
                "sd": _r(a_sd),
                "z": _r((a - ma) / sa, 3),
                "percentile": _r(_pct(ra, a), 3),
            },
            "defence": {
                "log_rate": _r(d),
                "sd": _r(d_sd),
                "z": _r((d - md) / sd_, 3),
                "percentile": _r(_pct(rd, d), 3),
            },
            "net_rating": {
                "value": _r(a + d),
                "z": _r((a + d - mn) / sn, 3),
                "percentile": _r(_pct(net, a + d), 3),
            },
            "expected_vs_average_opponent": {
                "neutral": {"scored": _r(math.exp(a - md), 3), "conceded": _r(math.exp(ma - d), 3)},
                "home": {
                    "scored": _r(math.exp(a - md + gamma), 3),
                    "conceded": _r(math.exp(ma - d), 3),
                },
                "away": {
                    "scored": _r(math.exp(a - md), 3),
                    "conceded": _r(math.exp(ma - d + gamma), 3),
                },
            },
            "effective_matches": _r(eff[i], 1),
            "sample_quality": _sample_quality(float(eff[i])),
            "schedule_strength": ctx.get("schedule_strength"),
            "raw_form": ctx.get("raw_form"),
        }

    th, ta = team(home), team(away)
    ih, ia = teams.index(home), teams.index(away)
    g = 0.0 if neutral else gamma

    def pairing(side: str, opp: str, i_att: int, i_def: int, home_adv: float) -> dict[str, Any]:
        adv = (att[i_att] - ma) - (dfn[i_def] - md)
        var = (
            posterior.cov[i_att, i_att]
            + posterior.cov[n + i_def, n + i_def]
            - 2 * posterior.cov[i_att, n + i_def]
        )
        sd = float(np.sqrt(max(var, 1e-12)))
        z_att = (att[i_att] - ma) / sa
        z_def = (dfn[i_def] - md) / sd_
        eff_min = float(min(eff[i_att], eff[i_def]))
        return {
            "attack_z": _r(z_att, 3),
            "defence_z": _r(z_def, 3),
            "attack_percentile": _r(_pct(ra, att[i_att]), 3),
            "defence_percentile": _r(_pct(rd, dfn[i_def]), 3),
            "advantage_side": side if adv > 0 else opp,
            "advantage_log_rate": _r(adv),
            "advantage_sd": _r(sd),
            "p_attack_advantage": _r(0.5 * (1 + math.erf(adv / (sd * math.sqrt(2)))), 3),
            "z_gap": _r(z_att - z_def, 3),
            "expected_goals_model": _r(math.exp(att[i_att] - dfn[i_def] + home_adv), 3),
            "expected_goals_average_pairing": _r(math.exp(ma - md + home_adv), 3),
            "label": _label(side, opp, z_att, z_def),
            "evidence_quality": _sample_quality(eff_min),
        }

    pairs = {
        "HOME_ATTACK_vs_AWAY_DEFENSE": pairing("HOME", "AWAY", ih, ia, g),
        "AWAY_ATTACK_vs_HOME_DEFENSE": pairing("AWAY", "HOME", ia, ih, 0.0),
    }
    primary = max(pairs, key=lambda k: abs(pairs[k]["z_gap"] or 0.0))
    return {
        "version": MATCHUP_VERSION,
        "source": "production posterior (dc_laplace_v1) that priced this fixture",
        "metric_kind": "DIXON_COLES_LATENT_LOG_RATE (opponent- and schedule-adjusted; not xG)",
        "pool": pool_label,
        "pool_reference_teams": int(ref.sum()),
        "home_advantage_log_rate": _r(gamma),
        "neutral_site": neutral,
        "home": th,
        "away": ta,
        "matchups": pairs,
        "primary_mismatch": primary,
        "evidence_status": "MODEL_DERIVED",
    }


def team_context_from_rows(
    rows: list[Any], posterior: Any, *, as_of: Any, decay_per_day: float
) -> dict[str, Any]:
    """Schedule strength and raw form per team from the fit window (decay-weighted like the fit)."""
    teams = list(posterior.teams)
    n = len(teams)
    mean = np.asarray(posterior.mean)
    idx = {t: i for i, t in enumerate(teams)}
    acc: dict[str, dict[str, float]] = {}
    for r in rows:
        w = math.exp(-decay_per_day * max((as_of - r.date).days, 0)) * float(
            getattr(r, "weight", 1.0)
        )
        for t, o, gf, ga in (
            (r.home, r.away, r.home_goals, r.away_goals),
            (r.away, r.home, r.away_goals, r.home_goals),
        ):
            if t not in idx or o not in idx:
                continue
            a = acc.setdefault(t, {"w": 0.0, "opp": 0.0, "n": 0, "gf": 0.0, "ga": 0.0, "n365": 0})
            j = idx[o]
            a["w"] += w
            a["opp"] += w * float(mean[j] + mean[n + j])
            a["n"] += 1
            if (as_of - r.date).days <= 365:
                a["gf"] += gf
                a["ga"] += ga
                a["n365"] += 1
    out: dict[str, Any] = {}
    nets = np.array([mean[i] + mean[n + i] for i in range(n)])
    for t, a in acc.items():
        opp = a["opp"] / a["w"] if a["w"] > 0 else None
        out[t] = {
            "schedule_strength": None
            if opp is None
            else {
                "mean_opponent_net_rating": _r(opp),
                "percentile_vs_pool": _r(_pct(nets, opp), 3),
                "matches_in_window": a["n"],
                "basis": "decay-weighted mean (attack + defence) of opponents faced in the 730-day fit window",
            },
            "raw_form": {
                "matches_365d": a["n365"],
                "goals_for_per_match": _r(a["gf"] / a["n365"], 3) if a["n365"] else None,
                "goals_against_per_match": _r(a["ga"] / a["n365"], 3) if a["n365"] else None,
                "basis": "unadjusted context (not opponent-adjusted; not a strength estimate)",
            },
        }
    return out
