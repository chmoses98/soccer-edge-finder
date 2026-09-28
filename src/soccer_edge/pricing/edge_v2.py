"""edge_v2: reference-anchored, fee-aware, uncertainty-adjusted expected value (remediation phase 9; audit §G).

Retires `P(edge > 0)` from selection. That quantity is the share of the model's own posterior worlds in
which the model beats the price: it measures model-vs-price distance in units of the model's own
dispersion and, against a sharper market, ranks the model's largest errors first (audit B11). It survives
only as the diagnostic `model_posterior_edge_share`.

Definition (per contract side, per $1 contract):

    entry_cost      = executable price for the target size (order-book walk / VWAP when a book is
                      available, else top of book) + cent-rounded retail fee per contract
    p_ref           = de-vigged reference probability for the same contract and side
                      (SHARP_REFERENCE when available; else the best SECONDARY quote, flagged)
    p_star          = p_ref + w_family * (p_model - p_ref)         w_family = 0 until evidence justifies it
    expected_net_ev = p_star - entry_cost
    sigma_edge^2    = sigma_devig^2 + sigma_stale^2 + w_family^2 * sigma_struct^2(family)
    ev_lower        = expected_net_ev - 1.645 * sigma_edge

Research candidate rule (archived, NEVER a betting authority):
    candidate  iff  expected_net_ev >= 0.02  and  ev_lower >= 0.01

Status: `EVALUATED` when a reference exists and is fresh (<= max_reference_age_minutes), else
`NOT_EVALUATED` with the reason. `reference_anchored` is True only when the reference is SHARP.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from soccer_edge.kalshi.executable import ExecutableQuote
from soccer_edge.kalshi.fees import FeeRegime, RetailFeeModel, retail_breakeven

Z_90_ONE_SIDED = 1.645


@dataclass(frozen=True)
class EdgeV2Config:
    version: str = "edge_v2"
    min_expected_net_ev: float = 0.02
    min_ev_lower: float = 0.01
    z: float = Z_90_ONE_SIDED
    max_reference_age_minutes: float = 15.0
    # model weight per market family; 0 = pure reference (audit §G: today w = 0 ⇒ p* = p_ref)
    w_family: dict[str, float] | None = None
    # structural model error (logit-free probability points) per family, used only with w > 0
    sigma_struct: dict[str, float] | None = None
    # de-vig method dispersion (probability points); refined by the reference pipeline when several
    # de-vig methods / books are available, else this prior
    sigma_devig_default: float = 0.010
    # reference staleness drift per minute (probability points/min): 15 min -> ~0.6 pt
    stale_drift_per_minute: float = 0.0004
    retail_fee_model: str = RetailFeeModel.DOCUMENTED_CENT_CEILING.value


@dataclass(frozen=True)
class EdgeV2Assessment:
    ticker: str
    side: str
    status: str  # EVALUATED | NOT_EVALUATED
    reason: str
    entry_price: Decimal | None
    entry_price_source: str
    target_contracts: int
    retail_fee_per_contract: Decimal | None
    entry_cost: float | None  # entry break-even in probability points
    p_model: float | None
    p_ref: float | None
    reference_quality: str
    reference_age_minutes: float | None
    reference_anchored: bool
    w_family: float
    p_star: float | None
    expected_net_ev: float | None
    sigma_devig: float | None
    sigma_stale: float | None
    sigma_struct: float | None
    sigma_edge: float | None
    ev_lower: float | None
    candidate: bool
    config_version: str

    def to_json(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        for k in ("entry_price", "retail_fee_per_contract"):
            d[k] = str(d[k]) if d[k] is not None else None
        return d


def _not_evaluated(
    ticker: str, side: str, reason: str, cfg: EdgeV2Config, *, p_model: float | None, quality: str
) -> EdgeV2Assessment:
    return EdgeV2Assessment(
        ticker=ticker,
        side=side,
        status="NOT_EVALUATED",
        reason=reason,
        entry_price=None,
        entry_price_source="none",
        target_contracts=0,
        retail_fee_per_contract=None,
        entry_cost=None,
        p_model=p_model,
        p_ref=None,
        reference_quality=quality,
        reference_age_minutes=None,
        reference_anchored=False,
        w_family=0.0,
        p_star=None,
        expected_net_ev=None,
        sigma_devig=None,
        sigma_stale=None,
        sigma_struct=None,
        sigma_edge=None,
        ev_lower=None,
        candidate=False,
        config_version=cfg.version,
    )


def assess_v2(
    *,
    ticker: str,
    side: str,
    family: str,
    p_model: float | None,
    p_ref: float | None,
    reference_quality: str,
    reference_age_minutes: float | None,
    quote: ExecutableQuote | None,
    regime: FeeRegime,
    target_contracts: int = 1,
    sigma_devig: float | None = None,
    cfg: EdgeV2Config | None = None,
) -> EdgeV2Assessment:
    """Evaluate one contract side. `p_ref` is already in the bought side's probability."""
    cfg = cfg or EdgeV2Config()
    if p_ref is None:
        return _not_evaluated(
            ticker,
            side,
            "no reference probability for this contract",
            cfg,
            p_model=p_model,
            quality=reference_quality,
        )
    if (
        reference_age_minutes is None
        or reference_age_minutes > cfg.max_reference_age_minutes
        or reference_age_minutes < 0
    ):
        return _not_evaluated(
            ticker,
            side,
            f"reference age {reference_age_minutes} min outside [0, {cfg.max_reference_age_minutes}]",
            cfg,
            p_model=p_model,
            quality=reference_quality,
        )
    if quote is None or not quote.is_quote:
        return _not_evaluated(
            ticker, side, "no executable quote", cfg, p_model=p_model, quality=reference_quality
        )
    price = quote.vwap_for_size if quote.vwap_for_size is not None else quote.price
    source = "book_walk" if quote.vwap_for_size is not None else quote.source
    be = retail_breakeven(
        price,
        regime,
        contracts=max(1, target_contracts),
        model=RetailFeeModel(cfg.retail_fee_model),
    )
    fee = be - price
    w = float((cfg.w_family or {}).get(family, 0.0))
    if w != 0.0 and p_model is None:
        w = 0.0
    p_star = p_ref + w * ((p_model if p_model is not None else p_ref) - p_ref)
    ev = p_star - float(be)
    s_devig = float(sigma_devig) if sigma_devig is not None else cfg.sigma_devig_default
    s_stale = cfg.stale_drift_per_minute * float(reference_age_minutes)
    s_struct = float((cfg.sigma_struct or {}).get(family, 0.0)) if w != 0.0 else 0.0
    sigma = math.sqrt(s_devig**2 + s_stale**2 + (w * s_struct) ** 2)
    lower = ev - cfg.z * sigma
    candidate = ev >= cfg.min_expected_net_ev and lower >= cfg.min_ev_lower
    return EdgeV2Assessment(
        ticker=ticker,
        side=side,
        status="EVALUATED",
        reason="ok",
        entry_price=price,
        entry_price_source=source,
        target_contracts=max(1, target_contracts),
        retail_fee_per_contract=fee,
        entry_cost=float(be),
        p_model=p_model,
        p_ref=p_ref,
        reference_quality=reference_quality,
        reference_age_minutes=float(reference_age_minutes),
        reference_anchored=(reference_quality == "SHARP_REFERENCE"),
        w_family=w,
        p_star=p_star,
        expected_net_ev=ev,
        sigma_devig=s_devig,
        sigma_stale=s_stale,
        sigma_struct=s_struct,
        sigma_edge=sigma,
        ev_lower=lower,
        candidate=candidate,
        config_version=cfg.version,
    )
