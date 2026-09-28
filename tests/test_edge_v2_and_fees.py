"""edge_v2 (phase 9), retail fee model (phase 10), selection v2, move_v1 core (phase 11)."""

from __future__ import annotations

from decimal import Decimal

import numpy as np
import pytest

from soccer_edge.kalshi.executable import ExecutableQuote
from soccer_edge.kalshi.fees import (
    RETAIL_FEE_VERIFICATION,
    FeeRegime,
    RetailFeeModel,
    fee_per_contract,
    retail_breakeven,
    retail_fee,
    retail_fee_per_contract,
    walk_fill_cost,
)
from soccer_edge.policy.versions import SELECTION_V1, SELECTION_V2, SELECTION_VARIANTS
from soccer_edge.pricing.edge_v2 import EdgeV2Config, assess_v2

R = FeeRegime("quadratic")
RM = FeeRegime("quadratic_with_maker_fees")


# ------------------------------------------------------------------ retail fee model


@pytest.mark.parametrize(
    "price,contracts,expected_total",
    [
        ("0.05", 1, "0.01"),  # raw 0.003325 -> next cent
        ("0.40", 1, "0.02"),  # raw 0.0168
        ("0.50", 1, "0.02"),  # raw 0.0175
        ("0.99", 1, "0.01"),  # raw 0.000693
        ("0.50", 10, "0.18"),  # raw 0.175 -> 0.18 (per-fill ceiling, not 10 x 0.02)
        ("0.50", 100, "1.75"),  # raw 1.75 exactly: boundary, no rounding up
        ("0.50", 101, "1.77"),  # raw 1.7675 -> 1.77
        ("0.95", 20, "0.07"),  # raw 0.0665 -> 0.07
        ("0.30", 3, "0.05"),  # raw 0.0441 -> 0.05
    ],
)
def test_retail_fee_cent_ceiling_table(price, contracts, expected_total):
    assert retail_fee(Decimal(price), contracts, R) == Decimal(expected_total)


def test_retail_vs_quantum_and_yes_no_symmetry():
    # YES at p and NO at 1-p pay the same fee (symmetric p(1-p)); the retail per-contract fee is never
    # below the quantum one and differs by at most one cent per contract
    for p in ("0.05", "0.20", "0.50", "0.80", "0.95"):
        yes = retail_fee_per_contract(Decimal(p), R)
        no = retail_fee_per_contract(Decimal(1) - Decimal(p), R)
        assert yes == no
        q = fee_per_contract(Decimal(p), R)
        assert q <= yes <= q + Decimal("0.01")
    assert retail_fee(
        Decimal("0.50"), 1, R, model=RetailFeeModel.QUANTUM_MICRO
    ) == fee_per_contract(Decimal("0.50"), R)
    assert RETAIL_FEE_VERIFICATION == "VERIFIED_FROM_DOCUMENTATION_NOT_FILL_RECONCILED"


def test_retail_breakeven_and_maker():
    assert retail_breakeven(Decimal("0.05"), R) == Decimal("0.06")
    assert retail_breakeven(Decimal("0.50"), R, contracts=10) == Decimal("0.518")
    assert retail_fee(Decimal("0.50"), 1, R, maker=True) == 0
    assert retail_fee(Decimal("0.50"), 10, RM, maker=True) == Decimal(
        "0.05"
    )  # 0.0175*10*0.25=0.04375
    with pytest.raises(ValueError):
        retail_fee(Decimal("0.50"), 0, R)
    with pytest.raises(ValueError):
        retail_fee(Decimal("1.00"), 1, R)


def test_order_book_walk_across_levels_charges_fee_per_fill():
    c = walk_fill_cost([(Decimal("0.40"), 5), (Decimal("0.41"), 3), (Decimal("0.43"), 2)], R)
    assert c["contracts"] == 10 and c["vwap"] == Decimal("0.409")
    # per-fill: 0.084->0.09, 0.0508->0.06, 0.0343->0.04 = 0.19 (a single 10-lot at the VWAP would be 0.17)
    assert c["fee"] == Decimal("0.19") and c["breakeven"] == Decimal("0.428")
    single = retail_fee(Decimal("0.409"), 10, R)
    assert c["fee"] > single


# ------------------------------------------------------------------ edge_v2


def _q(price="0.45", vwap=None, source="top_of_book"):
    return ExecutableQuote(
        "T",
        "yes",
        Decimal(price),
        Decimal(10),
        source,
        vwap_for_size=Decimal(vwap) if vwap else None,
    )


def test_edge_v2_not_evaluated_without_fresh_reference_or_quote():
    a = assess_v2(
        ticker="T",
        side="yes",
        family="match_result_3way",
        p_model=0.55,
        p_ref=None,
        reference_quality="UNAVAILABLE",
        reference_age_minutes=None,
        quote=_q(),
        regime=R,
    )
    assert a.status == "NOT_EVALUATED" and "no reference" in a.reason and not a.candidate
    a = assess_v2(
        ticker="T",
        side="yes",
        family="match_result_3way",
        p_model=0.55,
        p_ref=0.5,
        reference_quality="SECONDARY_REFERENCE",
        reference_age_minutes=16,
        quote=_q(),
        regime=R,
    )
    assert a.status == "NOT_EVALUATED" and "age" in a.reason
    a = assess_v2(
        ticker="T",
        side="yes",
        family="match_result_3way",
        p_model=0.55,
        p_ref=0.5,
        reference_quality="SECONDARY_REFERENCE",
        reference_age_minutes=5,
        quote=ExecutableQuote("T", "yes", Decimal("0"), None, "none"),
        regime=R,
    )
    assert a.status == "NOT_EVALUATED" and "quote" in a.reason


def test_edge_v2_definition_with_w_zero_is_reference_minus_retail_breakeven():
    a = assess_v2(
        ticker="T",
        side="yes",
        family="match_result_3way",
        p_model=0.70,
        p_ref=0.50,
        reference_quality="SHARP_REFERENCE",
        reference_age_minutes=5,
        quote=_q("0.45"),
        regime=R,
    )
    assert (
        a.status == "EVALUATED" and a.w_family == 0.0 and a.p_star == 0.50
    )  # model ignored at w=0
    assert a.entry_cost == pytest.approx(0.47)  # 0.45 + 2c retail fee
    assert a.expected_net_ev == pytest.approx(0.03)
    assert a.reference_anchored is True
    assert a.sigma_edge == pytest.approx((0.01**2 + (0.0004 * 5) ** 2) ** 0.5)
    assert a.ev_lower == pytest.approx(0.03 - 1.645 * a.sigma_edge)
    assert a.candidate is True  # EV 0.03 >= 0.02 and lower ~0.013 >= 0.01
    j = a.to_json()
    assert j["entry_price"] == "0.45" and j["retail_fee_per_contract"] == "0.02"


def test_edge_v2_uses_vwap_when_present_and_secondary_is_not_anchored():
    a = assess_v2(
        ticker="T",
        side="yes",
        family="match_result_3way",
        p_model=None,
        p_ref=0.60,
        reference_quality="SECONDARY_REFERENCE",
        reference_age_minutes=2,
        quote=_q("0.45", vwap="0.47"),
        regime=R,
        target_contracts=10,
    )
    assert a.entry_price == Decimal("0.47") and a.entry_price_source == "book_walk"
    assert a.reference_anchored is False and a.p_star == 0.60


def test_edge_v2_lower_bound_monotone_in_sigma_and_w_blends():
    base = dict(
        ticker="T",
        side="no",
        family="total_goals",
        p_model=0.60,
        p_ref=0.50,
        reference_quality="SHARP_REFERENCE",
        reference_age_minutes=10,
        quote=_q("0.40"),
        regime=R,
    )
    lows = [assess_v2(**base, sigma_devig=s).ev_lower for s in (0.0, 0.01, 0.02, 0.05)]
    assert lows == sorted(lows, reverse=True)
    cfg = EdgeV2Config(w_family={"total_goals": 0.5}, sigma_struct={"total_goals": 0.04})
    b = assess_v2(**base, cfg=cfg)
    assert b.p_star == pytest.approx(0.55) and b.sigma_struct == 0.04 and b.w_family == 0.5
    assert b.sigma_edge > assess_v2(**base).sigma_edge


# ------------------------------------------------------------------ selection v2


def test_selection_v2_drops_p_edge_positive_criterion():
    edge = {
        "fee_adjusted_edge": 0.03,
        "p_edge_positive": 0.5,
        "worst_case_edge": 0.01,
        "price": "0.40",
    }
    assert SELECTION_V1.selects(edge, family="f", horizon="h", liquidity=10)[0] is False
    assert SELECTION_V2.selects(edge, family="f", horizon="h", liquidity=10)[0] is True
    edge_bad = {**edge, "worst_case_edge": -0.01}
    assert SELECTION_V2.selects(edge_bad, family="f", horizon="h", liquidity=10)[0] is False
    assert SELECTION_V2 in SELECTION_VARIANTS and SELECTION_V2.version == "selection_v2"


# ------------------------------------------------------------------ move_v1 core


def test_move_v1_recovers_beta_on_synthetic_data():
    from research.move_v1 import analyse_family, devig_power

    rng = np.random.default_rng(3)
    n = 3000
    p_open = rng.uniform(0.2, 0.7, n)
    x = rng.normal(0, 0.2, n)  # logit gap model - open
    p_model = 1 / (1 + np.exp(-(np.log(p_open / (1 - p_open)) + x)))
    true_beta = 0.4
    y_logit = np.log(p_open / (1 - p_open)) + true_beta * x + rng.normal(0, 0.05, n)
    p_close = 1 / (1 + np.exp(-y_logit))
    outcomes = (rng.uniform(size=n) < p_close).astype(float)
    clusters = np.repeat(np.arange(n // 5), 5)
    seasons = np.repeat(np.array(["2019-20", "2020-21", "2021-22"]), n // 3)
    leagues = np.array(["E0"] * n)
    r = analyse_family(p_open, p_close, p_model, outcomes, clusters, seasons, leagues, n_boot=100)
    assert abs(r["beta"] - true_beta) < 0.06 and r["beta_ci95"][0] > 0
    assert r["directional_accuracy"] > 0.8 and r["predicts_movement"] is True
    assert r["ll_close"] < r["ll_open"]
    # and a null: close = open + noise -> beta ~ 0, verdict False
    p_close0 = 1 / (1 + np.exp(-(np.log(p_open / (1 - p_open)) + rng.normal(0, 0.05, n))))
    r0 = analyse_family(p_open, p_close0, p_model, outcomes, clusters, seasons, leagues, n_boot=100)
    assert abs(r0["beta"]) < 0.05 and r0["predicts_movement"] is False
    # power de-vig sums to one and removes the overround
    p = devig_power(np.array([[1.9, 3.6, 4.2], [1.3, 5.0, 10.0]]))
    assert np.allclose(p.sum(axis=1), 1) and p[0, 0] < 1 / 1.9
