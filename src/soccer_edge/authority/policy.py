"""Authority states and promotion policy (docs/RESEARCH_AUTHORITY.md).

Evidence unit = settled prospective contract-predictions with a matching pre-kickoff market
snapshot. Thresholds are written *before* evaluation and are not tuned to results.
Nothing auto-promotes: `recommend_state` produces a proposal that a human applies by editing
config/authority.json (reviewed in a PR).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class Authority(str, Enum):
    RESEARCH_ONLY = "RESEARCH_ONLY"  # never surfaces as a recommendation
    SHADOW = "SHADOW"  # surfaces in shadow output, labelled, no real-money authority
    LIMITED = "LIMITED"  # may be surfaced as a recommendation with reduced confidence label
    TRUSTED = "TRUSTED"


@dataclass(frozen=True)
class PromotionRule:
    to_state: Authority
    min_settled: int
    min_skill_vs_market_logloss: float  # (market_logloss - model_logloss) must be >= this
    min_clv_points: float
    max_ece: float
    require_interval_coverage: (
        tuple[float, float] | None
    )  # acceptable band for 80% interval coverage


PROMOTION_RULES: tuple[PromotionRule, ...] = (
    PromotionRule(
        Authority.SHADOW,
        min_settled=100,
        min_skill_vs_market_logloss=-0.02,
        min_clv_points=-0.01,
        max_ece=0.08,
        require_interval_coverage=None,
    ),
    PromotionRule(
        Authority.LIMITED,
        min_settled=300,
        min_skill_vs_market_logloss=0.0,
        min_clv_points=0.0,
        max_ece=0.05,
        require_interval_coverage=(0.70, 0.90),
    ),
    PromotionRule(
        Authority.TRUSTED,
        min_settled=1000,
        min_skill_vs_market_logloss=0.005,
        min_clv_points=0.005,
        max_ece=0.03,
        require_interval_coverage=(0.75, 0.85),
    ),
)


@dataclass(frozen=True)
class AuthorityKey:
    model_family: str
    market_family: str
    horizon: str  # e.g. 'T-30m' or 'any'

    def as_str(self) -> str:
        return f"{self.model_family}|{self.market_family}|{self.horizon}"


class AuthorityMatrix:
    def __init__(
        self,
        entries: dict[str, Authority] | None = None,
        default: Authority = Authority.RESEARCH_ONLY,
    ) -> None:
        self.entries = entries or {}
        self.default = default

    @classmethod
    def load(cls, path: Path) -> AuthorityMatrix:
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        return cls(
            {k: Authority(v) for k, v in data.get("entries", {}).items()},
            Authority(data.get("default", "RESEARCH_ONLY")),
        )

    def get(self, key: AuthorityKey) -> Authority:
        for k in (
            key.as_str(),
            f"{key.model_family}|{key.market_family}|any",
            f"{key.model_family}|any|any",
        ):
            if k in self.entries:
                return self.entries[k]
        return self.default

    def to_json(self) -> dict[str, Any]:
        return {
            "default": self.default.value,
            "entries": {k: v.value for k, v in sorted(self.entries.items())},
        }


@dataclass(frozen=True)
class Evidence:
    n_settled: int
    model_logloss: float
    market_logloss: float
    clv_points_mean: float
    ece: float
    interval_coverage_80: float | None


def recommend_state(ev: Evidence, current: Authority) -> tuple[Authority, list[str]]:
    """Highest state whose rule is fully met; never above one step from current (no leapfrogging)."""
    order = [Authority.RESEARCH_ONLY, Authority.SHADOW, Authority.LIMITED, Authority.TRUSTED]
    best = Authority.RESEARCH_ONLY
    notes: list[str] = []
    for rule in PROMOTION_RULES:
        ok = True
        if ev.n_settled < rule.min_settled:
            ok = False
            notes.append(f"{rule.to_state.value}: need n>={rule.min_settled}, have {ev.n_settled}")
        skill = ev.market_logloss - ev.model_logloss
        if skill < rule.min_skill_vs_market_logloss:
            ok = False
            notes.append(
                f"{rule.to_state.value}: skill vs market {skill:+.4f} < {rule.min_skill_vs_market_logloss}"
            )
        if ev.clv_points_mean < rule.min_clv_points:
            ok = False
            notes.append(
                f"{rule.to_state.value}: CLV {ev.clv_points_mean:+.4f} < {rule.min_clv_points}"
            )
        if ev.ece > rule.max_ece:
            ok = False
            notes.append(f"{rule.to_state.value}: ECE {ev.ece:.3f} > {rule.max_ece}")
        if rule.require_interval_coverage and (
            ev.interval_coverage_80 is None
            or not (
                rule.require_interval_coverage[0]
                <= ev.interval_coverage_80
                <= rule.require_interval_coverage[1]
            )
        ):
            ok = False
            notes.append(
                f"{rule.to_state.value}: 80% interval coverage {ev.interval_coverage_80} outside {rule.require_interval_coverage}"
            )
        if ok:
            best = rule.to_state
    cur_i = order.index(current)
    best_i = min(order.index(best), cur_i + 1)
    return order[best_i], notes
