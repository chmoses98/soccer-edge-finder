"""Frozen baseline guard: the default StrengthConfig must match the frozen v1 values.
Changing the model means adding strength_config_v2, not editing v1."""

from __future__ import annotations

import json
from pathlib import Path

from soccer_edge.model.strength import StrengthConfig

REPO = Path(__file__).resolve().parents[1]


def test_default_strength_config_matches_frozen_v1():
    frozen = json.loads((REPO / "config" / "frozen_baselines.json").read_text())[
        "strength_config_v1"
    ]
    cfg = StrengthConfig()
    for k, v in frozen.items():
        assert getattr(cfg, k) == v, (
            f"{k} drifted from frozen v1 ({getattr(cfg, k)} != {v}); add a v2 entry instead"
        )


def test_authority_config_is_all_research_only():
    auth = json.loads((REPO / "config" / "authority.json").read_text())
    assert auth["default"] == "RESEARCH_ONLY"
    assert all(v == "RESEARCH_ONLY" for v in auth.get("entries", {}).values()), (
        "promotion requires documented prospective evidence"
    )
