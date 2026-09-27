from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from soccer_edge.contracts import APP_CONTRACT_VERSION, RecommendationV1, export_json_schemas


def _rec(**over):
    base = dict(
        recommendation_id="rec_1",
        sport="soccer",
        league="eng.premier_league",
        event_id="fx:1",
        event_name="A vs B",
        start_time=datetime(2026, 10, 10, 14, tzinfo=UTC),
        market_ticker="KXEPLTOTAL-26OCT10BA-3",
        market_family="total_goals",
        market_description="Total goals over 2.5",
        side="yes",
        current_price=Decimal("0.52"),
        fair_probability=0.59,
        fair_probability_low=0.55,
        fair_probability_high=0.63,
        probability_edge_positive=0.94,
        fee_adjusted_edge=0.05,
        worst_case_edge=0.02,
        authority="RESEARCH_ONLY",
        confidence_label="research",
        model_family="data_only.world_sim_v1",
        model_version="dc_laplace_v1",
        data_as_of=datetime(2026, 10, 9, tzinfo=UTC),
        market_as_of=datetime(2026, 10, 10, 13, tzinfo=UTC),
        model_as_of=datetime(2026, 10, 10, 12, tzinfo=UTC),
        lineup_status="unknown",
        coverage_status="complete",
        thesis="t",
        risks=["r"],
        correlation_group="fx:1#g0",
        fee_schedule_version="v1",
    )
    base.update(over)
    return RecommendationV1(**base)


def test_recommendation_serialises_prices_as_strings():
    d = json.loads(_rec().model_dump_json())
    assert d["current_price"] == "0.52" and d["schema_version"] == APP_CONTRACT_VERSION
    assert d["start_time"].endswith("Z")


def test_probabilities_bounded_and_extra_fields_rejected():
    with pytest.raises(ValidationError):
        _rec(fair_probability=1.2)
    with pytest.raises(ValidationError):
        RecommendationV1(**{**_rec().model_dump(), "surprise": 1})


def test_schema_export_is_deterministic(tmp_path):
    a = export_json_schemas(tmp_path / "a")
    b = export_json_schemas(tmp_path / "b")
    assert [p.read_text() for p in a] == [p.read_text() for p in b]
    names = {p.name for p in a}
    assert {
        "RecommendationV1.schema.json",
        "RunOutputV1.schema.json",
        "SettlementV1.schema.json",
        "PositionV1.schema.json",
        "ModelHealthV1.schema.json",
        "EventV1.schema.json",
    } <= names


def test_committed_schemas_match_code(tmp_path):
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    committed = repo / "docs" / "schemas"
    if not committed.exists():
        pytest.skip("schemas not exported yet")
    fresh = export_json_schemas(tmp_path)
    for p in fresh:
        assert (committed / p.name).read_text() == p.read_text(), (
            f"{p.name} drifted: run `soccer export-schemas`"
        )
