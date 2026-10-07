"""Price-time script survivability: cached P(contract | script) x the CURRENT executable price and verified fee.

Pure arithmetic over the model board; no simulation, no model. For one contract side with break-even b (ask +
fee per contract, `pricing/edge.assess`) and script conditionals p_S (YES: p_S, NO: 1 - p_S):

    conditional edge   e_S = p_S - b
    overall edge       e   = sum_S share_S * e_S          (= P(side) - b on the script basis, exact)
    contribution       c_S = share_S * e_S                 (sum_S c_S = e)
    material script    share_S >= 1 / (2 K)               (taxonomy.MATERIAL_SHARE_RULE)
    stance             SUPPORTS if e_S >= +band, OPPOSES if e_S <= -band, else NEUTRAL (band = 0.02)
    weighted support   sum of material SUPPORTS shares / sum of material shares
    edge concentration largest positive c_S / sum of positive c_S (1.0 = all value in one script)
    edge ex top script (e - c_top) / (1 - share_top): the edge left in the worlds outside the single most
                       valuable script (renormalised); published as a component, not a label rule:
                       scripts are outcome-defined, so for a moneyline-type side the script it always
                       wins carries most of the value by construction
    counter-case       the material script with the most negative contribution

Labels (first rule that matches; descriptive, never a bet signal):
    NO_EDGE           e <= 0
    SCRIPT_DEPENDENT  at most one material script supports the side (the value needs one specific game)
    VERY_ROBUST       weighted support >= 0.80 and >= 3 supporting material scripts
    ROBUST            weighted support >= 0.60
    MIXED             weighted support >= 0.35
    FRAGILE           otherwise (positive, but most material worlds do not support it)
Category: VERY_ROBUST/ROBUST -> ROBUST_ACROSS_SCRIPTS; SCRIPT_DEPENDENT/FRAGILE -> SCRIPT_SPECIFIC_UPSIDE;
MIXED -> MIXED; NO_EDGE -> NO_EDGE.
"""

from __future__ import annotations

from typing import Any

from soccer_edge.gamescript.taxonomy import MATERIAL_SHARE_MIN, SCRIPT_IDS, SCRIPTS

SURVIVABILITY_VERSION = "script_survivability_v1"
SUPPORT_BAND = 0.02
VERY_ROBUST_SUPPORT = 0.80
VERY_ROBUST_MIN_SCRIPTS = 3
ROBUST_SUPPORT = 0.60
MIXED_SUPPORT = 0.35
CATEGORY = {
    "VERY_ROBUST": "ROBUST_ACROSS_SCRIPTS",
    "ROBUST": "ROBUST_ACROSS_SCRIPTS",
    "MIXED": "MIXED",
    "FRAGILE": "SCRIPT_SPECIFIC_UPSIDE",
    "SCRIPT_DEPENDENT": "SCRIPT_SPECIFIC_UPSIDE",
    "NO_EDGE": "NO_EDGE",
}
TITLE = {s.script_id: s.title for s in SCRIPTS}

RULES = {
    "version": SURVIVABILITY_VERSION,
    "conditional_edge": "p(side | script) - break_even, break_even = executable ask + Kalshi fee per contract",
    "material": f"simulation_share >= {MATERIAL_SHARE_MIN:.6f} (1 / (2 x 6 scripts))",
    "stance_band": SUPPORT_BAND,
    "stance": "SUPPORTS if conditional edge >= +band; OPPOSES if <= -band; NEUTRAL otherwise; "
    "IMMATERIAL below the material share",
    "weighted_support_share": "sum of SUPPORTS material shares / sum of material shares",
    "edge_concentration": "largest positive share x edge contribution / sum of positive contributions",
    "edge_ex_top_script": "(overall edge - top contribution) / (1 - top script share)",
    "labels": [
        "NO_EDGE: overall edge <= 0",
        "SCRIPT_DEPENDENT: at most one supporting material script",
        f"VERY_ROBUST: weighted support >= {VERY_ROBUST_SUPPORT} and >= {VERY_ROBUST_MIN_SCRIPTS} supporting",
        f"ROBUST: weighted support >= {ROBUST_SUPPORT}",
        f"MIXED: weighted support >= {MIXED_SUPPORT}",
        "FRAGILE: otherwise",
    ],
    "counter_case": "material script with the most negative share x edge contribution",
}


def _r(x: float | None, d: int = 4) -> float | None:
    return None if x is None else round(float(x), d)


def side_conditionals(sp: list[float | None], side: str) -> list[float | None]:
    return [None if p is None else (p if side == "yes" else 1.0 - p) for p in sp]


def survivability(
    shares: list[float],
    p_side: list[float | None],
    breakeven: float,
    *,
    description: str = "",
) -> dict[str, Any]:
    """Transparent survivability components for one contract side at break-even `breakeven`."""
    K = len(shares)
    edges: list[float | None] = [None if p is None else p - breakeven for p in p_side]
    contrib = [0.0 if e is None else shares[i] * e for i, e in enumerate(edges)]
    overall = sum(contrib)
    stance: list[str] = []
    mat_share = sup_share = opp_share = 0.0
    n_mat = n_sup = n_opp = n_neu = 0
    for i, e in enumerate(edges):
        if shares[i] < MATERIAL_SHARE_MIN - 1e-12 or e is None:
            stance.append("IMMATERIAL")
            continue
        n_mat += 1
        mat_share += shares[i]
        if e >= SUPPORT_BAND:
            stance.append("SUPPORTS")
            n_sup += 1
            sup_share += shares[i]
        elif e <= -SUPPORT_BAND:
            stance.append("OPPOSES")
            n_opp += 1
            opp_share += shares[i]
        else:
            stance.append("NEUTRAL")
            n_neu += 1
    w_sup = sup_share / mat_share if mat_share > 0 else 0.0
    pos = [(c, i) for i, c in enumerate(contrib) if c > 0]
    pos_total = sum(c for c, _ in pos)
    top_c, top_i = max(pos) if pos else (0.0, None)
    concentration = top_c / pos_total if pos_total > 0 else None
    if top_i is not None and shares[top_i] < 1.0:
        ex_top = (overall - top_c) / (1.0 - shares[top_i])
    else:
        ex_top = None
    material_idx = [i for i in range(K) if stance[i] != "IMMATERIAL"]
    worst_i = min(material_idx, key=lambda i: edges[i]) if material_idx else None  # type: ignore[arg-type,return-value]
    if overall <= 0:
        label = "NO_EDGE"
    elif n_sup <= 1:
        label = "SCRIPT_DEPENDENT"
    elif w_sup >= VERY_ROBUST_SUPPORT and n_sup >= VERY_ROBUST_MIN_SCRIPTS:
        label = "VERY_ROBUST"
    elif w_sup >= ROBUST_SUPPORT:
        label = "ROBUST"
    elif w_sup >= MIXED_SUPPORT:
        label = "MIXED"
    else:
        label = "FRAGILE"
    out: dict[str, Any] = {
        "label": label,
        "category": CATEGORY[label],
        "overall_edge": _r(overall),
        "conditional_edges": [_r(e) for e in edges],
        "stance": stance,
        "material_scripts": n_mat,
        "supporting_scripts": n_sup,
        "opposing_scripts": n_opp,
        "neutral_scripts": n_neu,
        "weighted_support_share": _r(w_sup),
        "weighted_oppose_share": _r(opp_share / mat_share if mat_share > 0 else 0.0),
        "worst_material_script": None
        if worst_i is None
        else {"script": SCRIPT_IDS[worst_i], "edge": _r(edges[worst_i])},
        "edge_concentration": _r(concentration),
        "edge_ex_top_script": _r(ex_top),
        "strongest_support": None
        if top_i is None
        else {
            "script": SCRIPT_IDS[top_i],
            "share": _r(shares[top_i]),
            "p": _r(p_side[top_i]),
            "edge": _r(edges[top_i]),
            "contribution": _r(top_c, 5),
        },
        "counter_case": counter_case(
            shares, p_side, edges, contrib, stance, breakeven, description
        ),
    }
    return out


def counter_case(  # noqa: PLR0917
    shares: list[float],
    p_side: list[float | None],
    edges: list[float | None],
    contrib: list[float],
    stance: list[str],
    breakeven: float,
    description: str,
) -> dict[str, Any] | None:
    mat = [i for i, s in enumerate(stance) if s != "IMMATERIAL"]
    if not mat:
        return None
    i = min(mat, key=lambda j: contrib[j])
    p, e = p_side[i], edges[i]
    assert p is not None and e is not None
    if stance[i] != "OPPOSES":
        reason = "NO_MATERIAL_OPPOSITION"
    elif p <= 1e-9:
        reason = "SCRIPT_SETTLES_AGAINST"
    else:
        reason = "BELOW_BREAKEVEN"
    sid = SCRIPT_IDS[i]
    what = description or "this side"
    statement = (
        f"{TITLE[sid]} is {shares[i]:.0%} of simulations and prices {what} at {p:.0%} conditional fair "
        f"probability against a {breakeven:.0%} break-even."
    )
    if reason == "NO_MATERIAL_OPPOSITION":
        statement = f"No material script prices {what} below break-even; the weakest is {TITLE[sid]} ({p:.0%})."
    return {
        "script": sid,
        "share": _r(shares[i]),
        "p": _r(p),
        "edge": _r(e),
        "contribution": _r(contrib[i], 5),
        "reason_code": reason,
        "statement": statement,
    }
