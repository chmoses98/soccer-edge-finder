"""Explicit, versioned separation of the three decision layers.

MODEL     -> probabilities (MODEL_FAMILY_ID / parameter_hash on every prediction record)
SELECTION -> which (ticker, side) become candidates (thresholds on the archived edge assessment)
STAKING   -> how much (DISABLED everywhere; replay reports flat-unit outcomes only)

A prediction record archives the full EdgeAssessment for both sides, so *any* selection policy can
be replayed against the archive without re-simulating and without touching historical records.
Policies are frozen dataclasses with a version string and a content hash so results are attributable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SelectionPolicy:
    version: str
    min_fee_adjusted_edge: float = 0.02
    min_p_edge_positive: float = 0.80
    require_worst_case_positive: bool = True
    min_liquidity_contracts: float = 0.0
    families: tuple[str, ...] = ()  # empty = all families
    horizons: tuple[str, ...] = ()  # empty = all horizons
    max_price: float | None = None  # skip heavy favourites (fee drag), None = no cap
    min_price: float | None = None
    description: str = ""

    def policy_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

    def selects(
        self, edge: dict[str, Any], *, family: str, horizon: str, liquidity: float
    ) -> tuple[bool, list[str]]:
        """Apply the policy to one archived edge assessment (EdgeAssessment.to_json shape)."""
        reasons: list[str] = []
        if self.families and family not in self.families:
            reasons.append("family_excluded")
        if self.horizons and horizon not in self.horizons:
            reasons.append("horizon_excluded")
        if edge.get("fee_adjusted_edge") is None:
            return False, ["no_edge_assessment"]
        if edge["fee_adjusted_edge"] < self.min_fee_adjusted_edge:
            reasons.append("fee_adjusted_edge_below_min")
        if edge.get("p_edge_positive", 0.0) < self.min_p_edge_positive:
            reasons.append("p_edge_positive_below_min")
        if self.require_worst_case_positive and edge.get("worst_case_edge", -1.0) <= 0:
            reasons.append("worst_case_not_positive")
        if liquidity < self.min_liquidity_contracts:
            reasons.append("liquidity_below_min")
        price = float(edge["price"]) if edge.get("price") is not None else None
        if price is not None and self.max_price is not None and price > self.max_price:
            reasons.append("price_above_max")
        if price is not None and self.min_price is not None and price < self.min_price:
            reasons.append("price_below_min")
        return (not reasons), reasons


@dataclass(frozen=True)
class StakingPolicy:
    version: str
    mode: str = "DISABLED"  # DISABLED | FLAT_UNIT (replay accounting only) — never sizes real money
    unit_contracts: int = 1
    description: str = ""

    def policy_hash(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()[:16]


# The production selection as shipped in Mission 1 (EdgeConfig defaults + robust_positive_ev),
# frozen here as the benchmark selection policy. Changing production thresholds means a NEW version.
SELECTION_V1 = SelectionPolicy(
    version="selection_v1",
    min_fee_adjusted_edge=0.02,
    min_p_edge_positive=0.80,
    require_worst_case_positive=True,
    description="Mission-1 production: fee-adjusted edge >= 2pt, P(edge>0) >= 0.80, worst-case > 0",
)

# Research variants (RESEARCH_ONLY; replayed, never promoted here)
SELECTION_VARIANTS: tuple[SelectionPolicy, ...] = (
    SELECTION_V1,
    SelectionPolicy(
        version="selection_v1_strict",
        min_fee_adjusted_edge=0.04,
        min_p_edge_positive=0.90,
        description="stricter thresholds",
    ),
    SelectionPolicy(
        version="selection_v1_loose",
        min_fee_adjusted_edge=0.01,
        min_p_edge_positive=0.60,
        require_worst_case_positive=False,
        description="looser thresholds (diagnostic only)",
    ),
    SelectionPolicy(
        version="selection_v1_no_favourites",
        max_price=0.70,
        description="v1 plus skip prices above 0.70 (fee drag)",
    ),
    SelectionPolicy(
        version="selection_v1_totals_only",
        families=("total_goals",),
        description="v1 restricted to total goals",
    ),
    SelectionPolicy(
        version="selection_v1_3way_only",
        families=("match_result_3way",),
        description="v1 restricted to 3-way result",
    ),
)

STAKING_DISABLED = StakingPolicy(
    version="staking_disabled_v1",
    mode="DISABLED",
    description="no sizing; replay reports flat 1-contract outcomes for comparison only",
)
