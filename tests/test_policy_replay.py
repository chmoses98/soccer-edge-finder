from __future__ import annotations

from soccer_edge.policy.replay import replay
from soccer_edge.policy.versions import SELECTION_V1, SELECTION_VARIANTS, SelectionPolicy


def _edge(price, fee_adj, p_pos, worst, fee="0.0175"):
    return {
        "price": price,
        "fee_adjusted_edge": fee_adj,
        "p_edge_positive": p_pos,
        "worst_case_edge": worst,
        "fee_per_contract": fee,
    }


def _rec(rid, fam, yes=None, no=None, phash="h1"):
    return {
        "record_id": rid,
        "family": fam,
        "model_family": "data_only.world_sim_v1",
        "parameter_hash": phash,
        "market": {"yes_ask_size": "50", "no_ask_size": "0"},
        "edge": {"yes": yes, "no": no},
    }


def test_selection_v1_matches_production_thresholds():
    ok, why = SELECTION_V1.selects(
        _edge("0.40", 0.03, 0.85, 0.01), family="total_goals", horizon="T-6h", liquidity=10
    )
    assert ok and why == []
    ok, why = SELECTION_V1.selects(
        _edge("0.40", 0.01, 0.85, 0.01), family="total_goals", horizon="T-6h", liquidity=10
    )
    assert not ok and why == ["fee_adjusted_edge_below_min"]
    ok, why = SELECTION_V1.selects(
        _edge("0.40", 0.03, 0.70, -0.01), family="total_goals", horizon="T-6h", liquidity=10
    )
    assert set(why) == {"p_edge_positive_below_min", "worst_case_not_positive"}
    assert (
        SELECTION_V1.policy_hash()
        == SelectionPolicy(
            version="selection_v1", description=SELECTION_V1.description
        ).policy_hash()
    )
    assert len({p.version for p in SELECTION_VARIANTS}) == len(SELECTION_VARIANTS)


def test_replay_flat_unit_accounting_and_attribution():
    recs = [
        _rec("r1", "total_goals", yes=_edge("0.40", 0.03, 0.9, 0.01)),  # selected, wins
        _rec("r2", "total_goals", yes=_edge("0.40", 0.03, 0.9, 0.01)),  # selected, loses
        _rec("r3", "match_result_3way", no=_edge("0.60", 0.05, 0.95, 0.02)),  # selected NO, void
        _rec(
            "r4", "match_result_3way", yes=_edge("0.80", 0.03, 0.9, 0.01)
        ),  # v1 selects; no_favourites rejects
        _rec("r5", "total_goals", yes=_edge("0.40", 0.005, 0.5, -0.1)),  # rejected
    ]
    sett = {
        "r1": {
            "outcome": "yes",
            "horizon": "T-6h",
            "clv": {"yes": {"clv_probability_points": 0.02}},
        },
        "r2": {
            "outcome": "no",
            "horizon": "T-6h",
            "clv": {"yes": {"clv_probability_points": -0.01}},
        },
        "r3": {"outcome": "void", "horizon": "T-24h"},
        # r4 unsettled
    }
    out = replay(recs, sett, SELECTION_VARIANTS)
    v1 = out["policies"]["selection_v1"]["total"]
    assert v1["n_candidates"] == 5 and v1["n_selected"] == 4 and v1["n_settled"] == 3
    assert v1["n_won"] == 1 and v1["n_void"] == 1 and v1["hit_rate"] == 0.5
    # win: 1 - 0.40 - 0.0175 = 0.5825 ; loss: -(0.4175) ; void: 0
    assert abs(v1["pnl_units"] - (0.5825 - 0.4175)) < 1e-9
    assert abs(v1["roi"] - (0.165 / 0.835)) < 1e-4
    assert v1["clv_n"] == 2 and abs(v1["clv_mean_prob_points"] - 0.005) < 1e-9
    assert v1["rejection_reasons"] == {
        "fee_adjusted_edge_below_min": 1,
        "p_edge_positive_below_min": 1,
        "worst_case_not_positive": 1,
    }
    nf = out["policies"]["selection_v1_no_favourites"]["total"]
    assert nf["n_selected"] == 3 and nf["rejection_reasons"]["price_above_max"] == 1
    tot = out["policies"]["selection_v1_totals_only"]["total"]
    assert tot["n_selected"] == 2
    assert out["model"] == {"families": ["data_only.world_sim_v1"], "parameter_hash_count": 1}
    assert out["staking"]["mode"] == "DISABLED"
    assert set(out["policies"]["selection_v1"]["by_family_horizon"]) == {
        "total_goals|T-6h",
        "match_result_3way|T-24h",
        "match_result_3way|?",
        "total_goals|?",
    }
