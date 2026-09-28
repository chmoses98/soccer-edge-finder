"""Promotion evaluator v2 (phase 23) and LIMITED mode config (phase 24)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from soccer_edge.authority.limited_mode import LimitedModeConfig, LimitedModeError
from soccer_edge.authority.promotion_v2 import (
    VERDICT_ELIGIBLE,
    VERDICT_NOT_ELIGIBLE,
    PromotionGates,
    competition_group,
    evaluate_all,
    horizon_bucket,
)

REPO = Path(__file__).resolve().parents[1]


def _settlement(
    i: int,
    *,
    outcome="yes",
    p=0.6,
    ref_close=0.62,
    kalshi_close=True,
    true_close=True,
    shadow=True,
    fixture=None,
    entry="0.50",
):
    return {
        "schema": "settlement_record_v1",
        "prediction_record_id": f"pred_{i:06d}",
        "ticker": f"T{i}",
        "fixture_id": fixture or f"fx:eng.premier_league:2026-27:a{i}:b{i}",
        "family": "match_result_3way",
        "model_family": "data_only.world_sim_v2",
        "horizon": "T-60m",
        "outcome": outcome,
        "fair_probability_mean": p,
        "fair_probability_low": p - 0.1,
        "fair_probability_high": p + 0.1,
        "entry_yes_ask": entry,
        "entry_no_ask": "0.52",
        "entry_yes_mid": float(entry) - 0.01,
        "reference_probability_at_prediction": 0.58,
        "fee_regime": {"fee_type": "quadratic"},
        "clv": {"yes": {"clv_fee_aware_points": 0.01}, "no": {"clv_fee_aware_points": -0.01}},
        "recommended": {
            "yes": {"shadow": shadow, "recommended": False},
            "no": {"shadow": False, "recommended": False},
        },
        "close_v2": {
            "reference": {
                "close_class": "TRUE_CLOSE" if true_close else "NEAR_CLOSE",
                "probability_yes": ref_close,
                "probability_no": 1 - ref_close,
            },
            "kalshi": {"close_class": "KALSHI_CLOSE" if kalshi_close else "NONE"},
        },
    }


def _pred(i: int):
    return {
        "competition_id": "eng.premier_league",
        "market": {
            "yes_bid": "0.49",
            "yes_ask": "0.50",
            "yes_ask_size": "50",
            "yes_bid_size": "50",
        },
    }


INTEGRITY_OK = {"unaccounted_contracts_max": 0, "manifest_ok": True}


def test_empty_and_small_evidence_is_not_eligible_with_named_gates():
    rep = evaluate_all(
        [_settlement(i) for i in range(20)],
        {f"pred_{i:06d}": _pred(i) for i in range(20)},
        integrity=INTEGRITY_OK,
        as_of="t",
    )
    assert rep["cells_total"] == 1 and rep["eligible_for_owner_review"] == 0
    cell = rep["cells"][0]
    assert cell["verdict"] == VERDICT_NOT_ELIGIBLE
    assert (
        "clv:min_selected_sides" in cell["failed_gates"]
        and "clv:min_fixtures" in cell["failed_gates"]
    )
    assert (
        "reference:no_live_sharp_source" in cell["failed_gates"]
    )  # no free live sharp feed exists today
    assert all(c["verdict"] in (VERDICT_ELIGIBLE, VERDICT_NOT_ELIGIBLE) for c in rep["cells"])
    assert "AUTO_PROMOTE" not in {c["verdict"] for c in rep["cells"]}


def test_evaluator_names_integrity_failures():
    rep = evaluate_all(
        [_settlement(i) for i in range(5)],
        {},
        integrity={"unaccounted_contracts_max": 3, "manifest_ok": False},
        as_of="t",
    )
    fg = rep["cells"][0]["failed_gates"]
    assert "integrity:unaccounted_contracts" in fg and "integrity:archive_manifest" in fg


def test_a_cell_that_meets_every_evidence_gate_is_only_eligible_for_owner_review(monkeypatch):
    # make the reference gate pass hypothetically (a credentialed sharp source), everything else from data
    import soccer_edge.authority.promotion_v2 as pv2

    monkeypatch.setattr(pv2, "live_sharp_reference_available", lambda: (True, "hypothetical"))
    rows, preds = [], {}
    import random

    rng = random.Random(0)
    for i in range(400):
        p = 0.6
        outcome = "yes" if rng.random() < p else "no"
        rows.append(
            _settlement(
                i,
                outcome=outcome,
                p=p,
                ref_close=0.60,
                entry="0.50",
                fixture=f"fx:eng.premier_league:2026-27:h{i // 4}:a{i // 4}",
            )
        )
        preds[f"pred_{i:06d}"] = _pred(i)
    rep = evaluate_all(rows, preds, integrity=INTEGRITY_OK, gates=PromotionGates(), as_of="t")
    cell = rep["cells"][0]
    m = cell["metrics"]
    assert m["selected_sides"] == 400 and m["fixtures"] == 100 and m["true_close_share"] == 1.0
    assert m["mean_ev_close"] == pytest.approx(
        0.60 - 0.5175, abs=1e-6
    )  # p_ref_close - (0.50 + 1.75c fee)
    assert cell["verdict"] in (VERDICT_ELIGIBLE, VERDICT_NOT_ELIGIBLE)
    # whatever the verdict, the evaluator only proposes: authority.json is untouched and there is no auto path
    assert json.loads((REPO / "config" / "authority.json").read_text()) == {
        "default": "RESEARCH_ONLY",
        "entries": {},
    }
    assert rep["note"].startswith("report only")
    if cell["verdict"] == VERDICT_NOT_ELIGIBLE:
        # the remaining failures must be evidence gates, never a hidden switch
        assert all(":" in g for g in cell["failed_gates"])


def test_grouping_helpers():
    assert competition_group("eng.premier_league") == "top5"
    assert competition_group("uefa.nations_league") == "international"
    assert competition_group("usa.mls") == "americas"
    assert (
        horizon_bucket("T-60m") == "near_close"
        and horizon_bucket("T-24h") == "far"
        and horizon_bucket("T-2h") == "same_day"
    )


# ------------------------------------------------------------------ limited mode


def test_limited_mode_is_disabled_and_grants_no_authority():
    cfg = LimitedModeConfig.load()
    assert cfg.enabled is False
    cfg.assert_disabled()
    good = {
        "competition_id": "eng.premier_league",
        "family": "match_result_3way",
        "minutes_to_kickoff": 45,
        "reference_quality": "SHARP_REFERENCE",
        "reference_age_minutes": 5,
        "p_model": 0.55,
        "p_ref": 0.52,
        "price": 0.45,
        "spread": 0.02,
        "depth": 30,
        "order_size": 5,
        "expected_net_ev": 0.03,
        "ev_lower": 0.015,
        "sigma_edge": 0.01,
    }
    r = cfg.order_gate_report(good)
    assert (
        r["would_pass_gates"] is True and r["authority_granted"] is False and r["enabled"] is False
    )
    bad = {
        **good,
        "competition_id": "uefa.nations_league",
        "minutes_to_kickoff": 3,
        "reference_quality": "SECONDARY_REFERENCE",
        "price": 0.90,
        "spread": 0.06,
        "depth": 4,
        "expected_net_ev": 0.01,
    }
    r = cfg.order_gate_report(bad)
    assert set(r["failed"]) >= {
        "scope:competition",
        "timing",
        "reference:quality",
        "price:range",
        "price:spread",
        "liquidity:depth",
        "edge",
    }


def test_enabled_config_is_refused(tmp_path):
    p = tmp_path / "limited_mode.json"
    p.write_text(json.dumps({"schema": "limited_mode_config_v1", "enabled": True}))
    with pytest.raises(LimitedModeError):
        LimitedModeConfig.load(p).assert_disabled()
