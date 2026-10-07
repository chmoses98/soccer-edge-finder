"""Reprice-time game-script fields (docs/GAME_SCRIPTS.md section 6): survivability per contract side, fixture
script summary, robust / script-specific research edges and same-thesis groups.

Reads only the model board entry and the side's break-even from the reprice. Zero simulations: a Kalshi price
move changes the conditional edges, stances, labels, ranking and groups; it never changes a share or a
conditional probability (those are model state).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from soccer_edge.contracts.slate_v1 import (
    ScriptCounterCaseV1,
    ScriptRobustnessV1,
    SlateContractV1,
    SlateFixtureScriptsV1,
)
from soccer_edge.gamescript.cells import CellSpec
from soccer_edge.gamescript.expressions import JointSpace, rank_key, thesis_groups
from soccer_edge.gamescript.survivability import (
    SURVIVABILITY_VERSION,
    side_conditionals,
    survivability,
)
from soccer_edge.gamescript.taxonomy import TAXONOMY_VERSION

# a side enters the research-edge lists when its script-basis fee-adjusted edge reaches the production
# selection's minimum edge (EdgeConfig.min_fee_adjusted_edge); the lists never feed the selection itself
RESEARCH_EDGE_MIN = 0.02
PRICE_OK_ACTIONS = ("ACTIONABLE", "RESEARCH_CANDIDATE", "NO_EDGE", "EXCLUDED_BY_GATE")
STANCE_CHAR = {"SUPPORTS": "S", "OPPOSES": "O", "NEUTRAL": "N", "IMMATERIAL": "-"}


def scripts_ok(entry: dict[str, Any]) -> bool:
    sc = entry.get("scripts") or {}
    return sc.get("status") == "OK" and sc.get("taxonomy_version") == TAXONOMY_VERSION


def side_description(c: dict[str, Any], side: str) -> str:
    d = c.get("description") or "this contract"
    return d if side == "yes" else f"NO on '{d}'"


def contract_robustness(
    entry: dict[str, Any], c: dict[str, Any], side: str, breakeven: float, p_model_side: float
) -> ScriptRobustnessV1 | None:
    if not scripts_ok(entry) or not c.get("sc"):
        return None
    sc = c["sc"]
    shares = entry["scripts"]["shares"]
    p_side = side_conditionals(sc["sp"], side)
    sv = survivability(shares, p_side, breakeven, description=side_description(c, side))
    p_script = sc["p"] if side == "yes" else 1.0 - sc["p"]
    cc = sv["counter_case"]
    if sv["label"] == "NO_EDGE":
        # no edge at this price: the per-script edges and stances are enough (and keep the slate small)
        return ScriptRobustnessV1(
            label="NO_EDGE",
            category="NO_EDGE",
            overall_edge=sv["overall_edge"],
            p_script=round(p_script, 6),
            decomposition_residual=round(p_script - p_model_side, 6),
            conditional_edges=sv["conditional_edges"],
            stance="".join(STANCE_CHAR[s] for s in sv["stance"]),
            material_scripts=sv["material_scripts"],
            supporting_scripts=sv["supporting_scripts"],
        )
    return ScriptRobustnessV1(
        label=sv["label"],
        category=sv["category"],
        overall_edge=sv["overall_edge"],
        p_script=round(p_script, 6),
        decomposition_residual=round(p_script - p_model_side, 6),
        conditional_edges=sv["conditional_edges"],
        stance="".join(STANCE_CHAR[s] for s in sv["stance"]),
        material_scripts=sv["material_scripts"],
        supporting_scripts=sv["supporting_scripts"],
        opposing_scripts=sv["opposing_scripts"],
        neutral_scripts=sv["neutral_scripts"],
        weighted_support_share=sv["weighted_support_share"],
        weighted_oppose_share=sv["weighted_oppose_share"],
        worst_material_script=sv["worst_material_script"],
        edge_concentration=sv["edge_concentration"],
        edge_ex_top_script=sv["edge_ex_top_script"],
        strongest_support=sv["strongest_support"],
        counter_case=None if cc is None else ScriptCounterCaseV1(**cc),
    )


def fixture_scripts(
    entry: dict[str, Any],
    contracts: list[SlateContractV1],
    *,
    kalshi_status: str,
    priced_at: datetime | None,
) -> tuple[SlateFixtureScriptsV1, list[SlateContractV1]]:
    if not scripts_ok(entry):
        sc = entry.get("scripts") or {}
        reason = sc.get("reason") or (
            "board entry predates the script layer"
            if not sc
            else f"taxonomy {sc.get('taxonomy_version')} is not {TAXONOMY_VERSION}"
        )
        return SlateFixtureScriptsV1(status="UNAVAILABLE", reason=reason), contracts
    sc = entry["scripts"]
    base = {
        "status": "OK",
        "taxonomy_version": sc["taxonomy_version"],
        "survivability_version": SURVIVABILITY_VERSION,
        "scripts": sc["scripts"],
        "shares": sc["shares"],
        "primary": sc.get("primary"),
        "secondary": sc.get("secondary"),
        "material": sc.get("material") or [],
        "research_edge_min": RESEARCH_EDGE_MIN,
        "priced_at": priced_at,
    }
    eligible = [
        c
        for c in contracts
        if c.script_robustness is not None
        and c.action in PRICE_OK_ACTIONS
        and (c.script_robustness.overall_edge or 0.0) >= RESEARCH_EDGE_MIN
    ]
    if kalshi_status != "CURRENT" or not eligible:
        reason = (
            f"Kalshi price {kalshi_status}: survivability at an old price is not a current research edge"
            if kalshi_status != "CURRENT"
            else f"no contract side has a fee-adjusted edge >= {RESEARCH_EDGE_MIN} at the current price "
            "with a valid, fresh model"
        )
        return SlateFixtureScriptsV1(
            **base, no_compelling_edge=True, no_compelling_edge_reason=reason
        ), contracts
    rows = []
    for c in eligible:
        bc = entry["contracts"].get(c.ticker) or {}
        sr = c.script_robustness
        assert sr is not None
        rows.append(
            {
                "key": f"{c.ticker}|{c.side}",
                "spec": CellSpec.from_board(bc) if bc else None,
                "side": c.side,
                "shares": sc["shares"],
                "worst_case_edge": c.worst_case_edge,
                "script_robustness": sr.model_dump(),
            }
        )
    rows.sort(key=rank_key)
    space = None
    try:
        space = JointSpace(
            sc["score_grid"],
            sc["first_half_share"],
            requires_winner=bool((entry.get("inputs") or {}).get("requires_winner")),
            advance_table=sc.get("advance_home_given_score"),
        )
    except Exception:  # no joint -> every side is its own group (reported, never guessed)
        space = None
    rows_ok = [r for r in rows if r["spec"] is not None]
    groups, _corr = thesis_groups(rows_ok, space, fixture_id=entry["fixture_id"])
    rank = {r["key"]: i + 1 for i, r in enumerate(rows)}
    group_of = {r["key"]: r.get("thesis_group") for r in rows_ok}
    out = []
    for c in contracts:
        k = f"{c.ticker}|{c.side}"
        if k in rank and c.script_robustness is not None:
            c = c.model_copy(
                update={
                    "script_robustness": c.script_robustness.model_copy(
                        update={"robust_rank": rank[k], "thesis_group": group_of.get(k)}
                    )
                }
            )
        out.append(c)
    cat = {r["key"]: r["script_robustness"]["category"] for r in rows}
    robust = [k for k in cat if cat[k] == "ROBUST_ACROSS_SCRIPTS"]
    mixed = [k for k in cat if cat[k] == "MIXED"]
    specific = [k for k in cat if cat[k] == "SCRIPT_SPECIFIC_UPSIDE"]
    reason = (
        None
        if robust
        else "edges at the current price exist but none is supported across material scripts "
        "(ROBUST / VERY_ROBUST)"
    )
    return (
        SlateFixtureScriptsV1(
            **base,
            robust_edges=robust,
            mixed_edges=mixed,
            script_specific_edges=specific,
            thesis_groups=groups,
            best_robust_expression=robust[0] if robust else None,
            best_script_specific_expression=specific[0] if specific else None,
            no_compelling_edge=not robust,
            no_compelling_edge_reason=reason,
        ),
        out,
    )
