"""SIFT-ready per-fixture payload `soccer_script_engine.v1` (published as
`event_research.extensions.soccer_script_engine` in the explorer; docs/GAME_SCRIPTS.md section 8).

Pure assembly over the model board entry (model state) and the actionable slate rows (price state). Nothing is
recomputed from a model here and no prose is generated: every sentence is a fixed template filled from published
numbers, and the structured fields it was built from are published next to it.

Information tiers (mobile first): `glance` (primary: one screen), `scripts` (secondary: the cards), then deep
evidence (`matrix`, `survivability`, `matchup`, `context`, `lineup_rescripting`, `data_gaps`, `provenance`).
"""

from __future__ import annotations

from typing import Any

from soccer_edge.gamescript.conditional import script_definitions
from soccer_edge.gamescript.expressions import EXPRESSION_VERSION, RANK_BASIS, SAME_THESIS_PHI
from soccer_edge.gamescript.survivability import RULES as SURVIVABILITY_RULES
from soccer_edge.gamescript.survivability import TITLE
from soccer_edge.gamescript.taxonomy import MATERIAL_SHARE_MIN, MATERIAL_SHARE_RULE, SCRIPT_IDS

PAYLOAD_CONTRACT = "soccer_script_engine.v1"
EXACT_FAMILIES = ("exact_score", "first_half_exact_score")
HELP_HURT_N = 3
LINEUP_EPS = 0.0005
FEE_MODEL = {
    "break_even": "ask + fee per contract",
    "fee": "ceil_to_0.000001(0.07 x fee_multiplier x P x (1 - P)) per contract (taker); "
    "kalshi_fee_schedule_2026-07_transcribed_v1",
    "note": "recompute conditional edges at a fresher ask with: edge_S = p_side(S) - break_even(ask)",
}


def _r(x: Any, d: int = 4) -> float | None:
    return None if x is None else round(float(x), d)


def _names(entry: dict[str, Any]) -> tuple[str, str]:
    parts = (entry.get("event_name") or "").split(" vs ")
    if len(parts) == 2:
        return parts[0], parts[1]
    return entry.get("home") or "Home", entry.get("away") or "Away"


# ------------------------------------------------------------------------------------------- confidence
def data_confidence(
    entry: dict[str, Any], slate_fx: dict[str, Any] | None, *, intl_pool: bool
) -> dict[str, Any]:
    """HIGH / MEDIUM / LOW from named gates (no score). LOW if any LOW gate fails; HIGH only if all pass."""
    mu = entry.get("matchup") or {}
    effs = [((mu.get(s) or {}).get("effective_matches") or 0.0) for s in ("home", "away")]
    ctx = entry.get("match_context") or {}
    ctype = ((ctx.get("competition_type") or {}).get("value")) or "UNKNOWN"
    model = (slate_fx or {}).get("model") or {}
    lineup = ((slate_fx or {}).get("lineup") or {}).get("status") or "unknown"
    gates = {
        "model_valid_and_fresh": model.get("validity") == "VALID"
        and ((model.get("freshness") or {}).get("status") in ("CURRENT", "AGING")),
        "team_sample_adequate": min(effs) >= 8.0 if effs else False,
        "team_sample_strong": min(effs) >= 20.0 if effs else False,
        "competitive_fixture": ctype not in ("INTERNATIONAL_FRIENDLY", "CLUB_FRIENDLY", "UNKNOWN"),
        "competition_pool_validated": not intl_pool,
        "lineup_confirmed": lineup == "confirmed",
    }
    reasons = []
    if not gates["model_valid_and_fresh"]:
        reasons.append("model not VALID and fresh")
    if not gates["team_sample_adequate"]:
        reasons.append(f"thin team sample (effective matches {min(effs):.1f} < 8)")
    if not gates["competitive_fixture"]:
        reasons.append(
            "friendly / unknown competition: rotation and motivation differ from the competitive matches "
            "the model is fitted on (effect not measured)"
        )
    if not gates["competition_pool_validated"]:
        reasons.append("international pool not validated (audit §E6)")
    if not gates["lineup_confirmed"]:
        reasons.append("XI not confirmed")
    low = not (
        gates["model_valid_and_fresh"]
        and gates["team_sample_adequate"]
        and gates["competitive_fixture"]
    )
    high = all(
        gates[g]
        for g in (
            "model_valid_and_fresh",
            "team_sample_strong",
            "competitive_fixture",
            "competition_pool_validated",
        )
    )
    level = "LOW" if low else ("HIGH" if high else "MEDIUM")
    return {
        "level": level,
        "gates": gates,
        "reasons": reasons,
        "rule": "LOW if model/sample/competitive gate fails; HIGH if model, strong sample, competitive and "
        "validated pool all pass; MEDIUM otherwise. Describes the inputs, not the probability of winning.",
    }


# ------------------------------------------------------------------------------------------- matrix
def market_matrix(entry: dict[str, Any]) -> dict[str, Any]:
    """script x contract (YES side; NO = 1 - p). Compact rows, ordered by family then description."""
    rows = []
    for tk, c in sorted(
        entry.get("contracts", {}).items(),
        key=lambda kv: (kv[1].get("family") or "", kv[1].get("description") or "", kv[0]),
    ):
        sc = c.get("sc")
        if not sc:
            continue
        rows.append(
            [
                tk,
                c.get("family"),
                c.get("description"),
                sc["p"],
                sc["sp"],
                sc.get("lo"),
                sc.get("hi"),
            ]
        )
    return {
        "scripts": list(SCRIPT_IDS),
        "columns": [
            "ticker",
            "family",
            "description",
            "p_yes",
            "p_yes_by_script",
            "low_by_script",
            "high_by_script",
        ],
        "rows": rows,
        "side": "YES (the NO side is 1 - p)",
        "gaps": (entry.get("scripts") or {}).get("contract_gaps") or {},
    }


def helped_hurt(entry: dict[str, Any]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Per script: the YES contracts whose probability rises / falls most in that script (lift = P(M|S) - P(M)).
    Exact-score markets are left out (they are listed in the matrix)."""
    out: dict[str, dict[str, list[dict[str, Any]]]] = {}
    items = [
        (tk, c)
        for tk, c in entry.get("contracts", {}).items()
        if c.get("sc") and c.get("family") not in EXACT_FAMILIES
    ]
    for s, sid in enumerate(SCRIPT_IDS):
        lifts = []
        for tk, c in items:
            ps = c["sc"]["sp"][s]
            if ps is None:
                continue
            lifts.append((ps - c["sc"]["p"], tk, c, ps))
        lifts.sort(key=lambda x: (x[0], x[1]))
        mk = lambda x: {
            "ticker": x[1],
            "description": x[2].get("description"),
            "p": _r(x[2]["sc"]["p"]),
            "p_given_script": _r(x[3]),
            "lift": _r(x[0]),
        }
        out[sid] = {
            "helped": [mk(x) for x in reversed(lifts[-HELP_HURT_N:]) if x[0] > 0],
            "hurt": [mk(x) for x in lifts[:HELP_HURT_N] if x[0] < 0],
        }
    return out


# ------------------------------------------------------------------------------------------- survivability
def survivability_rows(
    slate_contracts: list[dict[str, Any]], entry: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = []
    for c in slate_contracts:
        sr = c.get("script_robustness")
        if not sr or sr.get("label") == "NO_EDGE":
            continue
        rows.append(
            {
                "key": f"{c['ticker']}|{c['side']}",
                "ticker": c["ticker"],
                "side": c["side"],
                "family": c.get("market_family"),
                "description": c.get("market_description"),
                "price": c.get("kalshi_price"),
                "break_even": c.get("breakeven_price"),
                "fair_probability": c.get("model_probability"),
                "fee_adjusted_ev": c.get("fee_adjusted_ev"),
                "worst_case_edge": c.get("worst_case_edge"),
                "action": c.get("action"),
                "authority": c.get("authority"),
                **{
                    k: sr.get(k)
                    for k in (
                        "label",
                        "category",
                        "overall_edge",
                        "p_script",
                        "decomposition_residual",
                        "stance",
                        "conditional_edges",
                        "material_scripts",
                        "supporting_scripts",
                        "opposing_scripts",
                        "weighted_support_share",
                        "worst_material_script",
                        "edge_concentration",
                        "edge_ex_top_script",
                        "strongest_support",
                        "counter_case",
                        "thesis_group",
                        "robust_rank",
                    )
                },
            }
        )
    rows.sort(key=lambda r: (r.get("robust_rank") or 10_000, r["key"]))
    return rows


# ------------------------------------------------------------------------------------------- lineups
def lineup_rescripting(entry: dict[str, Any], slate_fx: dict[str, Any] | None) -> dict[str, Any]:
    hist = entry.get("lineup_history") or []
    model = (slate_fx or {}).get("model") or {}
    lineup = (slate_fx or {}).get("lineup") or {}
    cur_sc = entry.get("scripts") or {}
    cur = {
        "model_generated_at": entry.get("model_generated_at"),
        "lineup_key": (entry.get("inputs") or {}).get("lineup_key"),
        "summary": entry.get("summary"),
        "scripts": {"shares": cur_sc.get("shares"), "primary": cur_sc.get("primary")}
        if cur_sc.get("status") == "OK"
        else None,
    }
    out: dict[str, Any] = {
        "lineup_status": lineup.get("status")
        or (entry.get("lineup") or {}).get("state")
        or "unknown",
        "lineup_last_change_at": lineup.get("last_change_at")
        or (entry.get("lineup") or {}).get("last_change_at"),
        "model_invalidated": model.get("validity") == "INVALIDATED",
        "invalidation_reasons": model.get("invalidation_reasons") or [],
        "model_uses_lineups": False,
        "model_uses_lineups_reason": (
            "the production model has no validated player-strength adjustment: a published XI changes the "
            "lineup status, the simulation key and freshness, not the team rates"
        ),
        "current": cur,
        "pre_lineup": hist[0] if hist else None,
        "history": hist,
    }
    pre = hist[0] if hist else None
    if pre is None:
        out["refreshed_after_lineup"] = False
        out["statement"] = "No lineup-driven model state change recorded for this fixture."
        return out
    out["refreshed_after_lineup"] = True
    ds = None
    if (pre.get("scripts") or {}).get("shares") and (cur.get("scripts") or {}).get("shares"):
        ds = {
            sid: _r(b - a, 5)
            for sid, a, b in zip(SCRIPT_IDS, pre["scripts"]["shares"], cur["scripts"]["shares"])
            if a is not None and b is not None
        }
    keys = ("p_home", "p_draw", "p_away", "p_over_2_5", "p_btts")
    dp = {
        k: _r((cur.get("summary") or {}).get(k, 0) - (pre.get("summary") or {}).get(k, 0), 5)
        for k in keys
        if k in (cur.get("summary") or {}) and k in (pre.get("summary") or {})
    }
    out["script_share_changes"] = ds
    out["key_probability_changes"] = dp
    out["primary_script_changed"] = (pre.get("scripts") or {}).get("primary") != (
        cur.get("scripts") or {}
    ).get("primary")
    out["survivability_change"] = None
    out["survivability_change_reason"] = (
        "per-contract conditionals of the pre-lineup state are not stored; survivability is recomputed at the "
        "current price from the current model state"
    )
    moved = max([abs(v) for v in (ds or {}).values()] + [abs(v) for v in dp.values()] + [0.0])
    out["statement"] = (
        "Model refreshed after the lineup changed; script shares and key probabilities are unchanged because "
        "the model does not adjust team rates for the XI."
        if moved < LINEUP_EPS
        else "Model refreshed after the lineup changed; the changes above are the full model difference between "
        "the two states (the model does not attribute them to individual players)."
    )
    return out


# ------------------------------------------------------------------------------------------- gaps
def data_gaps(
    entry: dict[str, Any], slate_fx: dict[str, Any] | None, *, intl_pool: bool
) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    add = lambda code, detail: gaps.append({"code": code, "detail": detail})
    lineup = (((slate_fx or {}).get("lineup") or {}).get("status")) or (
        entry.get("lineup") or {}
    ).get("state")
    if lineup != "confirmed":
        add("LINEUP_UNCONFIRMED", f"lineup status {lineup or 'unknown'}")
    add(
        "LINEUP_NOT_MODELLED",
        "a confirmed XI does not change team rates (no validated player-strength layer)",
    )
    add(
        "XG_UNAVAILABLE",
        "no verified xG input in production; matchup metrics are Dixon-Coles goal-rate parameters",
    )
    add(
        "PLAYER_LAYER_UNSUPPORTED",
        "player markets are not priced in production (no lineup/player provider)",
    )
    add("RED_CARDS_NOT_MODELLED", "world_sim_v2 drops red-card dynamics")
    add(
        "GAME_STATE_DYNAMICS_NOT_MODELLED",
        "goal timing is i.i.d. given the score; chase scripts reflect goal order only",
    )
    add(
        "SCRIPT_SHARES_NOT_CALIBRATED",
        "script shares are simulation shares; no empirical calibration of script frequencies yet",
    )
    ctx = entry.get("match_context") or {}
    for k in ("standings_implications", "must_win", "draw_utility"):
        if (ctx.get(k) or {}).get("status") == "UNAVAILABLE":
            add(
                "STANDINGS_SIGNIFICANCE_UNKNOWN"
                if k == "standings_implications"
                else f"{k.upper()}_UNKNOWN",
                ctx[k]["source"],
            )
    for k in ("stage", "leg_number", "aggregate"):
        if (ctx.get(k) or {}).get("status") == "UNAVAILABLE":
            add("CONTEXT_PARTIAL", f"{k}: {ctx[k]['source']}")
    if (ctx.get("rotation_uncertainty") or {}).get("value") == "ELEVATED_UNQUANTIFIED":
        add("ROTATION_UNKNOWN", "friendly: rotation uncertainty elevated and not quantified")
    elif (ctx.get("rotation_uncertainty") or {}).get("status") == "UNAVAILABLE":
        add("ROTATION_UNKNOWN", ctx["rotation_uncertainty"]["source"])
    if intl_pool:
        add(
            "INTL_POOL_NOT_VALIDATED",
            "international pool model has not passed its frozen holdout (audit §E6)",
        )
    mu = entry.get("matchup") or {}
    for side in ("home", "away"):
        t = mu.get(side) or {}
        if t and t.get("sample_quality") == "LOW":
            add("LOW_HISTORICAL_SAMPLE", f"{side}: {t.get('effective_matches')} effective matches")
        if t and not t.get("schedule_strength"):
            add(
                "SCHEDULE_STRENGTH_UNAVAILABLE",
                f"{side}: fit window rows not available to this run",
            )
    ref = (((slate_fx or {}).get("reference") or {}).get("freshness") or {}).get("status")
    if ref in ("STALE", "UNAVAILABLE"):
        add(
            "STALE_REFERENCE" if ref == "STALE" else "REFERENCE_UNAVAILABLE",
            f"Pinnacle reference {ref}",
        )
    sg = (entry.get("scripts") or {}).get("contract_gaps") or {}
    if sg:
        add("CONTRACTS_WITHOUT_SCRIPT_CONDITIONALS", f"{len(sg)} contracts (see matrix.gaps)")
    if (ctx.get("competition_type") or {}).get("value") == "UNKNOWN":
        add("UNSUPPORTED_COMPETITION", "competition not in the registry")
    return gaps


# ------------------------------------------------------------------------------------------- story
def story(entry: dict[str, Any], surv: dict[str, Any] | None) -> dict[str, Any]:
    sc = entry["scripts"]
    prof = sc["overall_profile"]
    home, away = _names(entry)
    ph, pd, pa = prof["p_home_win"], prof["p_draw"], prof["p_away_win"]
    sh = dict(zip(sc["scripts"], sc["shares"]))
    prim, sec = sc["primary"], sc["secondary"]
    if abs(ph - pa) < 0.05:
        lead = f"{home} and {away} are close to even ({ph:.0%} / {pa:.0%}, draw {pd:.0%})"
        favourite = None
    elif ph > pa:
        lead = f"{home} win more of the modelled matches than {away} ({ph:.0%} vs {pa:.0%}, draw {pd:.0%})"
        favourite = "HOME"
    else:
        lead = f"{away} win more of the modelled matches than {home} ({pa:.0%} vs {ph:.0%}, draw {pd:.0%})"
        favourite = "AWAY"
    shape = f"the most common shape is {TITLE[prim].lower()} ({sh[prim]:.0%}), then {TITLE[sec].lower()} ({sh[sec]:.0%})"
    edge_clause, edge_kind = "no compelling edge at the current price", "NONE"
    if surv:
        best = surv.get("best_robust")
        spec = surv.get("best_script_specific")
        if surv.get("price_status") != "CURRENT":
            edge_clause, edge_kind = (
                "prices are not current, so no edge is stated",
                "PRICE_NOT_CURRENT",
            )
        elif best:
            edge_clause = (
                f"the strongest research expression at the current price is {best['description']} "
                f"({best['side'].upper()}), supported in {best['supporting_scripts']} of {best['material_scripts']} "
                "material scripts"
            )
            edge_kind = "ROBUST"
        elif spec:
            anchor = (spec.get("strongest_support") or {}).get("script")
            edge_clause = (
                f"apparent value at the current price is script-specific: {spec['description']} "
                f"({spec['side'].upper()}) needs {TITLE.get(anchor, 'one script').lower()}"
            )
            edge_kind = "SCRIPT_SPECIFIC"
    sentence = f"{lead}; {shape}; {edge_clause}."
    sentence = sentence[0].upper() + sentence[1:]
    return {
        "sentence": sentence,
        "parts": {
            "favourite": favourite,
            "p_home": ph,
            "p_draw": pd,
            "p_away": pa,
            "primary_script": prim,
            "secondary_script": sec,
            "edge_kind": edge_kind,
        },
        "method": "fixed template over published fields (no language model)",
    }


# ------------------------------------------------------------------------------------------- payload
def script_engine_payload(
    entry: dict[str, Any] | None,
    slate_fx: dict[str, Any] | None,
    slate_contracts: list[dict[str, Any]],
    *,
    intl_pool: bool,
    slate_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not entry:
        return {
            "contract": PAYLOAD_CONTRACT,
            "status": "UNAVAILABLE",
            "reason": "fixture not on the model board",
        }
    sc = entry.get("scripts") or {}
    if sc.get("status") != "OK":
        return {
            "contract": PAYLOAD_CONTRACT,
            "status": "UNAVAILABLE",
            "reason": sc.get("reason") or "board entry predates the script layer",
            "matchup": entry.get("matchup"),
            "context": entry.get("match_context"),
        }
    slate_meta = slate_meta or {}
    fx_sc = (slate_fx or {}).get("scripts") or {}
    rows = survivability_rows(slate_contracts, entry)
    by_key = {r["key"]: r for r in rows}
    kal = slate_meta.get("kalshi") or {}
    price_status = kal.get("status") or "UNAVAILABLE"
    if ((slate_fx or {}).get("model") or {}).get("validity") != "VALID":
        price_status = "MODEL_NOT_VALID"
    best_robust = by_key.get(fx_sc.get("best_robust_expression") or "")
    best_spec = by_key.get(fx_sc.get("best_script_specific_expression") or "")
    surv = {
        "price_status": price_status,
        "best_robust": best_robust,
        "best_script_specific": best_spec,
    }
    shares = sc["shares"]
    cards = []
    hh = helped_hurt(entry)
    defs = {d["script_id"]: d for d in script_definitions()}
    order = sorted(range(len(SCRIPT_IDS)), key=lambda i: -shares[i])
    for rank, i in enumerate(order, start=1):
        sid = SCRIPT_IDS[i]
        p = sc["profiles"][sid]
        cards.append(
            {
                "script_id": sid,
                "title": defs[sid]["title"],
                "definition": defs[sid]["definition"],
                "rank": rank,
                "simulation_share": shares[i],
                "share_low": sc["share_low"][i],
                "share_high": sc["share_high"][i],
                "material": shares[i] >= MATERIAL_SHARE_MIN - 1e-12,
                "primary": {
                    "home_win": p["p_home_win"],
                    "draw": p["p_draw"],
                    "away_win": p["p_away_win"],
                    "exp_home_goals": p["exp_home_goals"],
                    "exp_away_goals": p["exp_away_goals"],
                    "typical_scores": p["typical_scores"],
                },
                "profile": p,
                "temporal": sc["temporal"][sid],
                "markets_helped": hh[sid]["helped"],
                "markets_hurt": hh[sid]["hurt"],
                "evidence": "SIMULATION_DERIVED share; MODEL_DERIVED profile; temporal profile assumes i.i.d. goal timing",
            }
        )
    ov = sc["overall_profile"]
    mu = entry.get("matchup") or {}
    ctx = entry.get("match_context") or {}
    lineup = (slate_fx or {}).get("lineup") or {}
    model = (slate_fx or {}).get("model") or {}
    conf = data_confidence(entry, slate_fx, intl_pool=intl_pool)

    def brief(r: dict[str, Any] | None) -> dict[str, Any] | None:
        if not r:
            return None
        return {
            k: r.get(k)
            for k in (
                "key",
                "ticker",
                "side",
                "description",
                "price",
                "label",
                "category",
                "overall_edge",
                "weighted_support_share",
                "supporting_scripts",
                "material_scripts",
                "counter_case",
            )
        }

    glance = {
        "h_d_a": {"home": ov["p_home_win"], "draw": ov["p_draw"], "away": ov["p_away_win"]},
        "expected_goals": {
            "home": ov["exp_home_goals"],
            "away": ov["exp_away_goals"],
            "basis": "Dixon-Coles model goal rates (mean over worlds); not xG",
        },
        "primary_script": {
            "script": sc["primary"],
            "title": TITLE[sc["primary"]],
            "share": shares[SCRIPT_IDS.index(sc["primary"])],
        },
        "secondary_script": {
            "script": sc["secondary"],
            "title": TITLE[sc["secondary"]],
            "share": shares[SCRIPT_IDS.index(sc["secondary"])],
        },
        "primary_mismatch": None
        if not mu.get("matchups")
        else {
            "matchup": mu["primary_mismatch"],
            **{
                k: mu["matchups"][mu["primary_mismatch"]].get(k)
                for k in ("label", "z_gap", "advantage_side", "evidence_quality")
            },
        },
        "data_confidence": conf["level"],
        "lineup": {
            "status": lineup.get("status") or "unknown",
            "last_change_at": lineup.get("last_change_at"),
        },
        "competition": {
            "name": (ctx.get("competition_name") or {}).get("value"),
            "type": (ctx.get("competition_type") or {}).get("value"),
            "stage": (ctx.get("stage") or {}).get("value"),
            "flags": ctx.get("flags") or [],
        },
        "best_robust_expression": brief(best_robust),
        "best_script_specific_expression": brief(best_spec),
        "no_compelling_edge": bool(fx_sc.get("no_compelling_edge", True)),
        "no_compelling_edge_reason": fx_sc.get("no_compelling_edge_reason"),
        "story": story(entry, surv),
    }
    return {
        "contract": PAYLOAD_CONTRACT,
        "status": "OK",
        "research_only": True,
        "methodology": {
            "taxonomy_version": sc["taxonomy_version"],
            "layer_version": sc.get("layer_version"),
            "survivability": SURVIVABILITY_RULES,
            "expressions": {
                "version": EXPRESSION_VERSION,
                "rank_basis": RANK_BASIS,
                "same_thesis_phi": SAME_THESIS_PHI,
            },
            "material_rule": MATERIAL_SHARE_RULE,
            "scripts": script_definitions(),
            "method": sc.get("method"),
            "evidence": sc.get("evidence"),
            "not_modelled": sc.get("not_modelled"),
            "fee_model": FEE_MODEL,
            "doc": "docs/GAME_SCRIPTS.md",
        },
        "freshness": {
            "model": {
                "generated_at": entry.get("model_generated_at"),
                "validity": model.get("validity"),
                "status": (model.get("freshness") or {}).get("status"),
                "invalidation_reasons": model.get("invalidation_reasons") or [],
            },
            "scripts": {
                "computed_at": entry.get("model_generated_at"),
                "basis": "model state (market-blind)",
            },
            "market": {
                "observed_at": kal.get("observed_at"),
                "status": kal.get("status"),
                "current_until": kal.get("current_until"),
                "stale_after": kal.get("stale_after"),
                "slate_id": slate_meta.get("slate_id"),
            },
            "lineup": lineup.get("freshness"),
            "context": (slate_fx or {}).get("context"),
            "reference": ((slate_fx or {}).get("reference") or {}).get("freshness"),
            "rule": "survivability is valid only while the market is CURRENT and the model VALID; after "
            "market.current_until treat every edge as stale",
        },
        "glance": glance,
        "scripts": {
            "order": [c["script_id"] for c in cards],
            "canonical_order": list(SCRIPT_IDS),
            "cards": cards,
            "overall_profile": ov,
            "material_min_share": round(MATERIAL_SHARE_MIN, 6),
        },
        "survivability": {
            "priced_at": fx_sc.get("priced_at") or kal.get("observed_at"),
            "price_status": price_status,
            "research_edge_min": fx_sc.get("research_edge_min"),
            "robust_edges": fx_sc.get("robust_edges") or [],
            "mixed_edges": fx_sc.get("mixed_edges") or [],
            "script_specific_edges": fx_sc.get("script_specific_edges") or [],
            "thesis_groups": fx_sc.get("thesis_groups") or [],
            "rows": rows,
            "note": "research presentation; never changes action, authority or selection",
        },
        "matrix": market_matrix(entry),
        "matchup": mu or None,
        "context": ctx or None,
        "lineup_rescripting": lineup_rescripting(entry, slate_fx),
        "data_confidence": conf,
        "data_gaps": data_gaps(entry, slate_fx, intl_pool=intl_pool),
        "authority": {
            "status": "RESEARCH_ONLY",
            "note": "every soccer model family is RESEARCH_ONLY; nothing in this payload permits a bet",
            "per_row": "rows carry the slate's authority and action",
        },
        "provenance": {
            "model_board": "runs/latest.model_board.v1.json",
            "source_run_id": entry.get("source_run_id"),
            "sim_key": entry.get("sim_key"),
            "model_family": (entry.get("inputs") or {}).get("model_family"),
            "engine_version": (entry.get("inputs") or {}).get("engine_version"),
            "actionable_slate": "runs/latest.actionable_slate.v1.json",
            "slate_id": slate_meta.get("slate_id"),
        },
    }
