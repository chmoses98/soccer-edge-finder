"""LIMITED mode configuration (remediation phase 24; audit §M). Loaded, validated, and DISABLED.

`LimitedModeConfig.load()` parses `config/limited_mode.json`. `assert_disabled()` is called by the run
pipeline's authority path and by `tests/test_frozen_config.py`: while every family is RESEARCH_ONLY the
file must say `enabled: false`, and nothing here grants a staking authority even when it would say true —
the gates below are the *design* that a future owner-approved cell would have to pass order by order.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PATH = REPO_ROOT / "config" / "limited_mode.json"


class LimitedModeError(Exception):
    pass


@dataclass(frozen=True)
class LimitedModeConfig:
    enabled: bool
    raw: dict[str, Any]

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> LimitedModeConfig:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("schema") != "limited_mode_config_v1":
            raise LimitedModeError("unexpected limited_mode config schema")
        return cls(bool(raw.get("enabled", False)), raw)

    def assert_disabled(self) -> None:
        if self.enabled:
            raise LimitedModeError(
                "config/limited_mode.json says enabled=true; LIMITED mode cannot be enabled while every "
                "family is RESEARCH_ONLY (owner decision + promotion evaluator + authority.json entry required)"
            )

    def order_gate_report(self, candidate: dict[str, Any]) -> dict[str, Any]:
        """Design-only check of one hypothetical order against the §M gates. Never places anything;
        used by tests and the handoff to show what a future LIMITED order would have to satisfy."""
        r = self.raw
        failed: list[str] = []
        if candidate.get("competition_id") not in r["scope"]["competitions"]:
            failed.append("scope:competition")
        if candidate.get("family") in r["scope"]["excluded_families"]:
            failed.append("scope:family_excluded")
        m = candidate.get("minutes_to_kickoff")
        if m is None or not (
            r["timing"]["latest_minutes_before_kickoff"]
            <= m
            <= r["timing"]["earliest_minutes_before_kickoff"]
        ):
            failed.append("timing")
        if candidate.get("reference_quality") != r["reference"]["required_quality"]:
            failed.append("reference:quality")
        age = candidate.get("reference_age_minutes")
        if age is None or age > r["reference"]["max_age_minutes"]:
            failed.append("reference:age")
        if (
            abs((candidate.get("p_model") or 0) - (candidate.get("p_ref") or 0))
            > r["reference"]["max_model_reference_disagreement"]
        ):
            failed.append("reference:disagreement")
        price = candidate.get("price")
        if price is None or not (r["price"]["min"] <= price <= r["price"]["max"]):
            failed.append("price:range")
        if (candidate.get("spread") or 1) > r["price"]["max_spread"]:
            failed.append("price:spread")
        if (candidate.get("depth") or 0) < r["liquidity"]["min_depth_multiple_of_order"] * (
            candidate.get("order_size") or 1
        ):
            failed.append("liquidity:depth")
        if (candidate.get("expected_net_ev") or 0) < r["edge"]["min_expected_net_ev"] or (
            candidate.get("ev_lower") or 0
        ) < r["edge"]["min_ev_lower"]:
            failed.append("edge")
        if (candidate.get("sigma_edge") or 1) > r["edge"]["max_sigma_edge"]:
            failed.append("edge:sigma")
        return {
            "would_pass_gates": not failed,
            "failed": failed,
            "enabled": self.enabled,
            "authority_granted": False,
        }
